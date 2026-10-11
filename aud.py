import os
import edge_tts
import asyncio
from typing import Dict, List
import re
import sys

AUDIO_OUTPUT_DIR = r"D:\Downloads\Edumate\static\audio"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

def clean_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

async def generate_audio(voice_id: str, text: str, output_path: str) -> str:
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        print(f"[ERROR] Failed to generate audio: {e}")
        return None

async def process_scene_dialogues(scene: Dict, characters: List[Dict]) -> Dict:
    scene_with_audio = scene.copy()
    scene_with_audio['dialogues_with_audio'] = []

    for dialogue in scene.get('dialogues', []):
        character_name = dialogue['character']
        line = dialogue['line']
        voice_id = next((c['voice_id'] for c in characters if c['name'] == character_name), "en-US-JennyNeural")

        scene_num = scene.get('scene_number', 0)
        clean_char_name = clean_filename(character_name)
        output_filename = f"scene_{scene_num}_{clean_char_name}_{abs(hash(line))}.mp3"
        output_path = os.path.join(AUDIO_OUTPUT_DIR, output_filename)

        audio_path = await generate_audio(voice_id, line, output_path)
        output_path=output_path.replace("\\","/")
        if audio_path:
            dialogue_with_audio = dialogue.copy()
            dialogue_with_audio['audio_path'] = output_path
            scene_with_audio['dialogues_with_audio'].append(dialogue_with_audio)

    return scene_with_audio

async def gen_audio(story_data: Dict) -> Dict:
    story_with_audio = story_data.copy()
    characters = story_with_audio.get('characters', story_with_audio.get('charaters', []))

    processed_scenes = []
    for scene in story_with_audio['scenes']:
        processed_scene = await process_scene_dialogues(scene, characters)
        processed_scenes.append(processed_scene)

    story_with_audio['scenes'] = processed_scenes
    return story_with_audio

# ✅ Wrapper that avoids crashing FastAPI or notebooks
def generate_audio_sync(story_data: Dict) -> Dict:
    try:
        loop = asyncio.get_running_loop()
        # Already inside an async context (FastAPI, Jupyter, etc.)
        future = asyncio.ensure_future(gen_audio(story_data))
        return loop.run_until_complete(future)
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(gen_audio(story_data))

# -----------------------------------
# CLI test block (WILL NOT RUN on server reboot)
# -----------------------------------
if __name__ == "__main__":
    # Test story for CLI use
    example_story = {
        "topic": "Photosynthesis",
        "story_name": "The Great Green Adventure",
        "characters": [
            {"name": "Leafy", "voice_id": "en-US-EmmaNeural"},
            {"name": "Sunshine", "voice_id": "zh-CN-YunyangNeural"},
            {"name": "Water", "voice_id": "zh-CN-XiaoxiaoNeural"},
            {"name": "Carbon Dioxide", "voice_id": "en-US-EmmaNeural"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "scene_title": "Sunlit Garden",
                "setting": "A garden...",
                "dialogues": [
                    {"character": "Leafy", "line": "I'm so excited to learn!"},
                    {"character": "Sunshine", "line": "Hello Leafy! Let's explore!"},
                    {"character": "Water", "line": "I'm bringing life to all!"}
                ]
            }
        ]
    }

    result = generate_audio_sync(example_story)
    print("✅ Audio generation done.")
