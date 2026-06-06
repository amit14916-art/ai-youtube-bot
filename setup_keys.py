#!/usr/bin/env python
"""
Quick Setup Script - Set API Keys for AI YouTube Bot
Run this once to configure your bot with API keys.
"""

import os
import sys
import json
from pathlib import Path

def setup_api_keys():
    """Interactive setup for API keys"""
    print("=" * 70)
    print("  🔑 AI YouTube Bot - API Keys Setup")
    print("=" * 70)
    print()
    
    keys_to_set = {
        "GROQ_API_KEY": {
            "prompt": "GROQ API Key (from https://console.groq.com/keys)",
            "required": True,
            "url": "https://console.groq.com/keys"
        },
        "YOUTUBE_API_KEY": {
            "prompt": "YouTube API Key (from Google Cloud Console)",
            "required": False,
            "url": "https://console.cloud.google.com/"
        },
        "GEMINI_API_KEY": {
            "prompt": "Gemini API Key (from https://aistudio.google.com/app/apikeys)",
            "required": False,
            "url": "https://aistudio.google.com/app/apikeys"
        },
        "GOOGLE_SEARCH_API_KEY": {
            "prompt": "Google Custom Search API Key (optional)",
            "required": False,
            "url": "https://console.cloud.google.com/"
        },
        "PEXELS_API_KEY": {
            "prompt": "Pexels API Key for stock footage (optional)",
            "required": False,
            "url": "https://www.pexels.com/api/"
        },
        "ELEVENLABS_API_KEY": {
            "prompt": "ElevenLabs API Key for better audio (optional)",
            "required": False,
            "url": "https://elevenlabs.io/"
        },
    }
    
    env_vars = {}
    
    for key_name, config in keys_to_set.items():
        marker = "🔴 REQUIRED" if config["required"] else "🟡 Optional"
        print(f"\n{marker}: {key_name}")
        print(f"   Get it from: {config['url']}")
        
        value = input(f"   Enter {key_name} (or skip): ").strip()
        
        if value:
            env_vars[key_name] = value
            print(f"   ✅ Set")
        elif config["required"]:
            print(f"   ⚠️  Required! Please set this.")
            sys.exit(1)
        else:
            print(f"   ⏭️  Skipped")
    
    # Save to Windows registry (persistent)
    if os.name == 'nt':  # Windows
        print("\n" + "=" * 70)
        print("  Saving to Windows Environment (persistent)")
        print("=" * 70)
        for key_name, value in env_vars.items():
            try:
                os.system(f'setx {key_name} "{value}"')
                print(f"  ✅ {key_name} saved")
            except Exception as e:
                print(f"  ❌ Failed to set {key_name}: {e}")
    
    # Also set in current session
    print("\n" + "=" * 70)
    print("  Setting in current session")
    print("=" * 70)
    for key_name, value in env_vars.items():
        os.environ[key_name] = value
        print(f"  ✅ {key_name} ready")
    
    # Create .env file as backup
    env_file = Path(__file__).parent / ".env"
    print(f"\n💾 Creating backup .env file: {env_file}")
    with open(env_file, "w") as f:
        for key_name, value in env_vars.items():
            f.write(f"{key_name}={value}\n")
    print(f"  ✅ Saved")
    
    # Test import
    print("\n" + "=" * 70)
    print("  Testing configuration")
    print("=" * 70)
    
    try:
        from config.settings import GROQ_API_KEY, YOUTUBE_API_KEY, GEMINI_API_KEY
        
        print(f"\n  GROQ_API_KEY set: {bool(GROQ_API_KEY)}")
        print(f"  YOUTUBE_API_KEY set: {bool(YOUTUBE_API_KEY)}")
        print(f"  GEMINI_API_KEY set: {bool(GEMINI_API_KEY)}")
        
        if GROQ_API_KEY or GEMINI_API_KEY:
            print("\n  ✅ Configuration looks good!")
        else:
            print("\n  ⚠️  No LLM key set - bot will fail during research!")
            
    except Exception as e:
        print(f"  ❌ Error testing: {e}")
    
    print("\n" + "=" * 70)
    print("  Next Steps:")
    print("=" * 70)
    print("\n  1. Restart PowerShell (to load new environment variables)")
    print("  2. Run: python main.py --dry-run")
    print("  3. Check output/ folder for generated video")
    print("  4. Run: python main.py (to upload to YouTube)")
    print("\n")

if __name__ == "__main__":
    try:
        setup_api_keys()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
