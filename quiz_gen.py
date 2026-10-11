import requests
import re
from textwrap import dedent
import datetime

def extract_topic_qwen(content):
    """Use Qwen to extract the most relevant topic title from content"""
    prompt = dedent(f"""
    Read the following content and provide the most relevant single-topic name or title that best describes the main subject of the content.Include key words at last but short. Respond ONLY with the topic title and nothing else.

    Content:
    {content}
    """)

    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            "model": "qwen2.5:latest",
            "prompt": prompt,
            "stream": False
        }
    )
    topic = response.json()['response'].strip()
    return topic

def generate_quiz(topic):
    print("Topic:", topic)
    """Generate quiz questions using Qwen for a specific topic"""
    prompt = dedent(f"""
    Create reasonable amount of questions(minimum 5,maximum 20) that are enough to test the user's clarity on the following topic/content that are innovative, engaging, intuitive, quality and reasonable quiz question about {topic} with:
    1. Multiple-choice questions (4 options each)
    2. Clear correct answers
    3. Detailed explanations
    4. Simple hints

    FORMAT STRICTLY AS:
    Q: [Question text]
    A) [Option A]
    B) [Option B]
    C) [Option C]
    D) [Option D]
    ANSWER: [Correct letter]
    EXPLANATION: [2-3 sentence explanation that is engaging, innovative, intuitive and of high quality (with reasonable examples if needed)]
    HINT: [1 short sentence hint that is actually indirectly refers to the correct answer. It should be a quality hint]

    Example:
    Q: What is the capital of France?
    A) London
    B) Paris
    C) Berlin
    D) Madrid
    ANSWER: B
    EXPLANATION: Paris didn't just become France's capital—it weaponized geography. The Seine River acted as a medieval superhighway, funneling trade like Amazon's distribution networks today, while its inland location provided fortress-like security. That's why global cities from London to Tokyo still cluster around strategic waterways—proving Clovis Is 508 AD decision was the original location, location, location masterstroke.
    HINT: Think of the Eiffel Tower's location.
    """)

    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            "model": "qwen2.5:latest",
            "prompt": prompt,
            "stream": False
        }
    )
    data = parse_quiz(response.json()['response'], topic)
    print("Data:", data)
    return data

def parse_quiz(raw_text, topic):
    """Extract structured quiz data from raw text"""
    questions = []
    blocks = re.split(r'\nQ:', raw_text)[1:]  # Split by questions

    for block in blocks:
        parts = re.match(
            r'(.*?)\nA\) (.*?)\nB\) (.*?)\nC\) (.*?)\nD\) (.*?)\n'
            r'ANSWER: (.*?)\nEXPLANATION: (.*?)\nHINT: (.*?)(?=\nQ|\Z)',
            block, re.DOTALL
        )
        if parts:
            questions.append({
                "question": parts.group(1).strip(),
                "options": {
                    "A": parts.group(2).strip(),
                    "B": parts.group(3).strip(),
                    "C": parts.group(4).strip(),
                    "D": parts.group(5).strip()
                },
                "answer": parts.group(6).strip(),
                "explanation": parts.group(7).strip(),
                "hint": parts.group(8).strip()
            })

    quiz_data = {
        "topic": topic,
        "generated_at": datetime.datetime.now().isoformat(),
        "questions": questions
    }

    return quiz_data

def gen_quiz(content):
    topic = extract_topic_qwen(content)
    return generate_quiz(topic)
