📘 How to Run the Video Transcripto Project

Follow the steps below to set up and run the project on your system:

🔧 1. Install Python (if not already installed)
- Make sure Python 3.8 or above is installed on your system.
- You can download it from: https://www.python.org/downloads/

📁 2. Extract the Project Folder
- Unzip the folder you received.
- Open the extracted folder in a terminal or command prompt.

💡 3. Create a Virtual Environment (Recommended)
Run the following command in the terminal:
    python -m venv venv

🟢 4. Activate the Virtual Environment
- For Windows:
    venv\Scripts\activate
- For Mac/Linux:
    source venv/bin/activate

📦 5. Install All Required Libraries
Run this command to install all dependencies:
    pip install -r requirements.txt

🧠 6. Download Extra Language Models (only once)
Run these two commands:
    python -m spacy download en_core_web_sm
    (then enter Python shell by typing `python` and run:)
        >>> import nltk
        >>> nltk.download('wordnet')

🚀 7. Start the Web App
Run this command in the terminal:
    python app.py

🌐 8. Open in Browser
- Once the app is running, open your browser and go to:
    http://127.0.0.1:5000

📋 Now you can upload a video and see the full analysis, subtitles, emotions, and more.

📁 Files inside:
- app.py → main Python backend
- templates/frontUI.html → UI layout
- static/ → CSS and JS files
- requirements.txt → dependencies
- This instruction file

✅ That’s it! You’re ready to run the project.
