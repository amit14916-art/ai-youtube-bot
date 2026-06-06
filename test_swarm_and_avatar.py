"""
test_swarm_and_avatar.py
Test script to run the Multi-Agent Swarm and verify avatar generation/overlay.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Force UTF-8 encoding for standard output and error
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# -----------------------------------------------------------------
#  MOCK LLM CALLS
# -----------------------------------------------------------------
def mock_call_agent_llm(prompt: str, system_prompt: str = "", json_mode: bool = False) -> str:
    sys_lower = system_prompt.lower()
    if "topic strategist" in sys_lower or "viral, high-interest" in sys_lower:
        return '{"topic": "The Rise of Autonomous AI Agents in 2026", "reason": "Autonomous AI agents are highly trending on YouTube with high search volume, high CTR potential, and extreme viewer interest."}'
    elif "scriptwriter specializing in" in sys_lower or "script writer" in sys_lower or "high-retention copywriting" in sys_lower:
        return (
            "Host A: The era of manual software is dead. Autonomous AI agents are taking over everything in 2026.\n"
            "Host B: Exactly. If you want to stay ahead of these rapid AI shifts, make sure to hit that subscribe button right now—we drop updates daily.\n"
            "Host A: These agents are executing complex workflows, building projects, and negotiating contracts without human intervention.\n"
            "Host B: It is a massive paradigm shift. If this blew your mind, drop a like and subscribe for more daily breakthroughs. See you tomorrow!"
        )
    elif "script editor" in sys_lower or "meticulous youtube script editor" in sys_lower:
        return (
            "Host A: The era of manual software is dead. Autonomous AI agents are taking over everything in 2026.\n"
            "Host B: Exactly. If you want to stay ahead of these rapid AI shifts, make sure to hit that subscribe button right now—we drop updates daily.\n"
            "Host A: These agents are executing complex workflows, building projects, and negotiating contracts without human intervention.\n"
            "Host B: It is a massive paradigm shift. If this blew your mind, drop a like and subscribe for more daily breakthroughs. See you tomorrow!"
        )
    elif "cinematic video director" in sys_lower or "creative director" in sys_lower:
        return '''{
  "scenes": [
    {
      "text": "The era of manual software is dead. Autonomous AI agents are taking over everything in 2026.",
      "keyword": "glowing server",
      "alt_keyword": "tech terminal",
      "prompt": "hyper-realistic 8k octane render, cinematic lighting, sharp focus, tech blue glow, Unreal Engine 5 style, glowing computer server racks"
    },
    {
      "text": "Exactly. If you want to stay ahead of these rapid AI shifts, make sure to hit that subscribe button right now—we drop daily updates.",
      "keyword": "neon circle",
      "alt_keyword": "glowing data",
      "prompt": "hyper-realistic 8k octane render, cinematic lighting, sharp focus, tech blue glow, Unreal Engine 5 style, cybernetic neon ring floating"
    },
    {
      "text": "These agents are executing complex workflows, building projects, and negotiating contracts without human intervention.",
      "keyword": "robot hands",
      "alt_keyword": "ai coding",
      "prompt": "hyper-realistic 8k octane render, cinematic lighting, sharp focus, tech blue glow, Unreal Engine 5 style, robotic hand interacting with holographic UI"
    },
    {
      "text": "It is a massive paradigm shift. If this blew your mind, drop a like and subscribe for more daily breakthroughs. See you tomorrow!",
      "keyword": "cyber grid",
      "alt_keyword": "glowing cyber",
      "prompt": "hyper-realistic 8k octane render, cinematic lighting, sharp focus, tech blue glow, Unreal Engine 5 style, high contrast dark tech background with grid"
    }
  ]
}'''
    elif "seo architect" in sys_lower or "seo optimizer" in sys_lower:
        return '''{
  "title": "Autonomous AI Agents are Taking Over 2026!",
  "description": "The era of manual software is dead. Autonomous AI agents are running the world. Subscribe to stay ahead: http://youtube.com/example/subscribe \\n\\nTimestamps:\\n0:00 - Intro\\n0:10 - The Rise of AI Agents\\n1:20 - Outro\\n\\n#ai #agents #technology #2026",
  "tags": ["ai agents", "autonomous agents", "artificial intelligence", "tech news"],
  "thumbnail_text": "AI AGENTS 2026"
}'''
    elif "qa auditor" in sys_lower or "quality control officer" in sys_lower:
        return '{"passed": true, "fix_instructions": ""}'
    else:
        return '{"passed": true, "fix_instructions": ""}'

# Inject Mock
import modules.agent_orchestrator
modules.agent_orchestrator.call_agent_llm = mock_call_agent_llm


def main():
    log.info("=== STEP 1: Running Multi-Agent Swarm Dry Run ===")
    from modules.agent_orchestrator import run_multi_agent_swarm
    
    # We will pass a custom topic to test the full scriptwriting, editing, and QA path
    topic = "The Rise of Autonomous AI Agents in 2026"
    log.info(f"Running swarm for topic: '{topic}'")
    
    try:
        draft = run_multi_agent_swarm(trends_data=[], custom_topic=topic, shorts_only=True)
        log.info("Swarm completed successfully!")
        log.info(f"Chosen Topic: {draft.get('chosen_topic')}")
        log.info(f"SEO Title   : {draft.get('seo_title')}")
        log.info(f"SEO Desc    : {draft.get('seo_description')[:150]}...")
        log.info(f"Script      : {draft.get('script')[:200]}...")
        log.info(f"Scenes Count: {len(draft.get('scenes', []))}")
        
        # Verify script criteria
        script = draft.get('script', '')
        has_hook = not any(greet in script[:50].lower() for greet in ["welcome", "hello", "hey guys", "in today's video"])
        has_subscribe = "subscribe" in script.lower()
        log.info(f"QA Check - Has explosive immediate hook: {has_hook}")
        log.info(f"QA Check - Has subscribe CTA: {has_subscribe}")
    except Exception as e:
        log.exception(f"Swarm failed: {e}")
        return

    log.info("\n=== STEP 2: Testing Avatar Generation ===")
    from modules.video_creator import create_presenter_avatar, create_video
    
    # Force removal of any existing test avatar files to verify fresh generation & caching
    from config.settings import NICHE, OUTPUT_DIR
    niche_slug = NICHE.replace(" ", "_").replace("/", "_").lower()
    avatar_long_path = os.path.join(OUTPUT_DIR, f"avatar_host_{niche_slug}_long.png")
    avatar_shorts_path = os.path.join(OUTPUT_DIR, f"avatar_host_{niche_slug}_shorts.png")
    for ap in [avatar_long_path, avatar_shorts_path]:
        if os.path.exists(ap):
            try:
                os.remove(ap)
                log.info(f"Removed existing avatar file to force fresh generation: {ap}")
            except Exception:
                pass

    try:
        # Generate long avatar
        avatar_long = create_presenter_avatar("test_job", is_shorts=False)
        log.info(f"Long avatar path: {avatar_long} (exists: {os.path.exists(avatar_long)})")
        
        # Generate shorts avatar
        avatar_shorts = create_presenter_avatar("test_job", is_shorts=True)
        log.info(f"Shorts avatar path: {avatar_shorts} (exists: {os.path.exists(avatar_shorts)})")
    except Exception as e:
        log.exception(f"Avatar generation failed: {e}")
        return

    log.info("\n=== STEP 3: Generating Mini Video Test Clip ===")
    try:
        from modules.audio_generator import generate_audio
        
        test_script = "Host A: This is a test. Host B: Perfect, the simple robot avatar should stay on screen."
        audio_res = generate_audio(test_script, "test_job")
        audio_path = audio_res.get("audio_path")
        log.info(f"Generated dummy audio at: {audio_path}")
        
        # Run video creation
        video_out = create_video(draft, audio_path, "test_job", is_shorts=True, audio_chunk_timing=audio_res.get("audio_chunk_timing", []))
        log.info(f"Render completed! Video saved at: {video_out}")
    except Exception as e:
        log.exception(f"Video rendering test failed: {e}")

if __name__ == "__main__":
    main()
