document.addEventListener('DOMContentLoaded', () => {
    const socket = io('http://localhost:5000');
    
    // DOM elements
    const elements = {
        lobby: document.getElementById('lobby'),
        game: document.getElementById('game'),
        username: document.getElementById('username'),
        createGame: document.getElementById('create-game'),
        joinGame: document.getElementById('join-game'),
        joinForm: document.getElementById('join-form'),
        roomId: document.getElementById('room-id'),
        confirmJoin: document.getElementById('confirm-join'),
        roomDisplay: document.getElementById('room-display'),
        crosswordGrid: document.getElementById('crossword-grid'),
        acrossClues: document.getElementById('across-clues'),
        downClues: document.getElementById('down-clues'),
        submitAnswers: document.getElementById('submit-answers'),
        resultMessage: document.getElementById('result-message'),
        playerScores: document.getElementById('player-scores')
    };

    let currentRoom = null;
    let currentUsername = null;
    let currentCrossword = null;
    let clueInputs = {}; // Stores references to clue input elements
    let cellElements = {}; // Stores references to cell elements in grid
    let wordMap = {}; // Maps words to their positions

    // Event listeners
    elements.createGame.addEventListener('click', createGame);
    elements.joinGame.addEventListener('click', showJoinForm);
    elements.confirmJoin.addEventListener('click', joinGame);
    elements.submitAnswers.addEventListener('click', submitAnswers);

    // Socket.IO event handlers
    socket.on('connection_ack', (data) => {
        console.log(data.status);
    });

    socket.on('game_created', (data) => {
        currentRoom = data.room_id;
        currentUsername = elements.username.value.trim();
        elements.roomDisplay.textContent = currentRoom;
        elements.lobby.classList.add('hidden');
        elements.game.classList.remove('hidden');
        initializeGame(data);
    });

    socket.on('player_joined', (data) => {
        updatePlayerScores(data.players);
        addGameMessage(`${data.username} joined the game`, 'info');
    });

    socket.on('player_left', (data) => {
        updatePlayerScores(data.players);
        addGameMessage(`${data.username} left the game`, 'info');
    });

    socket.on('game_state', (data) => {
        currentRoom = data.room_id;
        currentUsername = elements.username.value.trim();
        elements.roomDisplay.textContent = currentRoom;
        elements.lobby.classList.add('hidden');
        elements.game.classList.remove('hidden');
        initializeGame(data);
    });

    socket.on('answers_evaluated', (data) => {
        highlightAnswers(data);
        updatePlayerScores(data.players);
    });

    socket.on('error', (data) => {
        alert(data.message);
    });

    function createGame() {
        currentUsername = elements.username.value.trim();
        if (!currentUsername) {
            alert('Please enter your name');
            return;
        }
        socket.emit('create_game', { username: currentUsername });
    }

    function showJoinForm() {
        currentUsername = elements.username.value.trim();
        if (!currentUsername) {
            alert('Please enter your name first');
            return;
        }
        elements.joinForm.classList.remove('hidden');
    }

    function joinGame() {
        const roomId = elements.roomId.value.trim();
        if (!roomId) {
            alert('Please enter a room ID');
            return;
        }
        socket.emit('join_game', { 
            username: currentUsername, 
            room_id: roomId 
        });
    }

    // In your crossword game template
    function submitAnswers() {
        const answers = collectAnswers();
        socket.emit('submit_answers', { answers });
    }
    function collectAnswers() {
        const answers = {};
        
        Object.entries(clueInputs).forEach(([wordKey, input]) => {
            answers[wordKey.split('-')[0]] = input.value.toUpperCase();
        });
        
        return answers;
    }
    function initializeGame(data) {
        currentCrossword = data.crossword;
        buildWordMap();
        renderCrossword();
        renderClues();
        updatePlayerScores(data.players);
    }

    function buildWordMap() {
        wordMap = {};
        currentCrossword.words.forEach(word => {
            const wordKey = `${word.number}-${word.direction}`;
            wordMap[wordKey] = {
                positions: [],
                length: word.word.length
            };
            
            for (let i = 0; i < word.word.length; i++) {
                const row = word.direction === 'across' ? word.row : word.row + i;
                const col = word.direction === 'across' ? word.col + i : word.col;
                wordMap[wordKey].positions.push({ row, col, index: i });
            }
        });
    }

    function renderCrossword() {
        elements.crosswordGrid.innerHTML = '';
        cellElements = {};
        
        // Determine grid size (assuming 15x15 if not specified)
        const gridSize = 15;
        elements.crosswordGrid.style.gridTemplateColumns = `repeat(${gridSize}, 30px)`;
        
        // Create grid cells
        for (let row = 0; row < gridSize; row++) {
            for (let col = 0; col < gridSize; col++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                
                // Check if cell is part of any word
                const isActive = currentCrossword.words.some(word => {
                    if (word.direction === 'across') {
                        return word.row === row && col >= word.col && col < word.col + word.word.length;
                    } else {
                        return word.col === col && row >= word.row && row < word.row + word.word.length;
                    }
                });
                
                if (!isActive) {
                    cell.classList.add('black');
                    elements.crosswordGrid.appendChild(cell);
                    continue;
                }
                
                // Add number indicator if this is the start of a word
                const wordNumber = getWordNumber(row, col);
                if (wordNumber) {
                    const numberSpan = document.createElement('span');
                    numberSpan.className = 'cell-number';
                    numberSpan.textContent = wordNumber;
                    cell.appendChild(numberSpan);
                }
                
                // Add letter display
                const letterSpan = document.createElement('span');
                letterSpan.className = 'cell-letter';
                letterSpan.dataset.row = row;
                letterSpan.dataset.col = col;
                cell.appendChild(letterSpan);
                
                elements.crosswordGrid.appendChild(cell);
                cellElements[`${row}-${col}`] = letterSpan;
            }
        }
    }

    function renderClues() {
        elements.acrossClues.innerHTML = '';
        elements.downClues.innerHTML = '';
        clueInputs = {};

        currentCrossword.words.forEach(word => {
            const li = document.createElement('li');
            li.className = 'clue-item';
            
            const clueText = document.createElement('span');
            clueText.className = 'clue-text';
            clueText.textContent = `${word.number}. ${word.clue}`;
            li.appendChild(clueText);
            
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'clue-input';
            input.dataset.wordKey = `${word.number}-${word.direction}`;
            input.placeholder = 'Enter answer';
            input.maxLength = word.word.length;
            
            input.addEventListener('input', (e) => {
                updateGridFromClueInput(e.target);
            });
            
            input.addEventListener('focus', () => {
                highlightWord(word);
            });
            
            li.appendChild(input);
            
            if (word.direction === 'across') {
                elements.acrossClues.appendChild(li);
            } else {
                elements.downClues.appendChild(li);
            }
            
            clueInputs[`${word.number}-${word.direction}`] = input;
        });
    }

    function updateGridFromClueInput(input) {
        const wordKey = input.dataset.wordKey;
        const wordData = wordMap[wordKey];
        const value = input.value.toUpperCase();
        
        // Update each cell in the grid for this word
        wordData.positions.forEach((pos, index) => {
            const cell = cellElements[`${pos.row}-${pos.col}`];
            if (cell) {
                cell.textContent = index < value.length ? value.charAt(index) : '';
            }
        });
    }

    function highlightWord(word) {
        // Clear previous highlights
        document.querySelectorAll('.cell').forEach(cell => {
            cell.classList.remove('highlight');
        });
        
        const wordKey = `${word.number}-${word.direction}`;
        const wordData = wordMap[wordKey];
        
        if (wordData) {
            wordData.positions.forEach(pos => {
                const cell = document.querySelector(`.cell[data-row="${pos.row}"][data-col="${pos.col}"]`);
                if (cell) cell.classList.add('highlight');
            });
            
            // Focus the input for this word
            const input = clueInputs[wordKey];
            if (input) input.focus();
        }
    }

    function highlightAnswers(data) {
        // Reset all cell styles first
        document.querySelectorAll('.cell').forEach(cell => {
            cell.classList.remove('correct', 'incorrect');
        });
        
        // Mark correct answers
        currentCrossword.words.forEach(word => {
            const wordKey = `${word.number}-${word.direction}`;
            const isIncorrect = data.incorrect_words.some(w => 
                w.number === word.number && w.direction === word.direction
            );
            
            if (!isIncorrect) {
                const wordData = wordMap[wordKey];
                wordData.positions.forEach(pos => {
                    const cell = document.querySelector(`.cell[data-row="${pos.row}"][data-col="${pos.col}"]`);
                    if (cell) cell.classList.add('correct');
                });
            }
        });
        
        // Mark incorrect answers
        data.incorrect_words.forEach(word => {
            const wordKey = `${word.number}-${word.direction}`;
            const wordData = wordMap[wordKey];
            
            wordData.positions.forEach(pos => {
                const cell = document.querySelector(`.cell[data-row="${pos.row}"][data-col="${pos.col}"]`);
                if (cell) cell.classList.add('incorrect');
            });
        });
        
        // Show result message
        if (data.username === currentUsername) {
            elements.resultMessage.textContent = `You got ${data.correct} correct out of ${currentCrossword.words.length}`;
            elements.resultMessage.className = data.incorrect_words.length > 0 ? 'error' : 'success';
        }
    }

    function collectAnswers() {
        const answers = {};
        
        Object.entries(clueInputs).forEach(([wordKey, input]) => {
            answers[wordKey.split('-')[0]] = input.value.toUpperCase();
        });
        
        return answers;
    }

    function updatePlayerScores(players) {
        elements.playerScores.innerHTML = '';
        
        Object.entries(players).forEach(([username, data]) => {
            const scoreDiv = document.createElement('div');
            scoreDiv.className = 'player-score';
            
            if (username === currentUsername) {
                scoreDiv.classList.add('you');
                scoreDiv.textContent = `You: ${data.score} points`;
            } else {
                scoreDiv.textContent = `${username}: ${data.score} points`;
            }
            
            elements.playerScores.appendChild(scoreDiv);
        });
    }

    function addGameMessage(text, type) {
        const message = document.createElement('div');
        message.className = `message ${type}`;
        message.textContent = text;
        elements.resultMessage.appendChild(message);
    }

    // Helper function
    function getWordNumber(row, col) {
        for (const word of currentCrossword.words) {
            if (word.row === row && word.col === col) {
                return word.number;
            }
        }
        return null;
    }
 // Add this to your Socket.IO event handlers in script.js
socket.on('game_over', (data) => {
    displayWinner(data);
});
function displayWinner(data) {
    // Clear existing game content
    elements.game.innerHTML = '';

    // Create winner display elements
    const winnerContainer = document.createElement('div');
    winnerContainer.className = 'winner-container';

    const winnerMessage = document.createElement('div');
    winnerMessage.className = 'winner-message';
    
    // Create winner title
    const title = document.createElement('h2');
    if (data.winners.length === 1) {
        const isYou = data.winners[0] === currentUsername;
        title.textContent = isYou ? '🎉 You Win! 🎉' : `🏆 ${data.winners[0]} Wins! 🏆`;
    } else {
        const includesYou = data.winners.includes(currentUsername);
        title.textContent = includesYou ? '🎉 You Tied! 🎉' : '🏆 Game Tied! 🏆';
    }
    winnerMessage.appendChild(title);

    // Create scoreboard
    const scoreboard = document.createElement('div');
    scoreboard.className = 'scoreboard';

    // Sort scores descending
    const sortedScores = Object.entries(data.scores).sort((a, b) => b[1] - a[1]);

    sortedScores.forEach(([name, score]) => {
        const scoreRow = document.createElement('div');
        scoreRow.className = `player-score ${name === currentUsername ? 'you' : ''}`;
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = name === currentUsername ? 'You' : name;
        
        const scoreSpan = document.createElement('span');
        scoreSpan.textContent = `${score}/${data.total_words}`;

        scoreRow.appendChild(nameSpan);
        scoreRow.appendChild(scoreSpan);
        scoreboard.appendChild(scoreRow);
    });

    // Create play again button
    const playAgainButton = document.createElement('button');
    playAgainButton.id = 'play-again';
    playAgainButton.textContent = 'Play Again';
    playAgainButton.addEventListener('click', () => {
        location.reload();
    });

    // Assemble components
    winnerContainer.appendChild(winnerMessage);
    winnerContainer.appendChild(scoreboard);
    winnerContainer.appendChild(playAgainButton);

    // Update game screen
    elements.game.appendChild(winnerContainer);
    elements.game.classList.remove('hidden');
}
});