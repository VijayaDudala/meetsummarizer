# MeetSummarizer – AI-Powered Meeting Summaries 🎤📝

MeetSummarizer is an **AI-driven tool** that transcribes meeting conversations and generates **concise summaries with action items**.  
Built during my internship, this project combines **speech-to-text** with **LLM-powered summarization** to make meetings more productive.

---

## 🚀 Features
- 🎙️ **Speech-to-Text** – Converts meeting audio into transcripts using **Whisper ASR**.  
- 🧠 **Smart Summaries** – Uses **LLMs (Gemini/GPT)** for abstractive summarization.  
- ⚡ **Flask Backend** – Lightweight API to process audio and return results.  
- 💾 **Database Integration** – Stores transcripts and summaries for later reference.  
- 🌐 **Web Interface** – Simple frontend to upload audio and view summaries.  

---

## 🛠️ Tech Stack
- **Programming Language**: Python  
- **Backend**: Flask  
- **NLP Models**: Whisper ASR, Gemini/GPT  
- **Database**: SQLite (local)  
- **Frontend**: HTML, CSS, JavaScript  

---

## 📂 Project Structure
MeetSummarizer/
│── app.py # Main Flask application
│── actionbulletpoints.py # Summary + Action extraction logic
│── static/ # CSS, JS files
│── templates/ # HTML templates
│── requirements.txt # Python dependencies
│── .gitignore # Ignored files (venv, db, credentials.json)



---

## ⚙️ Installation & Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/VijayaDudala/meetsummarizer.git
   cd meetsummarizer
Create a virtual environment:
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows


Install dependencies:
pip install -r requirements.txt

Run the Flask app:
python app.py

Open in browser:
http://127.0.0.1:5000
🔐 Environment Variables

Create a .env file and add your API keys (instead of pushing credentials.json):
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
The project uses python-dotenv to load these securely.

