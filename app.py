from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from db import db


from flask import session as flask_session
from datetime import datetime, timedelta
import secrets
import requests

from models.user import User
from models.session import Session 
from models.inputfile import InputFile
from models.quiz import Quiz
from models.flashcard import Flashcard
from models.story import Story
from models.extractedcontent import ExtractedContent
from models.note import Note
from models.summary import Summary

from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

import os
from werkzeug.utils import secure_filename
from pathlib import Path

import json
import random
from uuid import uuid4
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
from moviepy import *
import cv2
import pytesseract
from moviepy import *
from fuzzywuzzy import fuzz

import re
import nltk
from nltk.corpus import wordnet
import string

from quiz_gen import gen_quiz
from flashcard_gen import gen_flashcards
from story_pipeline import gen_story_pipe
from flip_game_gen import gen_flipcard
from notes_gen import gen_notes
from summary_gen import auto_summary_gen
app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = "some-secret-key"  # Needed for flash messages

from story_pipeline import gen_story

# ======== SocketIO Configuration ========
try:
    import eventlet
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
except ImportError:
    socketio = SocketIO(app, cors_allowed_origins="*")

# Load levels from JSON file
with open(r'D:\Downloads\Edumate\levels.json', 'r') as f:
    LEVELS = json.load(f)


# PostgreSQL configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost:5432/edumate_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#D:\Downloads\Edumate\templates\about.html
db.init_app(app)

# ======== Crossword Game Configuration ========
crossword_rooms = {}
def generate_crossword():
    with open(r'D:\Downloads\Edumate\static\crossword_data\words.json', 'r') as f:
        return json.load(f)['crosswords'][0]

@app.route('/leaderboard')
def leaderboard():
    leaders = [
        {'name': 'CodeMaster', 'xp': 12450, 'badges': 5},
        {'name': 'WebWarrior', 'xp': 11200, 'badges': 3},
        {'name': 'DataWizard', 'xp': 9800, 'badges': 4}
    ]
    return render_template('index.html', leaders=leaders)

# ======== Crossword Game Routes ========
@app.route('/crossword')
def crossword_home():
    return render_template('crossword_index.html')

# ======== Crossword SocketIO Handlers ========
@socketio.on('connect')
def handle_connect():
    emit('connection_ack', {'status': 'Connected to server'})

@socketio.on('disconnect')
def handle_crossword_disconnect():
    room_id = flask_session.get('crossword_room_id')
    username = flask_session.get('crossword_username')
    
    if room_id and room_id in crossword_rooms and username in crossword_rooms[room_id]['players']:
        leave_room(room_id)
        del crossword_rooms[room_id]['players'][username]
        emit('player_left', {'username': username, 'players': crossword_rooms[room_id]['players']}, room=room_id)
        
        if not crossword_rooms[room_id]['players']:
            del crossword_rooms[room_id]

@socketio.on('create_game')
def handle_create_game(data):
    username = data.get('username')
    if not username:
        emit('error', {'message': 'Username is required'})
        return
    
    room_id = str(random.randint(1000, 9999))
    while room_id in crossword_rooms:
        room_id = str(random.randint(1000, 9999))
    
    crossword_rooms[room_id] = {
        'crossword': generate_crossword(),
        'players': {username: {'score': 0, 'incorrect_words': [], 'progress': {}}},
        'created_at': datetime.now().isoformat()
    }
    
    flask_session['crossword_room_id'] = room_id
    flask_session['crossword_username'] = username
    join_room(room_id)
    
    emit('game_created', {
        'room_id': room_id,
        'crossword': crossword_rooms[room_id]['crossword'],
        'players': crossword_rooms[room_id]['players']
    })

@socketio.on('join_game')
def handle_join_game(data):
    room_id = data.get('room_id')
    username = data.get('username')
    
    if not room_id or not username:
        emit('error', {'message': 'Room ID and username are required'})
        return
    
    if room_id not in crossword_rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    if username in crossword_rooms[room_id]['players']:
        emit('error', {'message': 'Username already taken'})
        return
    
    crossword_rooms[room_id]['players'][username] = {
        'score': 0,
        'incorrect_words': [],
        'progress': {}
    }
    
    flask_session['crossword_room_id'] = room_id
    flask_session['crossword_username'] = username
    join_room(room_id)
    
    emit('player_joined', {
        'username': username,
        'players': crossword_rooms[room_id]['players']
    }, room=room_id)
    
    emit('game_state', {
        'crossword': crossword_rooms[room_id]['crossword'],
        'players': crossword_rooms[room_id]['players'],
        'room_id': room_id
    }, room=room_id)
# Add this with other crossword handlers
@socketio.on('submit_answers')
def handle_submit_answers(data):
    room_id = flask_session.get('crossword_room_id')
    username = flask_session.get('crossword_username')
    
    if not room_id or not username or room_id not in crossword_rooms:
        emit('error', {'message': 'Invalid room'})
        return
    
    game = crossword_rooms[room_id]
    user_answers = data.get('answers', {})
    incorrect_words = []
    correct_count = 0
    print(user_answers)
    # Validate answers
    for word in game['crossword']['words']:
        user_answer = user_answers.get(str(word['number']), '').strip().upper()
        correct_answer = word['word'].upper()
        print("user_answer:",user_answer)
        print("correct_answer:",correct_answer)

        if user_answer == correct_answer:
            correct_count += 1
            print("count:",correct_count)
            game['players'][username]['progress'][word['number']] = True
        else:
            incorrect_words.append({
                'number': word['number'],
                'direction': word['direction'],
                'row': word['row'],
                'col': word['col'],
                'length': len(word['word'])
            })
            game['players'][username]['progress'][word['number']] = False

    # Update game state
    game['players'][username]['score'] = correct_count
    game['players'][username]['incorrect_words'] = incorrect_words

    # Check if all players have submitted
    all_players_submitted = all(
        len(player['progress']) == len(game['crossword']['words']) 
        for player in game['players'].values()
    )

    if all_players_submitted:
        max_score = max(player['score'] for player in game['players'].values())
        winners = [name for name, player in game['players'].items() 
                  if player['score'] == max_score]
        
        scores = {name: player['score'] for name, player in game['players'].items()}
        
        emit('game_over', {
            'winners': winners,
            'scores': scores,
            'total_words': len(game['crossword']['words'])
        }, room=room_id)
    else:
        emit('answers_evaluated', {
            'correct': correct_count,
            'incorrect_words': incorrect_words,
            'username': username,
            'players': game['players']
        }, room=room_id)

# --------------------------------flashcard----------------------------------------------------
connected_players = {}  # sid -> username
player_scores = {}
current_flashcard_index = 0
game_started = False
question_timer = 15
players_submitted = {}  # sid -> boolean

flashcards = [
    {"question": "What is the capital of France?", "answer": "Paris"},
    {"question": "What is 2 + 2?", "answer": "4"},
    {"question": "Python keyword for function?", "answer": "def"},
    {"question": "H2O is known as?", "answer": "water"},
    {"question": "Who painted Mona Lisa?", "answer": "Leonardo da Vinci"}
]

random.shuffle(flashcards)

@app.route('/battle')
def battle():
    return render_template('battle.html')

@socketio.on('join_game')
def handle_join(data):
    global game_started
    username = data.get('username', 'Player')
    sid = request.sid
    connected_players[sid] = username
    player_scores[sid] = 0
    players_submitted[sid] = False
    print(f"{username} connected with SID: {sid}")

    if len(connected_players) == 2 and not game_started:
        game_started = True
        socketio.emit('game_started', {'message': 'Game has started!', 'players': connected_players})
        send_current_flashcard()

def send_current_flashcard():
    global current_flashcard_index
    if current_flashcard_index < len(flashcards):
        card = flashcards[current_flashcard_index]
        socketio.emit('new_flashcard', {
            'flashcard': card,
            'index': current_flashcard_index
        })
        socketio.emit('start_timer', {'time': question_timer})
    else:
        end_game()

@socketio.on('submit_answer')
def handle_submit_answer(data):
    global current_flashcard_index, player_scores, players_submitted
    sid = request.sid
    answer = data['answer'].strip().lower()

    correct = flashcards[current_flashcard_index]['answer'].strip().lower()
    is_correct = answer == correct
    if is_correct:
        player_scores[sid] += 1

    players_submitted[sid] = True

    # Send feedback to the specific player only
    socketio.emit('answer_result', {
        'sid': sid,
        'result': 'correct' if is_correct else 'incorrect'
    }, room=sid)

    # Emit live score update immediately after submission
    emit_score_update()

    # Proceed if all submitted
    if all(players_submitted.values()):
        current_flashcard_index += 1
        players_submitted = {sid: False for sid in connected_players}
        send_current_flashcard()

def emit_score_update():
    sid_list = list(player_scores.keys())
    if len(sid_list) < 2:
        return
    player1 = connected_players[sid_list[0]]
    player2 = connected_players[sid_list[1]]
    socketio.emit('score_update', {
        'player1': player1,
        'player2': player2,
        'score1': player_scores[sid_list[0]],
        'score2': player_scores[sid_list[1]]
    })

@socketio.on('time_up')
def handle_time_up():
    global current_flashcard_index
    current_flashcard_index += 1
    # Reset submission status
    for sid in connected_players:
        players_submitted[sid] = False
    send_current_flashcard()

def end_game():
    sid_list = list(player_scores.keys())
    score1 = player_scores[sid_list[0]]
    score2 = player_scores[sid_list[1]]
    name1 = connected_players[sid_list[0]]
    name2 = connected_players[sid_list[1]]

    result = f"{name1}: {score1}<br>{name2}: {score2}<br>"
    if score1 > score2:
        result += f"🏆 {name1} wins!"
    elif score2 > score1:
        result += f"🏆 {name2} wins!"
    else:
        result += "🤝 It's a tie!"

    socketio.emit('game_ended', {'message': result})

@socketio.on('rematch')
def handle_rematch():
    global flashcards, current_flashcard_index, player_scores, game_started, players_submitted
    print("Rematch triggered by SID:", request.sid)

    current_flashcard_index = 0
    player_scores = {sid: 0 for sid in connected_players}
    players_submitted = {sid: False for sid in connected_players}
    game_started = True
    random.shuffle(flashcards)

    emit_score_update()
    send_current_flashcard()

@socketio.on('disconnect')
def handle_disconnect():
    global connected_players, player_scores, game_started, current_flashcard_index
    if request.sid in connected_players:
        username = connected_players[request.sid]
        print(f"{username} disconnected")
        del connected_players[request.sid]

        if len(connected_players) == 1:
            remaining = list(connected_players.values())[0]
            socketio.emit('game_ended', {'message': f"{username} disconnected. {remaining} wins!"})
        else:
            socketio.emit('game_ended', {'message': 'A player disconnected. Game ended.'})

    game_started = False
    current_flashcard_index = 0
    player_scores.clear()
#--------------------------------------------------------------------------------------------

@app.route("/login", methods=["POST"])
@csrf.exempt
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()
   
    if not user:
        return jsonify({"success": False, "message": "Email not found. Please sign up."})
   
    if user.check_password(password):
        # Create session only if login is successful
        session_id = secrets.token_hex(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store session in database
        new_session = Session(
            session_id=session_id,
            user_id=user.id,
            expires_at=expires_at
        )
        db.session.add(new_session)
        db.session.commit()
        
        # Set session cookie
        flask_session['session_id'] = session_id
        flask_session['user_id'] = user.id
        
        return jsonify({
            "success": True, 
            "message": "Login successful!",
            "session_id": session_id
        })
    else:
        return jsonify({"success": False, "message": "Incorrect password. Please try again."})

@app.route("/signup", methods=["GET","POST"])
@csrf.exempt
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirmPassword = request.form.get('confirmPassword')  # Corrected key
    print(password, confirmPassword)
    
    if password != confirmPassword:
        return jsonify({"success": False, "message": "Passwords do not match."})

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return jsonify({"success": False, "message": "Username or email already taken."})

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Registration successful!"})



def allowed_file(filename, file_type):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'].get(file_type, [])

class UploadForm(FlaskForm):
    files = FileField('Select Files', validators=[DataRequired()])
    file_type = SelectField('File Type', choices=[
        ('image', 'Image'), 
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('text', 'Text')
    ])
    description = TextAreaField('Description')
    submit = SubmitField('Upload Files')





app.config['UPLOAD_FOLDER'] = r'D:\Downloads\Edumate\static\uploads'
app.config['ALLOWED_EXTENSIONS'] = {
    'image': ['png', 'jpg', 'jpeg', 'gif'],
    'video': ['mp4', 'mov', 'avi'],
    'audio': ['mp3', 'wav', 'ogg'],
    'document': ['pdf', 'doc', 'docx'],
    'text': ['txt']
}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit


# --------------------------------------------------------------------------------



@app.route('/quiz', methods=['GET', 'POST'])
def courses():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()
    # Fetch uploaded files and their extracted content
    files = InputFile.query.filter_by(session_id=flask_session['session_id']) \
                           .order_by(InputFile.created_at.desc()).all()
    
    # Add URL and extracted content to each file object
    for file in files:
        file.url = url_for('static', filename=os.path.join(file.file_type, os.path.basename(file.file_path)))
        file.extracted_content = ExtractedContent.query.filter_by(file_id=file.file_id).first()

    return render_template("courses.html", form=form, files=files)


@app.route('/notesmake', methods=['GET', 'POST'])
def notes():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()
    # Fetch uploaded files and their extracted content
    files = InputFile.query.filter_by(session_id=flask_session['session_id']) \
                           .order_by(InputFile.created_at.desc()).all()
    
    # Add URL and extracted content to each file object
    for file in files:
        file.url = url_for('static', filename=os.path.join(file.file_type, os.path.basename(file.file_path)))
        file.extracted_content = ExtractedContent.query.filter_by(file_id=file.file_id).first()

    return render_template("notesmake.html", form=form, files=files)

@app.route('/generate-notes', methods=['POST'])
def generate_notes():
    print("Generate notes...............")
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        session_id = flask_session['session_id']
        file_ids = []

        for file in uploaded_files:
            if file and file.filename:
                # Validate file type and extension
                if not allowed_file(file.filename, form.file_type.data):
                    flash(f'Invalid file type for {file.filename}', 'danger')
                    continue

                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{secrets.token_hex(8)}{file_ext}"

                # Create type-specific directory
                file_type_dir = os.path.join(app.config['UPLOAD_FOLDER'], form.file_type.data).replace('\\', '/')
                os.makedirs(file_type_dir, exist_ok=True)

                # Save file
                file_path = os.path.join(file_type_dir, unique_filename).replace('\\', '/')
                file.save(file_path)

                # Save metadata to DB
                new_file = InputFile(
                    session_id=session_id,
                    file_type=form.file_type.data,
                    file_path=file_path.replace('D:/Downloads/Edumate/static/', '')
                )
                db.session.add(new_file)
                db.session.flush()  # Get the file_id immediately
                file_ids.append(new_file.file_id)
                print("process_step")
                # Process file based on type and extract content
                extracted_text = ""
                try:
                    if form.file_type.data == 'audio':
                        extracted_text = process_audio_file(file_path)
                    elif form.file_type.data == 'video':
                        extracted_text = process_video_file(file_path)
                    elif form.file_type.data == 'document':
                        if file_ext == '.pdf':
                            extracted_text = process_pdf_file(file_path)
                        elif file_ext in ['.doc', '.docx']:
                            extracted_text = process_word_file(file_path)
                        else:
                            extracted_text = process_text_file(file_path)
                    elif form.file_type.data == 'image':
                        extracted_text = process_image_file(file_path)
                    elif form.file_type.data == 'text':
                        extracted_text = process_text_file(file_path)
                    
                    # Save extracted content
                    if extracted_text:
                        new_content = ExtractedContent(
                            file_id=new_file.file_id,
                            raw_text=extracted_text,
                        )
                        db.session.add(new_content)
                        
                except Exception as e:
                    app.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    flash(f'Error processing {file.filename}', 'warning')

        db.session.commit()
        flash('Files uploaded and processed successfully! Generating quiz...', 'success')
        return redirect(url_for('notes_learn', file_ids=','.join(map(str, file_ids))))
    
    # If form validation fails, show errors and return to courses page
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('notes'))


