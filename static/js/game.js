window.addEventListener('load', () => {
            setTimeout(() => {
                document.getElementById('preloader').style.opacity = '0';
                setTimeout(() => {
                    document.getElementById('preloader').remove();
                }, 300);
            }, 700);
        });
document.addEventListener('DOMContentLoaded', function() {
  // DOM Elements
  const blocksPool = document.getElementById('blocks-pool');
  const dropZone = document.getElementById('drop-zone');
  const runBtn = document.getElementById('run-btn');
  const hintBtn = document.getElementById('hint-btn');
  const userOutput = document.getElementById('user-output');
  const resultMessage = document.getElementById('result-message');
  
  // Drag and Drop Functionality
  let draggedBlock = null;
  blocksPool.addEventListener('dragstart', function(e) {
      if (e.target.classList.contains('code-block')) {
          draggedBlock = e.target;
          e.target.classList.add('dragging');
          e.dataTransfer.setData('text/plain', e.target.dataset.id);
          e.dataTransfer.effectAllowed = 'move';
      }
  });

  document.addEventListener('dragend', function(e) {
      if (e.target.classList.contains('code-block')) {
          e.target.classList.remove('dragging');
          // Return to pool if not dropped in drop zone
          if (!e.target.parentElement.id === 'drop-zone') {
              blocksPool.appendChild(e.target);
          }
      }
  });

  dropZone.addEventListener('dragover', function(e) {
      e.preventDefault();
      this.classList.add('drag-over');
      e.dataTransfer.dropEffect = 'move';
  });

  dropZone.addEventListener('dragleave', function() {
      this.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', function(e) {
      e.preventDefault();
      this.classList.remove('drag-over');
      
      if (draggedBlock) {
          // Clone the block (keep original in pool)
          const clonedBlock = draggedBlock.cloneNode(true);
          clonedBlock.addEventListener('dblclick', removeBlock);
          this.appendChild(clonedBlock);
      }
  });

  // Double-click to remove blocks
  dropZone.addEventListener('dblclick', function(e) {
      if (e.target.classList.contains('code-block')) {
          removeBlock(e);
      }
  });

  function removeBlock(e) {
      e.target.remove();
  }

  // Run Solution
  runBtn.addEventListener('click', function() {
      const blocks = dropZone.querySelectorAll('.code-block');
      const blockOrder = Array.from(blocks).map(block => block.dataset.id);
      console.log(blockOrder);
      const language = this.dataset.language;
      const flag=this.dataset.flag;
      console.log(flag);
      fetch(`/submit_solution/${flag}/${language}/${levelId}`, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          },
          body: JSON.stringify({ order: blockOrder })
      })
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              let message = `<div class="success">${data.message}</div>`;
              showConfetti();
              if (data.new_completion) {
                  message += `<p>+${data.coins_earned} coins earned!</p>`;
                  // Update coins display
                  document.querySelector('.coins').textContent = `🪙 ${data.total_coins}`;
                  
                  // Show confetti for first completion
                
              }
              
              if (data.unlocked_new_level) {
                  message += '<p>🎉 New level unlocked!</p>';
              }
              
              resultMessage.innerHTML = message;
          } else {
              resultMessage.innerHTML = `<div class="error">${data.message}</div>`;
          }
      });
  });

  // Hint System
  hintBtn.addEventListener('click', function() {
    const language = this.dataset.language;
      fetch(`/use_hint/${language}/${levelId}`)
      .then(response => response.json())
      .then(data => {
          if (data.success) {
              // Create nice hint popup
              const hintPopup = document.createElement('div');
              hintPopup.className = 'hint-popup';
              hintPopup.innerHTML = `
                  <div class="hint-content">
                      <h3>💡 Hint</h3>
                      <p>${data.hint}</p>
                      <button class="close-hint">OK</button>
                  </div>
              `;
              
              document.body.appendChild(hintPopup);
              
              // Close button
              hintPopup.querySelector('.close-hint').addEventListener('click', function() {
                  hintPopup.remove();
              });
          } else {
              alert(data.message);
          }
      });
  });

  // Confetti Effect
  function showConfetti() {
    const colors = ['#f1c40f', '#e74c3c', '#3498db', '#2ecc71', '#9b59b6'];
    
    // Create a container for all confetti
    const confettiContainer = document.createElement('div');
    confettiContainer.style.position = 'fixed';
    confettiContainer.style.top = '0';
    confettiContainer.style.left = '0';
    confettiContainer.style.width = '100%';
    confettiContainer.style.height = '100%';
    confettiContainer.style.pointerEvents = 'none';
    confettiContainer.style.zIndex = '9999';
    confettiContainer.style.overflow = 'hidden';
    document.body.appendChild(confettiContainer);
    
    for (let i = 0; i < 100; i++) {
      const confetti = document.createElement('div');
      confetti.className = 'confetti';
      confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.left = `${Math.random() * 100}vw`;
      confetti.style.width = `${Math.random() * 10 + 5}px`;
      confetti.style.height = `${Math.random() * 10 + 5}px`;
      confetti.style.animationDuration = `${Math.random() * 2 + 2}s`;
      confetti.style.animationDelay = `${Math.random() * 0.5}s`;
      
      confettiContainer.appendChild(confetti);
    }
    
    // Remove after animation
    setTimeout(() => {
      confettiContainer.remove();
    }, 3000);
  }

  // Daily Challenge Countdown
  if (document.getElementById('countdown')) {
      function updateCountdown() {
          const now = new Date();
          const midnight = new Date();
          midnight.setHours(24, 0, 0, 0);
          
          const diff = midnight - now;
          const hours = Math.floor(diff / (1000 * 60 * 60));
          const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
          const seconds = Math.floor((diff % (1000 * 60)) / 1000);
          
          document.getElementById('countdown').textContent = 
              `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      }

      setInterval(updateCountdown, 1000);
      updateCountdown();
  }
});