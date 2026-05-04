"""
modules/director_agent.py
Analyzes the script and plans scenes with highly specific Pexels stock footage keywords.
Every keyword is chosen to visually MATCH what is being spoken in that scene.
"""

import json
import logging
import re
import random
from groq import Groq
from config.settings import GROQ_API_KEY, OPENAI_API_KEY, GROQ_MODEL, LLM_PROVIDER

log = logging.getLogger(__name__)

# ── Semantic keyword pools for AI-topic scenes ──────────────────────────────
# Used only in the NLP-based fallback if LLM Director fails.
KEYWORD_POOLS = {
    "robot|automation|humanoid": [
        "factory robot", "robot arm", "humanoid robot"
    ],
    "job|work|employ|career|worker": [
        "office desk", "business meeting", "typing laptop"
    ],
    "health|medical|hospital|doctor|patient": [
        "doctor surgery", "medical scan", "healthcare worker"
    ],
    "money|finance|invest|stock|economy|bank": [
        "stock market", "finance graph", "bitcoin"
    ],
    "code|software|developer|program|app": [
        "programmer coding", "developer laptop", "coding monitor"
    ],
    "future|innovation|technology|tech": [
        "city night", "innovation lab", "smart city"
    ],
    "data|analytics|big data|database": [
        "data dashboard", "analytics graph", "server blinking"
    ],
    "camera|surveillance|security|spy": [
        "security camera", "hacker screen", "cctv"
    ],
    "space|satellite|rocket|nasa": [
        "rocket launch", "satellite earth", "astronaut"
    ],
    "climate|environment|green|energy": [
        "solar panel", "wind turbine", "green nature"
    ],
    "war|military|weapon|drone|army": [
        "military drone", "army training", "defense radar"
    ],
    "education|school|student|learn|university": [
        "student laptop", "university campus", "online learning"
    ],
    "self-driving|autonomous|car|vehicle|transport": [
        "self driving", "autonomous car", "highway aerial"
    ],
    "agent|workflow|assistant|chatbot|prompt": [
        "typing laptop", "chat screen", "office desk"
    ],
    "youtube|video|shorts|creator|content|thumbnail|channel": [
        "video editing", "camera setup", "creator desk"
    ],
    "email|inbox|calendar|schedule|meeting|productivity": [
        "office desk", "calendar app", "business meeting"
    ],
    "spreadsheet|excel|dashboard|report|chart|sales": [
        "data dashboard", "analytics graph", "finance graph"
    ],
    "cloud|server|api|database|deploy|infrastructure": [
        "server room", "data center", "coding screen"
    ],
    "security|privacy|password|phishing|scam|hack": [
        "hacker screen", "security camera", "server room"
    ],
    "phone|mobile|app|notification|social": [
        "smartphone", "phone screen", "mobile app"
    ],
    "ai|artificial intelligence|machine learning|neural network|deep learning|llm|gpt|gemini|claude": [
        "data center", "coding screen", "server room", "computer chip"
    ],
}


def _clean_keyword(keyword: str, fallback: str = "data center") -> str:
    """Keep Pexels queries concrete and short enough to return relevant footage."""
    keyword = re.sub(r"[^a-zA-Z0-9 ]+", " ", keyword or "").strip().lower()
    keyword = re.sub(r"\s+", " ", keyword)
    bad_words = {"ai", "artificial", "intelligence", "technology", "future", "innovation", "tech"}
    words = [w for w in keyword.split() if w not in bad_words]
    if not words:
        return fallback
    return " ".join(words[:2])


def _nlp_keyword(text: str, topic: str) -> str:
    """Extract the best Pexels keyword from scene text using keyword pools."""
    scene_text = text.lower()
    for pattern, keywords in KEYWORD_POOLS.items():
        if re.search(pattern, scene_text):
            return _clean_keyword(random.choice(keywords))

    combined = (text + " " + topic).lower()
    for pattern, keywords in KEYWORD_POOLS.items():
        if re.search(pattern, combined):
            return _clean_keyword(random.choice(keywords))

    topic_words = [w for w in re.findall(r"[a-zA-Z0-9]+", topic.lower()) if len(w) > 3]
    topic_words = [w for w in topic_words if w not in {"agentic", "world", "news", "video"}]
    if topic_words:
        return _clean_keyword(" ".join(topic_words[:2]))
    return "data center"


