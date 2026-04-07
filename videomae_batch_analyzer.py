from transformers import VideoMAEFeatureExtractor, VideoMAEForVideoClassification
import cv2
import torch
from datetime import timedelta

# 🔧 Load pretrained model and feature extractor
feature_extractor = VideoMAEFeatureExtractor.from_pretrained("MCG-NJU/videomae-base-finetuned-kinetics")
model = VideoMAEForVideoClassification.from_pretrained("MCG-NJU/videomae-base-finetuned-kinetics")
model.eval()

# 🎯 Simple action-to-sentiment mapping
action_sentiment = {
    "hugging": "Positive",
    "fighting": "Negative",
    "crying": "Negative",
    "dancing": "Positive",
    "running": "Neutral",
    "walking": "Neutral",
    "clapping": "Positive",
    "shooting": "Negative",
    "punching person": "Negative",
    "smiling": "Positive"
}

# 🔍 Extract N frames between start_sec and end_sec
def extract_frames_chunk(cap, start_sec, end_sec, num_frames=16):
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)
    interval = max((end_frame - start_frame) // num_frames, 1)

    frames = []
    for i in range(num_frames):
        frame_id = start_frame + i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        success, frame = cap.read()
        if success:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(rgb)
    return frames

# 🚀 Main function to analyze full video in chunks
def analyze_video_chunks(video_path, chunk_duration=10):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    results = []
    start = 0

    while start < duration:
        end = min(start + chunk_duration, duration)
        frames = extract_frames_chunk(cap, start, end)

        if len(frames) == 16:
            inputs = feature_extractor(frames, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
            predicted_class = outputs.logits.argmax(-1).item()
            label = model.config.id2label[predicted_class]

            sentiment = action_sentiment.get(label.lower(), "Neutral")
            start_time = str(timedelta(seconds=int(start)))[:-3]
            end_time = str(timedelta(seconds=int(end)))[:-3]

            results.append({
                "start": start_time,
                "end": end_time,
                "action": label,
                "sentiment": sentiment
            })

        start += chunk_duration

    cap.release()
    return results
