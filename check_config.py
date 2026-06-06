#!/usr/bin/env python
"""
Diagnostic Tool - Check Bot Configuration
"""

import os
import sys
from pathlib import Path

def check_config():
    """Check all configuration"""
    print("=" * 70)
    print("  🔍 AI YouTube Bot - Configuration Diagnostic")
    print("=" * 70)
    
    # 1. Check files
    print("\n📁 FILES:")
    print("-" * 70)
    
    files_to_check = {
        "config/settings.py": "Settings file",
        "config/client_secrets.json": "YouTube OAuth credentials",
        "config/token.json": "YouTube auth token",
        ".env": "Environment variables file",
    }
    
    for file_path, desc in files_to_check.items():
        full_path = Path(file_path)
        exists = "✅" if full_path.exists() else "❌"
        print(f"  {exists} {file_path:30s} ({desc})")
    
    # 2. Check environment variables
    print("\n🔑 ENVIRONMENT VARIABLES:")
    print("-" * 70)
    
    keys_to_check = [
        "GROQ_API_KEY",
        "GEMINI_API_KEY", 
        "YOUTUBE_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "PEXELS_API_KEY",
        "ELEVENLABS_API_KEY",
    ]
    
    for key in keys_to_check:
        value = os.getenv(key)
        if value:
            # Show first 10 and last 5 chars
            masked = f"{value[:10]}...{value[-5:]}"
            print(f"  ✅ {key:30s} = {masked}")
        else:
            print(f"  ❌ {key:30s} = NOT SET")
    
    # 3. Check Python imports
    print("\n📦 PYTHON IMPORTS:")
    print("-" * 70)
    
    imports_to_check = [
        ("pytrends", "Google Trends research"),
        ("groq", "Groq LLM"),
        ("google.generativeai", "Gemini LLM"),
        ("google_auth_oauthlib", "YouTube OAuth"),
        ("googleapiclient", "YouTube API"),
        ("edge_tts", "Text-to-Speech"),
        ("moviepy.editor", "Video creation"),
    ]
    
    for module, desc in imports_to_check:
        try:
            __import__(module)
            print(f"  ✅ {module:30s} ({desc})")
        except ImportError:
            print(f"  ❌ {module:30s} ({desc}) - MISSING")
    
    # 4. Check settings values
    print("\n⚙️  SETTINGS VALUES:")
    print("-" * 70)
    
    try:
        from config.settings import (
            GROQ_API_KEY, GEMINI_API_KEY, YOUTUBE_API_KEY,
            NICHE, PRIVACY_STATUS, UPLOAD_HOUR, FONT_PATH
        )
        
        print(f"  GROQ API Key:        {'✅ SET' if GROQ_API_KEY else '❌ NOT SET'}")
        print(f"  Gemini API Key:      {'✅ SET' if GEMINI_API_KEY else '❌ NOT SET'}")
        print(f"  YouTube API Key:     {'✅ SET' if YOUTUBE_API_KEY else '❌ NOT SET'}")
        print(f"  Niche:               {NICHE}")
        print(f"  Privacy Status:      {PRIVACY_STATUS}")
        print(f"  Upload Time:         {UPLOAD_HOUR:02d}:00 UTC")
        print(f"  Font Path:           {'✅ Valid' if Path(FONT_PATH).exists() else '❌ Invalid'}")
        
    except Exception as e:
        print(f"  ❌ Error loading settings: {e}")
    
    # 5. Test OAuth file
    print("\n🔐 YOUTUBE OAUTH:")
    print("-" * 70)
    
    oauth_file = Path("config/client_secrets.json")
    if oauth_file.exists():
        try:
            import json
            with open(oauth_file) as f:
                data = json.load(f)
            if "installed" in data and "client_id" in data["installed"]:
                print(f"  ✅ Valid OAuth credentials found")
                print(f"     Client ID: {data['installed']['client_id'][:20]}...")
            else:
                print(f"  ❌ OAuth file format invalid")
        except Exception as e:
            print(f"  ❌ Error reading OAuth file: {e}")
    else:
        print(f"  ❌ OAuth file missing: {oauth_file}")
    
    # 6. Check output directory
    print("\n📂 OUTPUT DIRECTORY:")
    print("-" * 70)
    
    output_dir = Path("output")
    if output_dir.exists():
        files = list(output_dir.glob("*"))
        print(f"  ✅ Output directory exists")
        print(f"     Files: {len(files)}")
        
        # Show recent files
        recent = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        for f in recent:
            print(f"       - {f.name}")
    else:
        print(f"  ❌ Output directory missing: {output_dir}")
    
    # 7. Final status
    print("\n" + "=" * 70)
    print("  📊 STATUS SUMMARY:")
    print("=" * 70)
    
    try:
        from config.settings import GROQ_API_KEY, GEMINI_API_KEY
        
        if GROQ_API_KEY or GEMINI_API_KEY:
            print("\n  ✅ Bot is ready to run!")
            print("\n  Next step:")
            print("     python main.py --dry-run")
        else:
            print("\n  ⚠️  MISSING API KEYS - Bot cannot run")
            print("\n  Next step:")
            print("     python setup_keys.py")
            
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
    
    print("\n")

if __name__ == "__main__":
    check_config()