# Note Generation Function
def auto_note_gen(content, content_id):
    """Generate and store structured notes from extracted content"""
    try:
        # Generate notes using your existing create_notes function
        gen_content = gen_notes(content.raw_text)
        
        save_folder = os.path.join(app.static_folder, 'note_data')
        os.makedirs(save_folder, exist_ok=True)

        # Create safe filename
        safe_title = "".join([c if c.isalnum() else "_" for c in gen_content['title']])
        filename = f"{content_id}_{safe_title}.json"
        save_path = os.path.join(save_folder, filename)

        # Save note data to JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(gen_content, f, indent=4, ensure_ascii=False)

        # Store note metadata in database
        note_entry = Note(
            content_id=content_id,
            title=gen_content['title'],
            file_path=filename
        )
        
        db.session.add(note_entry)
        db.session.commit()
        return True
        
    except Exception as e:
        app.logger.error(f"Note generation failed: {str(e)}")
        db.session.rollback()
        return False

@app.route('/notes_learn')
def notes_learn():
    # Authentication check
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    # Validate file IDs
    file_ids = request.args.get('file_ids', '')
    try:
        file_ids = [int(id) for id in file_ids.split(',') if id.isdigit()]
    except ValueError:
        flash('Invalid file selection', 'danger')
        return redirect(url_for('courses'))

    # Initialize notes structure with proper sections
    notes_data = {
        "title": "Generated Notes",
        "pdf_path": "",
        "sections": {
            "main_notes": [],
            "key_terms": [],
            "examples": [],
            "connections": [],
            "questions": []
        }
    }

    if file_ids:
        files = InputFile.query.filter(
            InputFile.file_id.in_(file_ids),
            InputFile.session_id == flask_session['session_id']
        ).all()

        for file in files:
            content = ExtractedContent.query.filter_by(
                file_id=file.file_id
            ).order_by(ExtractedContent.content_id.desc()).first()

            if content:
                # Generate notes if not exists
                if not Note.query.filter_by(content_id=content.content_id).first():
                    if not auto_note_gen(content, content.content_id):
                        app.logger.error(f'Note generation failed for {file.file_path}')
                        continue

                # Retrieve generated notes
                note_entry = Note.query.filter_by(
                    content_id=content.content_id
                ).first()

                if note_entry:
                    try:
                        note_path = os.path.join(app.static_folder, 'note_data', note_entry.file_path)
                        with open(note_path, 'r') as f:
                            note_json = json.load(f)
                            
                            # Merge sections
                            notes_data['sections']['main_notes']=note_json.get('sections', {}).get('main_notes', [])
                            notes_data['sections']['key_terms'].extend(
                                note_json.get('sections', {}).get('key_terms', [])
                            )
                            notes_data['sections']['examples'].extend(
                                note_json.get('sections', {}).get('examples', [])
                            )
                            notes_data['sections']['connections'].extend(
                                note_json.get('sections', {}).get('connections', [])
                            )
                            notes_data['sections']['questions'].extend(
                                note_json.get('sections', {}).get('questions', [])
                            )
                            
                            if note_json.get('title'):
                                notes_data['title'] = note_json['title']
                            if note_json.get('pdf_path'):
                                notes_data['pdf_path'] = note_json['pdf_path'].replace("\\", "/")

                    except Exception as e:
                        app.logger.error(f"Failed to load notes: {str(e)}")
                        continue

    # Check if any sections have content
    has_content = any(len(section) > 0 for section in notes_data['sections'].values())
    
    if not has_content:
        flash('No notes found in selected files', 'warning')

    app.logger.debug(f"Prepared notes data: {notes_data}")
    
    return render_template("notes.html", 
        title=notes_data['title'],
        sections=notes_data['sections'],
        pdf_path=notes_data['pdf_path']
    )


@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    print("Generate summary...............")
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        session_id = flask_session['session_id']
        file_ids = []

        for file in uploaded_files:
            if file and file.filename:
                # Validate file type and extension
                if not allowed_file(file.filename, form.file_type.data):
                    flash(f'Invalid file type for {file.filename}', 'danger')
                    continue

                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{secrets.token_hex(8)}{file_ext}"

                # Create type-specific directory
                file_type_dir = os.path.join(app.config['UPLOAD_FOLDER'], form.file_type.data).replace('\\', '/')
                os.makedirs(file_type_dir, exist_ok=True)

                # Save file
                file_path = os.path.join(file_type_dir, unique_filename).replace('\\', '/')
                file.save(file_path)

                # Save metadata to DB
                new_file = InputFile(
                    session_id=session_id,
                    file_type=form.file_type.data,
                    file_path=file_path.replace('D:/Downloads/Edumate/static/', '')
                )
                db.session.add(new_file)
                db.session.flush()  # Get the file_id immediately
                file_ids.append(new_file.file_id)
                print("process_step")
                # Process file based on type and extract content
                extracted_text = ""
                try:
                    if form.file_type.data == 'audio':
                        extracted_text = process_audio_file(file_path)
                    elif form.file_type.data == 'video':
                        extracted_text = process_video_file(file_path)
                    elif form.file_type.data == 'document':
                        if file_ext == '.pdf':
                            extracted_text = process_pdf_file(file_path)
                        elif file_ext in ['.doc', '.docx']:
                            extracted_text = process_word_file(file_path)
                        else:
                            extracted_text = process_text_file(file_path)
                    elif form.file_type.data == 'image':
                        extracted_text = process_image_file(file_path)
                    elif form.file_type.data == 'text':
                        extracted_text = process_text_file(file_path)
                    
                    # Save extracted content
                    if extracted_text:
                        new_content = ExtractedContent(
                            file_id=new_file.file_id,
                            raw_text=extracted_text,
                        )
                        db.session.add(new_content)
                        
                except Exception as e:
                    app.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    flash(f'Error processing {file.filename}', 'warning')

        db.session.commit()
        flash('Files uploaded and processed successfully! Generating summary...', 'success')
        return redirect(url_for('summary_view', file_ids=','.join(map(str, file_ids))))
    
    # If form validation fails, show errors and return to summary page
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('summarizer'))

@app.route('/summarizer', methods=['GET', 'POST'])
def summarizer():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()
    # Fetch uploaded files and their extracted content
    files = InputFile.query.filter_by(session_id=flask_session['session_id']) \
                         .order_by(InputFile.created_at.desc()).all()
    
    # Add URL and extracted content to each file object
    for file in files:
        file.url = url_for('static', filename=os.path.join(file.file_type, os.path.basename(file.file_path)))
        file.extracted_content = ExtractedContent.query.filter_by(file_id=file.file_id).first()

    return render_template("summarizer.html", form=form, files=files)

@app.route('/summary_view')
def summary_view():
    # Authentication check
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    # Validate file IDs
    file_ids = request.args.get('file_ids', '')
    try:
        file_ids = [int(id) for id in file_ids.split(',') if id.isdigit()]
    except ValueError:
        flash('Invalid file selection', 'danger')
        return redirect(url_for('summarizer'))

    # Initialize summary structure
    summary_data = {
        "title": "Generated Summary",
        "pdf_path": "",
        "summary": "",
        "level": "detailed",
        "section_summaries": []
    }

    if file_ids:
        files = InputFile.query.filter(
            InputFile.file_id.in_(file_ids),
            InputFile.session_id == flask_session['session_id']
        ).all()

        for file in files:
            content = ExtractedContent.query.filter_by(
                file_id=file.file_id
            ).order_by(ExtractedContent.content_id.desc()).first()

            if content:
                # Generate summary if not exists
                # Check if summary already exists for this content
                existing_summary = Summary.query.filter_by(content_id=content.content_id).first()
                
                if not existing_summary:
                    # Generate new summary
                    web_content = auto_summary_gen(content, content.content_id)
                    if web_content.get("error"):
                        app.logger.error(f'Summary generation failed for {file.file_path}')
                        continue
                        
                    # Create new summary record
                    summary_entry = Summary(
                        content_id=content.content_id,
                        title=web_content["title"],
                        file_path=os.path.basename(web_content["pdf_path"]),
                        level=web_content["level"]
                    )
                    db.session.add(summary_entry)
                    db.session.commit()
                else:
                    # Load existing summary data
                    try:
                        summary_path = os.path.join(app.static_folder, 'summary_data', existing_summary.file_path)
                        with open(summary_path, 'r') as f:
                            web_content = json.load(f)
                    except Exception as e:
                        app.logger.error(f"Failed to load summary: {str(e)}")
                        continue

                # Update the summary data
                summary_data["title"] = web_content["title"]
                summary_data["pdf_path"] = web_content.get("pdf_path", "")
                summary_data["summary"] = web_content.get("summary", "")
                summary_data["level"] = web_content.get("level", "detailed")
                
                # Add section summaries if available
                if web_content.get("section_summaries"):
                    summary_data["section_summaries"].extend(web_content["section_summaries"])

    # Check if any content is available
    has_content = summary_data["summary"] != ""
    
    if not has_content:
        flash('No summary found in selected files', 'warning')

    app.logger.debug(f"Prepared summary data: {summary_data}")
    
    return render_template("summary_view.html", 
        title=summary_data["title"],
        summary=summary_data["summary"],
        level=summary_data["level"],
        section_summaries=summary_data["section_summaries"],
        pdf_path=summary_data["pdf_path"]
    )    
@app.route('/generate-flashcard', methods=['POST'])
def generate_flashcard():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        session_id = flask_session['session_id']
        file_ids = []

        for file in uploaded_files:
            if file and file.filename:
                # Validate file type and extension
                if not allowed_file(file.filename, form.file_type.data):
                    flash(f'Invalid file type for {file.filename}', 'danger')
                    continue

                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{secrets.token_hex(8)}{file_ext}"

                # Create type-specific directory
                file_type_dir = os.path.join(app.config['UPLOAD_FOLDER'], form.file_type.data).replace('\\', '/')
                os.makedirs(file_type_dir, exist_ok=True)

                # Save file
                file_path = os.path.join(file_type_dir, unique_filename).replace('\\', '/')
                file.save(file_path)

                # Save metadata to DB
                new_file = InputFile(
                    session_id=session_id,
                    file_type=form.file_type.data,
                    file_path=file_path.replace('D:/Downloads/Edumate/static/', '')
                )
                db.session.add(new_file)
                db.session.flush()  # Get the file_id immediately
                file_ids.append(new_file.file_id)

                # Process file based on type and extract content
                extracted_text = ""
                try:
                    if form.file_type.data == 'audio':
                        extracted_text = process_audio_file(file_path)
                    elif form.file_type.data == 'video':
                        extracted_text = process_video_file(file_path)
                    elif form.file_type.data == 'document':
                        if file_ext == '.pdf':
                            extracted_text = process_pdf_file(file_path)
                        elif file_ext in ['.doc', '.docx']:
                            extracted_text = process_word_file(file_path)
                        else:
                            extracted_text = process_text_file(file_path)
                    elif form.file_type.data == 'image':
                        extracted_text = process_image_file(file_path)
                    elif form.file_type.data == 'text':
                        extracted_text = process_text_file(file_path)
                    
                    # Save extracted content
                    if extracted_text:
                        new_content = ExtractedContent(
                            file_id=new_file.file_id,
                            raw_text=extracted_text,
                        )
                        db.session.add(new_content)
                        
                except Exception as e:
                    app.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    flash(f'Error processing {file.filename}', 'warning')

        db.session.commit()
        flash('Files uploaded and processed successfully! Generating quiz...', 'success')
        return redirect(url_for('flashcard', file_ids=','.join(map(str, file_ids))))
    
    # If form validation fails, show errors and return to courses page
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('trainers'))

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        session_id = flask_session['session_id']
        file_ids = []
        print(uploaded_files)
        for file in uploaded_files:
            if file and file.filename:
                # Validate file type and extension
                if not allowed_file(file.filename, form.file_type.data):
                    flash(f'Invalid file type for {file.filename}', 'danger')
                    continue

                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{secrets.token_hex(8)}{file_ext}"

                # Create type-specific directory
                file_type_dir = os.path.join(app.config['UPLOAD_FOLDER'], form.file_type.data).replace('\\', '/')
                os.makedirs(file_type_dir, exist_ok=True)

                # Save file
                file_path = os.path.join(file_type_dir, unique_filename).replace('\\', '/')
                file.save(file_path)

                # Save metadata to DB
                new_file = InputFile(
                    session_id=session_id,
                    file_type=form.file_type.data,
                    file_path=file_path.replace('D:/Downloads/Edumate/static/', '')
                )
                db.session.add(new_file)
                db.session.flush()  # Get the file_id immediately
                file_ids.append(new_file.file_id)

                # Process file based on type and extract content
                extracted_text = ""
                try:
                    print(form.file_type.data,file_ext)
                    if form.file_type.data == 'audio':
                        extracted_text = process_audio_file(file_path)
                    elif form.file_type.data == 'video':
                        extracted_text = process_video_file(file_path)
                    elif form.file_type.data == 'document':
                        if file_ext == '.pdf':
                            extracted_text = process_pdf_file(file_path)
                        elif file_ext in ['.doc', '.docx']:
                            extracted_text = process_word_file(file_path)
                        else:
                            extracted_text = process_text_file(file_path)
                    elif form.file_type.data == 'image':
                        extracted_text = process_image_file(file_path)
                    elif form.file_type.data == 'text':
                        extracted_text = process_text_file(file_path)
                    
                    # Save extracted content
                    if extracted_text:
                        new_content = ExtractedContent(
                            file_id=new_file.file_id,
                            raw_text=extracted_text,
                        )
                        db.session.add(new_content)
                        
                except Exception as e:
                    app.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    flash(f'Error processing {file.filename}', 'warning')

        db.session.commit()
        flash('Files uploaded and processed successfully! Generating quiz...', 'success')
        return redirect(url_for('quiz', file_ids=','.join(map(str, file_ids))))
    
    # If form validation fails, show errors and return to courses page
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('courses'))

