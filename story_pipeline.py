from story_gen import gen_story
from image_gen import gen_image
from audio_map import map_audio
from aud import generate_audio_sync as gen_audio
import json

def gen_story_pipe(content):
    story_data=gen_story(content)
    print("Story data generated")
    story_image=gen_image(story_data)
    print("Story image generated")
    mapped_with_audio=map_audio(story_image)
    print("Story audio mapped")
    print(mapped_with_audio)
    final=gen_audio(mapped_with_audio)
    print("Story generated")
    print(final)
    return final