document.addEventListener('DOMContentLoaded', () => {
    const elements = {
        matches: document.getElementById('matches'),
        timer: document.getElementById('timer'),
        moves: document.getElementById('moves'),
        score: document.getElementById('score'),
        totalPairs: document.getElementById('total-pairs'),
        restartBtn: document.getElementById('restart-btn'),
        gameBoard: document.getElementById('game-board'),
        completionOverlay: document.getElementById('game-completion'),
        finalTime: document.getElementById('final-time'),
        finalMoves: document.getElementById('final-moves'),
        finalScore: document.getElementById('final-score'),
        restartGameBtn: document.getElementById('restart-game')
    };

    let gameState = {
        flippedCards: [],
        matches: 0,
        moves: 0,
        score: 0,
        timerInterval: null,
        seconds: 0,
        isProcessing: false,
        totalPairs: 0
    };

    function initGame() {
        gameState.totalPairs = parseInt(elements.totalPairs.textContent) || 0;
        if (gameState.totalPairs === 0) {
            console.error('Invalid total pairs count!');
            return;
        }
        
        resetGameState();
        setupEventListeners();
        startGame();
    }

    function startGame() {
        clearInterval(gameState.timerInterval);
        elements.completionOverlay.classList.add('hidden');
        startTimer();
        shuffleCards();
        setupCardListeners();
    }

    function startTimer() {
        gameState.seconds = 0;
        elements.timer.textContent = '00:00';
        gameState.timerInterval = setInterval(() => {
            gameState.seconds++;
            elements.timer.textContent = formatTime(gameState.seconds);
        }, 1000);
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        return `${mins}:${secs}`;
    }

    function setupCardListeners() {
        elements.gameBoard.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', () => handleCardClick(card));
        });
    }

    function handleCardClick(card) {
        if (gameState.isProcessing || 
            card.classList.contains('flipped') || 
            card.classList.contains('matched')) return;

        card.classList.add('flipped');
        gameState.flippedCards.push(card);

        if (gameState.flippedCards.length === 2) {
            gameState.moves++;
            elements.moves.textContent = gameState.moves;
            gameState.isProcessing = true;
            setTimeout(checkMatch, 500);
        }
    }

    function checkMatch() {
        const [card1, card2] = gameState.flippedCards;
        const isMatch = card1.dataset.matchId === card2.dataset.id && 
                       card2.dataset.matchId === card1.dataset.id;

        isMatch ? handleMatch(card1, card2) : handleMismatch(card1, card2);
        gameState.flippedCards = [];
        gameState.isProcessing = false;
    }

    function handleMatch(card1, card2) {
        card1.classList.add('matched');
        card2.classList.add('matched');
        gameState.matches++;
        gameState.score += 10;
        updateScoreDisplay();

        if (gameState.matches === gameState.totalPairs) {
            endGame();
        }
    }

    function handleMismatch(card1, card2) {
        setTimeout(() => {
            card1.classList.remove('flipped');
            card2.classList.remove('flipped');
        }, 1000);
    }

    function updateScoreDisplay() {
        elements.matches.textContent = gameState.matches;
        elements.score.textContent = gameState.score;
        elements.score.classList.add('score-pop');
        setTimeout(() => elements.score.classList.remove('score-pop'), 300);
    }

    function setupEventListeners() {
        elements.restartBtn.addEventListener('click', restartGame);
        elements.restartGameBtn.addEventListener('click', restartGame);
    }

    function restartGame() {
        clearInterval(gameState.timerInterval);
        elements.completionOverlay.classList.add('hidden');
        resetGameState();
        startGame();
    }

    function resetGameState() {
        gameState = {
            flippedCards: [],
            matches: 0,
            moves: 0,
            score: 0,
            timerInterval: null,
            seconds: 0,
            isProcessing: false,
            totalPairs: parseInt(elements.totalPairs.textContent) || 0
        };

        elements.matches.textContent = '0';
        elements.moves.textContent = '0';
        elements.score.textContent = '0';
        elements.timer.textContent = '00:00';

        elements.gameBoard.querySelectorAll('.card').forEach(card => {
            card.classList.remove('flipped', 'matched');
        });
    }

    function shuffleCards() {
        const cards = Array.from(elements.gameBoard.children);
        for (let i = cards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            elements.gameBoard.appendChild(cards[j]);
        }
    }

    function endGame() {
        clearInterval(gameState.timerInterval);
        setTimeout(() => {
            elements.finalTime.textContent = formatTime(gameState.seconds);
            elements.finalMoves.textContent = gameState.moves;
            elements.finalScore.textContent = gameState.score;
            elements.completionOverlay.classList.remove('hidden');
        }, 1000);
    }

    // Initialize the game
    initGame();
});