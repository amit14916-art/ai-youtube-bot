"""
modules/researcher.py
Finds trending AI topics from Google Trends + YouTube search.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from pytrends.request import TrendReq

from config.settings import (
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    GOOGLE_SEARCH_API_KEY,
    GOOGLE_SEARCH_ENGINE_ID,
    NICHE,
    RESEARCH_TOPICS,
    SCRIPT_WORDS,
    TRENDS_GEO,
    YOUTUBE_API_KEY,
)
from modules.history_manager import get_recent_topics, save_topic_to_history

log = logging.getLogger(__name__)

# Lazy init clients
def get_llm_client(provider: str = None):
    """Return (client, provider_name) for the chosen LLM provider."""
    p = provider or LLM_PROVIDER
    if p == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel(GEMINI_MODEL), "gemini"
    elif p == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), "anthropic"
    elif p == "openai":
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY), "openai"
    else:  # groq
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY), "groq"


# -----------------------------------------------------------------
#  1. GOOGLE TRENDS
# -----------------------------------------------------------------

def get_google_trending_topics() -> list[str]:
    """Pull the top trending AI-related keywords from Google Trends."""
    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        # Seed keywords that anchor us in the AI niche
        seeds = ["ChatGPT", "Gemini AI", "AI tools", "machine learning", "LLM"]
        pytrends.build_payload(seeds[:5], cat=0, timeframe="now 7-d", geo=TRENDS_GEO)
        related = pytrends.related_queries()

        topics: list[str] = []
        for seed in seeds:
            df = related.get(seed, {}).get("top")
            if df is not None and not df.empty:
                topics.extend(df["query"].head(5).tolist())

        # Also grab real-time trending searches
        trending_df = pytrends.trending_searches(pn="united_states")
        rt_trends = trending_df[0].tolist()
        ai_rt = [t for t in rt_trends if any(
            k in t.lower() for k in ["ai", "gpt", "llm", "gemini", "claude", "robot", "neural"]
        )]
        topics.extend(ai_rt[:5])

        unique = list(dict.fromkeys(topics))  # preserve order, remove dupes
        log.info(f"Google Trends -> {len(unique)} topics found")
        return unique[:RESEARCH_TOPICS * 3]
    except Exception as e:
        log.warning(f"Google Trends error: {e} — using dynamic fallback list")
        import random
        base = [
            "GPT-5 release date leaks",
            "AI agents replacing humans",
            "Sora AI video update",
            "Groq chip architecture",
            "Anthropic Claude 4 news",
            "Google Gemini 2.0 Pro",
            "Open source Llama 4 rumors",
            "Humanoid robots with AI",
            "AI in healthcare 2025",
            "Web3 and AI integration"
        ]
        random.shuffle(base)
        return base[:5]


# -----------------------------------------------------------------
#  2. YOUTUBE TRENDING SEARCH
# -----------------------------------------------------------------

def get_youtube_trending_ai(max_results: int = 10) -> list[dict]:
    """Query YouTube for the most-viewed recent AI videos."""
    url = "https://www.googleapis.com/youtube/v3/search"
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "part": "snippet",
        "q": f"{NICHE} trending 2025",
        "type": "video",
        "order": "viewCount",
        "publishedAfter": week_ago,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "relevanceLanguage": "en",
        "videoDuration": "medium",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = [
            {
                "title": i["snippet"]["title"],
                "description": i["snippet"]["description"][:300],
                "channel": i["snippet"]["channelTitle"],
                "video_id": i["id"]["videoId"],
            }
            for i in items
        ]
        log.info(f"YouTube search -> {len(results)} trending videos found")
        return results
    except Exception as e:
        log.warning(f"YouTube search error: {e}")
        return []


# -----------------------------------------------------------------
#  3. GOOGLE WEB SEARCH (for article content)
# -----------------------------------------------------------------

def google_search(query: str, num: int = 5) -> list[dict]:
    """Search the web and return top result snippets."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "q": query,
        "num": num,
        "dateRestrict": "w1",  # last week
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"title": i.get("title", ""), "snippet": i.get("snippet", "")} for i in items]
    except Exception as e:
        log.warning(f"Google Search error for '{query}': {e}")
        return []


# -----------------------------------------------------------------
#  4. PICK BEST TOPIC + GENERATE SEO META + SCRIPT
# -----------------------------------------------------------------

