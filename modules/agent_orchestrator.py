"""
modules/agent_orchestrator.py
Multi-Agent Orchestrator Swarm for AI YouTube Bot.
Uses a network of 7 specialized AI agents (Researchers, Writers, Editors, Designers, and QA Audits)
to generate high-retention, studio-grade content with self-correction loops.
"""

import json
import logging
import re
import time
from typing import Dict, Any, List, Tuple

from config.settings import (
    LLM_PROVIDER,
    GEMINI_MODEL,
    GROQ_MODEL,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    NICHE,
    SCRIPT_WORDS,
)

log = logging.getLogger(__name__)


# -----------------------------------------------------------------
#  LLM CONNECTIONS & FALLBACKS
# -----------------------------------------------------------------

def get_client(provider: str):
    """Return LLM client and backend name."""
    if provider == "gemini":
        from google import genai as google_genai
        return google_genai.Client(api_key=GEMINI_API_KEY), "gemini"
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), "anthropic"
    elif provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY), "openai"
    else:  # groq
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY), "groq"


def call_agent_llm(prompt: str, system_prompt: str = "", json_mode: bool = False) -> str:
    """Safely query LLM with fallback chain matching researcher.py settings."""
    providers = [LLM_PROVIDER]
    if LLM_PROVIDER == "gemini":
        if GROQ_API_KEY: providers.append("groq")
        if OPENAI_API_KEY: providers.append("openai")
    elif LLM_PROVIDER == "groq":
        if GEMINI_API_KEY: providers.insert(0, "gemini")
        if OPENAI_API_KEY: providers.append("openai")
    elif LLM_PROVIDER == "openai":
        if GEMINI_API_KEY: providers.insert(0, "gemini")
        if GROQ_API_KEY: providers.append("groq")

    last_err = None
    for p in providers:
        try:
            client, name = get_client(p)
            combined_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
            
            if name == "gemini":
                # Ensure strict JSON rules for Gemini if json_mode
                prompt_mod = combined_prompt + ("\n\nRespond ONLY with a valid JSON block, no markdown wrapping, no extra text." if json_mode else "")
                resp = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt_mod,
                )
                return resp.text.strip()
                
            elif name == "anthropic":
                resp = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=3500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text.strip()
                
            elif name == "openai":
                args = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 3000
                }
                if json_mode:
                    args["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**args)
                return resp.choices[0].message.content.strip()
                
            else:  # groq
                args = {
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 3000
                }
                if json_mode:
                    args["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**args)
                return resp.choices[0].message.content.strip()
                
        except Exception as e:
            log.warning(f"Orchestrator LLM provider {p} failed: {e}")
            last_err = e

    raise RuntimeError(f"All LLM providers failed in multi-agent orchestrator. Last error: {last_err}")


# -----------------------------------------------------------------
#  INDIVIDUAL AGENT DEFINITIONS
# -----------------------------------------------------------------

class Agent:
    def __init__(self, name: str, role: str, system_prompt: str, json_mode: bool = False):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.json_mode = json_mode

    def run(self, prompt: str) -> str:
        log.info(f"[{self.name}] ({self.role}) is working...")
        return call_agent_llm(prompt, self.system_prompt, self.json_mode)


# 1. Topic Strategist Agent
topic_strategist = Agent(
    name="Topic Strategist",
    role="Niche Optimization & Clickability Analysis",
    system_prompt=(
        f"You are a master YouTube Niche Strategist specializing in the niche: {NICHE}.\n"
        "Your task is to analyze trending news/topics and select the single most viral, "
        "high-interest topic for a video designed to maximize Views, Click-Through-Rate (CTR), and Subscriber conversions.\n"
        "Focus heavily on search volume, extreme curiosity gaps, emotional triggers (wonder, shock, fear of missing out), and high retention potential.\n"
        "Avoid general/abstract concepts. Pick actionable, educational, or highly sensational topics (e.g. 'How to', 'Tutorial', 'Top 5', 'The Truth About').\n"
        "Respond ONLY in valid JSON format:\n"
        "{\n"
        "  \"topic\": \"Selected viral topic name\",\n"
        "  \"reason\": \"Detailed target audience search demand, CTR triggers, and subscriber conversion reasons\"\n"
        "}"
    ),
    json_mode=True
)

# 2. Script Writer Agent
script_writer = Agent(
    name="Script Writer",
    role="High-Retention Copywriting",
    system_prompt=(
        "You are an expert YouTube Scriptwriter specializing in high-retention faceless automation channels.\n"
        "Write a highly engaging video script using an alternating Host A and Host B conversational dialogue format.\n"
        "Write the FULL script. Do not write summaries or placeholders.\n"
        "CRITICAL FOR RETENTION (HOOK): The first 3 seconds MUST start with an explosive, high-intensity curiosity hook (a shocking question, paradox, or threat) that forces viewers to stay. Do NOT say 'welcome', do NOT mention channel names, do NOT greet the audience. Start immediately with dialogue.\n"
        "CRITICAL FOR SUBSCRIBERS (MID-ROLL CTA): Integrate a highly natural, compelling subscribe call-to-action (CTA) inside the first 30 seconds of the script once the core conflict/topic is set (e.g., Host A: 'Before we dive into the details, make sure to hit subscribe so you don't miss our daily deep-dives. Let's keep going.').\n"
        "CRITICAL FOR SUBSCRIBERS (OUTRO CTA): Integrate a strong closing Like & Subscribe call-to-action (CTA) in the final dialogue exchange (e.g., Host B: 'If this blew your mind, drop a like and subscribe for more daily breakthroughs. See you tomorrow!').\n"
        "Format as plain text dialogue. Use Host A and Host B labels."
    ),
    json_mode=False
)

# 3. Script Editor Agent
script_editor = Agent(
    name="Script Editor",
    role="Pacing, Word-count & Grammar Audit",
    system_prompt=(
        "You are a meticulous YouTube Script Editor auditing content for retention, pacing, and subscriber growth.\n"
        "Review the script and optimize it for high verbal energy, fast pacing, and speech naturalness.\n"
        f"Ensure the script has at least {SCRIPT_WORDS} words (unless it is a short-form, which is 150-180 words).\n"
        "Verify that: \n"
        "1. The first 3 seconds has an immediate retention hook (no greetings/intros allowed).\n"
        "2. There is a compelling mid-roll subscribe CTA.\n"
        "3. There is an end-of-video subscribe/like CTA.\n"
        "Ensure all bracketed instructions (like [Action], [Music], [Sound Effect]) are REMOVED from the dialogue itself.\n"
        "Ensure there are no markdown symbols (*, _, #) inside the dialogue lines."
    ),
    json_mode=False
)

# 4. Creative Director Agent
creative_director = Agent(
    name="Creative Director",
    role="Visual Flow & Scene Mapping",
    system_prompt=(
        "You are a Cinematic Video Director aiming for A1 studio-grade visual quality.\n"
        "Break a script into consecutive visual scenes. For each scene, design a concrete, dynamic stock footage keyword.\n"
        "Keywords MUST be highly visual, tangible objects or actions (maximum 1-2 words). Avoid abstract words like 'AI' or 'technology'.\n"
        "Also generate a premium, highly detailed fallback image prompt for each scene that specifies camera settings, lighting, and resolution (e.g., 'hyper-realistic 8k octane render, cinematic lighting, sharp focus, tech blue glow, Unreal Engine 5 style').\n"
        "Respond ONLY with a valid JSON array wrapped in a key named 'scenes'. Each item must contain:\n"
        "{\n"
        "  \"text\": \"Dialogue line from script matching this scene\",\n"
        "  \"keyword\": \"1-2 words concrete high-quality stock video query\",\n"
        "  \"alt_keyword\": \"Backup high-quality stock query\",\n"
        "  \"prompt\": \"Highly detailed cinematic image generation prompt matching this scene\"\n"
        "}"
    ),
    json_mode=True
)

# 5. SEO Metadata Agent
seo_agent = Agent(
    name="SEO Optimizer",
    role="YouTube Metadata Strategy",
    system_prompt=(
        "You are a YouTube SEO Architect specializing in maximizing algorithm views, search ranking, and click-through-rate.\n"
        "Title: 50-60 chars max. Highly searchable, curiosity-driven, click-worthy (CTR-optimized).\n"
        "Description: High-conversion structure. Start with a hook line, add a subscription link CTA, a 250-word keyword-rich summary (targeting algorithm recommendations), complete timestamps (0:00 - Intro, etc.), and 15+ hashtags. At the very bottom of the description, you MUST append: 'Altered Content Disclosure: Voiceover narration and presenter avatar are synthetic/AI-generated.'\n"
        "Thumbnail text: 3-4 bold caps words representing the core concept value hook.\n"
        "Respond ONLY with a valid JSON block:\n"
        "{\n"
        "  \"title\": \"SEO Title\",\n"
        "  \"description\": \"SEO Description\",\n"
        "  \"tags\": [\"tag1\", \"tag2\", ...],\n"
        "  \"thumbnail_text\": \"BOLD CAPS WORDS\"\n"
        "}"
    ),
    json_mode=True
)

# 6. Quality Assurance (QA) Audit Agent (Self-Correction Loop)
qa_agent = Agent(
    name="QA Auditor",
    role="Validation & Pipeline Safety Check",
    system_prompt=(
        "You are the final Quality Control Officer ensuring high-purity execution and optimization checkmarks.\n"
        "Your task is to review all gathered video components (Title, Script, Scenes, SEO Metadata) "
        "and verify they meet strict rules for maximum views and subscriber conversions:\n"
        "1. NO markdown formatting (**bold**, _italic_, ## headers) in the script or title.\n"
        "2. Description contains a subscription link CTA and timestamps (e.g. 0:00 - Intro, etc.).\n"
        "3. Script starts immediately with a strong, curiosity-inducing hook (reject if first lines contain greeting words like 'Welcome', 'Hey guys', 'In today's video').\n"
        "4. Script contains both a mid-roll subscribe/like CTA and a final subscribe CTA.\n"
        "5. Keywords are highly concrete and visual (no abstract queries like 'AI', 'innovation', or 'future').\n"
        "If everything is correct, set 'passed': true.\n"
        "If there are issues, set 'passed': false and list the details in 'fix_instructions'.\n"
        "Respond ONLY in valid JSON:\n"
        "{\n"
        "  \"passed\": true/false,\n"
        "  \"fix_instructions\": \"List details of what to fix if failed, otherwise empty\"\n"
        "}"
    ),
    json_mode=True
)


# -----------------------------------------------------------------
#  SWARM RUNNER
# -----------------------------------------------------------------

def run_multi_agent_swarm(trends_data: List[str], custom_topic: str = None, shorts_only: bool = False) -> Dict[str, Any]:
    """Execute the multi-agent pipeline from topic selection to QA sign-off."""
    log.info("Launching Multi-Agent Swarm (7 Specialized Agents)...")
    
    # 1. Topic Selection
    if custom_topic:
        chosen_topic = custom_topic
        selection_reason = "User-supplied custom topic."
    else:
        trends_summary = "\n".join(f"- {t}" for t in trends_data[:15])
        strategist_res = topic_strategist.run(f"Trends Data:\n{trends_summary}")
        # Parse JSON
        parsed_str = clean_json_string(strategist_res)
        selection_data = json.loads(parsed_str)
        chosen_topic = selection_data.get("topic", "AI Automation Trends")
        selection_reason = selection_data.get("reason", "High search popularity.")

    log.info(f"[Swarm Selected Topic]: '{chosen_topic}' (Reason: {selection_reason})")

    # 2. Scriptwriting
    target_words = 180 if shorts_only else SCRIPT_WORDS
    script_prompt = (
        f"Write an engaging podcast script about '{chosen_topic}'.\n"
        f"Niche context: {NICHE}.\n"
        f"Length: At least {target_words} words. Dialogue only."
    )
    raw_script = script_writer.run(script_prompt)

    # 3. Script Editing
    edit_prompt = (
        f"Script to edit:\n{raw_script}\n\n"
        f"Ensure length matches {target_words} words. Strip bracketed placeholders and markdown elements."
    )
    clean_script = script_editor.run(edit_prompt)
    
    # Strip LLM script headers/metadata
    clean_script = re.sub(r'\[.*?\]', '', clean_script).strip()
    # Remove bold markers
    clean_script = clean_script.replace("**", "").replace("__", "")
    
    word_count = len(clean_script.split())
    log.info(f"[Swarm Script Finalized]: {word_count} words.")

    # 4. Creative Direction (Scene Mapping)
    director_prompt = (
        f"Topic: {chosen_topic}\n"
        f"Script:\n{clean_script}\n\n"
        f"Map this script into consecutive visual scenes."
    )
    director_res = creative_director.run(director_prompt)
    scenes_data = json.loads(clean_json_string(director_res))
    scenes_list = scenes_data.get("scenes", [])
    log.info(f"[Swarm Creative Director]: Planned {len(scenes_list)} scenes.")

    # 5. SEO Optimization
    seo_prompt = (
        f"Topic: {chosen_topic}\n"
        f"Script length: {word_count} words.\n"
        "Generate optimized title, description (with 0:00 - Intro placeholder), tags, and thumbnail text."
    )
    seo_res = seo_agent.run(seo_prompt)
    seo_metadata = json.loads(clean_json_string(seo_res))
    log.info(f"[Swarm SEO]: Generated metadata (Title: '{seo_metadata.get('title')}')")

    # Assemble Draft
    draft = {
        "chosen_topic": chosen_topic,
        "reason": selection_reason,
        "seo_title": seo_metadata.get("title", "AI Revolution"),
        "seo_description": seo_metadata.get("description", ""),
        "tags": seo_metadata.get("tags", []),
        "thumbnail_text": seo_metadata.get("thumbnail_text", "AI NEW"),
        "thumbnail_prompt": f"Cinematic 8k shot representing: {chosen_topic}",
        "script": clean_script,
        "scenes": scenes_list
    }

    # 6. Self-Correction QA Loop
    for qa_attempt in range(2):
        qa_prompt = f"Review this video data block for formatting issues or markdown artifacts:\n{json.dumps(draft, indent=2)}"
        qa_res = qa_agent.run(qa_prompt)
        qa_verdict = json.loads(clean_json_string(qa_res))
        
        if qa_verdict.get("passed", True):
            log.info("[Swarm QA Auditor]: Audit PASSED. Output is robust.")
            break
        else:
            instructions = qa_verdict.get("fix_instructions", "Clean formatting.")
            log.warning(f"[Swarm QA Auditor]: Audit FAILED on attempt {qa_attempt+1}. Instructions: {instructions}")
            
            # Apply corrections dynamically using editor
            correction_prompt = (
                f"We have the following draft:\n{json.dumps(draft, indent=2)}\n\n"
                f"Please correct the following issues:\n{instructions}\n\n"
                "Return the complete corrected JSON block with the same fields."
            )
            corrected_res = script_editor.run(correction_prompt)
            try:
                draft = json.loads(clean_json_string(corrected_res))
            except Exception as e:
                log.error(f"Failed to parse corrected JSON draft: {e}")
                break

    return draft


# -----------------------------------------------------------------
#  HELPERS
# -----------------------------------------------------------------

def clean_json_string(raw: str) -> str:
    """Extract and repair JSON boundaries from LLM text responses."""
    raw = raw.strip()
    match = re.search(r"\{[\s\S]+\}", raw)
    if match:
        raw = match.group()
    else:
        # Match array if raw was just array
        match_arr = re.search(r"\[[\s\S]+\]", raw)
        if match_arr:
            raw = match_arr.group()
            
    # Remove markdown code blocks if any
    raw = raw.replace("```json", "").replace("```", "").strip()
    return raw
