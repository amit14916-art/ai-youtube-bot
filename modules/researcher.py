"""
modules/researcher.py
Finds trending AI topics from Google Trends + YouTube search.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import anthropic
import requests
from pytrends.request import TrendReq

from config.settings import (
    ANTHROPIC_API_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
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
def get_llm_client():
    if LLM_PROVIDER == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    else:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)


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
    
    prompt = f"""You are a TOP YouTube SEO strategist for an AI-focused channel targeting viral growth. Your job is to produce content that gets MAXIMUM clicks, watch time and subscribers.

Format: {'60-second vertical Short (punchy, fast-paced, TikTok style)' if shorts_only else 'long-form deep-dive podcast episode (10-15 min equivalent)'}
Target script words: {target_words}

{top_instruction}

{data_context}

CRITICAL SEO RULES YOU MUST FOLLOW:
1. TITLE: 50-60 chars max. Must START with a high-volume keyword. Use ONE of these power patterns:
   - "X Reasons Why [Topic] Will [Change/Replace/Shock] You"
   - "The Truth About [Topic] Nobody Talks About"
   - "How [Topic] Is [Disrupting/Replacing] Everything in [Year]"
   - "[Number] AI [Tools/Secrets/Facts] That Will [Blow Your Mind/Change Your Life]"
2. DESCRIPTION: Start with TWO emotional hook sentences (no keyword stuffing). Then write a 200-word keyword-rich summary. Include: timestamps, hashtags, CTAs ("Subscribe for daily AI updates!").
3. TAGS: Minimum 20 tags. Mix: broad (AI, artificial intelligence), mid-tail (AI automation 2025), long-tail (how AI is replacing jobs in 2025). No duplicates.
4. THUMBNAIL TEXT: 3-4 BOLD CAPS words max. Must create curiosity gap or shock. Examples: "AI REPLACING HUMANS?", "THIS CHANGES EVERYTHING", "99% DON'T KNOW THIS"
5. HOOK: First 5 seconds must be the most shocking/surprising fact or question from the topic.

Respond ONLY in valid JSON:

{{
  "chosen_topic": "The single best specific topic for today",
  "reason": "One sentence: why this will go viral today",
  "seo_title": "Power-word title, 50-60 chars, starts with main keyword, includes number if possible",
  "seo_description": "Line 1: Emotional hook sentence.\\nLine 2: Second hook sentence with primary keyword.\\n\\n[200-word keyword-rich description]\\n\\n⏱ TIMESTAMPS:\\n0:00 - Intro\\n0:30 - The Hook\\n\\n🔔 Subscribe for daily AI content!\\n\\n#AI #ArtificialIntelligence #AINews #FutureOfWork #TechNews",
  "tags": ["AI", "artificial intelligence", "AI tools 2025", "AI automation", "future of AI", "ChatGPT", "AI jobs", "machine learning", "AI news today", "AI replacing jobs", "OpenAI", "Google AI", "AI technology", "AI for beginners", "AI trends 2025", "AI productivity", "tech news", "AI content creation", "AI tutorial", "AI explained"],
  "thumbnail_text": "3-4 BOLD CAPS words that create curiosity or shock",
  "thumbnail_prompt": "Hyper-realistic cinematic thumbnail background. Dramatic lighting, 8K quality. Example: 'Shocked human faces watching a robot takeover, dark dramatic atmosphere, red and blue lighting, ultra-detailed'",
  "hook_line": "ONE shocking opening sentence that hooks viewer in 5 seconds. Start with 'Did you know...' or 'WARNING:' or a shocking statistic.",
  "script": "{'High-energy 60-second Short script. Start with hook_line. Fast cuts, short punchy sentences. End with Like & Subscribe CTA.' if shorts_only else 'Engaging podcast script with 5 sections: 1) HOOK (shocking stat/question), 2) DEEP DIVE (technical explanation with analogies), 3) CONTROVERSY (Host B challenges assumptions), 4) FUTURE IMPACT (where is this heading?), 5) CTA (like, subscribe, comment). Format as Host A: ... Host B: ... 400+ words minimum.'}"
}}

DO NOT add any text outside the JSON. Ensure all JSON strings are properly escaped."""

    log.info(f"Sending research data to {LLM_PROVIDER.upper()} for topic selection + content generation…")
    
    client = get_llm_client()
    
    if LLM_PROVIDER == "anthropic":
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
    else:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=6144, # Ensure enough room for ~1200 words + JSON overhead
        )
        raw = response.choices[0].message.content

    import json, re
    # Extract JSON even if wrapped in markdown code block
    match = re.search(r"\{[\s\S]+\}", raw)
    if not match:
        raise ValueError(f"{LLM_PROVIDER.upper()} did not return valid JSON")

    data = json.loads(match.group())
    log.info(f"Topic chosen: {data['chosen_topic']}")
    
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