def pick_best_topic_and_generate(
    google_topics: list[str],
    youtube_videos: list[dict],
    custom_topic: Optional[str] = None,
    shorts_only: bool = False
) -> dict:
    """
    Use Claude to:
    - Pick the single best video topic
    - Write SEO title, description, tags
    - Write the full voiceover script
    Returns a dict with all content.
    """
    yt_titles = "\n".join(f"- {v['title']}" for v in youtube_videos[:8])
    gt_topics = "\n".join(f"- {t}" for t in google_topics[:15])

    if custom_topic:
        top_instruction = f"CREATE A VIDEO SCRIPT ABOUT THIS SPECIFIC TOPIC: '{custom_topic}'."
        data_context = f"Based on this topic: {custom_topic}"
    else:
        recent = get_recent_topics()
        recent_str = ", ".join(recent) if recent else "None"
        top_instruction = f"Pick the single best UNUSED video topic. AVOID these recently used topics: [{recent_str}]. Pick something fresh."
        data_context = f"TRENDING DATA:\n=== Google Trends ===\n{gt_topics}\n\n=== Top YouTube Videos ===\n{yt_titles}"

    target_words = 180 if shorts_only else SCRIPT_WORDS
    min_words = 150 if shorts_only else 900  # Minimum acceptable word count

    # Pre-compute all conditional strings — backslashes not allowed inside f-string {} in Python < 3.12
    fmt_label = "60-second vertical Short (punchy, fast-paced, TikTok style)" if shorts_only else "long-form deep-dive podcast episode (10-15 min equivalent)"
    req1 = "Write AT LEAST 150 words for the Short script." if shorts_only else f"Write AT LEAST {target_words} words for the podcast script. The script MUST be long and detailed."
    req2 = "Use fast-paced, punchy sentences." if shorts_only else "Use Host A and Host B format alternating. Include 5 full sections: HOOK, DEEP DIVE, CONTROVERSY, FUTURE IMPACT, CTA."
    req3 = "End with a clear Subscribe CTA." if shorts_only else "Each section must be at least 200 words. Do NOT cut the script short."
    script_label = "60-second Short" if shorts_only else f"{target_words}-WORD PODCAST"
    long_format = (
        "Host A: [HOOK - 200+ words]\n\n"
        "Host B: [DEEP DIVE - 200+ words]\n\n"
        "Host A: [CONTROVERSY - 200+ words]\n\n"
        "Host B: [FUTURE IMPACT - 200+ words]\n\n"
        "Host A: [CTA - 100+ words]"
    )
    script_format = "Short script: hook + punchy content + Subscribe CTA." if shorts_only else long_format

    prompt = f"""You are a TOP YouTube SEO strategist for an AI-focused channel targeting viral growth. Your job is to produce content that gets MAXIMUM clicks, watch time and subscribers.

Format: {fmt_label}
Target script words: {target_words} words MINIMUM. THIS IS CRITICAL - write a FULL, COMPLETE, DETAILED script.

{top_instruction}

{data_context}

CRITICAL SEO RULES:
1. TITLE: 50-60 chars max. START with a high-volume keyword.
2. DESCRIPTION: Two emotional hook sentences + 200-word keyword-rich summary + timestamps + hashtags.
3. TAGS: Minimum 20 tags mixing broad, mid-tail, and long-tail keywords.
4. THUMBNAIL TEXT: 3-4 BOLD CAPS words that create curiosity or shock.
5. HOOK: First 5 seconds = most shocking fact or question.

SCRIPT REQUIREMENTS (MOST IMPORTANT):
- {req1}
- {req2}
- {req3}

Respond ONLY in valid JSON (no text outside the JSON block):

{{
  "chosen_topic": "The single best specific topic for today",
  "reason": "One sentence: why this will go viral today",
  "seo_title": "Power-word title 50-60 chars",
  "seo_description": "Hook line 1.\nHook line 2.\n\n200-word keyword-rich summary.\n\n0:00 - Intro\n\n#AI #ArtificialIntelligence #TechNews",
  "tags": ["AI", "artificial intelligence", "AI tools 2025", "AI automation", "future of AI", "ChatGPT", "AI jobs", "machine learning", "AI news today", "AI replacing jobs", "OpenAI", "Google AI", "AI technology", "AI for beginners", "AI trends 2025", "AI productivity", "tech news", "AI content creation", "AI tutorial", "AI explained"],
  "thumbnail_text": "3-4 BOLD CAPS WORDS",
  "thumbnail_prompt": "Hyper-realistic cinematic thumbnail background. Dramatic lighting, 8K quality.",
  "hook_line": "ONE shocking opening sentence.",
  "script": "WRITE THE FULL {script_label} SCRIPT HERE. DO NOT TRUNCATE. {script_format}"
}}

THE SCRIPT FIELD MUST CONTAIN AT LEAST {min_words} WORDS. DO NOT add any text outside the JSON."""

    import json, re

    # --- Auto-fallback provider order: Gemini (free) → Groq → OpenAI ---
    provider_order = [LLM_PROVIDER]
    if LLM_PROVIDER == "gemini":
        if GROQ_API_KEY:
            provider_order.append("groq")
        if OPENAI_API_KEY:
            provider_order.append("openai")
    elif LLM_PROVIDER == "groq":
        if GEMINI_API_KEY:
            provider_order.insert(0, "gemini")  # try gemini first
        if OPENAI_API_KEY:
            provider_order.append("openai")
    elif LLM_PROVIDER == "openai":
        if GEMINI_API_KEY:
            provider_order.insert(0, "gemini")  # try gemini first
        if GROQ_API_KEY:
            provider_order.append("groq")

    data = None
    last_error = None

    for provider_attempt, current_provider in enumerate(provider_order):
        log.info(f"Sending research data to {current_provider.upper()} for topic selection + content generation{'  (FALLBACK)' if provider_attempt > 0 else ''}.")
        try:
            client, pname = get_llm_client(current_provider)
        except Exception as e:
            log.warning(f"Could not init {current_provider} client: {e}")
            last_error = e
            continue

        max_retries = 2
        retry_prompt = prompt

        for attempt in range(max_retries + 1):
            try:
                if pname == "gemini":
                    # Gemini uses generate_content, not chat.completions
                    gemini_prompt = retry_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON, no text before or after."
                    response = client.generate_content(gemini_prompt)
                    raw = response.text
                elif pname == "anthropic":
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=8000,
                        messages=[{"role": "user", "content": retry_prompt}],
                    )
                    raw = response.content[0].text
                elif pname == "openai":
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": retry_prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=8000,
                        temperature=0.7,
                        timeout=120,
                    )
                    raw = response.choices[0].message.content
                else:  # groq
                    response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{"role": "user", "content": retry_prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=8000,
                        temperature=0.7,
                        timeout=120,
                    )
                    raw = response.choices[0].message.content

            except Exception as e:
                err_str = str(e)
                # Auth errors → skip to next provider immediately
                if "401" in err_str or "invalid_api_key" in err_str or "AuthenticationError" in err_str:
                    log.error(f"❌ {current_provider.upper()} API Key is INVALID (401). "
                              f"Go regenerate it at the provider dashboard.")
                    if provider_attempt < len(provider_order) - 1:
                        log.warning(f"Falling back to next provider: {provider_order[provider_attempt+1].upper()}")
                    last_error = e
                    break  # break inner loop → try next provider
                elif "timeout" in err_str.lower() or "ConnectTimeout" in err_str:
                    log.warning(f"{current_provider.upper()} timed out (attempt {attempt+1}). "
                                 f"{'Retrying...' if attempt < max_retries else 'Switching provider.'}")
                    last_error = e
                    if attempt >= max_retries:
                        break  # try next provider
                    continue
                else:
                    log.error(f"{current_provider.upper()} error: {e}")
                    last_error = e
                    break
            else:
                # Extract JSON even if wrapped in markdown code block
                match = re.search(r"\{[\s\S]+\}", raw)
                if not match:
                    log.warning(f"Attempt {attempt+1}: LLM did not return valid JSON. Retrying...")
                    continue

                parsed = json.loads(match.group())
                script_word_count = len(parsed.get("script", "").split())
                log.info(f"Attempt {attempt+1}: Script word count = {script_word_count} (min required: {min_words})")

                if script_word_count >= min_words:
                    data = parsed
                    break
                elif attempt < max_retries:
                    log.warning(f"Script too short ({script_word_count} words). Retrying with stronger enforcement...")
                    retry_prompt = retry_prompt + f"\n\nPREVIOUS ATTEMPT HAD ONLY {script_word_count} WORDS. WRITE A MUCH LONGER SCRIPT THIS TIME — MINIMUM {min_words} WORDS."
                else:
                    log.warning(f"Script still short after retries ({script_word_count} words). Using best result.")
                    data = parsed

        if data:
            break  # success — exit provider loop

    if not data:
        raise ValueError(
            f"All LLM providers failed. Last error: {last_error}\n"
            f"🔧 FIX: Set GEMINI_API_KEY (free at aistudio.google.com) in GitHub Secrets"
        )

    log.info(f"Topic chosen: {data['chosen_topic']} | Script: {len(data.get('script','').split())} words")

    # Save to history
    save_topic_to_history(data['chosen_topic'])
    return data


# -----------------------------------------------------------------
#  PUBLIC ENTRY POINT
# -----------------------------------------------------------------

def run_research(custom_topic: Optional[str] = None, shorts_only: bool = False) -> dict:
    """Full research pipeline. Returns content dict."""
    log.info("=== Starting Research Phase ===")
    
    if custom_topic:
        log.info(f"Using custom topic: {custom_topic}")
        # Still get some context for the custom topic
        youtube_videos = get_youtube_trending_ai() # Or search specifically for topic
        google_topics = [custom_topic]
    else:
        google_topics  = get_google_trending_topics()
        youtube_videos = get_youtube_trending_ai()
        
    content = pick_best_topic_and_generate(google_topics, youtube_videos, custom_topic=custom_topic, shorts_only=shorts_only)
    return content
