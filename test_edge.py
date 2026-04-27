import asyncio
import edge_tts

async def amain() -> None:
    TEXT = "This is a test of the new high quality free voice. It replaces ElevenLabs when the key fails."
    VOICE = "en-US-AndrewNeural"
    OUTPUT_FILE = "test_voice_edge.mp3"
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(OUTPUT_FILE)
    print(f"Success! Voice saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(amain())
