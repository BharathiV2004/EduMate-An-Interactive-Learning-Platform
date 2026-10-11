from moviepy import *

def extract_audio(video_path, output_audio_path):
    try:
        # Load the video
        clip = VideoFileClip(video_path)
        
        # Extract and save the audio
        if clip.audio is not None:
            clip.audio.write_audiofile(output_audio_path)
            print(f"Audio successfully saved to {output_audio_path}")
        else:
            print("No audio stream found in the video.")
    except Exception as e:
        print("An error occurred:", e)


# Replace with your actual video path
video_path = r"D:\Edumate\video_file.mp4"
output_audio_path = "extracted_audio.mp3"

extract_audio(video_path, output_audio_path)