def generate_scene_data(topic: str, seo_title: str, script: str, is_shorts: bool) -> list[dict]:
    """
    Uses an LLM to act as a Video Director.
    Breaks the script into scenes and assigns a hyper-specific Pexels keyword
    to each scene so footage VISUALLY MATCHES what is being spoken.
    """
    log.info("🎬 Director Agent is analyzing the script and planning scenes...")

    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        model_name = "gpt-4o"
        use_groq = False
    elif GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)
        model_name = GROQ_MODEL
        use_groq = True
    else:
        log.warning("No API keys found. Using NLP fallback for scene planning.")
        return fallback_generate_scene_data(script, seo_title, topic)

    sys_prompt = """You are a PROFESSIONAL YouTube Video Director at a top media company.
Your job: read a podcast script and break it into scenes for a faceless YouTube video.
Each scene MUST have a hyper-specific stock footage keyword that VISUALLY MATCHES the dialogue.
The video also has a presenter avatar, so your b-roll should show the exact object/action being discussed behind the presenter.

=== PEXELS SEARCH ENGINE LIMITATIONS (CRITICAL) ===
The Pexels API strictly uses exact tag matching and FAILS COMPLETELY on phrases, sentences, or abstract ideas.
If you generate a complex phrase, Pexels returns 0 results, and the video will look like garbage.

BAD keywords (will fail or return irrelevant garbage):
  ❌ "artificial intelligence", "technology", "innovation", "future", "cybersecurity" (Too abstract!)
  ❌ "person typing on laptop computer", "doctor reading an xray" (Too long! Pexels will fail!)
  
GOOD keywords (highly literal, maximum 1-2 words, concrete tangible objects):
  ✅ Script says "AI is analyzing medical scans" → keyword: "doctor xray"
  ✅ Script says "hackers are breaching cybersecurity" → keyword: "hacker screen"
  ✅ Script says "robots replacing factory workers" → keyword: "factory robot"
  ✅ Script says "self-driving cars on highways" → keyword: "autonomous car"
  ✅ Script says "LLMs generating code" → keyword: "coding screen"
  ✅ Script says "AI agent handles emails" → keyword: "office desk"
  ✅ Script says "YouTube automation" → keyword: "video editing"
  ✅ Script says "business dashboard" → keyword: "data dashboard"

RULES:
1. MAXIMUM 2 WORDS STRICTLY. Never generate 3 or 4 words. Exactly 1 or 2 words.
2. Must be a concrete, tangible noun and/or simple action. (e.g. "server room", "brain glowing", "typing laptop").
3. NEVER use the words "AI", "artificial", "intelligence", or "technology".
4. For intro scenes use: "data center" or "city night".
5. For CTA/subscribe scenes use: "smartphone" or "thumbs up".
6. Do NOT reuse the same keyword more than once unless the same visual action is literally repeated.
7. Prefer real-world footage terms: people, desks, cameras, servers, phones, dashboards, robots, hospitals, cars, labs.

=== OUTPUT FORMAT ===
Return a JSON object with a single key "scenes" containing an array.
Each item in the array has exactly:
  - "text": the exact dialogue from the script for this scene (do NOT skip or summarize any dialogue)  
  - "keyword": your strict 1-2 word literal Pexels search keyword
  - "alt_keyword": a backup 1-2 word literal keyword if first one fails (must be DIFFERENT)
  - "prompt": a cinematic AI image prompt for this scene (used as fallback background)

Example output format:
{"scenes": [{"text": "...", "keyword": "doctor xray", "alt_keyword": "medical scan", "prompt": "Cinematic shot of doctor examining patient, dramatic lighting, 4K"}, ...]}
"""

    user_prompt = f"""Video Topic: {topic}
SEO Title: {seo_title}
Is Shorts Format: {is_shorts}

Script to break into scenes:
{script}

Remember: assign a UNIQUE, SPECIFIC, VISUAL keyword to EACH scene. No generic keywords. The keyword must match the exact sentence, not only the broad AI topic."""

    try:
        call_kwargs = dict(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.15,
            max_tokens=4000,
        )
        # Groq json_object mode only works for objects (not bare arrays)
        # We wrap scenes in {"scenes": [...]} so this is safe
        if use_groq:
            call_kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**call_kwargs)
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        # Parse JSON
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            log.warning(f"Director: JSON parse failed, trying json_repair. Preview: {raw[:200]}")
            try:
                from json_repair import repair_json
                parsed = json.loads(repair_json(raw))
            except Exception:
                match = re.search(r'\{[\s\S]+\}', raw)
                if match:
                    parsed = json.loads(match.group())
                else:
                    raise ValueError("Could not parse Director Agent response as JSON")

        # Extract the scenes array (handle both {"scenes": [...]} and bare [...])
        if isinstance(parsed, dict):
            scene_data = parsed.get("scenes", parsed.get("scene_data", []))
            if not scene_data:
                # Some models return {"0": {...}, "1": {...}}
                scene_data = list(parsed.values()) if parsed else []
        elif isinstance(parsed, list):
            scene_data = parsed
        else:
            raise ValueError(f"Unexpected Director Agent response type: {type(parsed)}")

        # Validate and sanitize
        valid_scenes = []
        seen_keywords = []
        for i, scene in enumerate(scene_data):
            if not isinstance(scene, dict):
                continue
            text = scene.get("text", "").strip()
            keyword = scene.get("keyword", "").strip()
            alt_keyword = scene.get("alt_keyword", "").strip()
            prompt = scene.get("prompt", "").strip()

            # Reject obviously bad generic keywords
            bad_kw = {"technology", "artificial intelligence", "innovation", "future", "ai", "tech"}
            if not keyword or keyword.lower() in bad_kw:
                keyword = _nlp_keyword(text, topic)
            if not alt_keyword or alt_keyword.lower() in bad_kw or alt_keyword == keyword:
                alt_keyword = _nlp_keyword(text + " alternate", topic)
            keyword = _clean_keyword(keyword, _nlp_keyword(text, topic))
            alt_keyword = _clean_keyword(alt_keyword, _nlp_keyword(text + " alternate", topic))
            if alt_keyword == keyword:
                alt_keyword = _clean_keyword(_nlp_keyword(text + " different visual", topic), "office desk")
            if not prompt:
                prompt = f"Cinematic {keyword}, professional lighting, 4K"

            # Avoid repeating the same keyword consecutively
            if seen_keywords and keyword == seen_keywords[-1]:
                keyword, alt_keyword = alt_keyword, keyword

            if text:
                valid_scenes.append({
                    "text": text,
                    "keyword": keyword,
                    "alt_keyword": alt_keyword,
                    "prompt": prompt
                })
                seen_keywords.append(keyword)

        if not valid_scenes:
            raise ValueError("Director Agent returned no valid scenes")

        log.info(f"✅ Director Agent planned {len(valid_scenes)} scenes with specific keywords.")
        return valid_scenes

    except Exception as e:
        log.error(f"Director Agent failed: {e}. Using NLP fallback.")
        return fallback_generate_scene_data(script, seo_title, topic)


