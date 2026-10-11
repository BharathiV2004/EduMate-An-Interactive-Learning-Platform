from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import uuid
import time

app = Flask(__name__)
socketio = SocketIO(app)

# Game rooms storage
game_rooms = {}  # room_id -> {players, flashcards, state, etc}
leaderboard = {}  # username -> {total_wins, total_games}

# Sample flashcards - can be expanded
flashcards = [
    {"question": "What is the capital of France?", "answer": "Paris"},
    {"question": "What is 2 + 2?", "answer": "4"},
    {"question": "Python keyword for function?", "answer": "def"},
    {"question": "H2O is known as?", "answer": "water"},
    {"question": "Who painted Mona Lisa?", "answer": "Leonardo da Vinci"},
    {"question": "Which planet is known as the Red Planet?", "answer": "Mars"},
    {"question": "What is the largest ocean on Earth?", "answer": "Pacific"},
    {"question": "What language is React built with?", "answer": "JavaScript"},
    {"question": "What does CPU stand for?", "answer": "Central Processing Unit"},
    {"question": "What is the chemical symbol for gold?", "answer": "Au"}
]

@app.route('/')
def index():
    """Main page with options to create or join a room"""
    return render_template('index.html')

@app.route('/battle/<room_id>')
def battle(room_id):
    """Game room page"""
    if room_id not in game_rooms:
        return redirect(url_for('index'))
    return render_template('battle.html', room_id=room_id)

@app.route('/leaderboard')
def show_leaderboard():
    """Display the global leaderboard"""
    sorted_leaders = sorted(leaderboard.items(), 
                          key=lambda x: (x[1]['total_wins'], x[1]['total_wins']/max(x[1]['total_games'], 1)), 
                          reverse=True)
    return render_template('leaderboard.html', leaderboard=sorted_leaders)

@socketio.on('create_room')
def handle_create_room(data):
    """Create a new game room"""
    username = data.get('username', 'Host')
    room_id = str(uuid.uuid4())[:8]  # Generate a unique room ID
    
    # Initialize the room
    game_rooms[room_id] = {
        'players': {},
        'flashcards': random.sample(flashcards, len(flashcards)),  # Shuffle cards
        'current_index': 0,
        'game_started': False,
        'question_timer': 15,
        'players_submitted': {},
        'room_size': min(4, max(2, int(data.get('room_size', 2))))  # Between 2-4 players
    }
    
    # Add player to room
    sid = request.sid
    join_room(room_id)
    game_rooms[room_id]['players'][sid] = {
        'username': username,
        'score': 0,
        'is_host': True  # First player is the host
    }
    game_rooms[room_id]['players_submitted'][sid] = False
    
    # Initialize leaderboard entry if new player
    if username not in leaderboard:
        leaderboard[username] = {'total_wins': 0, 'total_games': 0}
    
    emit('room_created', {
        'room_id': room_id,
        'username': username,
        'room_size': game_rooms[room_id]['room_size']
    })
    
    # Also join the room from socket perspective
    emit('room_status', {
        'players': [{'username': player_data['username'], 'score': player_data['score'], 'is_host': player_data.get('is_host', False)} 
                   for player_data in game_rooms[room_id]['players'].values()],
        'room_size': game_rooms[room_id]['room_size'],
        'host': username
    }, room=room_id)

