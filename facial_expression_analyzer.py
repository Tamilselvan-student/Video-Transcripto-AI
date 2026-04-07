import cv2
from deepface import DeepFace
from datetime import timedelta

# Map DeepFace emotion to sentiment
emotion_to_sentiment = {
    "angry": "Negative",
    "disgust": "Negative",
    "fear": "Negative",
    "sad": "Negative",
    "happy": "Positive",
    "surprise": "Positive",
    "neutral": "Neutral"
}

def format_time(seconds):
    return str(timedelta(seconds=int(seconds))).zfill(8)


def analyze_facial_emotions(video_path, sample_rate=1):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = int(frame_count / fps)

    results = []

    for sec in range(0, duration, sample_rate):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        success, frame = cap.read()
        if not success:
            continue

        try:
            analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)[0]
            emotion = analysis['dominant_emotion']
            sentiment = emotion_to_sentiment.get(emotion.lower(), "Neutral")

            results.append({
                "start": format_time(sec),
                "end": format_time(sec + sample_rate),
                "expression": emotion,
                "sentiment": sentiment
            })

        except Exception as e:
            print(f"⚠️ DeepFace failed at {sec}s:", str(e))

    cap.release()
    return results