@app.route('/generate-story', methods=['POST'])
def generate_story():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('files')
        session_id = flask_session['session_id']
        file_ids = []

        for file in uploaded_files:
            if file and file.filename:
                # Validate file type and extension
                if not allowed_file(file.filename, form.file_type.data):
                    flash(f'Invalid file type for {file.filename}', 'danger')
                    continue

                # Secure the filename
                original_filename = secure_filename(file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{secrets.token_hex(8)}{file_ext}"

                # Create type-specific directory
                file_type_dir = os.path.join(app.config['UPLOAD_FOLDER'], form.file_type.data).replace('\\', '/')
                os.makedirs(file_type_dir, exist_ok=True)

                # Save file
                file_path = os.path.join(file_type_dir, unique_filename).replace('\\', '/')
                file.save(file_path)

                # Save metadata to DB
                new_file = InputFile(
                    session_id=session_id,
                    file_type=form.file_type.data,
                    file_path=file_path.replace('D:/Downloads/Edumate/static/', '')
                )
                db.session.add(new_file)
                db.session.flush()  # Get the file_id immediately
                file_ids.append(new_file.file_id)

                # Process file based on type and extract content
                extracted_text = ""
                try:
                    print(form.file_type.data)
                    if form.file_type.data == 'audio':
                        extracted_text = process_audio_file(file_path)
                    elif form.file_type.data == 'video':
                        extracted_text = process_video_file(file_path)
                    elif form.file_type.data == 'document':
                        if file_ext == '.pdf':
                            extracted_text = process_pdf_file(file_path)
                        elif file_ext in ['.doc', '.docx']:
                            extracted_text = process_word_file(file_path)
                        else:
                            extracted_text = process_text_file(file_path)
                    elif form.file_type.data == 'image':
                        extracted_text = process_image_file(file_path)
                    elif form.file_type.data == 'text':
                        extracted_text = process_text_file(file_path)
                    
                    # Save extracted content
                    if extracted_text:
                        new_content = ExtractedContent(
                            file_id=new_file.file_id,
                            raw_text=extracted_text,
                        )
                        db.session.add(new_content)
                        
                except Exception as e:
                    app.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    flash(f'Error processing {file.filename}', 'warning')

        db.session.commit()
        flash('Files uploaded and processed successfully! Generating quiz...', 'success')
        return redirect(url_for('story', file_ids=','.join(map(str, file_ids))))
    
    # If form validation fails, show errors and return to courses page
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('courses'))

@app.route('/flashcard_learn')
def flashcard():
    # Check authentication
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    # Get and validate file IDs
    file_ids = request.args.get('file_ids', '')
    try:
        file_ids = [int(id) for id in file_ids.split(',') if id.isdigit()]
    except ValueError:
        flash('Invalid file selection', 'danger')
        return redirect(url_for('courses'))

    # Initialize card data with default structure
    card_data = {
        "topic": "Generated Flashcards",
        "cards": []
    }

    # Only proceed if we have valid file IDs
    if file_ids:
        files = InputFile.query.filter(
            InputFile.file_id.in_(file_ids),
            InputFile.session_id == flask_session['session_id']
        ).all()

        for file in files:
            content = ExtractedContent.query.filter_by(
                file_id=file.file_id
            ).order_by(ExtractedContent.content_id.desc()).first()

            if content:
                # Generate flashcards if they don't exist
                if not Flashcard.query.filter_by(content_id=content.content_id).first():
                    if not auto_card_gen(content.raw_text, content.content_id):
                        app.logger.warning(f'Flashcard generation failed for {file.file_path}')
                        continue

                # Get generated flashcards
                card_entry = Flashcard.query.filter_by(
                    content_id=content.content_id
                ).first()

                if card_entry:
                    try:
                        card_path = os.path.join(app.static_folder, 'card_data', card_entry.file_path)
                        with open(card_path, 'r') as f:
                            card_json = json.load(f)
                            card_data['cards'].extend(card_json.get('cards', []))
                            if card_json.get('topic'):
                                card_data['topic'] = card_json['topic']
                    except Exception as e:
                        app.logger.error(f"Failed to load card {card_entry.file_path}: {str(e)}")
                        continue

    # Ensure we always have at least the default structure
    if not card_data['cards']:
        flash('No flashcards found in selected files', 'warning')

    # Debug output
    app.logger.info(f"Prepared card data: {card_data}")
    
    return render_template("flashcard.html", card_data=card_data)

@app.route('/quiz_learn')
def quiz():
    # Check authentication
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    # Get and validate file IDs
    file_ids = request.args.get('file_ids', '')
    try:
        file_ids = [int(id) for id in file_ids.split(',') if id.isdigit()]
    except ValueError:
        flash('Invalid file selection', 'danger')
        return redirect(url_for('courses'))

    # Fetch files with session validation
    files = InputFile.query.filter(
        InputFile.file_id.in_(file_ids),
        InputFile.session_id == flask_session['session_id']
    ).all()

    if not files:
        flash('No valid files found for quiz generation', 'warning')
        return redirect(url_for('courses'))

    # Process files and collect quizzes
    quiz_data = {
        'topic': 'Generated Quiz',
        'questions': []
    }
    seen_topics = set()

    for file in files:
        content = ExtractedContent.query.filter_by(
            file_id=file.file_id
        ).order_by(ExtractedContent.content_id.desc()).first()

        if content:
            print(content.raw_text)
            # Generate quiz if not exists
            if not Quiz.query.filter_by(content_id=content.content_id).order_by(Quiz.quiz_id.desc()).first():
                if not auto_quiz_gen(content.raw_text, content.content_id):
                    flash(f'Quiz generation failed for {file.file_path}', 'warning')
                    continue

            # Get generated quiz
            quiz_entry = Quiz.query.filter_by(
                content_id=content.content_id
            ).order_by(Quiz.quiz_id.desc()).first()

            if quiz_entry:
                try:
                    quiz_path = os.path.join(app.static_folder, 'quiz_data', quiz_entry.file_path)
                    with open(quiz_path, 'r') as f:
                        quiz_json = json.load(f)
                        quiz_data['questions'].extend(quiz_json.get('questions', []))
                        if quiz_json.get('topic'):
                            seen_topics.add(quiz_json['topic'])
                except Exception as e:
                    app.logger.error(f"Failed to load quiz {quiz_entry.file_path}: {str(e)}")
                    continue
    
    # Set topic name based on content
    if seen_topics:
        quiz_data['topic'] = " & ".join(seen_topics) if len(seen_topics) > 1 else seen_topics.pop()

    if not quiz_data['questions']:
        flash('No quiz questions found in selected files', 'warning')
        return redirect(url_for('courses'))

    return render_template("quiz.html", quiz_data=quiz_data)


@app.route('/story')
def story():
    # Check authentication
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    # Get and validate file IDs
    file_ids = request.args.get('file_ids', '')
    try:
        file_ids = [int(id) for id in file_ids.split(',') if id.isdigit()]
    except ValueError:
        flash('Invalid file selection', 'danger')
        return redirect(url_for('courses'))

    # Initialize story data with default structure
    story_data = {
        'topic': 'Generated Story',
        'story_name': 'Educational Story',
        'characters': [],
        'scenes': []
    }

    # Only proceed if we have valid file IDs
    if file_ids:
        files = InputFile.query.filter(
            InputFile.file_id.in_(file_ids),
            InputFile.session_id == flask_session['session_id']
        ).all()

        for file in files:
            content = ExtractedContent.query.filter_by(
                file_id=file.file_id
            ).order_by(ExtractedContent.content_id.desc()).first()

            if content:
                # Generate story if it doesn't exist
                if not Story.query.filter_by(content_id=content.content_id).first():
                    if not auto_story_gen(content.raw_text, content.content_id):
                        app.logger.warning(f'Story generation failed for {file.file_path}')
                        continue

                # Get generated story
                story_entry = Story.query.filter_by(
                    content_id=content.content_id
                ).first()

                if story_entry:
                    try:
                        story_path = os.path.join(app.static_folder, 'story_data', story_entry.file_path)
                        with open(story_path, 'r') as f:
                            story_json = json.load(f)
                            
                            # Safely merge data
                            if 'scenes' in story_json:
                                story_data['scenes'].extend(story_json['scenes'])
                            if 'topic' in story_json:
                                story_data['topic'] = story_json['topic']
                            if 'story_name' in story_json:
                                story_data['story_name'] = story_json['story_name']
                            if 'characters' in story_json:
                                story_data['characters'] = story_json['characters']

                    except Exception as e:
                        app.logger.error(f"Failed to load story {story_entry.file_path}: {str(e)}")
                        continue

    # Ensure we have at least one scene
    if not story_data['scenes']:
        flash('No story scenes found in selected files', 'warning')
        return redirect(url_for('events'))

    # Debug output
    app.logger.info(f"Prepared story data: {story_data}")
    
    return render_template("story.html", story_data=story_data)

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import docx
import zipfile

# ===== UPDATED PROCESSING FUNCTIONS =====

def process_text_file(txt_path):
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        return " "


def process_word_file(docx_path):
    text = ""
    try:
        # Step 1: Extract visible text using python-docx
        doc = docx.Document(docx_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

        # Step 2: Extract images from docx (they're stored in a zip archive)
        with zipfile.ZipFile(docx_path, 'r') as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]

            for idx, image_file in enumerate(image_files):
                image_data = docx_zip.read(image_file)
                image = Image.open(io.BytesIO(image_data))

                # Perform OCR on the image
                ocr_text = pytesseract.image_to_string(image)
                text += f"\n[Image {idx + 1} OCR Text:]\n{ocr_text.strip()}\n"

        return text
    except Exception as e:
        return " "


def process_pdf_file(pdf_path):
    full_text = ""
    # print("Here it comes.............")
    try:
        # Open PDF
        doc = fitz.open(pdf_path)

        for page_number, page in enumerate(doc, start=1):
            # Step 1: Extract visible text from page
            full_text += f"\n--- Page {page_number} ---\n"
            full_text += page.get_text()

            # Step 2: Extract and OCR images
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))

                # Perform OCR on image
                ocr_text = pytesseract.image_to_string(image)
                full_text += f"\n[Image {img_index+1} OCR Text:]\n{ocr_text.strip()}\n"

        doc.close()
        return full_text

    except Exception as e:
        return ""

def process_audio_file(file_path):
    """Convert audio to text using speech recognition with proper FFmpeg setup"""
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        from io import BytesIO
        
        # Configure FFmpeg path (Windows example)
        AudioSegment.converter = r"D:\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"  # Update this path
        AudioSegment.ffprobe = r"D:\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffprobe.exe"  # Update this path
        
        # Load audio file
        audio = AudioSegment.from_file(file_path)
        
        # Convert to WAV in memory
        wav_io = BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # Recognize speech
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            # Adjust for ambient noise and record
            recognizer.adjust_for_ambient_noise(source)
            audio_data = recognizer.record(source)
            
            # Try Google Web Speech API
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                app.logger.warning("Google Speech Recognition could not understand audio")
                return ""
            except sr.RequestError as e:
                app.logger.error(f"Could not request results from Google SR service; {e}")
                return ""
                
    except Exception as e:
        app.logger.error(f"Audio processing error: {str(e)}")
        return ""

def process_video_file(file_path):
    """Extract text from video frames and audio with proper FFmpeg setup"""
    try:
        from moviepy import VideoFileClip
        import cv2
        import pytesseract
        from fuzzywuzzy import fuzz
        
        # Configure paths (Windows example)
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        os.environ["IMAGEIO_FFMPEG_EXE"] = r"D:\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"
        
        # Extract text from video frames
        clip = VideoFileClip(file_path)
        duration = int(clip.duration)
        extracted_text = []
        last_text = ""
        SIMILARITY_THRESHOLD = 85  # Slightly lower threshold for better results
        
        # Process every 3 seconds (adjust as needed)
        for t in range(0, duration, 3):
            try:
                frame = clip.get_frame(t)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Preprocess image for better OCR
                gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Perform OCR with custom config
                text = pytesseract.image_to_string(
                    thresh,
                    config='--psm 6 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?()[]{}:;\"\' '
                ).strip()
                
                # Check similarity to last text
                if text and (not last_text or fuzz.ratio(text, last_text) < SIMILARITY_THRESHOLD):
                    extracted_text.append(f"[Frame at {t} sec]\n{text}\n")
                    last_text = text
                    
            except Exception as frame_error:
                app.logger.warning(f"Error processing frame at {t} sec: {frame_error}")
                continue
        
        # Extract audio and convert to text
        audio_text = process_audio_from_video(file_path)
        if audio_text:
            extracted_text.append("\n[Audio Transcript]\n" + audio_text)
        
        clip.close()
        return "\n".join(extracted_text)
        
    except Exception as e:
        app.logger.error(f"Video processing error: {str(e)}")
        return ""

def process_audio_from_video(video_path):
    """Extract audio from video and convert to text"""
    try:
        from moviepy import VideoFileClip
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                clip.audio.write_audiofile(tmp.name)
                return process_audio_file(tmp.name)
        return ""
    except Exception as e:
        app.logger.error(f"Video audio extraction error: {str(e)}")
        return ""
