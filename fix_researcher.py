content = open('modules/researcher.py', 'r', encoding='utf-8').read()

# Find and fix the broken get_llm_client function
broken = (
    '    p = provider or LLM_PROVIDER\r\n'
    '    elif p == "gemini":\r\n'
    '        from google import genai as google_genai\r\n'
    '        client_obj = google_genai.Client(api_key=GEMINI_API_KEY)\r\n'
    '        return client_obj, "gemini"\r\n'
    '        import anthropic\r\n'
    '        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), "anthropic"\r\n'
    '    elif p == "openai":\r\n'
)

fixed = (
    '    p = provider or LLM_PROVIDER\r\n'
    '    if p == "gemini":\r\n'
    '        from google import genai as google_genai\r\n'
    '        client_obj = google_genai.Client(api_key=GEMINI_API_KEY)\r\n'
    '        return client_obj, "gemini"\r\n'
    '    elif p == "anthropic":\r\n'
    '        import anthropic\r\n'
    '        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY), "anthropic"\r\n'
    '    elif p == "openai":\r\n'
)

if broken in content:
    content = content.replace(broken, fixed)
    open('modules/researcher.py', 'w', encoding='utf-8').write(content)
    print('SUCCESS: Fixed get_llm_client!')
else:
    # Try with \n instead of \r\n
    broken2 = broken.replace('\r\n', '\n')
    fixed2 = fixed.replace('\r\n', '\n')
    if broken2 in content:
        content = content.replace(broken2, fixed2)
        open('modules/researcher.py', 'w', encoding='utf-8').write(content)
        print('SUCCESS: Fixed get_llm_client (LF)!')
    else:
        print('Pattern not found!')
        idx = content.find('p = provider or LLM_PROVIDER')
        print(repr(content[idx:idx+400]))
