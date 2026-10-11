import requests
import re

voice_data = {
    "Warm & Friendly Voices": [
        {"voice": "en-US-AndrewNeural", "characteristics": ["Warm", "Confident"], "age_group": "Adult Male"},
        {"voice": "zh-CN-XiaoxiaoNeural", "characteristics": ["Warm"], "age_group": "Young Female"},
        {"voice": "es-ES-ElviraNeural", "characteristics": ["Friendly"], "age_group": "Adult Female"}
    ],
    "Cheerful & Lively Voices": [
        {"voice": "en-US-EmmaNeural", "characteristics": ["Cheerful"], "age_group": "Young Female"},
        {"voice": "zh-CN-YunxiNeural", "characteristics": ["Lively", "Sunshine"], "age_group": "Child Male"},
        {"voice": "ja-JP-NanamiNeural", "characteristics": ["Friendly", "Positive"], "age_group": "Teen Female"}
    ],
    "Professional & Reliable Voices": [
        {"voice": "en-US-ChristopherNeural", "characteristics": ["Reliable", "Authority"], "age_group": "Adult Male"},
        {"voice": "zh-CN-YunyangNeural", "characteristics": ["Professional"], "age_group": "Middle-aged Male"},
        {"voice": "de-DE-ConradNeural", "characteristics": ["Friendly", "Positive"], "age_group": "Adult Male"}
    ],
    "Expressive & Emotional Voices": [
        {"voice": "en-US-AvaNeural", "characteristics": ["Expressive", "Caring"], "age_group": "Young Adult Female"},
        {"voice": "fr-FR-DeniseNeural", "characteristics": ["Friendly"], "age_group": "Middle-aged Female"},
        {"voice": "it-IT-IsabellaNeural", "characteristics": ["Friendly"], "age_group": "Adult Female"}
    ],
    "Cute & Playful Voices": [
        {"voice": "en-US-AnaNeural", "characteristics": ["Cute"], "age_group": "Child Female"},
        {"voice": "zh-CN-YunxiaNeural", "characteristics": ["Cute"], "age_group": "Young Female"},
        {"voice": "es-MX-DaliaNeural", "characteristics": ["Friendly"], "age_group": "Teen Female"}
    ],
    "Passionate & Energetic Voices": [
        {"voice": "en-US-GuyNeural", "characteristics": ["Passion"], "age_group": "Adult Male"},
        {"voice": "zh-CN-YunjianNeural", "characteristics": ["Passion"], "age_group": "Young Male"},
        {"voice": "hi-IN-SwaraNeural", "characteristics": ["Friendly"], "age_group": "Young Female"}
    ],
    "Humorous & Bright Voices": [
        {"voice": "zh-CN-liaoning-XiaobeiNeural", "characteristics": ["Humorous"], "age_group": "Teen Male"},
        {"voice": "pt-BR-AntonioNeural", "characteristics": ["Friendly"], "age_group": "Adult Male"},
        {"voice": "ru-RU-DmitryNeural", "characteristics": ["Friendly"], "age_group": "Middle-aged Male"}
    ],
    "Elderly & Wise Voices": [
        {"voice": "en-GB-ThomasNeural", "characteristics": ["Friendly"], "age_group": "Senior Male"},
        {"voice": "fr-CA-SylvieNeural", "characteristics": ["Friendly"], "age_group": "Senior Female"},
        {"voice": "ar-SA-HamedNeural", "characteristics": ["Friendly"], "age_group": "Middle-aged Male"}
    ],
    "Young & Energetic Voices": [
        {"voice": "en-US-JennyNeural", "characteristics": ["Friendly", "Comfort"], "age_group": "Teen Female"},
        {"voice": "es-AR-ElenaNeural", "characteristics": ["Friendly"], "age_group": "Young Adult Female"},
        {"voice": "ko-KR-SunHiNeural", "characteristics": ["Friendly"], "age_group": "Young Female"}
    ],
    "Multilingual & Versatile Voices": [
        {"voice": "en-US-AvaMultilingualNeural", "characteristics": ["Expressive"], "age_group": "Young Adult Female"},
        {"voice": "de-DE-SeraphinaMultilingualNeural", "characteristics": ["Friendly"], "age_group": "Adult Female"},
        {"voice": "fr-FR-VivienneMultilingualNeural", "characteristics": ["Friendly"], "age_group": "Adult Female"}
    ]
}

def recommend_voice(user_input):
    all_voice_descriptions = []
    for category, voices in voice_data.items():
        for voice in voices:
            all_voice_descriptions.append(
                f"Voice ID: {voice['voice']} | Characteristics: {', '.join(voice['characteristics'])} | Age Group: {voice['age_group']} | Category: {category}"
            )

    full_voice_list = "\n".join(all_voice_descriptions)

    prompt = f"""You are a voice selection assistant. Your job is to find the **most suitable voice** for the user input.Prioritize the age and gender constraint in the user input

User description: "{user_input}"

Available voice options:
{full_voice_list}

Reply with ONLY the most appropriate voice ID in brackets like this: [voice-id]
Make sure that the voice best suits the age and gender before responding
"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3}
            },
        )
        result = response.json()['response']
        print("Raw Model Output:", result)

        match = re.search(r'\[([a-zA-Z\-]+Neural)\]', result)
        if match:
            return match.group(1)
        else:
            print("No matching voice ID found.")
            return None

    except Exception as e:
        print("Voice recommendation error:", e)
        return None

def map_audio(story_data):
    # Make a copy of the input dictionary to avoid modifying the original
    story_with_voices = story_data.copy()
    
    # Process each character in the story
    for character in story_with_voices['characters']:
        # Get the character's description
        description = character['description']
        
        # Get recommended voice based on the description
        voice_id = recommend_voice(description)
        
        # Add the voice_id to the character dictionary
        character['voice_id'] = voice_id if voice_id else "en-US-JennyNeural"  # default fallback
    
    return story_with_voices