@socketio.on('join_room')
def handle_join_room(data):
    """Join an existing game room"""
    username = data.get('username', 'Player')
    room_id = data.get('room_id')
    
    # Validate room exists and is not full
    if room_id not in game_rooms:
        emit('error', {'message': 'Room does not exist'})
        return
    
    if len(game_rooms[room_id]['players']) >= game_rooms[room_id]['room_size']:
        emit('error', {'message': 'Room is full'})
        return
    
    if game_rooms[room_id]['game_started']:
        emit('error', {'message': 'Game already in progress'})
        return
    
    # Add player to room
    sid = request.sid
    join_room(room_id)
    game_rooms[room_id]['players'][sid] = {
        'username': username,
        'score': 0,
        'is_host': False
    }
    game_rooms[room_id]['players_submitted'][sid] = False
    
    # Initialize leaderboard entry if new player
    if username not in leaderboard:
        leaderboard[username] = {'total_wins': 0, 'total_games': 0}
    
    # Notify all players in room
    emit('player_joined', {
        'username': username,
        'room_id': room_id
    }, room=room_id)
    
    emit('room_status', {
        'players': [{'username': player_data['username'], 'score': player_data['score'], 'is_host': player_data.get('is_host', False)} 
                   for player_data in game_rooms[room_id]['players'].values()],
        'room_size': game_rooms[room_id]['room_size'],
        'host': next((player_data['username'] for sid, player_data in game_rooms[room_id]['players'].items() 
                     if player_data.get('is_host', False)), None)
    }, room=room_id)

@socketio.on('start_game')
def handle_start_game(data):
    """Start the game (host only)"""
    room_id = data.get('room_id')
    
    if room_id not in game_rooms:
        emit('error', {'message': 'Room does not exist'})
        return
    
    # Check if sender is host
    sid = request.sid
    room = game_rooms[room_id]
    if sid not in room['players'] or not room['players'][sid].get('is_host', False):
        emit('error', {'message': 'Only the host can start the game'})
        return
    
    # Check minimum players (at least 2)
    if len(room['players']) < 2:
        emit('error', {'message': 'Need at least 2 players to start'})
        return
    
    # Start the game
    room['game_started'] = True
    
    # Update games played count for each player
    for player_sid, player_data in room['players'].items():
        leaderboard[player_data['username']]['total_games'] += 1
    
    # Notify all players
    emit('game_started', {
        'message': 'Game has started!',
        'players': [player_data['username'] for player_data in room['players'].values()]
    }, room=room_id)
    
    # Send first flashcard
    send_current_flashcard(room_id)

def send_current_flashcard(room_id):
    """Send the current flashcard to all players in the room"""
    room = game_rooms[room_id]
    current_index = room['current_index']
    
    if current_index < len(room['flashcards']):
        card = room['flashcards'][current_index]
        socketio.emit('new_flashcard', {
            'flashcard': card,
            'index': current_index,
            'total': len(room['flashcards'])
        }, room=room_id)
        
        socketio.emit('start_timer', {'time': room['question_timer']}, room=room_id)
    else:
        end_game(room_id)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    """Process a player's answer submission"""
    room_id = data.get('room_id')
    answer = data.get('answer', '').strip().lower()
    
    if room_id not in game_rooms:
        return
    
    room = game_rooms[room_id]
    sid = request.sid
    
    if sid not in room['players'] or room['current_index'] >= len(room['flashcards']):
        return
    
    # Check if answer is correct
    correct_answer = room['flashcards'][room['current_index']]['answer'].strip().lower()
    is_correct = answer == correct_answer
    
    if is_correct:
        room['players'][sid]['score'] += 1
    
    # Mark player as submitted
    room['players_submitted'][sid] = True
    
    # Send feedback to this player only
    emit('answer_result', {
        'result': 'correct' if is_correct else 'incorrect',
        'correct_answer': correct_answer
    })
    
    # Update scores for all players
    socketio.emit('score_update', {
        'players': [{'username': player_data['username'], 'score': player_data['score']} 
                  for sid, player_data in room['players'].items()]
    }, room=room_id)
    
    # Check if all players have submitted
    if all(room['players_submitted'].values()):
        # Move to next question
        room['current_index'] += 1
        # Reset submission status
        for player_sid in room['players']:
            room['players_submitted'][player_sid] = False
        
        # Small delay before next question
        socketio.sleep(1)
        send_current_flashcard(room_id)

@socketio.on('time_up')
def handle_time_up(data):
    """Handle when time runs out for a question"""
    room_id = data.get('room_id')
    
    if room_id not in game_rooms:
        return
    
    room = game_rooms[room_id]
    room['current_index'] += 1
    
    # Reset submission status
    for sid in room['players']:
        room['players_submitted'][sid] = False
    
    send_current_flashcard(room_id)

