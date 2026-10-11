EduMate - AI-Powered Interactive Learning Platform
===================================================

Overview:
---------
EduMate is an AI-integrated desktop application that transforms static educational materials (PDFs, videos, audios, and text) into dynamic and personalized learning experiences. It enhances user engagement and retention by generating interactive content such as quizzes, summaries, flashcards, and gamified modules like CodeQuest and WordScape.

Key Features:
-------------
- Multi-format Input: Accepts PDFs, audio files, videos, and plain text.
- AI Content Transformation: Uses advanced LLMs (e.g., Qwen, GPT) and ML models to extract key concepts.
- Output Modules:
  - QuizGenie: Auto-generates quizzes from content.
  - NotesMaker: Extracts concise notes.
  - AISummarizer: Summarizes input text using LLMs.
  - Gamified Learning: CodeBlocks, CodeQuest, WordScape, etc.
- Personalization: Adapts content to learner preferences and levels.
- Real-time Generation: On-demand content transformation.
- Scalable & Extensible: Built to support large content volumes and multiple domains.

Tech Stack:
-----------
- Backend: Python, OpenAI Whisper, MoviePy, Pydub, Edge-TTS
- AI/ML Models: Qwen2.5, GPT, BERT, LLaVA, QLoRA
- Database: PostgreSQL (with JSON support, full-text search, and ACID compliance)
- Frontend: GUI-based desktop application

System Architecture:
--------------------
1. **Input Module** – Accepts PDFs, audio, video, or text.
2. **Processing Engine** – Converts input to structured text.
3. **Content Analyzer** – Uses LLMs to extract and summarize key points.
4. **Module Generator** – Produces quizzes, stories, summaries, and games.
5. **Personalizer** – Customizes output based on user profiles.
6. **UI Layer** – Simple, user-friendly interface for learners and educators.

Installation & Usage:
---------------------
1. Install dependencies listed in `requirements.txt`
2. Set up PostgreSQL and initialize the schema using `init_db.sql`
3. Run the application using:
4. Navigate the GUI to upload educational content and generate outputs.

Contributors:
-------------
- Valan Antony Raj G
- Sailesh K
- Sanjay P
- Roopesh Khanna B
- Pragadeesh L A
- Athithiya A
- Nithishkrishna R S
- Mukarram Ahamed U

References:
-----------
- OpenAI Whisper: Speech Recognition
- Qwen2.5 LLM: Content & Reasoning
- LLaVA: Vision + Language Integration
- MoviePy: Video Processing
- Pydub: Audio Handling
- Edge-TTS: Text-to-Speech
- PostgreSQL: Database Backend

License:
--------
This project is for academic and educational use only.

