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
        from google import genai as google_genai
        client_obj = google_genai.Client(api_key=GEMINI_API_KEY)
        return client_obj, "gemini"
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
            f"AI agents that automate your entire workflow in {datetime.now().year}",
            "How to make money with AI tools (realistic income breakdown)",
            "Best free AI tools most people don't know about",
            "AI is replacing these jobs faster than anyone expected",
            "How to use ChatGPT like a pro (advanced tricks)",
            "Google's new AI model vs OpenAI — honest comparison",
            "I built an AI business in 30 days — here's what happened",
            "The AI tools that actually save time (tested for 30 days)",
            "Why most AI tutorials are lying to you",
            "How to automate your business with AI for free",
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


def get_rss_news() -> list[str]:
    """Fetch latest AI news from RSS feeds to increase topic variety."""
    import xml.etree.ElementTree as ET
    feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.artificialintelligence-news.com/feed/"
    ]
    news = []
    for f in feeds:
        try:
            resp = requests.get(f, timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:5]:
                    title = item.find("title")
                    if title is not None and title.text:
                        news.append(title.text.strip())
        except Exception as e:
            log.warning(f"RSS feed error for {f}: {e}")
    unique = list(set(news))
    log.info(f"RSS Feeds -> {len(unique)} news items found")
    return unique


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
    rss_news: list[str] = None,
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
    rss_str = "\n".join(f"- {n}" for n in (rss_news or [])[:10])

    if custom_topic:
        top_instruction = f"CREATE A VIDEO SCRIPT ABOUT THIS SPECIFIC TOPIC: '{custom_topic}'."
        data_context = f"Based on this topic: {custom_topic}"
    else:
        recent = get_recent_topics()
        recent_str = ", ".join(recent) if recent else "None"
        top_instruction = f"Pick the single best UNUSED video topic. AVOID these recently used topics: [{recent_str}]. \nCRITICAL: DO NOT just summarize news! Instead, create actionable 'How to', 'Tutorial', 'Top 5 Tools', or 'Step-by-Step Guide' style topics based on these trends to guarantee high search volume and extreme topic variety."
        data_context = f"TRENDING DATA:\n=== Google Trends ===\n{gt_topics}\n\n=== RSS Feed News ===\n{rss_str}\n\n=== Top YouTube Videos ===\n{yt_titles}"

    target_words = 180 if shorts_only else SCRIPT_WORDS
    min_words = 150 if shorts_only else max(800, SCRIPT_WORDS - 200)

    from datetime import datetime as _dt
    current_year = _dt.now().year
    current_month = _dt.now().strftime("%B %Y")

    fmt_label = "60-second vertical Short (punchy, TikTok style)" if shorts_only else f"long-form YouTube video (8-10 minutes) for {current_month}"
    script_label = "Short" if shorts_only else "LONG-FORM"

    prompt = f"""You are a WORLD-CLASS YouTube SEO strategist and scriptwriter. AI content that consistently hits 100K+ views.

FORMAT: {fmt_label}
TARGET SCRIPT LENGTH: {target_words} words minimum. Write EVERY word — do NOT truncate or summarize.

{top_instruction}

{data_context}

═══ YOUTUBE SEO RULES ═══

TITLE (55-70 characters):
- Include {current_year} OR a specific number
- Use one of these proven patterns:
  "I Tested [X] AI Tools — Here\'s What Actually Works ({current_year})"
  "How to [Goal] with AI (Step-by-Step Guide)"
  "[Number] AI Tools That Will [Benefit] in {current_year}"
  "The Truth About [AI Topic] Nobody Is Talking About"
- NEVER use vague words: amazing, incredible, revolutionary
- NEVER use ALL CAPS in the title

DESCRIPTION (350-500 words total):
Line 1: Punchy hook sentence with a shocking number or bold claim
Line 2: Second hook that teases what they will learn
[blank line]
200+ word body: keyword-rich, explains what viewers learn, mentions specific tools/companies naturally
[blank line]
Chapter timestamps:
0:00 - Introduction
1:30 - [Topic-specific section]
3:00 - [Topic-specific section]
5:00 - [Topic-specific section]
7:00 - [Topic-specific section]
8:30 - Final Thoughts & Subscribe
[blank line]
20 hashtags: mix of broad (#AI #MachineLearning) and specific (#AITools{current_year} #OpenAI)

TAGS: 30 tags — 5 exact title keywords, 10 topic variations, 10 broad AI terms, 5 question-format (e.g. "how to use AI agents")

THUMBNAIL TEXT:
- Exactly 3-5 words, ALL CAPS, PLAIN TEXT ONLY
- NO asterisks (**), NO markdown, NO bold markers whatsoever
- Create extreme curiosity or show a shocking number
- GOOD: "AI REPLACED MY JOB", "EARN 500 DAY AI", "GOOGLE LIED TO US"
- BAD: "AI REVOLUTION 2025" (too vague), "**BUILD ROBOT**" (has asterisks)

═══ SCRIPT RULES ═══

Write Host A / Host B podcast format. They are knowledgeable, conversational co-hosts who:
- Sometimes disagree, ask each other questions, react naturally
- Use contractions and informal phrases: "Wait, really?", "That\'s wild", "Okay so here\'s the thing"
- NEVER sound like news anchors or say corporate phrases

SCRIPT STRUCTURE:
Host A: [HOOK — 150+ words]
Jump straight to a shocking statistic or controversial claim. NO welcome message, NO channel name.
Example: "Okay so I just found out that 40% of companies are already replacing junior developers with AI..."

Host B: [DEEP DIVE 1 — 200+ words]
First major point. Include specific company names (OpenAI, Google DeepMind, Anthropic, Meta AI, etc.) and real numbers.

Host A: [DEEP DIVE 2 — 200+ words]
Second major point. Include a surprising counterargument.

Host B: [PRACTICAL STEPS — 200+ words]
Actionable steps listeners can take right now. Name specific free tools with actual features.

Host A: [HOT TAKE — 150+ words]
A bold controversial opinion that will generate comments. Something people want to debate.

Host B: [FUTURE IMPACT — 150+ words]
Specific prediction for 6-12 months from now.

Host A: [CTA — 80+ words]
Natural ask to like and subscribe. Connect it to the topic value.

MANDATORY:
- First sentence = shocking hook, zero pleasantries
- At least 3 real company names
- At least 2 statistics with source context
- No placeholders: [Channel Name], [Link], [Insert Stat]
- No markdown in script: no **, no *, no ## headers
- Do NOT ask to like/subscribe at the start

Respond ONLY with valid JSON. No text outside the JSON:

{{
  "chosen_topic": "Specific detailed topic (not vague)",
  "reason": "One sentence: why this gets clicks today",
  "seo_title": "Compelling title 55-70 chars including {current_year} or a number",
  "seo_description": "First hook sentence with a bold claim or number.\nSecond hook teasing what they will learn.\n\n[200+ word body paragraph. Write naturally, embed keywords. Mention tools, companies, specific benefits. Multiple paragraphs okay.]\n\n0:00 - Introduction\n1:30 - [Section]\n3:00 - [Section]\n5:00 - [Section]\n7:00 - [Section]\n8:30 - Subscribe & Resources\n\n#AI #ArtificialIntelligence #AITools #ChatGPT #MachineLearning #TechNews #AINews #FutureOfWork #AITutorial #OpenAI #GoogleAI #AIAutomation #AIForBeginners #TechTrends #{current_year} #DeepLearning #AIProductivity #AIAgents #DigitalTransformation #FutureOfAI",
  "tags": ["exact topic keyword", "topic keyword variation", "how to use topic", "best topic tools", "topic tutorial", "AI", "artificial intelligence", "AI tools {current_year}", "AI tutorial", "AI explained", "machine learning", "ChatGPT tutorial", "AI news", "future of AI", "AI automation", "AI for beginners", "OpenAI news", "Google AI", "AI technology", "AI trends {current_year}", "tech news today", "AI productivity", "AI content creation", "AI agents", "how to use AI", "what is AI", "AI replacing jobs", "AI tools free", "best AI tools", "AI workflow"],
  "thumbnail_text": "3-5 PLAIN CAPS WORDS NO SYMBOLS",
  "thumbnail_prompt": "Cinematic 8K photorealistic thumbnail background. [Specific dramatic visual matching the topic]. Dark moody background, dramatic studio lighting, sharp focus, no text in image.",
  "hook_line": "One shocking sentence without any markdown symbols",
  "script": "[WRITE THE COMPLETE SCRIPT HERE following Host A/B format with all 7 sections. Minimum {target_words} words. Write every word of dialogue. Do not write section headers in brackets — just write the actual dialogue.]"
}}

SCRIPT MUST BE {min_words}+ WORDS. DO NOT ADD ANY TEXT OUTSIDE THE JSON."""

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
                    # New google-genai SDK syntax
                    gemini_prompt = retry_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON, no text before or after."
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=gemini_prompt,
                    )
                    raw = response.text
                elif pname == "anthropic":
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": retry_prompt}],
                    )
                    raw = response.content[0].text
                elif pname == "openai":
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": retry_prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=4000,
                        temperature=0.7,
                        timeout=120,
                    )
                    raw = response.choices[0].message.content
                else:  # groq
                    response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{"role": "user", "content": retry_prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=4000,
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
                
                # Clean up LLM prompt placeholders from the generated script
                if "script" in parsed:
                    import re
                    script_text = parsed["script"]
                    # Completely strip ALL bracketed placeholders like [HOOK ...], [Channel Name], etc.
                    clean_script = re.sub(r'\[.*?\]', '', script_text)
                    parsed["script"] = clean_script.strip()
                    
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
    log.info("=== Starting Research Phase (Multi-Agent Swarm Mode) ===")
    
    google_topics = []
    if not custom_topic:
        try:
            google_topics = get_google_trending_topics()
        except Exception as e:
            log.warning(f"Failed to fetch trends: {e}")
            
    # Import and run our new Multi-Agent Orchestrator Swarm!
    from modules.agent_orchestrator import run_multi_agent_swarm
    content = run_multi_agent_swarm(
        trends_data=google_topics,
        custom_topic=custom_topic,
        shorts_only=shorts_only
    )
    return content
