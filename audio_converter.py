import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO

# Load MP3 file and convert to WAV in memory (no need for temp files)
mp3_audio = AudioSegment.from_mp3(r"D:\Edumate\extracted_audio.mp3")

# Convert MP3 audio to WAV in memory
wav_io = BytesIO()
mp3_audio.export(wav_io, format="wav")
wav_io.seek(0)

# Initialize recognizer
recognizer = sr.Recognizer()

# Use AudioFile to process the in-memory WAV
with sr.AudioFile(wav_io) as source:
    audio_data = recognizer.record(source)  # Read the audio data
    try:
        # Perform speech recognition using Google Web Speech API
        text = recognizer.recognize_google(audio_data)
        print("Transcription:", text)  # Output the transcribed text
    except sr.UnknownValueError:
        print("Could not understand the audio")  # If speech is unclear
    except sr.RequestError as e:
        print(f"Could not request results: {e}")  # If there's an API issue
