document.addEventListener('DOMContentLoaded', function() {
    const gameState = {
        currentLevel: 1,
        score: 0,
        lives: 3,
        totalLevels: 1,
        currentSnippet: null,
        currentLanguage: document.getElementById('currentLanguage').value
    };

    // DOM Elements
    const elements = {
        level: document.getElementById('level'),
        score: document.getElementById('score'),
        lives: document.getElementById('lives'),
        problemDescription: document.getElementById('problem-description'),
        codeTemplate: document.getElementById('code-template'),
        editor: document.getElementById('editor'),
        snippetPool: document.getElementById('snippetPool'),
        checkBtn: document.getElementById('checkBtn'),
        skipBtn: document.getElementById('skipBtn'),
        feedbackModal: document.getElementById('feedbackModal'),
        feedbackTitle: document.getElementById('feedbackTitle'),
        feedbackMessage: document.getElementById('feedbackMessage'),
        solutionDisplay: document.getElementById('solutionDisplay'),
        correctSolution: document.getElementById('correctSolution'),
        progressBar: document.getElementById('progressBar'),
        continueBtn: document.getElementById('continueBtn'),
        backToCoursesBtn: document.getElementById('backToCoursesBtn'),
        backToLanguageBtn: document.getElementById('backToLanguageBtn')
    };

    // Initialize game
    function initGame() {
        updateGameStats();
        setupDragAndDrop();
        setupEventListeners();
        setCommentMarkers();
    }

    function setCommentMarkers() {
        const markers = {
            python: '# DRAG SNIPPET HERE',
            javascript: '/* DRAG SNIPPET HERE */',
            java: '// DRAG SNIPPET HERE',
            c: '/* DRAG SNIPPET HERE */',
            cpp: '// DRAG SNIPPET HERE'
        };
        gameState.dragMarker = markers[gameState.currentLanguage] || '/* DRAG SNIPPET HERE */';
    }

    function updateGameStats() {
        elements.level.textContent = gameState.currentLevel;
        elements.score.textContent = gameState.score;
        elements.lives.textContent = '❤️'.repeat(gameState.lives);
        elements.progressBar.style.width = `${((gameState.currentLevel - 1) / gameState.totalLevels) * 100}%`;
    }

    function setupDragAndDrop() {
        document.querySelectorAll('.snippet').forEach(snippet => {
            snippet.addEventListener('dragstart', function(e) {
                gameState.currentSnippet = e.target.getAttribute('data-snippet');
                e.dataTransfer.setData('text/plain', gameState.currentSnippet);
                this.classList.add('dragging');
            });

            snippet.addEventListener('dragend', function(e) {
                this.classList.remove('dragging');
            });
        });

        elements.editor.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drop-target');
        });

        elements.editor.addEventListener('dragleave', function() {
            this.classList.remove('drop-target');
        });

        elements.editor.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drop-target');
            const snippetText = e.dataTransfer.getData('text/plain');
            if (snippetText) {
                this.textContent = this.textContent.replace(gameState.dragMarker, snippetText);
                gameState.currentSnippet = snippetText;
            }
        });
    }

    function setupEventListeners() {
        elements.checkBtn.addEventListener('click', async function() {
            if (!gameState.currentSnippet) {
                showFeedback('Error', 'Please place a code fragment first!', false);
                return;
            }

            try {
                const response = await fetch(`/check_answer/${gameState.currentLanguage}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        question_id: gameState.currentLevel, 
                        answer: gameState.currentSnippet 
                    })
                });

                const result = await response.json();
                
                if (result.correct) {
                    gameState.score += 100;
                    showFeedback('Success!', 'Your code works perfectly!', true);
                } else {
                    gameState.lives--;
                    showFeedback('Incorrect', 'Your solution didn\'t work as expected.', false, result.solution);
                    if (gameState.lives <= 0) showGameOver();
                }
                
                updateGameStats();
            } catch (error) {
                console.error('Error:', error);
                showFeedback('Error', 'Something went wrong. Please try again.', false);
            }
        });

        elements.skipBtn.addEventListener('click', async function() {
            const response = await fetch(`/next_question/${gameState.currentLanguage}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_id: gameState.currentLevel })
            });

            const nextQuestion = await response.json();
            handleNextQuestion(nextQuestion);
        });

        elements.continueBtn.addEventListener('click', async function() {
            elements.feedbackModal.style.display = 'none';
            if (gameState.lives > 0) {
                const response = await fetch(`/next_question/${gameState.currentLanguage}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_id: gameState.currentLevel })
                });
                handleNextQuestion(await response.json());
            }
        });

        elements.backToCoursesBtn.addEventListener('click', () => window.location.href = '/quiz');
        elements.backToLanguageBtn.addEventListener('click', () => window.location.href = '/language_selection');
    }

    function showFeedback(title, message, isSuccess, solution = null) {
        elements.feedbackTitle.textContent = title;
        elements.feedbackMessage.textContent = message;
        elements.feedbackTitle.style.color = isSuccess ? '#00d1b2' : '#f14668';
        //elements.continueBtn.style.display = 'inline-block'

        if (solution) {
            elements.correctSolution.textContent = solution;
            elements.solutionDisplay.classList.remove('hidden');
        } else {
            elements.solutionDisplay.classList.add('hidden');
        }

        elements.feedbackModal.style.display = 'flex';
    }

    function showGameOver() {
        setTimeout(() => {
            showFeedback('Game Over', `Final Score: ${gameState.score}`, false);
        }, 1500);
    }

    function handleNextQuestion(nextQuestion) {
        if (nextQuestion.completed) {
            showFeedback('Congratulations!', 'You completed all levels!', true);
        } else {
            gameState.currentLevel++;
            updateGameStats();
            loadQuestion(nextQuestion.question);
        }
    }

    function loadQuestion(questionData) {
        elements.problemDescription.textContent = questionData.description || 'Complete the function to pass this level.';
        elements.editor.textContent = questionData.template;
        
        // Add this line to update the expected output
        elements.codeTemplate.textContent = questionData.expected_output || 'Expected output will appear here';
        
        elements.snippetPool.innerHTML = '';
        questionData.snippets.forEach(snippet => {
            const snippetElement = document.createElement('div');
            snippetElement.className = 'snippet';
            snippetElement.setAttribute('draggable', true);
            snippetElement.setAttribute('data-snippet', snippet);
            snippetElement.innerHTML = `
                <span class="snippet-text">${snippet}</span>
                <div class="snippet-drag-handle">≡</div>
            `;
            elements.snippetPool.appendChild(snippetElement);
        });
        
        gameState.currentSnippet = null;
        setupDragAndDrop();
    }

    initGame();
});