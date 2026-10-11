import requests
import json

def extract_topic_qwen(content):
    """Extract a concise topic title from provided content using Qwen."""
    prompt = f"""Extract a concise topic title (2-5 words) from the following content. Include key words at last but short.Return only the topic title without extra text.

Content:
{content}
"""
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            "model": "qwen2.5:latest",
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()['response'].strip()

def extract_part(text, marker):
    """Helper to cleanly extract each card component"""
    if marker in text:
        return text.split(marker)[1].split('\n')[0].strip()
    return ""

def gen_flashcards(content, max_cards=10):
    """
    Accepts raw content, extracts topic using Qwen, generates high-quality flashcards, and returns them as a dictionary.
    """
    topic = extract_topic_qwen(content)

    prompt = f"""Generate exactly {max_cards} high-quality flashcards about '{topic}' using this EXACT format for each:

Front: [Conceptual question]
Answer: [Concise explanation]
Analogy: [Real-world comparison]
Mistake: [Common misunderstanding]

Separate cards with '---' and include nothing else."""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7}
            }
        ).json()['response']

        cards = []
        for card_text in response.split('---'):
            parts = {
                "front": extract_part(card_text, "Front:"),
                "answer": extract_part(card_text, "Answer:"),
                "analogy": extract_part(card_text, "Analogy:"),
                "mistake": extract_part(card_text, "Mistake:")
            }

            if all(parts.values()):
                cards.append({
                    "front": parts["front"],
                    "back": {
                        "answer": parts["answer"],
                        "analogy": parts["analogy"],
                        "common_mistake": parts["mistake"]
                    }
                })

        result = {
            "topic": topic,
            "card_count": len(cards),
            "cards": cards[:max_cards]
        }

        print(f"✅ Generated {len(cards)} flashcards for topic: {topic}")
        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

# Example usage:
# content = "Photosynthesis is the process used by plants, algae and certain bacteria to harness energy from sunlight..."
# flashcard_data = generate_flashcards(content, max_cards=15)
# print(json.dumps(flashcard_data, indent=2))
