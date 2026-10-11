let currentScene = 0;
let currentDialogue = 0;
const loading = document.getElementById("loading");
const titleScreen = document.getElementById("title-screen");
const storyContainer = document.getElementById("story-container");
const completionScreen = document.getElementById("completion-screen");
const startBtn = document.getElementById("start-btn");
const replayBtn = document.getElementById("replay-btn");
const sceneImage = document.getElementById("scene-image");
const sceneTitle = document.getElementById("scene-title");
const dialogueContainer = document.getElementById("dialogue-container");
const audioPlayer = document.getElementById("audio-player");
const progress = document.getElementById("progress");

// Animation timing
const DIALOGUE_TRANSITION_TIME = 500;
const SCENE_TRANSITION_TIME = 1000;

function preloadAssets() {
    let totalAssets = 0;
    let loadedAssets = 0;
    
    // Count all assets
    storyData.scenes.forEach(scene => {
        totalAssets++; // Scene image
        scene.dialogues_with_audio.forEach(() => totalAssets++); // Audio files
    });
    storyData.characters.forEach(() => totalAssets++); // Character images

    function assetLoaded() {
        loadedAssets++;
        progress.style.width = `${(loadedAssets / totalAssets) * 100}%`;
        
        if (loadedAssets >= totalAssets) {
            setTimeout(() => {
                loading.classList.add("hidden");
                titleScreen.classList.remove("hidden");
            }, 500);
        }
    }

    // Preload scene images
    storyData.scenes.forEach(scene => {
        const img = new Image();
        img.src = scene.scene_image_path;
        img.onload = assetLoaded;
        img.onerror = assetLoaded;
    });

    // Preload character images
    storyData.characters.forEach(character => {
        const img = new Image();
        img.src = character.image_path;
        img.onload = assetLoaded;
        img.onerror = assetLoaded;
    });

    // Preload audio files
    storyData.scenes.forEach(scene => {
        scene.dialogues_with_audio.forEach(dialogue => {
            const audio = new Audio(dialogue.audio_path);
            audio.addEventListener('canplaythrough', assetLoaded, { once: true });
            audio.addEventListener('error', assetLoaded, { once: true });
        });
    });
}

function startStory() {
    titleScreen.classList.add("hidden");
    storyContainer.classList.remove("hidden");
    loadScene();
}

function loadScene() {
    const scene = storyData.scenes[currentScene];
    
    // Fade in scene
    sceneImage.style.opacity = 0;
    setTimeout(() => {
        sceneImage.src = scene.scene_image_path;
        sceneImage.style.opacity = 1;
    }, SCENE_TRANSITION_TIME / 2);
    
    sceneTitle.textContent = scene.scene_title;
    sceneTitle.classList.add("active");
    currentDialogue = 0;
    dialogueContainer.innerHTML = "";
    
    // Start showing dialogues after scene loads
    setTimeout(showDialogue, SCENE_TRANSITION_TIME);
}

function showDialogue() {
    const scene = storyData.scenes[currentScene];
    
    // Check if all dialogues are done
    if (currentDialogue >= scene.dialogues_with_audio.length) {
        currentScene++;
        currentDialogue = 0;
        
        // Check if all scenes are done
        if (currentScene >= storyData.scenes.length) {
            completeStory();
            return;
        }
        
        // Load next scene
        loadScene();
        return;
    }
    
    const dialogue = scene.dialogues_with_audio[currentDialogue];
    const character = storyData.characters.find(c => c.name === dialogue.character);
    
    // Create dialogue box
    const dialogueBox = document.createElement("div");
    dialogueBox.className = "dialogue-box";
    dialogueBox.innerHTML = `
        <img class="character-image" src="${character.image_path}" alt="${character.name}">
        <div class="dialogue-content">
            <div class="character-name">${dialogue.character}</div>
            <div class="dialogue-text">${dialogue.line}</div>
        </div>
    `;
    
    // Clear previous dialogue and add new one
    dialogueContainer.innerHTML = "";
    dialogueContainer.appendChild(dialogueBox);
    
    // Fade in dialogue
    setTimeout(() => {
        dialogueBox.classList.add("active");
    }, 50);
    
    // Play audio
    audioPlayer.src = dialogue.audio_path;
    audioPlayer.currentTime = 0;
    audioPlayer.play();
    
    // Auto-advance when audio ends
    audioPlayer.onended = () => {
        currentDialogue++;
        showDialogue();
    };
}

function completeStory() {
    // Fade out story container
    storyContainer.style.opacity = 0;
    setTimeout(() => {
        storyContainer.classList.add("hidden");
        storyContainer.style.opacity = 1;
        completionScreen.classList.remove("hidden");
    }, SCENE_TRANSITION_TIME);
}

// Event listeners
startBtn.addEventListener("click", startStory);
replayBtn.addEventListener("click", () => {
    currentScene = 0;
    currentDialogue = 0;
    completionScreen.classList.add("hidden");
    titleScreen.classList.remove("hidden");
});

// Initialize
window.addEventListener('load', preloadAssets);