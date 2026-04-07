from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, session
from flask_cors import CORS
from moviepy.editor import VideoFileClip
import whisper
import os
import uuid
import json
from textblob import TextBlob
from datetime import timedelta
import spacy
from dotenv import load_dotenv
from noun_classifier import categorize_nouns_single_line
from facial_expression_analyzer import analyze_facial_emotions

load_dotenv()  # Load variables from .env file


# Flask setup
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_dev_key_change_this')
CORS(app)

model = whisper.load_model("base")

UPLOAD_FOLDER = "uploads"
USERS_FILE = "users.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ AUTH ROUTES ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        else:
            users = {}

        if username not in users:
            return render_template("login.html", error="Username not found")

        user_data = users[username]
        stored_password = user_data["password"] if isinstance(user_data, dict) else user_data

        if password != stored_password:
            return render_template("login.html", error="Incorrect password")

        session["user"] = username
        return redirect("/home")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        else:
            users = {}

        if username in users:
            return render_template("register.html", error="Username already exists")

        users[username] = {
            "email": email,
            "password": password
        }

        with open(USERS_FILE, "w") as f:
            json.dump(users, f)

        return redirect("/")
    return render_template("register.html")


@app.route("/home")
def index():
    if "user" not in session:
        return redirect("/")
    return render_template("frontUI.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ------------------ UPLOAD & PROCESS ------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files["file"]
        video_id = str(uuid.uuid4())
        video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp4")
        audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.mp3")
        file.save(video_path)

        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path)
        video_duration = clip.duration  # in seconds

        result = model.transcribe(audio_path)

        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds - int(seconds)) * 1000)
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        # Save SRT
        srt_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result["segments"]):
                start = format_time(seg["start"])
                end = format_time(seg["end"])
                categorized = categorize_nouns_single_line(seg['text'].strip())
                f.write(f"{i+1}\n{start} --> {end}\n{categorized}\n\n")

        # Save VTT
        # Save VTT with original dialogue
        vtt_path = os.path.join(UPLOAD_FOLDER, f"{video_id}.vtt")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for seg in result["segments"]:
                start = format_time(seg["start"]).replace(",", ".")
                end = format_time(seg["end"]).replace(",", ".")
                actual_dialogue = seg['text'].strip()
                f.write(f"{start} --> {end}\n{actual_dialogue}\n\n")

        # Dialogue-based Sentiment
        segments = result["segments"]
        intervals = []
        start = 0
        while start < video_duration:
            end = min(start + 60, video_duration)
            intervals.append((start, end))
            start = end

        sentiment_table = []
        for start_sec, end_sec in intervals:
            combined_text = " ".join(
                seg["text"].strip()
                for seg in segments
                if seg["start"] >= start_sec and seg["start"] < end_sec
            )

            sentiment = TextBlob(combined_text).sentiment
            score = sentiment.polarity
            label = (
                "Positive" if score > 0.2 else
                "Negative" if score < -0.2 else
                "Neutral"
            )

            start_time = f"{int(start_sec//60):02}:{int(start_sec%60):02}"
            end_time = f"{int(end_sec//60):02}:{int(end_sec%60):02}"


            sentiment_table.append({
                "minute": f"{start_time} - {end_time}",
                "dialogues": combined_text if combined_text else "(no speech)",
                "sentiment": label,
                "score": round(score, 3)
            })

        # ✅ Safe action-based sentiment detection
        try:
            action_sentiment_table = analyze_facial_emotions(video_path)
            print("🎬 Action sentiment output:", action_sentiment_table)
        except Exception as e:
            print("⚠️ Action sentiment failed:", str(e))
            action_sentiment_table = []

        # ✅ Final response
        # ✅ 10-sec Combined Sentiment + Noun Chunk Table
        interval_data = []
        for start_sec in range(0, int(video_duration), 10):
            end_sec = min(start_sec + 10, int(video_duration))

            # 1. Text: gather dialogues in this 10s block
            block_segments = [seg for seg in segments if start_sec <= seg["start"] < end_sec]
            combined_text = " ".join(seg["text"].strip() for seg in block_segments)
            text_sentiment_score = TextBlob(combined_text).sentiment.polarity if combined_text else 0.0
            text_sentiment_label = (
                "Positive" if text_sentiment_score > 0.2 else
                "Negative" if text_sentiment_score < -0.2 else
                "Neutral"
            )

            # 2. Expression: gather facial expression outputs in this 10s range
            def time_to_sec(t):
                    h, m, s = map(int, t.split(":"))
                    return h * 3600 + m * 60 + s

            chunk_expressions = [
                item for item in action_sentiment_table 
                if start_sec <= time_to_sec(item["start"]) < end_sec
            ]


            expressions = [item["expression"] for item in chunk_expressions]
            expression_sentiments = [
                1 if item["sentiment"] == "Positive" else
                -1 if item["sentiment"] == "Negative" else 0
                for item in chunk_expressions
            ]
            if expressions:
                from collections import Counter
                most_common_expression = Counter(expressions).most_common(1)[0][0]
                avg_expression_score = round(sum(expression_sentiments)/len(expression_sentiments), 2)
                expression_sentiment_label = (
                    "Positive" if avg_expression_score > 0.2 else
                    "Negative" if avg_expression_score < -0.2 else
                    "Neutral"
                )
            else:
                most_common_expression = "N/A"
                avg_expression_score = 0.0
                expression_sentiment_label = "Neutral"

            # 3. Categorize nouns in that 10s
            categorized = categorize_nouns_single_line(combined_text)
            parts = {
                "People": "", "Places": "", "Characters": "", "Things": "", "Animals": "", "Others": ""
            }

            for part in categorized.split(", "):
              if " - " in part:
                   label, content = part.split(" - ", 1)
                   if label in parts:
                       parts[label] = content
            def format_hms(seconds):
                return str(timedelta(seconds=int(seconds))).zfill(8)
            
            interval_data.append({
                "start": format_hms(start_sec),
                "end": format_hms(end_sec),
                "expression": most_common_expression,
                "expression_sentiment": expression_sentiment_label,
                "dialogue_sentiment": text_sentiment_label,
                "people": parts["People"],
                "places": parts["Places"],
                "characters": parts["Characters"],
                "things": parts["Things"],
                "animals": parts["Animals"],
                "others": parts["Others"]
            })

        # ✅ Final response
        response = {
            "transcript": categorize_nouns_single_line(result["text"]),
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": categorize_nouns_single_line(seg["text"].strip())
                }
                for seg in result["segments"]
            ],
            "sentiment_table": sentiment_table,
            "action_sentiment_table": action_sentiment_table,
            "chunk_analysis_table": interval_data,  # ⬅️ NEW CHUNK DATA
            "srt_url": f"/download/{video_id}.srt",
            "vtt_url": f"/video/{video_id}.vtt"
        }


        print("✅ Success response:", response)
        return jsonify(response)

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


# ------------------ FILE SERVE ------------------

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/video/<filename>")
def serve_video(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(debug=True)
