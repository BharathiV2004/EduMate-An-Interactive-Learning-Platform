#!/usr/bin/env python3
import subprocess
import json
import re

def gen_crossword(topic):
    prompt = f"""Generate a 15x15 crossword puzzle about '{topic}' in JSON format. Follow these rules:

1. Grid: 15x15 with '#' for blocked cells and '.' for open cells
2. Words: 7-10 relevant words, all uppercase
3. For each word include:
   - word
   - clue (complete sentence)
   - direction ("across" or "down")
   - row/col (1-indexed)
   - number
4. Output MUST be valid JSON with this exact structure:
{{
    "crosswords": [
        {{
            "grid": [
                ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "#"],
                ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"]
            "words": [
                {{
                    "word": "EXAMPLE",
                    "clue": "Sample clue",
                    "direction": "across",
                    "row": 2,
                    "col": 3,
                    "number": 1
                }}
            ]
        }}
    ]
}}

IMPORTANT:
- All words must fit properly
- No overlapping conflicts
- Output ONLY the raw JSON with no additional text or commentary"""

    try:
        # Run Qwen2.5 via Ollama
        result = subprocess.run(
            ["ollama", "run", "qwen2.5", prompt],
            encoding='utf-8',  # Add this line
            errors='ignore',
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract JSON (multiple methods for robustness)
        json_str = result.stdout.strip()
        
        # Method 1: Try parsing directly
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError:
            # Method 2: Extract between curly braces
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                raise ValueError("No JSON found in output")
                
    except Exception as e:
        print(f"Error generating crossword: {e}")
        return None



if __name__ == "__main__":
    topic = input("Enter the topic for your crossword puzzle: ")
    crossword_data = gen_crossword(topic)
    print(crossword_data)
    
