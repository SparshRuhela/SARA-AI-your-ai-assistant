Sarah AI – Smarter, Faster Personal Assistant

Sarah AI is a multilingual personal assistant with a clean GUI, powered by Google Gemini API, gTTS, and Speech Recognition.
It supports voice + text input, speaks back in your chosen language, and is lightweight enough to run on any computer.

✨ Features

🎤 Voice & Text Input – talk or type with Sarah
🗣️ Text-to-Speech Output – Sarah replies with voice in your chosen language
🌍 Multilingual Support – input in one language, output in another
🧠 Powered by Gemini AI – smarter & more natural responses
🖥️ GUI Interface – easy-to-use chat window
🔊 Real-time Speech Recognition – Sarah listens & responds instantly

🛠️ Tech Stack
Python 3.8+
Tkinter – GUI
Google Gemini API – AI intelligence
gTTS – Speech synthesis
SpeechRecognition + PyAudio – Voice input

📂 Project Structure
SaraAI/
│── sara.py              # Main application
│── requirements.txt     # Dependencies
│── README.md            # Documentation
│── assets/              # (Optional) icons, backgrounds, audio

⚙️ Installation
Clone this repository
.
git clone (https://github.com/SparshRuhela/SARA-AI-your-ai-assistant.git)
cd SarahAI
.
Create virtual environment (recommended)
.
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac/Linux
.
Install dependencies
pip install -r requirements.txt
.
Set up Gemini API key
Get your key from Google AI Studio
.
Save it in environment variables:
setx GOOGLE_API_KEY "your_api_key_here"     # Windows
export GOOGLE_API_KEY="your_api_key_here"   # Mac/Linux

▶️ Run Sarah
python sara.py
Select input language (what you’ll speak/type in).
Select output language (Sarah’s reply language).
Type or click Speak to Sarah to start.

📖 Example Usage
English to English
You: What is Newton’s first law?
Sarah: Newton’s first law states that an object...
English to Hindi
You: Translate "Good Morning" in Hindi
Sarah: शुभ प्रभात

🧩 requirements.txt
Example dependencies:
google-generativeai
gTTS
SpeechRecognition
pyaudio
(tkinter is built-in with Python, no need to install separately.)

🔮 Future Enhancements
Offline mode (speech + AI)
Android app version
Reminders & scheduling
Camera-based AI features

🤝 Contributing
Pull requests are welcome! For big changes, open an issue first to discuss ideas.

📜 License
MIT License © 2025
