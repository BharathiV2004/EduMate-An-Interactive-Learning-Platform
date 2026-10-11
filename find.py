from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Puzzle data
PUZZLE_DATA = {
    "title": "Summer Activities Crossword Like Word Search Puzzle #07",
    "instructions": "Find the words in the grid. There are 2 steps to solve the puzzle. First, solve for each clue and record the answer. Next find the words hidden in the grid. Words can go horizontally, vertically and diagonally in all eight directions.",
    "grid": [
        ['m', 'e', 'd', 'x', 'c', 'u', 'e', 'm', 's', 'i', 'e', 'p', 'a', 'x', 'l', 'v', 'y'],
        ['a', 's', 'e', 'l', 'b', 'b', 'u', 'b', 'w', 'o', 'l', 'b', 'u', 'y', 'j', 'v', 'x'],
        ['k', 'l', 'l', 'a', 'b', 'e', 's', 'a', 'b', 'y', 'a', 'l', 'p', 'p', 'l', 'd', 'z'],
        ['e', 'g', 'n', 'i', 'b', 'm', 'i', 'l', 'c', 'k', 'c', 'o', 'r', 'd', 'p', 'h', 'm'],
        ['m', 'k', 'n', 'y', 'x', 'v', 'g', 'n', 'n', 'o', 'q', 'q', 'b', 'e', 'a', 'e', 's'],
        ['u', 'a', 'w', 'f', 'x', 'n', 'h', 'm', 'p', 'f', 'l', 'f', 'b', 'f', 'k', 'u', 't'],
        ['f', 'e', 'r', 'f', 'i', 'd', 'o', 'l', 'p', 'h', 'i', 'n', 'w', 'a', 't', 'c', 'h'],
        ['f', 'a', 'q', 'f', 'q', 'j', 'q', 'n', 'u', 'm', 'r', 'n', 'j', 'v', 'f', 'x', 'u'],
        ['i', 'i', 'r', 's', 't', 'f', 'a', 'r', 'c', 'r', 'e', 'm', 'm', 'u', 's', 'c', 'x'],
        ['n', 'u', 'p', 'x', 'c', 'v', 'u', 'x', 'e', 'b', 's', 'w', 'p', 'c', 's', 'j', 'y'],
        ['s', 'l', 'a', 'n', 'k', 'm', 'a', 'k', 'e', 'c', 'u', 'p', 'c', 'a', 'k', 'e', 's'],
        ['g', 'n', 'i', 't', 'f', 'a', 'r', 'r', 'e', 't', 'a', 'w', 'e', 't', 'i', 'h', 'w']
    ],
    "clues": [
        {"id": 1, "text": "Pinochhio is an example of this.", "answer": "lie"},
        {"id": 2, "text": "Indoor or outdoor activity.", "answer": "play"},
        {"id": 3, "text": "Do this by the dozen.", "answer": "bubbles"},
        {"id": 4, "text": "Needs water and rapids.", "answer": "whitewater"},
        {"id": 5, "text": "Waves required for this.", "answer": "surfing"},
        {"id": 6, "text": "Kids do this in their drink.", "answer": "blowbubbles"},
        {"id": 7, "text": "Creativity explored with this.", "answer": "makecupcakes"},
        {"id": 8, "text": "Do this by the dozen. Often, sweet!", "answer": "makecupcakes"},
        {"id": 9, "text": "Do this on land or sea.", "answer": "dolphinwatch"},
        {"id": 10, "text": "Summer sign up needed.", "answer": "rockclimbing"}
    ],
    "answers": [
        {
            "answer": "lie", 
            "locations": [
                {"row": 2, "col": 1, "direction": "horizontal"}
            ]
        },
        {
            "answer": "play", 
            "locations": [
                {"row": 2, "col": 8, "direction": "horizontal"}
            ]
        },
        {
            "answer": "blowbubbles", 
            "locations": [
                {"row": 1, "col": 1, "direction": "horizontal"}
            ]
        },
        {
            "answer": "whitewater", 
            "locations": [
                {"row": 11, "col": 7, "direction": "horizontal", "reversed": True}
            ]
        },
        {
            "answer": "surfing", 
            "locations": [
                {"row": 9, "col": 1, "direction": "diagonal", "reversed": True}
            ]
        },
        {
            "answer": "blowbubbles", 
            "locations": [
                {"row": 1, "col": 1, "direction": "horizontal"}
            ]
        },
        {
            "answer": "rockclimbing", 
            "locations": [
                {"row": 3, "col": 9, "direction": "horizontal", "reversed": True}
            ]
        },
        {
            "answer": "makecupcakes", 
            "locations": [
                {"row": 10, "col": 2, "direction": "horizontal"}
            ]
        },
        {
            "answer": "dolphinwatch", 
            "locations": [
                {"row": 6, "col": 4, "direction": "horizontal"}
            ]
        },
        {
            "answer": "summer", 
            "locations": [
                {"row": 8, "col": 13, "direction": "horizontal", "reversed": True}
            ]
        }
    ]
}

# Store user progress
user_progress = {}

@app.route('/')
def index():
    return render_template('index.html', puzzle=PUZZLE_DATA)

@app.route('/check_answer', methods=['POST'])
def check_answer():
    data = request.json
    clue_id = data.get('clue_id')
    answer = data.get('answer').lower().strip()
    
    # Find the corresponding clue
    clue = next((c for c in PUZZLE_DATA['clues'] if c['id'] == clue_id), None)
    
    if clue and answer == clue['answer'].lower():
        return jsonify({'correct': True})
    else:
        return jsonify({'correct': False})

@app.route('/check_found_word', methods=['POST'])
def check_found_word():
    data = request.json
    word = data.get('word').lower().strip()
    cells = data.get('cells', [])
    
    # Check if the word is in the answers
    word_data = next((a for a in PUZZLE_DATA['answers'] if a['answer'].lower() == word), None)
    
    if word_data:
        # Mark as found in user progress
        user_id = request.cookies.get('user_id', 'anonymous')
        if user_id not in user_progress:
            user_progress[user_id] = {'found_words': []}
        
        if word not in user_progress[user_id]['found_words']:
            user_progress[user_id]['found_words'].append(word)
        
        return jsonify({
            'correct': True,
            'word': word,
            'found_words': user_progress[user_id]['found_words']
        })
    else:
        return jsonify({'correct': False})

@app.route('/get_progress')
def get_progress():
    user_id = request.cookies.get('user_id', 'anonymous')
    if user_id not in user_progress:
        user_progress[user_id] = {'found_words': []}
    
    return jsonify(user_progress[user_id])

@app.route('/reset_progress')
def reset_progress():
    user_id = request.cookies.get('user_id', 'anonymous')
    if user_id in user_progress:
        user_progress[user_id] = {'found_words': []}
    
    flash('Progress has been reset!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)