def fallback_generate_scene_data(script: str, seo_title: str, topic: str = "") -> list[dict]:
    """
    NLP-based fallback: uses keyword pools to assign visually relevant footage
    based on what each chunk of the script is actually talking about.
    """
    log.info("📋 Using NLP keyword fallback for scene planning...")
    lines = re.split(r'(Host [AB]:)', script)
    scenes = [{
        "text": seo_title.upper(),
        "keyword": "data center",
        "alt_keyword": "city night",
        "prompt": f"Cinematic title screen, {seo_title}, dramatic lighting, 4k"
    }]

    current_host = ""
    for item in lines:
        item = item.strip()
        if not item:
            continue
        if item in ["Host A:", "Host B:"]:
            current_host = item
        else:
            words = item.split()
            chunk_size = 20  # ~5 seconds of speech per chunk
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                kw = _nlp_keyword(chunk, topic)
                scenes.append({
                    "text": chunk,
                    "keyword": kw,
                    "alt_keyword": _nlp_keyword(chunk + " alternate visual", topic),
                    "prompt": f"Cinematic professional shot of {kw}, dramatic lighting, 4K"
                })

    scenes.append({
        "text": "LIKE  •  SUBSCRIBE  •  AI NEWS DAILY",
        "keyword": "thumbs up",
        "alt_keyword": "smartphone",
        "prompt": "Cinematic YouTube subscribe end screen, glowing neon lights, 4K"
    })
    return scenes