def process_word_file(file_path):
    """Improved Word document text extraction"""
    try:
        if file_path.lower().endswith('.docx'):
            from docx import Document
            doc = Document(file_path)
            full_text = []
            
            # Extract from paragraphs
            full_text.extend([para.text for para in doc.paragraphs])
            
            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        full_text.append(cell.text)
            
            return "\n".join(full_text)
            
        elif file_path.lower().endswith('.doc'):
            try:
                # Try textract as a more reliable solution
                import textract
                return textract.process(file_path).decode('utf-8')
            except:
                # Fallback to antiword if available
                try:
                    import subprocess
                    result = subprocess.run(
                        ['antiword', file_path],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    return result.stdout
                except:
                    return "DOC processing requires textract or antiword installation"
                    
    except Exception as e:
        app.logger.error(f"Word document processing error: {str(e)}")
        return ""

def process_image_file(file_path):
    """Extract text from image using OCR"""
    try:
        import pytesseract
        from PIL import Image
        
        # Set Tesseract path (Windows)
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        text = pytesseract.image_to_string(Image.open(file_path))
        return text.strip()
    except Exception as e:
        app.logger.error(f"Image processing error: {str(e)}")
        return ""


def auto_card_gen(content, content_id):
    """Generate and store flashcards from extracted content"""
    try:
        # In a real implementation, you would generate cards from the content.raw_text
        # For now, using sample data similar to your HTML file
        gen_content=gen_flashcards(content)
        # gen_content = {
        #     "topic": "General Knowledge",
        #     "cards": [
        #         {
        #             "question": "What is the capital of France?",
        #             "answer": "Paris",
        #             "analogy": "Just like Washington D.C. is to the United States, Paris is to France.",
        #             "common_mistake": "Many people think it's London or Berlin."
        #         },
        #         {
        #             "question": "What is the largest planet in our solar system?",
        #             "answer": "Jupiter",
        #             "analogy": "Jupiter is like the big brother of the solar system family.",
        #             "common_mistake": "People often confuse it with Saturn because of its rings."
        #         },
        #         {
        #             "question": "Who wrote 'Romeo and Juliet'?",
        #             "answer": "William Shakespeare",
        #             "analogy": "Shakespeare is to literature what Einstein is to physics.",
        #             "common_mistake": "Some attribute it to Charles Dickens by mistake."
        #         }
        #     ]
        # }
        
        save_folder = os.path.join(app.static_folder, 'card_data')
        os.makedirs(save_folder, exist_ok=True)

        # Create safe filename
        safe_topic = "".join([c if c.isalnum() else "_" for c in gen_content['topic']])
        filename = f"{content_id}_{safe_topic}.json"
        save_path = os.path.join(save_folder, filename)

        # Save card data to JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(gen_content, f, indent=4, ensure_ascii=False)

        # Store card metadata in database
        card_entry = Flashcard(
            content_id=content_id,
            topic=gen_content['topic'],
            file_path=filename  # Store just the filename
        )
        
        db.session.add(card_entry)
        db.session.commit()
        return True
        
    except Exception as e:
        app.logger.error(f"Flashcard generation failed: {str(e)}")
        db.session.rollback()
        return False
    
def auto_quiz_gen(content, content_id):
    """Generate and store quiz from extracted content"""
    try:
        gen_content=gen_quiz(content)
        # Generate quiz using actual content
#         gen_content = {
#   "topic": "photosynthesis",
#   "generated_at": "2025-04-21T18:24:40.139461",
#   "questions": [
#     {
#       "question": "Which gas is primarily used by plants during the process of photosynthesis?",
#       "options": {
#         "A": "Oxygen (O\u2082)",
#         "B": "Carbon Dioxide (CO\u2082)",
#         "C": "Nitrogen (N\u2082)",
#         "D": "Water Vapor (H\u2082O)"
#       },
#       "answer": "B",
#       "explanation": "Plants breathe in CO\u2082 and exhale O\u2082, much like us. Think of it as a reverse carbon cycle\u2014they take what we expel and turn it into food and oxygen.",
#       "hint": "Consider the air we breathe out versus what plants need to grow.\n\n---"
#     },
#     {
#       "question": "Which process is primarily responsible for the production of glucose during photosynthesis?",
#       "options": {
#         "A": "Respiration",
#         "B": "Transpiration",
#         "C": "Calvin Cycle",
#         "D": "Photolysis"
#       },
#       "answer": "C",
#       "explanation": "The Calvin Cycle is like a factory within the plant, turning CO\u2082 and energy from the light reactions into glucose. It's the assembly line where sugar is made.",
#       "hint": "Think about what happens after sunlight hits a leaf.\n\n---"
#     },
#     {
#       "question": "What molecule acts as the primary pigment that absorbs light energy in photosynthesis?",
#       "options": {
#         "A": "Carotenoids",
#         "B": "Chlorophyll",
#         "C": "Anthocyanins",
#         "D": "Phycobilins"
#       },
#       "answer": "B",
#       "explanation": "Chlorophyll is green and abundant in leaves. It's like the sun\u2019s favorite color, absorbing red and blue wavelengths while reflecting green back to our eyes.",
#       "hint": "Think about why plants appear green.\n\n---"
#     },
#     {
#       "question": "Which of the following statements best describes the role of stomata during photosynthesis?",
#       "options": {
#         "A": "They release oxygen into the atmosphere.",
#         "B": "They absorb light energy from the sun.",
#         "C": "They control the exchange of gases between the plant and its environment.",
#         "D": "They transport glucose to other parts of the plant."
#       },
#       "answer": "C",
#       "explanation": "Stomata are tiny pores that open and close to let CO\u2082 in for photosynthesis and release O\u2082. It\u2019s like a plant's respiratory system, ensuring it gets what it needs while breathing out what isn\u2019t used.",
#       "hint": "Think about how you breathe\u2014open and close your mouth and nose."
#     }
#   ]
# }
        
        # Ensure output directory exists
        save_folder = os.path.join(app.static_folder, 'quiz_data')
        os.makedirs(save_folder, exist_ok=True)

        # Create safe filename
        safe_topic = "".join([c if c.isalnum() else "_" for c in gen_content['topic']])
        filename = f"{content_id}_{safe_topic}.json"
        save_path = os.path.join(save_folder, filename)

        # Save quiz data to JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(gen_content, f, indent=4, ensure_ascii=False)

        # Store quiz metadata in database
        quiz_entry = Quiz(
            content_id=content_id,
            created_at=datetime.utcnow(),
            topic=gen_content['topic'],
            file_path=filename  # Store just the filename
        )
        
        db.session.add(quiz_entry)
        db.session.commit()
        return True
        
    except Exception as e:
        app.logger.error(f"Quiz generation failed: {str(e)}")
        db.session.rollback()
        return False    


from flask import url_for

def convert_dataset_to_flask_format(data):
    converted = {
        "topic": data["topic"],
        "story_name": data["story_name"],
        "characters": [],
        "scenes": []
    }

    for char in data["characters"]:
        converted["characters"].append({
            "name": char["name"],
            "description": char["description"],
            "image_path": url_for('static', filename='images/' + char["image_path"].split('/')[-1]),
            "voice_id": char["voice_id"]
        })

    for scene in data["scenes"]:
        new_scene = {
            "scene_number": scene["scene_number"],
            "scene_title": scene["scene_title"],
            "setting": scene["setting"],
            "scene_image_path": url_for('static', filename='images/' + scene["scene_image_path"].split('/')[-1]),
            "dialogues_with_audio": []
        }
        for dlg in scene["dialogues_with_audio"]:
            new_scene["dialogues_with_audio"].append({
                "character": dlg["character"],
                "line": dlg["line"],
                "audio_path": url_for('static', filename='audio/' + dlg["audio_path"].split('/')[-1])
            })
        converted["scenes"].append(new_scene)

    return converted

def auto_story_gen(content, content_id):
    """Generate and store quiz from extracted content"""
    try:
        #gen_content=gen_story_pipe(content)
        # Generate quiz using actual content
        #print("Generated story for reference: ",gen_content)
        gen_content = {'topic': 'Web Technology', 'story_name': 'The Digital Journey', 'characters': [{'name': 'Sam', 'description': 'A 20-year-old web developer with a passion for coding and design.(Male,20 years old)', 'image_path': '/static/images/character_Sara.png', 'voice_id': 'en-US-AnaNeural'}, {'name': 'Ella', 'description': 'Samâ€™s 18-year-old younger sister who loves exploring the internet but is clueless about how it works.(Female,18 years old)', 'image_path': '/static/images/character_Ella.png', 'voice_id': 'en-US-EmmaNeural'}], 'scenes': [{'scene_number': 1, 'scene_title': 'Introduction to Web Technology', 'setting': "Sam's home office, filled with computers and coding materials.", 'scene_image_path': '/static/images/scene_1.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'Hey Ella! Ever wondered how websites work?', 'audio_path': '/static/audio/scene_1_Sam_8803048711182253209.mp3'}, {'character': 'Ella', 'line': 'Nope, I just use them. But now that you mention it, they seem magical!', 'audio_path': '/static/audio/scene_1_Ella_5073892552213998016.mp3'}]}, {'scene_number': 2, 'scene_title': 'Explaining the Browser', 'setting': 'Same as Scene 1, but now Sam is showing Ella a browser window.', 'scene_image_path': '/static/images/scene_2.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'A web browser like Chrome or Firefox acts like your guide to the internet world.', 'audio_path': '/static/audio/scene_2_Sam_5585488773933349911.mp3'}, {'character': 'Ella', 'line': 'So, when I type in a websiteâ€™s address, it just magically appears?', 'audio_path': '/static/audio/scene_2_Ella_5200373228080006657.mp3'}]}, {'scene_number': 3, 'scene_title': 'The Web Page and Server', 'setting': 'Same as Scene 1, but now Sam explains using an online example.', 'scene_image_path': '/static/images/scene_3.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'Well, when you enter a URL, your browser sends a request to the server.', 'audio_path': '/static/audio/scene_3_Sam_4389710041419340902.mp3'}, {'character': 'Ella', 'line': "A server? Isn't that where they keep all the data?", 'audio_path': '/static/audio/scene_3_Ella_3125721385763101166.mp3'}]}, {'scene_number': 4, 'scene_title': 'The Process Behind It', 'setting': 'Same as Scene 1, but now Sam is drawing a flowchart on a whiteboard.', 'scene_image_path': '/static/images/scene_4.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'Exactly! Think of it like this: You type in an address, your request goes to the server, and the server responds with a web page.', 'audio_path': '/static/audio/scene_4_Sam_8820062971787829019.mp3'}, {'character': 'Ella', 'line': 'Wait, so websites are just documents that live online?', 'audio_path': '/static/audio/scene_4_Ella_4931873346853986970.mp3'}]}, {'scene_number': 5, 'scene_title': 'The Various Languages', 'setting': 'Same as Scene 1, but now Sam is showing Ella various coding languages.', 'scene_image_path': '/static/images/scene_5.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': "Yes, they're like recipes for building those web pages. HTML, CSS, and JavaScript all have their roles.", 'audio_path': '/static/audio/scene_5_Sam_4825247617952534862.mp3'}, {'character': 'Ella', 'line': 'Oh! So thatâ€™s why websites look different when you inspect them.', 'audio_path': '/static/audio/scene_5_Ella_8241726353388407965.mp3'}]}, {'scene_number': 6, 'scene_title': 'The Role of Back-End Languages', 'setting': 'Same as Scene 1, but now Sam is explaining with an example.', 'scene_image_path': '/static/images/scene_6.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'You see, some sites use languages like Python or Java on the back end to handle dynamic content.', 'audio_path': '/static/audio/scene_6_Sam_6299336235364698005.mp3'}, {'character': 'Ella', 'line': 'Thatâ€™s pretty cool! So those languages are behind the scenes?', 'audio_path': '/static/audio/scene_6_Ella_142838826489415262.mp3'}]}, {'scene_number': 7, 'scene_title': 'The Role of Databases', 'setting': 'Same as Scene 1, but now Sam is explaining about databases.', 'scene_image_path': '/static/images/scene_7.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'Absolutely. Databases store all that data like user information or product details.', 'audio_path': '/static/audio/scene_7_Sam_1006774595629906558.mp3'}, {'character': 'Ella', 'line': 'So websites need both servers and databases to function properly?', 'audio_path': '/static/audio/scene_7_Ella_1694715696976579206.mp3'}]}, {'scene_number': 8, 'scene_title': 'The Future of Web Development', 'setting': 'Same as Scene 1, but now Sam and Ella are looking at the future trends.', 'scene_image_path': '/static/images/scene_8.png', 'dialogues_with_audio': [{'character': 'Sam', 'line': 'Yes, itâ€™s evolving. Technologies like Golang or C# can make development more efficient.', 'audio_path': '/static/audio/scene_8_Sam_1613135523112767365.mp3'}, {'character': 'Ella', 'line': "Wow, I want to learn all about this! Maybe one day I'll create my own website.", 'audio_path': '/static/audio/scene_8_Ella_9124851288458067533.mp3'}]}]}
        gen_content=convert_dataset_to_flask_format(gen_content)
        # Ensure output directory exists
        save_folder = os.path.join(app.static_folder, 'story_data')
        os.makedirs(save_folder, exist_ok=True)

        # Create safe filename
        safe_topic = "".join([c if c.isalnum() else "_" for c in gen_content['topic']])
        filename = f"{content_id}_{safe_topic}.json"
        save_path = os.path.join(save_folder, filename)

        # Save quiz data to JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(gen_content, f, indent=4, ensure_ascii=False)

        # Store quiz metadata in database
        story_entry = Story(
            content_id=content_id,
            created_at=datetime.utcnow(),
            topic=gen_content['topic'],
            file_path=filename  # Store just the filename
        )
        
        db.session.add(story_entry)
        db.session.commit()
        return True
        
    except Exception as e:
        app.logger.error(f"Story generation failed: {str(e)}")
        db.session.rollback()
        return False    
# ----------------------------------------------------------------------------------

# Main Pages
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/story_based_learning")
def events():
    # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()
    # Fetch uploaded files and their extracted content
    files = InputFile.query.filter_by(session_id=flask_session['session_id']) \
                           .order_by(InputFile.created_at.desc()).all()
    
    # Add URL and extracted content to each file object
    for file in files:
        file.url = url_for('static', filename=os.path.join(file.file_type, os.path.basename(file.file_path)))
        file.extracted_content = ExtractedContent.query.filter_by(file_id=file.file_id).first()

    return render_template("events.html", form=form, files=files)

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/flashcard")
def trainers():
        # Check if user is logged in
    if 'session_id' not in flask_session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('index'))

    form = UploadForm()
    # Fetch uploaded files and their extracted content
    files = InputFile.query.filter_by(session_id=flask_session['session_id']) \
                           .order_by(InputFile.created_at.desc()).all()
    
    # Add URL and extracted content to each file object
    for file in files:
        file.url = url_for('static', filename=os.path.join(file.file_type, os.path.basename(file.file_path)))
        file.extracted_content = ExtractedContent.query.filter_by(file_id=file.file_id).first()


    return render_template("trainers.html", form=form, files=files)

# @app.route("/starter-page")
# def starter_page():
#     return render_template("starter-page.html")

@app.route("/<page>.html")
def redirect_html_pages(page):
    return redirect(url_for(page))



