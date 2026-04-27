import os

targets = [
    'modules/audio_generator.py',
    'modules/video_creator.py',
    'modules/researcher.py',
    'main.py',
    'modules/uploader.py'
]

replacements = {
    '\u2500': '-',  # Light horizontal
    '\u2192': '->', # Arrow
    '\u2713': '[OK]', # Checkmark
    '\u2550': '=',  # Heavy horizontal
}

for path in targets:
    if not os.path.exists(path):
        print(f"Skipping {path}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    orig = content
    for k, v in replacements.items():
        content = content.replace(k, v)
    
    if orig != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {path}")
    else:
        print(f"No changes for {path}")
