import requests
import io
import time
import os
import json
from PIL import Image

# Load API keys from environment variable (comma-separated)
total_keys = os.getenv("HF_KEYS", "").split(",")
curr_idx = len(total_keys) - 1
curr_key = total_keys[curr_idx] if curr_idx >= 0 else None

IMAGE_DIR = "D:/Downloads/Edumate/static/images"

# Ensure the image directory exists
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Internal API query function
def query(prompt):
    global curr_idx
    global curr_key

    if not curr_key:
        print("❌ No Hugging Face API keys found. Please set HF_KEYS environment variable.")
        return None

    try:
        API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
        HEADERS = {"Authorization": f"Bearer {curr_key}"}
        response = requests.post(API_URL, headers=HEADERS, json={
            "inputs": f"Create an animated simple image of the following: {prompt}",
            "options": {"wait_for_model": True}
        })

        # Handle successful image response
        if response.headers.get("Content-Type") in ["image/png", "image/jpeg"]:
            return response.content

        # Handle error response
        error_data = response.json()
        print(f"❌ API Error: {error_data}")
        curr_idx = max(0, curr_idx - 1)
        curr_key = total_keys[curr_idx] if curr_idx >= 0 else None
        return None

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

# Prompt image generation function
def generate_image(name, prompt):
    max_retries = 3
    wait_time = 10  # seconds

    for attempt in range(max_retries):
        print(f"🔄 Generating image for {name} (Attempt {attempt + 1})...")
        image_bytes = query(prompt)

        if image_bytes:
            try:
                image = Image.open(io.BytesIO(image_bytes))
                image_path = os.path.join(IMAGE_DIR, f"{name}.png")
                image_path = image_path.replace(" ", "_").replace("\\", "/")
                image.save(image_path)
                print(f"✅ Image saved as '{image_path}'")
                return image_path
            except Exception as e:
                print(f"❌ Image processing failed: {e}")
        else:
            print(f"⏳ Attempt {attempt + 1} failed. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    print("❌ All attempts failed. Check your API key and model status.")
    return None

# Process the story JSON
def gen_image(story_json):
    # Generate character images
    for character in story_json['characters']:
        prompt = f"A simple animated character of {character['name']}, {character['description']}"
        image_path = generate_image(f"character_{character['name']}", prompt)
        if image_path:
            character['image_path'] = image_path

    # Generate scene images
    for scene in story_json['scenes']:
        prompt = f"A simple animated scene (with only non living things) of {scene['scene_title']}, {scene['setting']}"
        image_path = generate_image(f"scene_{scene['scene_number']}", prompt)
        if image_path:
            scene['scene_image_path'] = image_path

    return story_json