def init_user_data():
    return {
        'random_challenge':{},
        'unlocked_levels': {"python":1,"c++":1,"c":1,"java":1},
        'coins': 50,
        'completed_levels': {},
        'inventory': [],
        'last_login': datetime.now().isoformat(),
        'username': 'Player',
        'streak': 0
    }

@app.before_request
def before_request():
    if 'user_data' not in flask_session:  # Fixed
        flask_session['user_data'] = init_user_data()
    else:
        last_login = datetime.fromisoformat(flask_session['user_data']['last_login'])  # Fixed
        today = datetime.now().date()
        if last_login.date() < today:
            if (today - last_login.date()).days == 1:
                flask_session['user_data']['streak'] += 1  # Fixed
            else:
                flask_session['user_data']['streak'] = 1  # Fixed
            flask_session['user_data']['last_login'] = datetime.now().isoformat()
    if 'user_data' not in flask_session:  # Changed from session
        flask_session['user_data'] = init_user_data()  # Changed from session
    else:
        # Check for daily streak
        last_login = datetime.fromisoformat(flask_session['user_data']['last_login'])  # Changed
        today = datetime.now().date()
        if last_login.date() < today:
            if (today - last_login.date()).days == 1:
                flask_session['user_data']['streak'] += 1  # Changed
            else:
                flask_session['user_data']['streak'] = 1  # Changed
            flask_session['user_data']['last_login'] = datetime.now().isoformat()

@app.route('/code_blocks')
def cb_index():
    user_data = flask_session.get('user_data', init_user_data())  # Fixed
    selected_language = request.args.get('language')
    if selected_language:
        print("Selected language:", selected_language)
    else:
        selected_language = 'python'
    filtered_levels = [level for level in LEVELS if level['language'].lower() == selected_language.lower()]
    return render_template('cb_index.html', levels=filtered_levels, language=selected_language, 
                         progress=user_data['unlocked_levels'][selected_language.lower()], user_data=user_data)

@app.route('/level/<language>/<int:level_id>')
def level(language, level_id):
    user_data = flask_session.get('user_data', init_user_data())
    # print(user_data['unlocked_levels'][language.lower()])
    if level_id > user_data['unlocked_levels'][language.lower()]:
        return redirect(url_for('cb_index', language=language))

    # Filter the level using both ID and language
    level_data = next(
        (lvl for lvl in LEVELS if lvl['id'] == level_id and lvl['language'].lower() == language.lower()),
    )
    if not level_data:
        return redirect(url_for('cb_index', language=language))

    return render_template('level.html', level=level_data, user_data=user_data)

@app.route('/submit_solution/<int:flag>/<language>/<int:level_id>', methods=['POST'])
@csrf.exempt  
def submit_solution(flag, language, level_id):
    total = 50
    lang_lower = language.lower()
    
    # Set total levels per language
    if lang_lower == "python":
        total = 50
    elif lang_lower == "c":
        total = 19
    elif lang_lower == "c++":
        total = 50
    else:  # java
        total = 37

    # Get user data and request data
    user_data = flask_session.get('user_data', init_user_data())
    data = request.get_json(silent=True) or {}
    submitted_order = data.get('order', [])

    # Find matching level
    level_data = next(
        (lvl for lvl in LEVELS 
         if lvl['id'] == level_id 
         and lvl['language'].lower() == lang_lower
        ), 
        None
    )

    if not level_data:
        return jsonify({'success': False, 'message': 'Level not found'}), 404

    # Check solution
    is_correct = submitted_order == level_data['solution']
    level_str = str(level_id)+language
    already_completed = level_str in user_data['completed_levels'] or level_str in user_data["random_challenge"]

    if is_correct:
        coins_earned = 0
        
        if flag == 0:  # Regular level
            if not already_completed:
                coins_earned = level_data['base_coins'] + level_data['first_time_bonus']
                user_data['coins'] += coins_earned
                user_data['completed_levels'][level_str] = {
                    'completed': True,
                    'timestamp': datetime.now().isoformat(),
                    'coins_earned': coins_earned,
                }
                # Unlock next level if applicable
                if user_data['unlocked_levels'][lang_lower] == level_id and level_id < total:
                    user_data['unlocked_levels'][lang_lower] += 1
                    
        elif flag == 1:  # Random challenge
            if not already_completed:
                coins_earned = level_data['base_coins'] + level_data['first_time_bonus']
                user_data['coins'] += coins_earned
                user_data['random_challenge'][level_str] = {
                    'completed': True,
                    'timestamp': datetime.now().isoformat(),
                    'coins_earned': coins_earned,
                }

        # Save updated session
        flask_session['user_data'] = user_data

        return jsonify({
            'success': True,
            'message': 'Correct solution!',
            'coins_earned': coins_earned,
            'total_coins': user_data['coins'],
            'new_completion': not already_completed,
            'unlocked_new_level': (level_id == user_data['unlocked_levels'][lang_lower] - 1)
        })

    return jsonify({
        'success': False,
        'message': 'Incorrect solution. Try again!'
    })
@app.route('/profile')
def profile():
    user_data = flask_session.get('user_data', init_user_data())  # Fixed
    return render_template('profile.html', user_data=user_data)
    user_data = flask_session.get('user_data', init_user_data())  # Changed from session
    return render_template('profile.html', user_data=user_data)

@app.route('/store')
def store():
    user_data = flask_session.get('user_data', init_user_data())  # Changed from session
    store_items = [
        {'id': 1, 'name': 'Robot Avatar', 'price': 100, 'type': 'avatar', 'color': 'e74c3c'},
        {'id': 2, 'name': 'Golden Code Block', 'price': 200, 'type': 'cosmetic'},
        {'id': 3, 'name': 'Debugger Theme', 'price': 150, 'type': 'theme', 'preview_gradient': 'linear-gradient(135deg, #2c3e50, #4ca1af)'},
        {'id': 4, 'name': 'Hint Pack (5)', 'price': 75, 'type': 'utility', 'description': 'Get 5 hints for tough levels'},
        {'id': 5, 'name': 'Pro Coder Avatar', 'price': 250, 'type': 'avatar', 'color': '3498db'}
    ]
    return render_template('store.html', items=store_items, user_data=user_data)

@app.route('/buy_item/<int:item_id>', methods=['POST'])
@csrf.exempt
def buy_item(item_id):
    user_data = flask_session.get('user_data', init_user_data())
    store_items = [
        {'id': 1, 'name': 'Robot Avatar', 'price': 100, 'type': 'avatar', 'color': 'e74c3c'},
        {'id': 2, 'name': 'Golden Code Block', 'price': 200, 'type': 'cosmetic'},
        {'id': 3, 'name': 'Debugger Theme', 'price': 150, 'type': 'theme', 'preview_gradient': 'linear-gradient(135deg, #2c3e50, #4ca1af)'},
        {'id': 4, 'name': 'Hint Pack (5)', 'price': 75, 'type': 'utility', 'description': 'Get 5 hints for tough levels'},
        {'id': 5, 'name': 'Pro Coder Avatar', 'price': 250, 'type': 'avatar', 'color': '3498db'}
    ]
    
    item = next((item for item in store_items if item['id'] == item_id), None)
    
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'})
    
    if user_data['coins'] >= item['price']:
        # Check if already owns non-consumable item
        if item['type'] in ['avatar', 'theme', 'cosmetic'] and any(i['id'] == item_id for i in user_data['inventory']):
            return jsonify({'success': False, 'message': 'You already own this item'})
        
        user_data['coins'] -= item['price']
        user_data['inventory'].append(item)
        
        # Apply avatar color immediately if purchased
        if item['type'] == 'avatar' and 'color' in item:
            user_data['avatar_color'] = item['color']
        
        flask_session['user_data'] = user_data
        return jsonify({
            'success': True,
            'message': f'Purchased {item["name"]}!',
            'remaining_coins': user_data['coins']
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Not enough coins!'
        })

@app.route('/use_hint/<language>/<int:level_id>')
def use_hint(language,level_id):
    user_data = flask_session.get('user_data', init_user_data())
    
    # Check if user has hints
    '''hint_items = [item for item in LEVELS['inventory'] if item['type'] == 'utility']
    if not hint_items:
        return jsonify({'success': False, 'message': 'No hints available'})
    
    # Use one hint
    user_data['inventory'].remove(hint_items[0])'''
    
    # Get a random hint for the level
    level_data = next((lvl for lvl in LEVELS if lvl['id'] == level_id), None)
    # print(level_data)
    if not level_data:
        return jsonify({'success': False, 'message': 'Level not found'})
    
    hint = random.choice(level_data['hints'])
    # print("Hints:",hint)
    flask_session['user_data'] = user_data
    return jsonify({
        'success': True,
        'hint': hint,
        'hints_remaining': len([item for item in user_data['inventory'] if item['type'] == 'utility'])
    })

@app.route('/daily_challenge')
def daily_challenge():
    user_data = flask_session.get('user_data', init_user_data())  # Fixed
    level_data = random.choice(LEVELS)
    return render_template('daily_challenge.html', level=level_data, user_data=user_data)


