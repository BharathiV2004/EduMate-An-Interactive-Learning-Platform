import cv2
import pytesseract
from moviepy import *
from fuzzywuzzy import fuzz

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Video file path
video_path = r"D:\Edumate\uploads\sample_video.mp4"
clip = VideoFileClip(video_path)

interval = 2  # seconds
duration = int(clip.duration)

extracted_text = []
last_text = ""

# Similarity threshold (0-100) - higher means stricter matching
SIMILARITY_THRESHOLD = 90

for t in range(0, duration, interval):
    frame = clip.get_frame(t)
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(gray).strip()

    # Check similarity to last text
    similarity = fuzz.ratio(text, last_text)

    if text and similarity < SIMILARITY_THRESHOLD:
        print(f"[{t} sec] Unique Text:\n{text}\n{'-'*50}")
        extracted_text.append(f"[{t} sec]\n{text}\n")
        last_text = text

# Save to file
with open("video_text_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(extracted_text))

print("✅ Done! Duplicates removed with fuzzy matching.")