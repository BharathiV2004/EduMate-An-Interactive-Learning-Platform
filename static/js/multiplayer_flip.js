document.addEventListener('DOMContentLoaded', () => {
    const elements = {
        lobby: document.getElementById('lobby'),
        gameSection: document.getElementById('game-section'),
        playerNameInput: document.getElementById('player-name'),
        joinBtn: document.getElementById('join-btn'),
        createBtn: document.getElementById('create-btn'),
        roomInfo: document.getElementById('room-info'),
        roomIdDisplay: document.getElementById('room-id'),
        copyBtn: document.getElementById('copy-btn'),
        playerList: document.getElementById('player-list'),
        startBtn: document.getElementById('start-btn'),
        gameBoard: document.getElementById('game-board'),
        matchesDisplay: document.getElementById('matches'),
        totalPairsDisplay: document.getElementById('total-pairs'),
        timerDisplay: document.getElementById('timer'),
        playersScoreboard: document.getElementById('players-scoreboard'),
        restartBtn: document.getElementById('restart-btn'),
        leaveBtn: document.getElementById('leave-btn'),
        currentPlayerDisplay: document.createElement('div')
    };

    elements.currentPlayerDisplay.id = 'current-player';
    elements.currentPlayerDisplay.className = 'current-player-display';
    elements.gameSection.insertBefore(elements.currentPlayerDisplay, elements.gameBoard);

    let gameState = {
        socket: null,
        roomId: null,
        playerId: null,
        playerName: null,
        isHost: false,
        players: {},
        cards: [],
        flippedCards: [],
        matchedPairs: 0,
        totalPairs: 0,
        timer: 0,
        timerInterval: null,
        currentPlayer: null,
        noCards: 0
    };

    function initSocket() {
        gameState.socket = io();
        
        gameState.socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        gameState.socket.on('player_update', (data) => {
            updatePlayerList(data.players);
            gameState.players = data.players;
            gameState.currentPlayer = data.current_player;
            updateCurrentPlayerDisplay();
            
            if (gameState.isHost) {
                elements.startBtn.disabled = Object.keys(data.players).length < 1;
            }
        });
        
        gameState.socket.on('game_started', (data) => {
            startGame(data.cards, data.total_pairs, data.current_player);
        });
        gameState.socket.on('reset_cards', (data) => {
            gameState.currentPlayer = data.current_player;
            updateCurrentPlayerDisplay();
            resetCardsOnBoard([data.card1_id, data.card2_id]);
        });
        
        gameState.socket.on('game_completed', (data) => {
    stopTimer();
    updateScoreboard(data.players);
    elements.gameBoard.style.pointerEvents = 'none';
    
    const victoryMessage = document.createElement('div');
    victoryMessage.className = 'victory-message';
    victoryMessage.innerHTML = `
        <h2>Game Over!</h2>
        <p>Final Scores</p>
    `;
    elements.gameSection.insertBefore(victoryMessage, elements.playersScoreboard);
});
        
        gameState.socket.on('not_your_turn', (data) => {
            updateCurrentPlayerDisplay();
            alert(data.message);
        });
        
        gameState.socket.on('error', (data) => {
            alert(data.message);
        });
            // In the socket event handlers section:
gameState.socket.on('card_flipped', (data) => {
    flipCardOnBoard(data.card_id, data.player_id);
    gameState.currentPlayer = data.current_player;
    updateCurrentPlayerDisplay();
});

gameState.socket.on('match_found', (data) => {
    handleMatchFound(data.card1_id, data.card2_id, data.players, data.matched_pairs);
    gameState.currentPlayer = data.current_player;
    updateCurrentPlayerDisplay();
});

gameState.socket.on('no_match', (data) => {
    gameState.currentPlayer = data.current_player;
    updateCurrentPlayerDisplay();
    setTimeout(() => {
        resetCardsOnBoard([data.card1_id, data.card2_id]);
    }, 1000);
});

gameState.socket.on('reset_cards', (data) => {
    gameState.currentPlayer = data.current_player;
    updateCurrentPlayerDisplay();
    resetCardsOnBoard([data.card1_id, data.card2_id]);
});
    }

    function updateCurrentPlayerDisplay() {
        if (!gameState.currentPlayer) return;
        
        const currentPlayer = gameState.players[gameState.currentPlayer];
        if (!currentPlayer) return;
        
        const isMyTurn = gameState.currentPlayer === gameState.playerId;
        const playerName = currentPlayer.name + (isMyTurn ? ' (You)' : '');
        
        elements.currentPlayerDisplay.innerHTML = `
            <span class="turn-label">Current Turn:</span>
            <span class="player-name" style="color: ${getPlayerColor(gameState.currentPlayer)}">
                ${playerName}
            </span>
            ${isMyTurn ? '<span class="your-turn-badge">Your Turn!</span>' : ''}
        `;
        
        // Highlight current player in player list
        document.querySelectorAll('.player').forEach(playerEl => {
            playerEl.classList.remove('current-turn');
            if (playerEl.textContent.includes(currentPlayer.name)) {
                playerEl.classList.add('current-turn');
            }
        });
    }

    function createRoom() {
        const topic = elements.gameBoard.dataset.topic;
        gameState.playerName = elements.playerNameInput.value.trim() || 'Player';
        
        fetch(`/create-room/${topic}`)
            .then(response => response.json())
            .then(data => {
                gameState.roomId = data.room_id;
                gameState.isHost = true;
                
                elements.roomIdDisplay.textContent = gameState.roomId;
                elements.roomInfo.classList.remove('hidden');
                elements.lobby.classList.add('host-lobby');
                
                gameState.socket.emit('join', {
                    room_id: gameState.roomId,
                    player_name: gameState.playerName
                });
            })
            .catch(error => {
                console.error('Error creating room:', error);
                alert('Failed to create room. Please try again.');
            });
    }

    function joinRoom() {
        const roomId = prompt('Enter Room ID:');
        if (!roomId) return;
        
        gameState.roomId = roomId;
        gameState.playerName = elements.playerNameInput.value.trim() || 'Player';
        gameState.isHost = false;
        
        gameState.socket.emit('join', {
            room_id: gameState.roomId,
            player_name: gameState.playerName
        });
        
        elements.roomIdDisplay.textContent = gameState.roomId;
        elements.roomInfo.classList.remove('hidden');
        elements.startBtn.disabled = true;
    }

    function updatePlayerList(players) {
        elements.playerList.innerHTML = '';
        
        Object.values(players).forEach(player => {
            const playerElement = document.createElement('div');
            playerElement.className = 'player';
            playerElement.textContent = player.name;
            if (player.socket_id === gameState.socket.id) {
                playerElement.classList.add('you');
            }
            elements.playerList.appendChild(playerElement);
        });
    }

    function startGame(cards, totalPairs, currentPlayer) {
        elements.lobby.classList.add('hidden');
        elements.gameSection.classList.remove('hidden');
        
        gameState.cards = cards;
        gameState.totalPairs = totalPairs;
        gameState.matchedPairs = 0;
        gameState.flippedCards = [];
        gameState.noCards=0;
        gameState.currentPlayer = currentPlayer;
        
        elements.matchesDisplay.textContent = '0';
        elements.totalPairsDisplay.textContent = totalPairs;
        
        createBoard();
        startTimer();
        updateCurrentPlayerDisplay();
    }

    function createBoard() {
        elements.gameBoard.innerHTML = '';
        
        gameState.cards.forEach(card => {
            const cardElement = document.createElement('div');
            cardElement.className = 'card';
            cardElement.dataset.id = card.id;
            
            cardElement.innerHTML = `
                <div class="card-face card-front">?</div>
                <div class="card-face card-back">${card.content}</div>
            `;
            
            cardElement.addEventListener('click', () => flipCard(cardElement));
            elements.gameBoard.appendChild(cardElement);
        });
    }

    function flipCard(cardElement) {
        const cardId = cardElement.dataset.id;
        
        if (cardElement.classList.contains('flipped') || 
            cardElement.classList.contains('matched')) {
            return;
        }
        
        const flippedCards = document.querySelectorAll('.card.flipped:not(.matched)');
        if (flippedCards.length >= 2) {
            return;
        }
        
        gameState.socket.emit('flip_card', {
            room_id: gameState.roomId,
            card_id: cardId
        });
    }

    function flipCardOnBoard(cardId, playerId) {
        const cardElement = document.querySelector(`.card[data-id="${cardId}"]`);
        if (!cardElement) return;
        
        cardElement.classList.add('flipped');
        
        const player = gameState.players[playerId];
        if (player) {
            const indicator = document.createElement('div');
            indicator.className = 'player-indicator';
            indicator.textContent = player.name.charAt(0);
            indicator.style.backgroundColor = getPlayerColor(playerId);
            cardElement.appendChild(indicator);
        }
    }



// Update the handleMatchFound function:
function handleMatchFound(card1Id, card2Id, players, matchedPairs) {
    const card1 = document.querySelector(`.card[data-id="${card1Id}"]`);
    const card2 = document.querySelector(`.card[data-id="${card2Id}"]`);
    
    if (card1 && card2) {
        card1.classList.add('matched');
        card2.classList.add('matched');
        
        gameState.matchedPairs = matchedPairs;
        elements.matchesDisplay.textContent = matchedPairs;
        
        updateScoreboard(players);
    }
}
    function resetCardsOnBoard(cardIds) {
        cardIds.forEach(cardId => {
            const card = document.querySelector(`.card[data-id="${cardId}"]`);
            if (card) {
                card.classList.remove('flipped');
                const indicator = card.querySelector('.player-indicator');
                if (indicator) {
                    indicator.remove();
                }
            }
        });
    }

    function updateScoreboard(players) {
        elements.playersScoreboard.innerHTML = '';
        
        const sortedPlayers = Object.values(players).sort((a, b) => b.score - a.score);
        const maxScore = sortedPlayers[0]?.score || 1;
        
        const leaderboard = document.createElement('div');
        leaderboard.className = 'leaderboard';
        
        const header = document.createElement('div');
        header.className = 'leaderboard-header';
        header.innerHTML = '<h2 class="leaderboard-title">Leaderboard</h2>';
        leaderboard.appendChild(header);
        
        const list = document.createElement('ul');
        list.className = 'leaderboard-list';
        
        sortedPlayers.forEach((player, index) => {
            const li = document.createElement('li');
            li.className = `leaderboard-item rank-${index + 1}`;
            
            // Rank badge
            const rank = document.createElement('div');
            rank.className = 'rank-badge';
            rank.textContent = index + 1;
            li.appendChild(rank);
            
            // Player info
            const playerInfo = document.createElement('div');
            playerInfo.className = 'player-info';
            
            // Avatar
            const avatar = document.createElement('div');
            avatar.className = 'player-avatar';
            avatar.style.backgroundColor = getPlayerColor(Object.keys(gameState.players).find(
                id => gameState.players[id].name === player.name
            ));
            avatar.textContent = player.name.charAt(0).toUpperCase();
            playerInfo.appendChild(avatar);
            
            // Stats
            const stats = document.createElement('div');
            stats.className = 'player-stats';
            
            // Name
            const name = document.createElement('div');
            name.className = 'player-name';
            name.textContent = player.name + (player.socket_id === gameState.socket.id ? ' (You)' : '');
            stats.appendChild(name);
            
            // Progress bar
            const progress = document.createElement('div');
            progress.className = 'score-progress';
            const progressBar = document.createElement('div');
            progressBar.className = 'score-progress-bar';
            progressBar.style.width = `${(player.score / maxScore) * 100}%`;
            progress.appendChild(progressBar);
            
            // Score text
            const scoreText = document.createElement('div');
            scoreText.className = 'score-text';
            scoreText.innerHTML = `
                <span>Score: ${player.score}</span>
                <span>Matches: ${Math.floor(player.matched_pairs)}</span>
            `;
            
            stats.appendChild(progress);
            stats.appendChild(scoreText);
            playerInfo.appendChild(stats);
            li.appendChild(playerInfo);
            list.appendChild(li);
        });
        
        leaderboard.appendChild(list);
        elements.playersScoreboard.appendChild(leaderboard);
        
        // Add confetti if game is completed
        if (gameState.matchedPairs === gameState.totalPairs) {
            addConfetti();
        }
    }
    
    function addConfetti() {
        const colors = ['#4285f4', '#34a853', '#fbbc05', '#ea4335'];
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDelay = Math.random() * 2 + 's';
            elements.playersScoreboard.appendChild(confetti);
        }
    }

    function startTimer() {
        gameState.timer = 0;
        updateTimerDisplay();
        gameState.timerInterval = setInterval(() => {
            gameState.timer++;
            updateTimerDisplay();
        }, 1000);
    }

    function stopTimer() {
        clearInterval(gameState.timerInterval);
    }

    function updateTimerDisplay() {
        const minutes = Math.floor(gameState.timer / 60).toString().padStart(2, '0');
        const seconds = (gameState.timer % 60).toString().padStart(2, '0');
        elements.timerDisplay.textContent = `${minutes}:${seconds}`;
    }

    function getPlayerColor(playerId) {
        const colors = [
            '#4285f4', '#ea4335', '#fbbc05', '#34a853', 
            '#673ab7', '#ff5722', '#009688', '#e91e63'
        ];
        
        const playerIndex = Object.keys(gameState.players).indexOf(playerId);
        return colors[playerIndex % colors.length];
    }

    elements.createBtn.addEventListener('click', createRoom);
    elements.joinBtn.addEventListener('click', joinRoom);
    elements.copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(gameState.roomId);
        alert('Room ID copied to clipboard!');
    });
    elements.startBtn.addEventListener('click', () => {
        gameState.socket.emit('start_game', {
            room_id: gameState.roomId
        });
    });
    elements.restartBtn.addEventListener('click', () => {
        if (gameState.isHost) {
            gameState.socket.emit('start_game', {
                room_id: gameState.roomId
            });
        }
    });
    elements.leaveBtn.addEventListener('click', () => {
        window.location.href = '/';
    });

    initSocket();
});