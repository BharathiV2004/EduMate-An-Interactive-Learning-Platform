import requests
import json
import re
from uuid import uuid4

def gen_flipcard(topic, max_pairs=10, filename=r"D:\edumate\dataset_collection\game_flip.json"):
    """
    Generates term-definition pairs with unique IDs in this format:
    {
        "topic": [
            {"id": "unique1", "term": "...", "definition": "..."},
            {"id": "unique2", "term": "...", "definition": "..."}
        ]
    }
    """
    prompt = f"""Generate exactly {max_pairs} concise term-definition pairs about '{topic}' using this EXACT format:

Term: [Single word or short phrase]
Definition: [Clear explanation in one short sentence]

Separate pairs with '---' and include nothing else. Keep definitions under 15 words."""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "qwen2.5:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7}
            },
        ).json()['response']

        pairs = []
        seen_terms = set()
        
        for pair_text in re.split(r'-{3,}', response):  # Split on 3+ dashes
            pair_text = pair_text.strip()
            if not pair_text:
                continue

            # Robust extraction using regex
            term_match = re.search(r'Term:\s*(.+?)\s*(?=\n|$)', pair_text, re.IGNORECASE)
            def_match = re.search(r'Definition:\s*(.+?)\s*(?=\n|$)', pair_text, re.IGNORECASE)

            if term_match and def_match:
                term = term_match.group(1).strip()
                definition = def_match.group(1).strip()
                
                # Validate and ensure uniqueness
                if (term and definition and 
                    len(definition.split()) <= 15 and
                    term not in seen_terms):
                    
                    # Generate short unique ID based on topic and term
                    short_id = f"{topic[:2].lower()}{str(len(pairs)+1)}"
                    pairs.append({
                        "id": short_id,
                        "term": term,
                        "definition": definition
                    })
                    seen_terms.add(term)

        # Prepare final structure
        result = {
            topic: pairs[:max_pairs]  # Ensure we don't exceed max
        }

        # Atomic write operation
        temp_filename = f"{filename}.tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Replace old file only if new one is good
        import os
        os.replace(temp_filename, filename)

        print(f"✅ Generated {len(pairs[:max_pairs])} term-definition pairs with IDs in {filename}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {str(e)}")
        return {"None":[]}
    except json.JSONDecodeError:
        print("❌ Invalid API response format")
        return {"None":[]}
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return {"None":[]}

def extract_part(text, marker):
    """Helper to cleanly extract each component"""
    if marker in text:
        return text.split(marker)[1].split('\n')[0].strip()
    return ""

if __name__ == "__main__":
    topic = input("Enter the topic for your flipcard game: ").strip()
    while not topic:
        print("Topic cannot be empty")
        topic = input("Enter the topic for your flipcard game: ").strip()

    try:
        max_pairs = int(input("How many term-definition pairs do you want? (6-20, default 10): ") or 10)
        max_pairs = max(4, min(10, max_pairs))  # Clamp between 4-10
    except ValueError:
        max_pairs = 10
        print("Using default value of 10 pairs")

    success = generate_flipcard_data(topic, max_pairs)
    if success:
        print("\nSample output:")
        with open(r"D:\edumate\dataset_collection\game_flip.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            sample = data[topic][0]
            print(json.dumps(sample, indent=2))