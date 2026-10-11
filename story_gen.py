import requests
import json
import re

# Define the base URL for the Ollama server
base_url = 'http://localhost:11434'
generate_endpoint = f'{base_url}/api/generate'

def gen_story(content):
    # Build the prompt with TWO examples
    prompt = f'''Please create a story that explains the following concept/content in an engaging and educational manner suitable for readers aged 15-28:

"{content}"

Strictly follow this exact structure without changing any headers, symbols, or numbering:

Example 1:

*Topic*: Photosynthesis
*Story Name*: The Magical Leaf

*Characters:*
1. *Lily*: A curious 16-year-old girl who loves nature.(Female,16 years old)
2. *Professor*: A wise botanist, 50 years old, patient and kind.(Male,50 years old)

*Scene 1: Discovery*
Setting: A sunny garden filled with vibrant plants.

*Lily*: "Professor, how do plants make their food?"
*Professor*: "Ah, that's called photosynthesis! Let me explain."

---

*Scene 2: The Science Behind It*
Setting: Inside a cozy laboratory full of plants and tools.

*Professor*: "Plants use sunlight, water, and carbon dioxide to create energy."
*Lily*: "Wow, plants are like little factories!"

---

Example 2:

*Topic*: Internet Safety
*Story Name*: The Digital Guardian

*Characters:*
1. *Alex*: 17-year-old tech-savvy boy.(Male,17 years old)
2. *Mrs_Moore*: 45-year-old school IT teacher, caring and wise.(Female,45 years old)

*Scene 1: The Warning*
Setting: High school computer lab.

*Alex*: "I clicked a link and now weird ads are popping up!"
*Mrs_Moore*: "You may have clicked on a phishing link, Alex. Let me show you how to stay safe."

---

*Scene 2: Learning to Protect*
Setting: School auditorium during an internet safety seminar.

*Mrs_Moore*: "Always verify links and never share personal info online."
*Alex*: "Got it! I'll be more careful from now on."

---

Now, generate the story for the concept provided above following the exact same structure.

Rules:
- Make clear choices of characters.
- The story can be  a little long(upto 4 or 5 scenes) but reasonable and it should explain all aspects of the content clearly.
- Make sure that the story has clear fllow before responding.
- Make sure you add gender and age of the character in the characters sectiona as in the example.
- Use reasonable amount of content to generate stories.
- Do not add any extra commentary or text outside this format.
- Use exact header styles (*Topic*: , *Story Name*: , *Characters:*, *Scene 1: Title* etc.).
- Dialogues must exactly follow: *Character_Name*: "Dialogue"
- If you mistakenly generate wrong format, redo internally before responding.
'''

    # Send request to Ollama
    payload = {'model': 'qwen2.5:latest', 'prompt': prompt, 'stream': False}
    try:
        response = requests.post(generate_endpoint, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None

    generated_text = response.json().get('response', '')
    if not generated_text.strip():
        print("Error: Empty response")
        return None

    print("\nGenerated Raw Response:\n", generated_text)

    # === Extraction Section ===

    # Extract Topic
    topic_match = re.search(r"\*Topic\*:\s*(.+)", generated_text)
    topic = topic_match.group(1).strip() if topic_match else "Unknown Topic"

    # Extract Story Name
    story_match = re.search(r"\*Story Name\*:\s*(.+)", generated_text)
    story_name = story_match.group(1).strip() if story_match else "Untitled Story"

    # Extract Characters
    characters = []
    characters_section = re.search(r"\*Characters:\*\s*((?:.|\n)+?)\n\s*\*Scene\s*\d+", generated_text)
    if characters_section:
        character_lines = characters_section.group(1).strip().splitlines()
        for line in character_lines:
            line = line.strip()
            match = re.match(r"(?:\d+\.\s*|\-\s*)(\*?.+?\*?)\s*:\s*(.+)", line)
            if match:
                name = match.group(1).strip("* ").strip()
                description = match.group(2).strip()
                characters.append({"name": name, "description": description})

    # Extract Scenes
    scenes = []
    scene_pattern = re.compile(
        r"\*Scene\s*(\d+):\s*(.+?)\*\s*\nSetting:\s*(.+?)\n\n((?:\*.+?:\s*\".*?\"\n?)+)",
        re.DOTALL
    )
    for num, title, setting, body in scene_pattern.findall(generated_text):
        dialogues = []
        dialogue_lines = body.strip().splitlines()
        for line in dialogue_lines:
            m = re.match(r"\*?(.+?)\*?\s*:\s*\"(.*?)\"", line.strip())
            if m:
                character = m.group(1).strip()
                dialogue = m.group(2).strip()
                dialogues.append({"character": character, "line": dialogue})
        scenes.append({
            "scene_number": int(num),
            "scene_title": title.strip(),
            "setting": setting.strip(),
            "dialogues": dialogues
        })

    # === Final Story Assembly ===
    story_data = {
        "topic": topic,
        "story_name": story_name,
        "characters": characters,
        "scenes": scenes
    }

    return story_data

# Example usage
if __name__ == "__main__":
    concept = "Firewall and its importance"
    story = gen_story(concept)
    if story:
        print("\nStructured Story JSON:\n")
        print(json.dumps(story, indent=2, ensure_ascii=False))
