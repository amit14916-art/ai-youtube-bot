import json
import logging
import os
from groq import Groq
from langchain_core.prompts import PromptTemplate
from config.settings import GROQ_API_KEY, GROQ_MODEL

log = logging.getLogger(__name__)

def generate_scene_data(topic: str, seo_title: str, script: str, is_shorts: bool) -> list[dict]:
    """
    Uses LangChain and Groq to act as a Video Director.
    It reads the script and breaks it down into small scenes (1-2 sentences each).
    For each scene, it generates an exact video search keyword for Pexels and a cinematic visual prompt for Fal.ai.
    """
    log.info("🎬 Director Agent is analyzing the script and planning scenes...")
    
    if not GROQ_API_KEY:
        log.warning("GROQ_API_KEY is missing. Falling back to simple slide extraction.")
        return fallback_generate_scene_data(script, seo_title)

    client = Groq(api_key=GROQ_API_KEY)
    
    format_instructions = """
    Return ONLY a valid JSON array of objects. Do not include any markdown formatting like ```json or ```.
    Each object must have exactly these keys:
    - "text": The exact dialogue text for the scene (keep it strictly synchronized with the script, break it down mostly by speaker or every 2-3 sentences max).
    - "keyword": A 1-2 word VERY BROADER stock footage keyword for Pexels (e.g. "technology", "abstract data", "server", "scifi", "computer"). Avoid highly specific or complex terms to ensure we find a matching video!
    - "prompt": A detailed cinematic prompt for generating an AI video on Luma/Hunyuan (e.g. "A futuristic glowing robot analyzing code, cinematic lighting, 4k macro").
    """

    sys_prompt = f"""You are an Expert YouTube Video Director for an AI tech channel.
    Your job is to read the podcast script and break it down into visual cuts (scenes).
    
    Task Rules:
    1. Break the script into multiple scenes. Each scene should contain exactly the dialogue spoken text. Do not skip any dialogue.
    2. For each scene, provide a highly relevant stock footage 'keyword'.
    3. For each scene, provide a cohesive cinematic AI video generation 'prompt'.
    
    Format:
    {format_instructions}
    """
    
    user_prompt = f"""
    Video Topic: {topic}
    Is Shorts Format: {is_shorts}
    Script:
    {script}
    """

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up markdown formatting if the model still outputs it
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.endswith("```"):
            content = content[:-3]
            
        scene_data = json.loads(content.strip())
        log.info(f"Director Agent planned {len(scene_data)} scenes.")
        return scene_data
        
    except Exception as e:
        log.error(f"Director Agent failed: {e}")
        return fallback_generate_scene_data(script, seo_title)


def fallback_generate_scene_data(script: str, seo_title: str) -> list[dict]:
    import re
    lines = re.split(r'(Host [AB]:)', script)
    scenes = [{"text": seo_title.upper(), "keyword": "ai technology", "prompt": f"Futuristic cinematic title screen, {seo_title}, high tech, 4k"}]
    
    current_host = ""
    for item in lines:
        item = item.strip()
        if not item: continue
        if item in ["Host A:", "Host B:"]:
            current_host = item
        else:
            words = item.split()
            chunk_size = 15
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                scenes.append({
                    "text": chunk,
                    "keyword": "technology artificial intelligence",
                    "prompt": "Cinematic AI visual, macro tech, futuristic, high quality"
                })

    scenes.append({
        "text": "LIKE  •  SUBSCRIBE  •  AI NEWS DAILY", 
        "keyword": "subscribe button", 
        "prompt": "Cinematic YouTube subscribe end screen, glowing neon lights"
    })
    return scenes