def end_game(room_id):
    """End the game and announce results"""
    room = game_rooms[room_id]
    
    # Calculate results
    results = [{
        'username': player_data['username'],
        'score': player_data['score']
    } for sid, player_data in room['players'].items()]
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Find winners (could be tie)
    max_score = results[0]['score'] if results else 0
    winners = [r['username'] for r in results if r['score'] == max_score]
    
    # Update leaderboard
    for winner in winners:
        leaderboard[winner]['total_wins'] += 1/len(winners)  # Split win if tie
    
    # Format results message
    message = "<h3>🏆 Game Results</h3>"
    for i, result in enumerate(results):
        is_winner = result['username'] in winners
        message += f"<p>{i+1}. {result['username']}: {result['score']} {'🏆' if is_winner else ''}</p>"
    
    socketio.emit('game_ended', {
        'message': message,
        'results': results,
        'winners': winners
    }, room=room_id)
    
    # Game is over but room stays active for rematch
    room['game_started'] = False

@socketio.on('rematch')
def handle_rematch(data):
    """Start a rematch in the same room"""
    room_id = data.get('room_id')
    
    if room_id not in game_rooms:
        return
    
    # Check if sender is host
    sid = request.sid
    room = game_rooms[room_id]
    if sid not in room['players'] or not room['players'][sid].get('is_host', False):
        emit('error', {'message': 'Only the host can start a rematch'})
        return
    
    # Reset room for new game
    room['current_index'] = 0
    room['game_started'] = True
    
    # Reset scores but keep players
    for sid in room['players']:
        room['players'][sid]['score'] = 0
        room['players_submitted'][sid] = False
        # Update games played count
        leaderboard[room['players'][sid]['username']]['total_games'] += 1
    
    # Shuffle flashcards
    random.shuffle(room['flashcards'])
    
    # Notify all players
    socketio.emit('rematch_started', {
        'message': 'Rematch started!'
    }, room=room_id)
    
    # Reset and show score board
    socketio.emit('score_update', {
        'players': [{'username': player_data['username'], 'score': player_data['score']} 
                  for sid, player_data in room['players'].items()]
    }, room=room_id)
    
    # Send first flashcard after a short delay
    socketio.sleep(1)
    send_current_flashcard(room_id)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle player disconnection"""
    sid = request.sid
    
    # Find which room this player was in
    for room_id, room in list(game_rooms.items()):
        if sid in room['players']:
            username = room['players'][sid]['username']
            
            # Remove player from room
            leave_room(room_id)
            was_host = room['players'][sid].get('is_host', False)
            del room['players'][sid]
            if sid in room['players_submitted']:
                del room['players_submitted'][sid]
            
            # If room is empty, remove it
            if not room['players']:
                del game_rooms[room_id]
                continue
            
            # If host left, assign a new host
            if was_host and room['players']:
                new_host_sid = next(iter(room['players']))
                room['players'][new_host_sid]['is_host'] = True
                new_host = room['players'][new_host_sid]['username']
            else:
                new_host = None
            
            # Notify remaining players
            socketio.emit('player_left', {
                'username': username,
                'new_host': new_host
            }, room=room_id)
            
            # Update room status
            socketio.emit('room_status', {
                'players': [{'username': player_data['username'], 'score': player_data['score'], 'is_host': player_data.get('is_host', False)} 
                           for player_data in room['players'].values()],
                'room_size': room['room_size'],
                'host': next((player_data['username'] for sid, player_data in room['players'].items() 
                             if player_data.get('is_host', False)), None)
            }, room=room_id)
            
            # End game if not enough players
            if room['game_started'] and len(room['players']) < 2:
                socketio.emit('game_paused', {
                    'message': f"{username} disconnected. Waiting for more players to join."
                }, room=room_id)
                room['game_started'] = False
            
            break

if __name__ == '__main__':
    socketio.run(app, debug=True)