def generate_code_template(language: str, concept: str, difficulty: str) -> dict:
    """
    Generate code templates with snippets for a given programming language using locally hosted Llama 3 via Ollama.
    
    Args:
        language (str): The programming language to generate templates for (e.g., "python", "c++", "java")
        concept (str): The programming concept to focus on (e.g., "recursion", "loops", "classes")
    
    Returns:
        dict: A dictionary with language as key and list of 5 templates as value
    """
    
    ollama_url = "http://localhost:11434/api/generate"
    
    # System prompt that will guide Llama 3 to generate the desired output
    system_prompt = f"""You are a helpful coding assistant that generates programming exercises in {language} containing {concept} concept of difficulty {difficulty}. 
    Generate exactly 5 different code templates with missing parts marked with '# DRAG SNIPPET HERE'.
    For each template, provide exactly 4 snippets where only one is correct, including the solution and a brief description.
    Also include expected output and a hint for each exercise.

    Here are 2 examples of the exact format required:

    Example 1 (Python - Basic Function):
    {{
        "id": 1,
        "template": "def max_of_two_numbers(a, b):\\n    # DRAG SNIPPET HERE\\n",
        "snippets": [
            "return min(a,b)",
            "if a > b: return a else: return b",
            "return (a if a > b else b)",
            "return (b if a < b else a)"
        ],
        "solution": "return (a if a > b else b)",
        "description": "Create a function that takes two numbers as arguments and returns the larger one.\\nThis exercise tests understanding of conditional statements and function creation.",
        "expected_output": "When called with max_of_two_numbers(3, 5), the function should return 5",
        "hint": "Think about how to compare two values and return one based on the comparison"
    }}

    Example 2 (Python - List Operations):
    {{
        "id": 2,
        "template": "my_list = [10, 20, 30]\\nprint(# DRAG SNIPPET HERE)",
        "snippets": [
            "[10, 20, 30][1]",
            "my_list[1]",
            "2nd_element",
            "list[1]"
        ],
        "solution": "my_list[1]",
        "description": "Define a list and print its second element.\\nThis exercise tests understanding of list indexing.",
        "expected_output": "20",
        "hint": "Remember Python uses zero-based indexing for lists"
    }}

    Now generate 5 different exercises for {language} about {concept} of difficulty {difficulty}following EXACTLY this format:
    {{
        "{language.lower()}": [
            {{ (Exercise 1 - must be different from examples above) }},
            {{ (Exercise 2) }},
            {{ (Exercise 3) }},
            {{ (Exercise 4) }},
            {{ (Exercise 5) }}
        ]
    }}

    Important Rules:
    1. All fields must be included exactly as shown in examples
    1.1. The Solution should be at max three lines not more than that rest should be in the question snippet itself
    2. Never repeat the same exercise concept
    3. Ensure code is syntactically correct
    4. Provide specific expected outputs
    5. Hints should be helpful but not give away the solution
    6. Maintain consistent JSON formatting
    7. Generate exactly 5 exercises
    8. All snippets should be plausible but only one correct
    9. Make sure the solution is present in the snippets
    10.Make sure you follow the difficulty level
    11. Make sure the response is really good before responding
    """
    
    # Prepare the prompt for Ollama
    prompt = {
        "model": "qwen2.5:latest",
        "system": system_prompt,
        "prompt": f"Generate 5 different coding exercise templates in {language} about {concept} of {difficulty} with snippets, solutions and descriptions.",
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(ollama_url, json=prompt)
        response.raise_for_status()
        
        # Parse the response
        response_data = json.loads(response.text)
        generated_content = response_data.get("response", "")
        
        # Clean the response if it's wrapped in markdown
        if generated_content.strip().startswith("```json"):
            generated_content = generated_content[generated_content.find('{'):generated_content.rfind('}')+1]
        
        # Parse the JSON content
        templates = json.loads(generated_content)
        
        # Verify we got exactly 5 templates
        if len(templates.get(language.lower(), [])) != 5:
            raise ValueError("Did not receive exactly 5 templates")
            
        return templates
        
    except Exception as e:
        print(f"Error generating code template: {e}")
        # Return empty structure with correct format
        return {language.lower(): []}


@app.route('/code_quest')
def language_selection():
    questions={"Java":1,"Python":1,"C":1,"C++":1,"Javascript":1}
    return render_template('language_selection.html', languages=list(questions.keys()))

@app.route('/start_game/<language>/<concept>/<difficulty>')
@csrf.exempt
def start_game(language,concept,difficulty):
    questions=generate_code_template(language,concept,difficulty)

    '''questions={
    "python": [
        {
            "id": 1,
            "template": "def evaluate_postfix(expression):\n    stack = []\n    # DRAG SNIPPET HERE\n",
            "snippets": [
                "for char in expression:\n        if char.isdigit():\n            stack.append(int(char))\n        else:\n            operand1 = stack.pop()\n            operand2 = stack.pop()\n            result = 0\n            if char == '+':\n                result = operand2 + operand1\n            elif char == '-':\n                result = operand2 - operand1\n            elif char == '*':\n                result = operand2 * operand1\n            else:\n                result = operand2 / operand1\n            stack.append(result)\n    return stack[0]",
                "for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))\n        else:\n            while len(stack) > 1:\n                stack.pop()\n            result = 0\n            operand2 = stack.pop()\n            operand1 = stack.pop()\n            if char == '+':\n                result = operand2 + operand1\n            elif char == '-':\n                result = operand2 - operand1\n            elif char == '*':\n                result = operand2 * operand1\n            else:\n                result = operand2 / operand1\n            stack.append(result)",
                "for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))\n        else:\n            stack.pop()\n    return stack[0]",
                "for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))\n        else:\n            while len(stack) > 1:\n                stack.pop()",
                "return 5"
            ],
            "solution": "for char in expression:\n    if char.isdigit():\n        stack.append(int(char))\n    else:\n        operand1 = stack.pop()\n        operand2 = stack.pop()\n        result = 0\n        if char == '+':\n            result = operand2 + operand1\n        elif char == '-':\n            result = operand2 - operand1\n        elif char == '*':\n            result = operand2 * operand1\n        else:\n            result = operand2 / operand1\n        stack.append(result)\n    return stack[0]",
            "description": "Evaluate a postfix expression using a stack.\nThis exercise tests understanding of stack operations and conditional statements.",
            "expected_output": "When called with evaluate_postfix('5 3 +'), the function should return 8",
            "hint": "Think about how to pop operands from the stack and perform arithmetic operations based on the operator"
        },
        {
            "id": 2,
            "template": "def validate_brackets(expression):\n    stack = []\n    # DRAG SNIPPET HERE\n",
            "snippets": [
                "for char in expression:\n        if char == '(':\n            stack.append('(')\n        elif char == ')':\n            if len(stack) > 0 and stack.pop() == '(':",
                "stack = []\n    for i, char in enumerate(expression):\n        if char == '(':\n            stack.append('(')",
                "for char in expression:\n        if char == '[' or char == '{':\n            stack.append(char)\n        elif char == ']' or char == '}':",
                "stack = []\n    for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))",
                "return True"
            ],
            "solution": "for char in expression:\n    if char == '(':\n        stack.append('(')\n    elif char == ')':\n        if len(stack) > 0 and stack.pop() == '(':",
            "description": "Validate a string of brackets by ensuring they are properly nested.\nThis exercise tests understanding of stack operations.",
            "expected_output": "When called with validate_brackets('(5 + 3)'), the function should return True",
            "hint": "Think about how to use the stack to track the opening and closing of brackets"
        },
        {
            "id": 3,
            "template": "def find_max_depth(expression):\n    stack = []\n    # DRAG SNIPPET HERE\n",
            "snippets": [
                "max_depth = 0\n    for char in expression:\n        if char == '(' or char == '[' or char == '{':\n            stack.append(char)\n            max_depth += 1\n        elif char == ')' or char == ']' or char == '}':",
                "for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))\n    return len(stack)",
                "stack = []\n    for char in expression:\n        if char == '(':\n            stack.append('(')\n        elif char == ')':",
                "max_depth = 0\n    for i, char in enumerate(expression):\n        if char == '(' or char == '[' or char == '{':\n            max_depth += 1",
                "return 5"
            ],
            "solution": "max_depth = 0\nfor char in expression:\n    if char == '(' or char == '[' or char == '{':\n        stack.append(char)\n        max_depth += 1\n    elif char == ')' or char == ']' or char == '}':",
            "description": "Find the maximum depth of a nested bracketed expression.\nThis exercise tests understanding of stack operations and conditional statements.",
            "expected_output": "When called with find_max_depth('(5 + (3 - 2))'), the function should return 4",
            "hint": "Think about how to use the stack to track the nesting depth of brackets"
        },
        {
            "id": 4,
            "template": "def parse_expression(expression):\n    stack = []\n    # DRAG SNIPPET HERE\n",
            "snippets": [
                "for i, char in enumerate(expression):\n    if char.isdigit():\n        stack.append(int(char))\n    elif char == '+' or char == '-' or char == '*' or char == '/':",
                "stack = []\n    for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))",
                "for char in expression:\n    if char.isdigit():\n        stack.append(int(char))\n    elif char == '(' or char == '[' or char == '{':",
                "stack = []\n    for i, char in enumerate(expression):\n        if char == '(':",
                "return 5"
            ],
            "solution": "for i, char in enumerate(expression):\n    if char.isdigit():\n        stack.append(int(char))\n    elif char == '+' or char == '-' or char == '*' or char == '/':",
            "description": "Parse a postfix expression into its components.\nThis exercise tests understanding of stack operations and conditional statements.",
            "expected_output": "When called with parse_expression('5 3 +'), the function should return [5, 3, '+']",
            "hint": "Think about how to use the stack to separate the input expression into its components"
        },
        {
            "id": 5,
            "template": "def is_palindrome(expression):\n    stack = []\n    # DRAG SNIPPET HERE\n",
            "snippets": [
                "for i, char in enumerate(expression):\n    if char.isalpha():\n        stack.append(char.lower())\n    elif char == ' ':",
                "stack = []\n    for i, char in enumerate(expression):\n        if char.isdigit():\n            stack.append(int(char))",
                "for char in expression:\n    if char.isalnum():\n        stack.append(char)\n    elif char == ' ':",
                "return True"
            ],
            "solution": "for i, char in enumerate(expression):\n    if char.isalpha():\n        stack.append(char.lower())\n    elif char == ' ':\n        while len(stack) > 0 and stack.pop() == '':",
            "description": "Check if a given string is a palindrome.\nThis exercise tests understanding of stack operations.",
            "expected_output": "When called with is_palindrome('A man, a plan, a canal: Panama'), the function should return True",
            "hint": "Think about how to use the stack to track characters and check for palindrome"
        }
    ]
}'''
    #print(questions)
    with open(r"D:\Downloads\Edumate\static\codequest_data\question.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    #print("questions:",questions)
    # if language not in questions:
    #     return "Language not supported", 404
    current_question = questions[language][0]
    return render_template('game.html', 
                         question=current_question,
                         total_levels=len(questions[language]),
                         language=language)

@app.route('/check_answer/<language>', methods=['POST'])
@csrf.exempt
def check_answer(language):
    data = request.json
    question_id = data['question_id']
    user_answer = data['answer']
    # print("Data:",data)
    # print("User answer:",user_answer)
    with open(r"D:\Downloads\Edumate\static\codequest_data\question.json", "r", encoding="utf-8") as f:
        questions=json.load(f)
    solution=""
    for i in questions[language]:
        if(i["id"]==question_id):
            solution=i["solution"]
    # print(solution)
    is_correct = (user_answer.strip() == solution.strip())
    question = next(q for q in questions[language] if q["id"] == question_id)
    
    #question["attempts_left"] -= 1
    
    response = {
        "correct": is_correct,
        "solution": question["solution"] if not is_correct else None,
        "attempts_left":1, #changed over here
        "move_to_next": True #changed over here
    }
    
    if response["move_to_next"]:
        question["attempts_left"] = 3  # Reset attempts
    
    return jsonify(response)

@app.route('/next_question/<language>', methods=['POST'])
@csrf.exempt
def next_question(language):
    current_id = request.json['current_id']
    next_id = current_id + 1
    with open(r"D:\Downloads\Edumate\static\codequest_data\question.json", "r", encoding="utf-8") as f:
        questions=json.load(f)
    # print(questions)
    if next_id <= len(questions[language]):
        next_q = next(q for q in questions[language] if q["id"] == next_id)
        return jsonify({
            "question": next_q,
            "completed": False
        })
    return jsonify({"completed": True})




#-------------------------------------------------------------------------------------------

# Configuration
TOPICS_FILE_FLIP = r"D:\Downloads\Edumate\static\flip_data\game_flip.json"

def load_topics():
    try:
        with open(TOPICS_FILE_FLIP, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'Web Technology': []}  # Default empty topic

def save_topics(topics):
    with open(TOPICS_FILE_FLIP, 'w', encoding='utf-8') as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

# Game state storage
rooms = {}
player_sessions = {}

def generate_flipcard_data(topic):
    """Mock generation using existing Web Technology data"""
    topics = load_topics()
    # print(topics)
    if topic not in topics:
        data_gen=gen_flipcard(topic)
        # print(data_gen)
        # Copy Web Technology data as fallback
        # web_tech_data = topics.get('web technology',[])
        # print(web_tech_data)
        topics[topic] = data_gen[topic]
        save_topics(topics)
        return True
    return True

@app.route('/neuro_flip')
def index_flip():
    flask_session['player_id'] = str(uuid4())
    topics = load_topics()
    return render_template('index_flip.html', topics=list(topics.keys()), topics_data=topics)

@app.route('/generate-content', methods=['POST'])
@csrf.exempt
def handle_generate_content():
    # Debugging - print raw request data
    # print(f"Request Content-Type: {request.content_type}")
    # print(f"Request data: {request.data}")
    
    # Ensure request is JSON
    if not request.is_json:
        # print("Request is not JSON")
        return jsonify({
            "error": "Request must be JSON",
            "received_content_type": request.content_type,
            "received_data": str(request.data)[:200]  # First 200 chars for debugging
        }), 400
    
    try:
        data = request.get_json()
        # print(f"Parsed JSON data: {data}")
    except Exception as e:
        print(f"JSON parsing error: {str(e)}")
        return jsonify({
            "error": "Invalid JSON received",
            "exception": str(e),
            "received_data": str(request.data)[:200]
        }), 400
    
    # Validate required fields
    if not data or 'topic' not in data:
        print("Missing 'topic' field")
        return jsonify({
            "error": "Missing required 'topic' parameter",
            "received_fields": list(data.keys()) if data else None
        }), 400
    
    topic = data['topic'].strip()
    if not topic:
        print("Empty topic received")
        return jsonify({"error": "Topic cannot be empty"}), 400
    
    try:
        if generate_flipcard_data(topic):
            # print(f"Successfully generated content for topic: {topic}")
            return jsonify({
                "success": True,
                "message": f"Topic '{topic}' ready for play",
                "topic": topic
            }), 200
        else:
            print("Content generation failed")
            return jsonify({"error": "Content preparation failed"}), 500
            
    except Exception as e:
        print(f"Error during generation: {str(e)}")
        return jsonify({
            "error": "Server error during generation",
            "details": str(e)
        }), 500
    
@app.route('/game_flip/<topic>')
def game_flip(topic):
    topics = load_topics()
    if topic not in topics:
        if not generate_flipcard_data(topic):
            return render_template('404.html'), 404
    
    pairs = topics[topic]
    cards = []
    
    for pair in pairs:
        # Create properly linked pairs
        term_id = f"{pair['id']}_term"
        def_id = f"{pair['id']}_def"
        cards.extend([
            {'id': term_id, 'content': pair["term"], 'match_id': def_id},
            {'id': def_id, 'content': pair["definition"], 'match_id': term_id}
        ])
    
    random.shuffle(cards)
    return render_template('game_flip.html',
                         topic=topic,
                         cards=cards,
                         total_pairs=len(pairs),
                         is_multiplayer=False,
                         timer_enabled=True)

@app.route('/multiplayer_flip/<topic>')
def multiplayer_flip(topic):
    topics = load_topics()
    if topic not in topics:
        if not generate_flipcard_data(topic):
            return render_template('404.html'), 404
    return render_template('multiplayer_flip.html', topic=topic)

@app.route('/api/cards/<topic>')
def get_cards(topic):
    topics = load_topics()
    if topic not in topics:
        if not generate_flipcard_data(topic):
            return jsonify({"error": "Topic not found"}), 404
    
    pairs = topics[topic]
    cards = []
    
    for pair in pairs:
        cards.append({
            "id": f"{pair['id']}_term",
            "type": "term",
            "content": pair["term"],
            "match_id": f"{pair['id']}_def",
            "match_content": pair["definition"]
        })
        cards.append({
            "id": f"{pair['id']}_def",
            "type": "definition",
            "content": pair["definition"],
            "match_id": f"{pair['id']}_term",
            "match_content": pair["term"]
        })
    
    random.shuffle(cards)
    return jsonify({
        "cards": cards,
        "total_pairs": len(pairs),
        "timer_enabled": True
    })

@app.route('/create-room/<topic>')
def create_room(topic):
    topics = load_topics()
    if topic not in topics:
        if not generate_flipcard_data(topic):
            return jsonify({"error": "Topic not found"}), 404
    
    room_id = str(uuid4())[:8]
    rooms[room_id] = {
        'topic': topic,
        'players': {},
        'game_state': {
            'cards': [],
            'flipped_cards': [],
            'matched_pairs': 0,
            'total_pairs': len(topics[topic]),
            'game_started': False,
            'timer': 0,
            'current_player': None,
            'player_order': [],
            'last_flipped_by': None
        }
    }
    return jsonify({'room_id': room_id})

@socketio.on('join')
def handle_join(data):
    room_id = data['room_id']
    player_id = flask_session.get('player_id', str(uuid4()))
    player_name = data.get('player_name', 'Player')
    
    if room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    join_room(room_id)
    
    rooms[room_id]['players'][player_id] = {
        'name': player_name,
        'score': 0,
        'matched_pairs': 0,
        'socket_id': request.sid
    }
    
    player_sessions[request.sid] = {
        'player_id': player_id,
        'room_id': room_id
    }
    
    rooms[room_id]['game_state']['player_order'] = list(rooms[room_id]['players'].keys())
    if rooms[room_id]['game_state']['player_order']:
        rooms[room_id]['game_state']['current_player'] = rooms[room_id]['game_state']['player_order'][0]
    
    emit('player_update', {
        'players': rooms[room_id]['players'],
        'game_state': rooms[room_id]['game_state'],
        'current_player': rooms[room_id]['game_state']['current_player']
    }, room=room_id)

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data['room_id']
    if room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    topic = rooms[room_id]['topic']
    topics = load_topics()  # Add this line to load current topics
    pairs = topics[topic]   # Change TOPICS to topics
    cards = []
    
    # Rest of the function remains the same
    for pair in pairs:
        cards.append({
            "id": f"{pair['id']}_term",
            "type": "term",
            "content": pair["term"],
            "match_id": f"{pair['id']}_def"
        })
        cards.append({
            "id": f"{pair['id']}_def",
            "type": "definition",
            "content": pair["definition"],
            "match_id": f"{pair['id']}_term"
        })
    
    random.shuffle(cards)
    
    rooms[room_id]['game_state'] = {
        'cards': cards,
        'flipped_cards': [],
        'matched_pairs': 0,
        'total_pairs': len(pairs),
        'game_started': True,
        'timer': 0,
        'current_player': rooms[room_id]['game_state']['player_order'][0],
        'player_order': rooms[room_id]['game_state']['player_order'],
        'last_flipped_by': None
    }
    
    emit('game_started', {
        'cards': cards,
        'total_pairs': len(pairs),
        'current_player': rooms[room_id]['game_state']['current_player']
    }, room=room_id)

def get_next_player(room_id):
    game_state = rooms[room_id]['game_state']
    player_order = game_state['player_order']
    current_index = player_order.index(game_state['current_player'])
    next_index = (current_index + 1) % len(player_order)
    return player_order[next_index]

@socketio.on('flip_card')
def handle_flip_card(data):
    room_id = data['room_id']
    card_id = data['card_id']
    
    if room_id not in rooms or not rooms[room_id]['game_state']['game_started']:
        return
    
    game_state = rooms[room_id]['game_state']
    player_id = player_sessions.get(request.sid, {}).get('player_id')
    
    if player_id != game_state['current_player']:
        current_player_name = rooms[room_id]['players'].get(game_state['current_player'], {}).get('name', 'Another player')
        emit('not_your_turn', {
            'message': f"It's not your turn! {current_player_name} is playing now.",
            'current_player': game_state['current_player']
        }, room=request.sid)
        return
    
    for card in game_state['cards']:
        if card['id'] == card_id:
            if card.get('flipped') or card.get('matched'):
                return
    
    for card in game_state['cards']:
        if card['id'] == card_id:
            card['flipped'] = True
            card['flipped_by'] = player_id
            game_state['flipped_cards'].append(card)
            game_state['last_flipped_by'] = player_id
            break
    
    emit('card_flipped', {
        'card_id': card_id,
        'player_id': player_id,
        'flipped_count': len(game_state['flipped_cards']),
        'current_player': game_state['current_player']
    }, room=room_id)
    
    if len(game_state['flipped_cards']) == 2:
        card1, card2 = game_state['flipped_cards']
        
        if card1['match_id'] == card2['id']:
            for card in game_state['cards']:
                if card['id'] in [card1['id'], card2['id']]:
                    card['matched'] = True
                    card['flipped'] = False
            
            player = rooms[room_id]['players'].get(player_id)
            if player:
                player['score'] += 10
                player['matched_pairs'] += 1
            
            game_state['matched_pairs'] += 1
            game_state['flipped_cards'] = []
            game_state['current_player'] = get_next_player(room_id)
            
            emit('match_found', {
                'card1_id': card1['id'],
                'card2_id': card2['id'],
                'players': rooms[room_id]['players'],
                'matched_pairs': game_state['matched_pairs'],
                'current_player': game_state['current_player']
            }, room=room_id)
        else:
            game_state['current_player'] = get_next_player(room_id)
            
            emit('no_match', {
                'card1_id': card1['id'],
                'card2_id': card2['id'],
                'current_player': game_state['current_player']
            }, room=room_id)
            
            def reset_cards():
                for card in game_state['cards']:
                    if card['id'] in [card1['id'], card2['id']] and not card.get('matched'):
                        card['flipped'] = False
                game_state['flipped_cards'] = []
                emit('reset_cards', {
                    'card1_id': card1['id'],
                    'card2_id': card2['id'],
                    'current_player': game_state['current_player']
                }, room=room_id)
            
            socketio.sleep(1)
            reset_cards()
        
        if game_state['matched_pairs'] == game_state['total_pairs']:
            emit('game_completed', {
                'players': rooms[room_id]['players']
            }, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    session_info = player_sessions.get(request.sid)
    if not session_info:
        return
    
    room_id = session_info['room_id']
    player_id = session_info['player_id']
    
    if room_id in rooms and player_id in rooms[room_id]['players']:
        if not rooms[room_id]['game_state']['game_started'] and player_id in rooms[room_id]['game_state']['player_order']:
            rooms[room_id]['game_state']['player_order'].remove(player_id)
            
            if rooms[room_id]['game_state']['current_player'] == player_id:
                if rooms[room_id]['game_state']['player_order']:
                    rooms[room_id]['game_state']['current_player'] = rooms[room_id]['game_state']['player_order'][0]
                else:
                    rooms[room_id]['game_state']['current_player'] = None
        
        del rooms[room_id]['players'][player_id]
        emit('player_update', {
            'players': rooms[room_id]['players'],
            'game_state': rooms[room_id]['game_state'],
            'current_player': rooms[room_id]['game_state']['current_player']
        }, room=room_id)
    
    del player_sessions[request.sid]



#------------------------------------------------------------------------------

# Add this function to your app.py
def get_file_icon(file_type):
    """Maps file types to Font Awesome icons"""
    type_map = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'txt': 'fas fa-file-alt',
        'image': 'fas fa-file-image',
        'audio': 'fas fa-file-audio',
        'video': 'fas fa-file-video'
    }
    
    # Handle MIME types like 'application/pdf'
    if '/' in file_type:
        main_type, sub_type = file_type.split('/', 1)
        return type_map.get(sub_type, type_map.get(main_type, 'fas fa-file'))
    
    return type_map.get(file_type.lower(), 'fas fa-file')

# Make the function available to templates
@app.context_processor
def utility_processor():
    return dict(get_file_icon=get_file_icon)

#-----------------------------Wordscape------------------------------------------------------------

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

# Download required NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Define the base URL for the Ollama server
OLLAMA_BASE_URL = 'http://localhost:11434'
OLLAMA_GENERATE_ENDPOINT = f'{OLLAMA_BASE_URL}/api/generate'

# Form class for topic input
class TopicForm(FlaskForm):
    topic = StringField('Enter a Topic:', validators=[DataRequired()])
    submit = SubmitField('Generate Puzzle')

# Function to generate a story for the topic using Ollama
def generate_story_ws(topic):
    prompt = f'''Please create a brief educational story that explains "{topic}" in a clear and technical way.
    The story should be 2-6 paragraphs long and suitable for someone solving a word search puzzle about {topic}.
    Make it engaging and informative.'''
    
    payload = {
        'model': 'qwen2.5:latest',
        'prompt': prompt,
        'stream': False
    }
    
    try:
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json().get('response', '')
        return result
    except Exception as e:
        print(f"Error generating story: {e}")
        return f"A fun word search puzzle about {topic}! Find all the words to complete the challenge."

# Function to get related words for a given topic using Ollama API
def get_related_words_ollama_ws(topic, num_words=10):
    prompt = f"""Generate {num_words} single words that are related to the topic: "{topic}".

Each word should:
- Be 4–10 letters long
- Be a simple noun, verb, or adjective
- Not be a proper noun
- Be suitable for a word search puzzle

Return ONLY a JSON array like the examples below, and nothing else:

Example 1 (Topic: "ocean"):
["wave", "fish", "coral", "splash", "tide", "beach", "shell", "shark", "whale", "anchor"]

Example 2 (Topic: "school"):
["teacher", "student", "classroom", "pencil", "book", "homework", "lesson", "chalk", "exam", "subject"]

Now return for topic "{topic}":
"""

    
    payload = {
        'model': 'qwen2.5:latest',
        'prompt': prompt,
        'stream': False
    }
    
    try:
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json().get('response', '')
        
        # Extract the JSON array from the response
        json_match = re.search(r'\[.+\]', result.replace('\n', ' '))
        if json_match:
            try:
                words_list = json.loads(json_match.group(0))
                # Filter and clean the words
                filtered_words = []
                for word in words_list:
                    # Clean up the word
                    clean_word = word.strip().lower()
                    if '_' in clean_word:
                        clean_word = clean_word.replace('_', '')
                    if len(clean_word) >= 4 and clean_word.isalpha() and clean_word not in filtered_words:
                        filtered_words.append(clean_word)
                
                return filtered_words[:num_words]
            except json.JSONDecodeError:
                print("Failed to parse JSON from Ollama response")
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
    
    # Fallback to WordNet if Ollama fails
    return get_related_words_wordnet_ws(topic, num_words)

# Function to get related words for a given topic using WordNet
def get_related_words_wordnet_ws(topic, num_words=10):
    related_words = []
    
    # Try to get words directly from WordNet
    synsets = wordnet.synsets(topic)
    
    # Get hyponyms (more specific terms)
    for synset in synsets:
        for hyponym in synset.hyponyms():
            word = hyponym.lemmas()[0].name()
            if '_' in word:  # Replace underscores with spaces
                word = word.replace('_', ' ')
            if len(word) >= 4 and word not in related_words:  # Only include words of decent length
                related_words.append(word)
    
    # Get hypernyms (more general terms)
    for synset in synsets:
        for hypernym in synset.hypernyms():
            word = hypernym.lemmas()[0].name()
            if '_' in word:
                word = word.replace('_', ' ')
            if len(word) >= 4 and word not in related_words:
                related_words.append(word)
    
    # Add synonyms
    for synset in synsets:
        for lemma in synset.lemmas():
            word = lemma.name()
            if '_' in word:
                word = word.replace('_', ' ')
            if len(word) >= 4 and word not in related_words:
                related_words.append(word)
    
    # If we don't have enough words from WordNet, add some default activity words
    if len(related_words) < num_words:
        default_activities = {
            "summer": ["swimming", "camping", "hiking", "picnic", "beach", "biking", "fishing", 
                      "travel", "barbecue", "gardening", "carnival", "baseball"],
            "winter": ["skiing", "sledding", "skating", "snowman", "hockey", "fireplace", 
                      "snowball", "holidays", "cocoa", "mittens"],
            "school": ["reading", "writing", "homework", "science", "history", "mathematics", 
                      "recess", "learning", "teacher", "student"],
            "food": ["baking", "cooking", "grilling", "recipe", "dinner", "breakfast",
                    "dessert", "snacks", "fruits", "vegetables"],
            "sports": ["baseball", "football", "soccer", "tennis", "swimming", "running",
                      "jumping", "cycling", "volleyball", "basketball"]
        }
        
        # Try to find the closest category
        for category, words in default_activities.items():
            if category in topic.lower() or topic.lower() in category:
                for word in words:
                    if word not in related_words:
                        related_words.append(word)
        
        # If still not enough, add some general activities
        if len(related_words) < num_words:
            general_activities = ["reading", "writing", "walking", "talking", "playing", 
                                "making", "watching", "learning", "creating", "building"]
            for word in general_activities:
                if word not in related_words:
                    related_words.append(word)
    
    # Ensure the original topic is included
    if topic not in related_words and len(topic) >= 3:
        related_words.insert(0, topic)
    
    # Limit to requested number and filter out any non-alphabetic words
    filtered_words = [word for word in related_words if word.isalpha()]
    return filtered_words[:num_words]

# Main function to get related words, tries Ollama first, then falls back to WordNet
def get_related_words_ws(topic, num_words=10):
    words = get_related_words_ollama_ws(topic, num_words)
    if not words or len(words) < 5:  # If Ollama fails or returns too few words
        words = get_related_words_wordnet_ws(topic, num_words)
    return words

# Function to create clues for words using Ollama
def create_clues_ollama_ws(topic, words):
    # Create a prompt for Ollama to generate clues
    word_list = ', '.join(words)
    prompt = f"""Create short, fun clues for a word search puzzle about "{topic}".

Words: {word_list}

Each clue should:
- Be a short hint (less than 15 words)
- Not directly mention the word
- Help someone guess the word in a puzzle

Return ONLY a JSON object like the examples below, and nothing else:

Example:
Words: ["pencil", "chalk", "book"]
Output:
{{
  "pencil": "Used for writing or drawing in school.",
  "chalk": "White stick for writing on blackboards.",
  "book": "You read this to learn or enjoy stories."
}}

Now generate clues for: {words}
"""

    
    payload = {
        'model': 'qwen2.5:latest',
        'prompt': prompt,
        'stream': False
    }
    
    try:
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json().get('response', '')
        
        # Extract the JSON object from the response
        json_match = re.search(r'\{.+\}', result.replace('\n', ' '))
        if json_match:
            try:
                clues_dict = json.loads(json_match.group(0))
                # Ensure all words have clues
                for word in words:
                    if word not in clues_dict or not clues_dict[word].strip():
                        clues_dict[word] = create_default_clue_ws(topic, word)
                return clues_dict
            except json.JSONDecodeError:
                print("Failed to parse JSON clues from Ollama response")
    except Exception as e:
        print(f"Error calling Ollama API for clues: {e}")
    
    # Fall back to default clue creation
    return create_default_clues_ws(topic, words)

# Function to create a default clue for a word
def create_default_clue_ws(topic, word):
    clue_templates = [
        f"Related to {topic}: {word}",
        f"Something about {topic}",
        f"Connected with {topic}",
        f"A {topic} concept",
        f"Part of {topic} activities"
    ]
    return random.choice(clue_templates)

# Function to create default clues for words
def create_default_clues_ws(topic, words):
    clues = {}
    
    for word in words:
        # Different types of clues
        clue_types = [
            f"Activity related to {topic}: {word}",
            f"You might {word} during {topic}",
            f"People enjoy this {topic} activity",
            f"{word.capitalize()} is associated with {topic}",
            f"A {topic} favorite: {word}",
            f"This {topic} term starts with {word[0].upper()}",
            f"Popular {topic} concept: {word}",
            f"Look for this {topic} word",
            f"Important in {topic}",
            f"Common {topic} term"
        ]
        clues[word] = random.choice(clue_types)
    
    return clues

# Main function to create clues, tries Ollama first, then falls back to default method
def create_clues_ws(topic, words):
    clues = create_clues_ollama_ws(topic, words)
    # No need for explicit fallback as create_clues_ollama already handles it
    return clues

# Function to create a word search grid
def create_grid_ws(words, size=15):
    # Convert all words to lowercase
    words = [word.lower() for word in words]
    
    # Initialize grid with empty spaces
    grid = [[' ' for _ in range(size)] for _ in range(size)]
    
    # Track placed words
    placed_words = []
    
    # Try to place each word
    for word in words:
        # Remove spaces if any
        word = word.replace(' ', '')
        
        # Skip if word is too long for the grid
        if len(word) > size:
            continue
        
        # Try multiple times to place the word
        for _ in range(50):
            # Choose a random direction (0=horizontal, 1=vertical, 2=diagonal down, 3=diagonal up)
            direction = random.randint(0, 3)
            
            # Choose a random starting position
            if direction == 0:  # horizontal
                row = random.randint(0, size - 1)
                col = random.randint(0, size - len(word))
            elif direction == 1:  # vertical
                row = random.randint(0, size - len(word))
                col = random.randint(0, size - 1)
            elif direction == 2:  # diagonal down
                row = random.randint(0, size - len(word))
                col = random.randint(0, size - len(word))
            else:  # diagonal up
                row = random.randint(len(word) - 1, size - 1)
                col = random.randint(0, size - len(word))
            
            # Check if word can be placed
            can_place = True
            positions = []
            
            for i in range(len(word)):
                if direction == 0:  # horizontal
                    r, c = row, col + i
                elif direction == 1:  # vertical
                    r, c = row + i, col
                elif direction == 2:  # diagonal down
                    r, c = row + i, col + i
                else:  # diagonal up
                    r, c = row - i, col + i
                
                # Check if position is empty or has the same letter
                if grid[r][c] != ' ' and grid[r][c] != word[i]:
                    can_place = False
                    break
                positions.append((r, c))
            
            if can_place:
                # Place the word
                for i, (r, c) in enumerate(positions):
                    grid[r][c] = word[i]
                placed_words.append(word)
                break
    
    # Fill remaining empty spaces with random letters
    for i in range(size):
        for j in range(size):
            if grid[i][j] == ' ':
                grid[i][j] = random.choice(string.ascii_lowercase)
    
    return grid, placed_words
@csrf.exempt
@app.route('/wordscape', methods=['GET', 'POST'])
def index_ws():
    form = TopicForm()
    # print("It came heree atleast...............")
    # print(request.form)
    if form.validate_on_submit():
        topic = form.topic.data
        # Generate a brief story about the topic
        # print("It arrived here................")
        story = generate_story_ws(topic)
        # print(story)
        return render_template('game_ws.html', topic=topic, story=story)
    
    return render_template('index_ws.html', form=form)
@csrf.exempt
@app.route('/generate_ws', methods=['POST'])

def generate_puzzle_ws():
    # data = request.get_json()
    topic = request.form.get('topic')
    print(topic)
    # Get words related to the topic
    words = get_related_words_ws(topic, 10)
    print(words)
    
    # Create a word search grid
    grid, placed_words = create_grid_ws(words)
    
    # Create clues for the placed words using Ollama
    clues_dict = create_clues_ws(topic, placed_words)
    # print(clues_dict)
    
    # Format clues for the frontend
    clues = {}
    for i, word in enumerate(placed_words):
        clues[i+1] = {"word": word, "clue": clues_dict.get(word, f"Activity related to {topic}: {word}")}
    
    return jsonify({
        'grid': grid,
        'words': placed_words,
        'clues': clues
    })
@csrf.exempt
@app.route('/submit_score_ws', methods=['POST'])
def submit_score_ws():
    data = request.get_json()
    score = data.get('score', 0)
    time_taken = data.get('time', 0)
    found_words = data.get('found_words', [])
    total_words = data.get('total_words', 0)
    
    # Here you could save scores to a database if desired
    
    return jsonify({
        'success': True,
        'message': f'Great job! You found {len(found_words)} out of {total_words} words in {time_taken} seconds.'
    })

#--------------------------------Crossword-----------------------------------------


# Download required NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Define the base URL for the Ollama server
OLLAMA_BASE_URL = 'http://localhost:11434'
OLLAMA_GENERATE_ENDPOINT = f'{OLLAMA_BASE_URL}/api/generate'

class PuzzleForm(FlaskForm):
    topic = StringField('Topic', validators=[DataRequired()])
    submit = SubmitField('Generate Puzzle')

# Function to generate a thematic story for the puzzle using Ollama
def generate_story_cw(topic):
    prompt = f'''Please create a brief engaging story that introduces a crossword puzzle about "{topic}".
    The story should be 1-3 paragraphs long and set up a fun scenario for why the player needs to solve
    a crossword puzzle related to {topic}. Make it creative and immersive.'''
    
    payload = {
        'model': 'qwen2.5:latest',
        'prompt': prompt,
        'stream': False
    }
    
    try:
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json().get('response', '')
        return result
    except Exception as e:
        print(f"Error generating story: {e}")
        return f"""Embark on an exciting journey through the realm of {topic}! This cosmic crossword contains 
        hidden knowledge that will expand your understanding of this fascinating subject. Can you solve all 
        the clues and complete the puzzle?"""

# Function to get related words and clues for a given topic using Ollama API
def get_words_and_clues_ollama_cw(topic, num_words=8):
    prompt = f"""Generate {num_words} words and their clues related to the topic "{topic}" for a crossword puzzle.

Each word should:
- Be 4-10 letters long
- Be a common noun, verb, or adjective related to {topic}
- Be suitable for a crossword puzzle

For each word, create a clue that:
- Hints at the word without directly stating it
- Is concise (under 10 words)
- Is appropriate for a crossword puzzle

Return ONLY a JSON object like the example below, with each word as a key and its clue as the value:

Example (Topic: "ocean"):
{{
  "WAVE": "Movement of water on the surface",
  "CORAL": "Colorful marine invertebrate structure",
  "SHARK": "Predatory fish with multiple rows of teeth",
  "TIDE": "Regular rise and fall of sea levels",
  "REEF": "Underwater ridge of rock or coral",
  "OCEAN": "Vast body of saltwater covering most of Earth",
  "BEACH": "Sandy or pebbly shore by the water",
  "SHELL": "Hard protective covering of marine animals"
}}

Now generate for topic "{topic}":
"""
    
    payload = {
        'model': 'qwen2.5:latest',
        'prompt': prompt,
        'stream': False
    }
    
    try:
        response = requests.post(OLLAMA_GENERATE_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json().get('response', '')
        
        # Extract the JSON object from the response
        json_match = re.search(r'\{.+\}', result.replace('\n', ' '))
        if json_match:
            try:
                words_clues = json.loads(json_match.group(0))
                return words_clues
            except json.JSONDecodeError:
                print("Failed to parse JSON from Ollama response")
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
    
    # Fallback to WordNet if Ollama fails
    return get_words_and_clues_wordnet_cw(topic, num_words)

# Function to get related words for a given topic using WordNet
def get_words_and_clues_wordnet_cw(topic, num_words=8):
    words_clues = {}
    
    # Try to get words directly from WordNet
    synsets = wordnet.synsets(topic)
    
    related_words = []
    
    # Get hyponyms (more specific terms)
    for synset in synsets:
        for hyponym in synset.hyponyms():
            word = hyponym.lemmas()[0].name().upper()
            if '_' in word:  # Replace underscores with spaces
                word = word.replace('_', '')
            if len(word) >= 4 and word not in related_words and len(word) <= 10:
                related_words.append(word)
    
    # Get hypernyms (more general terms)
    for synset in synsets:
        for hypernym in synset.hypernyms():
            word = hypernym.lemmas()[0].name().upper()
            if '_' in word:
                word = word.replace('_', '')
            if len(word) >= 4 and word not in related_words and len(word) <= 10:
                related_words.append(word)
    
    # Add synonyms
    for synset in synsets:
        for lemma in synset.lemmas():
            word = lemma.name().upper()
            if '_' in word:
                word = word.replace('_', '')
            if len(word) >= 4 and word not in related_words and len(word) <= 10:
                related_words.append(word)
    
    # Add the topic itself if it's not already in the list
    if topic.upper() not in related_words and len(topic) >= 4 and len(topic) <= 10:
        related_words.append(topic.upper())
    
    # Ensure we have unique words
    related_words = list(set(related_words))
    
    # If we don't have enough words from WordNet, add some default words
    if len(related_words) < num_words:
        default_words = {
            "astronomy": ["STARS", "MOON", "COMET", "GALAXY", "PLANET", "ORBIT", "NEBULA", "MARS"],
            "animals": ["TIGER", "PANDA", "GIRAFFE", "RHINO", "LION", "ELEPHANT", "ZEBRA", "MONKEY"],
            "movies": ["ACTOR", "SCENE", "SCRIPT", "CAMERA", "DRAMA", "COMEDY", "CINEMA", "FILM"],
            "sports": ["FIELD", "SCORE", "COACH", "TEAM", "PLAYER", "MATCH", "MEDAL", "GAME"],
            "food": ["BREAD", "PASTA", "SUGAR", "SPICE", "FRUIT", "SALAD", "ONION", "COOK"]
        }
        
        # Try to find the closest category
        for category, words in default_words.items():
            if category in topic.lower() or topic.lower() in category:
                for word in words:
                    if word not in related_words:
                        related_words.append(word)
    
    # Limit to requested number
    related_words = related_words[:num_words]
    
    # Create default clues for each word
    for word in related_words:
        clue_templates = [
            f"Related to {topic}",
            f"Type of {topic}",
            f"Found in {topic} context",
            f"Important {topic} concept",
            f"{topic} terminology"
        ]
        words_clues[word] = f"{random.choice(clue_templates)}"
    
    return words_clues

# Function to generate a crossword grid
def generate_crossword_grid_cw(words_clues, grid_size=10):
    words = list(words_clues.keys())
    random.shuffle(words)  # Randomize word order to try different placements
    
    # Initialize an empty grid
    grid = [['' for _ in range(grid_size)] for _ in range(grid_size)]
    
    # Track words successfully placed in the grid
    placed_words = []
    word_positions = {}  # To store position and direction of each word
    
    # Attempt to place the first word horizontally in middle row
    if words:
        word = words[0]
        middle_row = grid_size // 2
        start_col = max(0, (grid_size - len(word)) // 2)
        
        # Place the first word
        for i, letter in enumerate(word):
            grid[middle_row][start_col + i] = letter
        
        placed_words.append(word)
        word_positions[word] = {
            "direction": "across",
            "position": [middle_row, start_col],
            "answer": word
        }
    
    # Try to place remaining words
    for word in words[1:]:
        best_score = -1
        best_placement = None
        
        # Try each letter of the word
        for i, letter in enumerate(word):
            # Look for this letter in the existing grid
            for row in range(grid_size):
                for col in range(grid_size):
                    if grid[row][col] == letter:
                        # Try placing horizontally
                        if i > 0 and col >= i:  # Check if we can fit the word
                            can_place = True
                            for j in range(len(word)):
                                if j != i and (col - i + j < 0 or col - i + j >= grid_size):
                                    can_place = False
                                    break
                                if j != i and grid[row][col - i + j] != '' and grid[row][col - i + j] != word[j]:
                                    can_place = False
                                    break
                                
                                # Check for adjacent words (to avoid unwanted small words)
                                if j != i:
                                    # Check above and below
                                    if (row > 0 and grid[row-1][col-i+j] != '') or \
                                       (row < grid_size-1 and grid[row+1][col-i+j] != ''):
                                        can_place = False
                                        break
                            
                            if can_place:
                                # Calculate intersection score (more intersections is better)
                                score = 1  # Base score for a valid placement
                                for j in range(len(word)):
                                    if j != i and grid[row][col - i + j] == word[j]:
                                        score += 1
                                
                                if score > best_score:
                                    best_score = score
                                    best_placement = {
                                        "word": word,
                                        "direction": "across",
                                        "row": row,
                                        "col": col - i,
                                        "intersect": True
                                    }
                        
                        # Try placing vertically
                        if i > 0 and row >= i:  # Check if we can fit the word
                            can_place = True
                            for j in range(len(word)):
                                if j != i and (row - i + j < 0 or row - i + j >= grid_size):
                                    can_place = False
                                    break
                                if j != i and grid[row - i + j][col] != '' and grid[row - i + j][col] != word[j]:
                                    can_place = False
                                    break
                                
                                # Check for adjacent words
                                if j != i:
                                    # Check left and right
                                    if (col > 0 and grid[row-i+j][col-1] != '') or \
                                       (col < grid_size-1 and grid[row-i+j][col+1] != ''):
                                        can_place = False
                                        break
                            
                            if can_place:
                                # Calculate intersection score
                                score = 1  # Base score for a valid placement
                                for j in range(len(word)):
                                    if j != i and grid[row - i + j][col] == word[j]:
                                        score += 1
                                
                                if score > best_score:
                                    best_score = score
                                    best_placement = {
                                        "word": word,
                                        "direction": "down",
                                        "row": row - i,
                                        "col": col,
                                        "intersect": True
                                    }
        
        # If no intersection is found, try placing without intersection
        if best_placement is None:
            # Try to place horizontally in empty rows
            for row in range(grid_size):
                for col in range(grid_size - len(word) + 1):
                    can_place = True
                    for j in range(len(word)):
                        if grid[row][col + j] != '':
                            can_place = False
                            break
                    
                    if can_place:
                        best_placement = {
                            "word": word,
                            "direction": "across",
                            "row": row,
                            "col": col,
                            "intersect": False
                        }
                        break
                if best_placement is not None:
                    break
            
            # Try to place vertically in empty columns
            if best_placement is None:
                for col in range(grid_size):
                    for row in range(grid_size - len(word) + 1):
                        can_place = True
                        for j in range(len(word)):
                            if grid[row + j][col] != '':
                                can_place = False
                                break
                        
                        if can_place:
                            best_placement = {
                                "word": word,
                                "direction": "down",
                                "row": row,
                                "col": col,
                                "intersect": False
                            }
                            break
                    if best_placement is not None:
                        break
        
        # Place the word if a valid placement was found
        if best_placement:
            word = best_placement["word"]
            row = best_placement["row"]
            col = best_placement["col"]
            direction = best_placement["direction"]
            
            # Place the word in the grid
            if direction == "across":
                for j in range(len(word)):
                    grid[row][col + j] = word[j]
            else:  # direction == "down"
                for j in range(len(word)):
                    grid[row + j][col] = word[j]
            
            placed_words.append(word)
            word_positions[word] = {
                "direction": direction,
                "position": [row, col],
                "answer": word
            }
    
    # Format the output to match the expected structure
    clues = {}
    for i, word in enumerate(placed_words):
        clues[str(i+1)] = {
            "direction": word_positions[word]["direction"],
            "position": word_positions[word]["position"],
            "clue": words_clues[word],
            "answer": word
        }
    
    return {
        "grid": grid,
        "words": placed_words,
        "clues": clues,
        "dimensions": {"width": grid_size, "height": grid_size}
    }

# Main function to generate crossword puzzle
def generate_crossword_cw(topic):
    # Get words and clues using Ollama
    words_clues = get_words_and_clues_ollama_cw(topic)
    # print(words_clues)
    # Generate crossword grid
    puzzle_data = generate_crossword_grid_cw(words_clues)
    # print(puzzle_data)
    
    return puzzle_data

@app.route('/wordmaze')
def index_cw():
    form = PuzzleForm()
    return render_template('index_cw.html', form=form)

@csrf.exempt
@app.route('/puzzle_cw', methods=['POST'])
def create_puzzle_cw():
    form = PuzzleForm()
    if form.validate_on_submit():
        topic = form.topic.data
        # print(topic)
        return redirect(url_for('display_puzzle_cw', topic=topic))
    return redirect(url_for('index_cw'))

@app.route('/puzzle_cw/<topic>')
def display_puzzle_cw(topic):
    # print("disp_puzzle: ",topic)
    story = generate_story_cw(topic)
    # print(story)
    return render_template('puzzle_cw.html', topic=topic, story=story)

@csrf.exempt
@app.route('/generate_cw', methods=['POST'])
def generate_cw():
    topic = request.json.get('topic', 'general')
    # print("topic: ",topic)
    puzzle_data = generate_crossword_cw(topic)
    # print(puzzle_data)
    return jsonify(puzzle_data)

@csrf.exempt
@app.route('/submit_score_cw', methods=['POST'])
def submit_score_cw():
    # In a real app, this would save to a database
    score_data = request.json
    # Just acknowledge receipt for now
    return jsonify({"success": True, "message": "Score recorded"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, 
                host='0.0.0.0',
                port=80,  # Use port 80 for standard HTTP
                debug=True, 
                use_reloader=False, 
                allow_unsafe_werkzeug=True)