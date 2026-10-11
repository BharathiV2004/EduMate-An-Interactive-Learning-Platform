document.addEventListener('DOMContentLoaded', () => {
    const pathSegments = window.location.pathname.split('/');
    const isMultiplayer = pathSegments.includes('multiplayer');
    const topic = document.getElementById('game-board').dataset.topic;
    
    // Common DOM elements
    const elements = {
        lobby: document.getElementById('lobby'),
        gameScreen: document.getElementById('game-screen'),
        gameBoard: document.getElementById('game-board'),
        movesDisplay: document.getElementById('moves'),
        matchesDisplay: document.getElementById('matches'),
        totalPairsDisplay: document.getElementById('total-pairs'),
        scoreDisplay: document.getElementById('score'),
        playerScores: document.getElementById('player-scores'),
        restartBtn: document.getElementById('restart-btn')
    };

    // Single-player mode initialization
    if (!isMultiplayer) {
        initSinglePlayer();
        return;
    }

    // Multiplayer initialization (only if in multiplayer mode)
    if (isMultiplayer) {
        initMultiplayer();
    }

    // --- SINGLE PLAYER LOGIC ---
    function initSinglePlayer() {
        // Hide multiplayer-specific elements
        elements.lobby.classList.add('hidden');
        elements.playerScores.classList.add('hidden');
        elements.gameScreen.classList.remove('hidden');
    
        // Single-player game state
        let gameState = {
            flippedCards: [],
            moves: 0,
            matches: 0,
            score: 0,
            totalPairs: 0,
            isProcessing: false,  // Add this flag
            timer: 0,
            timerInterval: null
        };
    
        // Start timer
        startTimer();
    
        // Load game directly
        loadGame(topic);
    
        function startTimer() {
            gameState.timerInterval = setInterval(() => {
                gameState.timer++;
                updateTimerDisplay();
            }, 1000);
        }
    
        function updateTimerDisplay() {
            const minutes = Math.floor(gameState.timer / 60).toString().padStart(2, '0');
            const seconds = (gameState.timer % 60).toString().padStart(2, '0');
            document.getElementById('timer').textContent = `${minutes}:${seconds}`;
        }
    
        function stopTimer() {
            clearInterval(gameState.timerInterval);
        }
    
        function handleCardFlip(cardElement) {
            // Prevent flipping if:
            if (gameState.isProcessing || 
                cardElement.classList.contains('flipped') || 
                cardElement.classList.contains('matched')) {
                return;
            }
    
            // Flip the card
            cardElement.classList.add('flipped');
            gameState.flippedCards.push(cardElement);
    
            // If two cards are flipped, check for match
            if (gameState.flippedCards.length === 2) {
                gameState.isProcessing = true;
                gameState.moves++;
                elements.movesDisplay.textContent = gameState.moves;
    
                const [card1, card2] = gameState.flippedCards;
                
                // Wait for flip animation to complete
                setTimeout(() => {
                    // Bidirectional match check
                    const isMatch = card1.dataset.matchId === card2.dataset.id && 
                                    card2.dataset.matchId === card1.dataset.id;
    
                    if (isMatch) {
                        // Match found
                        card1.classList.add('matched');
                        card2.classList.add('matched');
                        gameState.matches++;
                        gameState.score += 100;
                        elements.matchesDisplay.textContent = gameState.matches;
                        elements.scoreDisplay.textContent = gameState.score;
                        
                        if (gameState.matches === gameState.totalPairs) {
                            stopTimer();
                            setTimeout(() => {
                                alert(`Game Over! Final Score: ${gameState.score}`);
                            }, 500);
                        }
                    } else {
                        // No match - flip back after delay
                        setTimeout(() => {
                            card1.classList.remove('flipped');
                            card2.classList.remove('flipped');
                        }, 1000);
                    }
                    
                    // Reset state after handling
                    gameState.flippedCards = [];
                    gameState.isProcessing = false;
                }, 600); // Wait for flip animation to complete
            }
        }

        // Restart functionality
        elements.restartBtn.addEventListener('click', () => {
            clearInterval(gameState.timerInterval);
            elements.gameBoard.innerHTML = '';
            gameState = {
                flippedCards: [],
                moves: 0,
                matches: 0,
                score: 0,
                totalPairs: 0,
                isProcessing: false,
                canFlip: true,
                timer: 0,
                timerInterval: null
            };
            elements.movesDisplay.textContent = '0';
            elements.matchesDisplay.textContent = '0';
            elements.scoreDisplay.textContent = '0';
            document.getElementById('timer').textContent = '00:00';
            loadGame(topic);
        });
    }

    function initMultiplayer() {
        // Original multiplayer code remains unchanged below
        const socket = io('http://localhost:5000');
        
        // Multiplayer-specific elements
        elements.username = document.getElementById('username');
        elements.createGame = document.getElementById('create-game');
        elements.joinGame = document.getElementById('join-game');
        elements.joinForm = document.getElementById('join-form');
        elements.roomId = document.getElementById('room-id');
        elements.confirmJoin = document.getElementById('confirm-join');
        elements.roomDisplay = document.getElementById('room-display');
        elements.topicDisplay = document.getElementById('topic-display');

        let currentRoom = null;
        let currentUsername = null;
        let gameState = {
            cards: [],
            totalPairs: 0,
            myScore: 0,
            myMatches: 0,
            myMoves: 0
        };

        // Event listeners
        elements.createGame.addEventListener('click', createGame);
        elements.joinGame.addEventListener('click', showJoinForm);
        elements.confirmJoin.addEventListener('click', joinGame);
        elements.restartBtn.addEventListener('click', restartGame);

        // Socket.IO event handlers
        socket.on('connection_ack', (data) => {
            console.log(data.status);
        });

        socket.on('room_created', (data) => {
            currentRoom = data.room_id;
            elements.roomDisplay.textContent = currentRoom;
            elements.topicDisplay.textContent = data.topic;
            elements.lobby.classList.add('hidden');
            elements.gameScreen.classList.remove('hidden');
            loadGame(data.topic);
        });

        socket.on('player_joined', (data) => {
            updatePlayerScores(data.players);
        });

        socket.on('player_left', (data) => {
            updatePlayerScores(data.players);
        });

        socket.on('room_state', (data) => {
            currentRoom = data.room_id;
            elements.roomDisplay.textContent = currentRoom;
            elements.topicDisplay.textContent = data.topic;
            elements.lobby.classList.add('hidden');
            elements.gameScreen.classList.remove('hidden');
            loadGame(data.topic);
            updatePlayerScores(data.players);
        });

        socket.on('card_flipped', (data) => {
            const card = document.querySelector(`.card[data-id="${data.card_id}"]`);
            if (card) {
                card.classList.add('flipped');
                const indicator = document.createElement('div');
                indicator.className = 'player-indicator';
                indicator.textContent = data.username;
                indicator.style.backgroundColor = getPlayerColor(data.username);
                card.appendChild(indicator);
            }
        });

        socket.on('match_found', (data) => {
            data.card_ids.forEach(card_id => {
                const card = document.querySelector(`.card[data-id="${card_id}"]`);
                if (card) {
                    card.classList.add('matched');
                    const indicators = card.querySelectorAll('.player-indicator');
                    indicators.forEach(ind => ind.remove());
                }
            });
            updatePlayerScores(data.players);
            updateMyStats();
        });

        socket.on('no_match', (data) => {
            setTimeout(() => {
                data.card_ids.forEach(card_id => {
                    const card = document.querySelector(`.card[data-id="${card_id}"]`);
                    if (card) {
                        card.classList.remove('flipped');
                        const indicators = card.querySelectorAll('.player-indicator');
                        indicators.forEach(ind => ind.remove());
                    }
                });
            }, 1000);
            updatePlayerScores(data.players);
            updateMyStats();
        });

        socket.on('game_completed', (data) => {
            updatePlayerScores(data.players);
            alert('Game completed! Check the scores to see who won!');
        });

        socket.on('error', (data) => {
            alert(data.message);
        });

        // Multiplayer functions
        function createGame() {
            currentUsername = elements.username.value.trim();
            if (!currentUsername) {
                alert('Please enter your name');
                return;
            }
            socket.emit('create_room', {
                username: currentUsername,
                topic: topic
            });
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
            socket.emit('join_room', {
                username: currentUsername,
                room_id: roomId
            });
        }

        function loadGame(topic) {
            fetch(`/api/cards/${topic}`)
                .then(response => response.json())
                .then(data => {
                    gameState.totalPairs = data.total_pairs;
                    elements.totalPairsDisplay.textContent = data.total_pairs;
                    createBoard(data.cards);
                })
                .catch(handleLoadError);
        }

        function createBoard(cards) {
            elements.gameBoard.innerHTML = '';
            gameState.cards = cards;
            
            cards.forEach(card => {
                const cardElement = createCardElement(card);
                cardElement.addEventListener('click', () => flipCard(cardElement));
                elements.gameBoard.appendChild(cardElement);
            });
        }

        function flipCard(cardElement) {
            if (cardElement.classList.contains('flipped') || 
                cardElement.classList.contains('matched')) {
                return;
            }
            
            const cardId = cardElement.dataset.id;
            socket.emit('flip_card', {
                card_id: cardId
            });
        }

        function updatePlayerScores(players) {
            elements.playerScores.innerHTML = '';
            
            for (const [username, data] of Object.entries(players)) {
                const playerScore = document.createElement('div');
                playerScore.className = 'player-score';
                const youBadge = username === currentUsername ? ' (You)' : '';
                playerScore.textContent = `${username}${youBadge}: ${data.score} points (${data.matched_pairs} matches, ${data.moves} moves)`;
                
                if (username === currentUsername) {
                    gameState.myScore = data.score;
                    gameState.myMatches = data.matched_pairs;
                    gameState.myMoves = data.moves;
                    playerScore.style.fontWeight = 'bold';
                    updateMyStats();
                }
                
                elements.playerScores.appendChild(playerScore);
            }
        }

        function updateMyStats() {
            elements.movesDisplay.textContent = gameState.myMoves;
            elements.matchesDisplay.textContent = gameState.myMatches;
            elements.scoreDisplay.textContent = gameState.myScore;
        }

        function restartGame() {
            if (currentRoom) {
                socket.emit('join_room', {
                    username: currentUsername,
                    room_id: currentRoom
                });
            }
        }

        function getPlayerColor(username) {
            let hash = 0;
            for (let i = 0; i < username.length; i++) {
                hash = username.charCodeAt(i) + ((hash << 5) - hash);
            }
            
            const colors = [
                '#FF6633', '#FFB399', '#FF33FF', '#FFFF99', '#00B3E6',
                '#E6B333', '#3366E6', '#999966', '#99FF99', '#B34D4D',
                '#80B300', '#809900', '#E6B3B3', '#6680B3', '#66991A'
            ];
            
            return colors[Math.abs(hash) % colors.length];
        }
    }

    // Shared functions
    function createCardElement(card) {
        const cardElement = document.createElement('div');
        cardElement.className = 'card';
        cardElement.dataset.id = card.id;
        cardElement.dataset.matchId = card.match_id;
        cardElement.innerHTML = `
            <div class="card-face card-front">?</div>
            <div class="card-face card-back">${card.content}</div>
        `;
        return cardElement;
    }

    function handleLoadError(error) {
        console.error('Error:', error);
        elements.gameBoard.innerHTML = 
            '<div class="error">Failed to load game data. Please try again.</div>';
    }
});