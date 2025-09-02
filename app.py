import os
import uuid
import platform
import subprocess
import sqlite3
import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import whisper
from fpdf import FPDF
from email.message import EmailMessage
import smtplib
from actionbulletpoints import summarize_text  # Your summarizer

app = Flask(__name__)
app.secret_key = "super-secret-key"

DB_NAME = "users.db"
recording_process = None

# Google OAuth settings
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = "credentials.json"

# ---------------------- DB Setup ----------------------
def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
        conn.commit()
        conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# -------------------- Whisper Setup --------------------
print("[INFO] Loading Whisper model...")
whisper_model = whisper.load_model("base")
print("[SUCCESS] Whisper model loaded.")


def ffmpeg_audio_command(output_path):
    if platform.system() == "Windows":
        mic_name = "Microphone Array (2- Realtek(R) Audio)"
        stereo_name = "Stereo Mix (2- Realtek(R) Audio)"
        
        return [
            "ffmpeg", "-y",
            "-f", "dshow", "-i", f"audio={mic_name}",
            "-f", "dshow", "-i", f"audio={stereo_name}",
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest",
            "-ar", "16000", "-ac", "1",
            output_path
        ]
    else:
        raise RuntimeError("Only Windows supported.")


def transcribe_wav(wav_path):
    result = whisper_model.transcribe(wav_path, fp16=False)
    return result.get("text", "").strip()

def generate_pdf(meet_link, transcript, bullet_points, path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Meeting Summary", ln=True)
    if meet_link:
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 8, f"Meeting Link: {meet_link}")
    pdf.multi_cell(0, 8, "\nTranscript:\n" + transcript)
    pdf.multi_cell(0, 8, "\nBullet Points:")
    for point in bullet_points:
        pdf.multi_cell(0, 8, f"- {point}")
    pdf.output(path)

def send_email_function(to_email, pdf_path):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "gg607158@gmail.com"    # <-- Replace
    SMTP_PASSWORD = "rstpgneomxuvhyzu"       # <-- Replace

    msg = EmailMessage()
    msg["Subject"] = "Meeting Summary PDF"
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email
    msg.set_content("Please find the attached meeting summary PDF.")

    with open(pdf_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(pdf_path)
    msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

def credentials_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

# ---------------------- Routes ----------------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        if not email.endswith("@gmail.com"):
            flash("Only Gmail addresses allowed.", "danger")
            return render_template("register.html")
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            flash("Registered successfully! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user:
            session.clear()  # clear old session data
            session["user"] = email
            # Optionally clear meeting-related session data
            session.pop("meet_link", None)
            session.pop("transcript", None)
            session.pop("pdf_file", None)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")
        
        

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    flash("Google account connected successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    global recording_process
    if "user" not in session:
        return redirect(url_for("login"))

    transcript = None
    bullet_points = None
    pdf_filename = None
    meet_link = session.get("meet_link")

    if request.method == "POST":
        action = request.form.get("action")

        # Meeting recorder actions
        if action == "join":
            meet_link = request.form.get("meet_link")
            session["meet_link"] = meet_link
            wav_path = os.path.join(os.getenv("TEMP", "/tmp"), f"meeting_{uuid.uuid4()}.wav")
            session["wav_path"] = wav_path
            command = ffmpeg_audio_command(wav_path)
            recording_process = subprocess.Popen(command)
            flash("Recording started.", "success")
            return redirect(url_for("dashboard"))

        elif action == "stop":
            if recording_process:
                recording_process.terminate()
                recording_process = None
            wav_path = session.get("wav_path")
            if wav_path and os.path.exists(wav_path):
                transcript = transcribe_wav(wav_path)
                bullet_points = summarize_text(transcript)
                pdf_filename = f"summary_{uuid.uuid4().hex}.pdf"
                pdf_path = os.path.join("static", pdf_filename)
                os.makedirs("static", exist_ok=True)
                generate_pdf(meet_link, transcript, bullet_points, pdf_path)
                flash("Recording stopped and summary generated.", "success")
            session["transcript"] = transcript
            session["bullet_points"] = bullet_points
            session["pdf_filename"] = pdf_filename

    # Show stored transcript etc.
    transcript = session.get("transcript")
    bullet_points = session.get("bullet_points")
    pdf_filename = session.get("pdf_filename")

    return render_template(
        "dashboard.html",
        user=session["user"],
        meet_link=meet_link,
        transcript=transcript,
        bullet_points=bullet_points,
        pdf_file=pdf_filename
    )

@app.route("/send_email", methods=["POST"])
def send_email():
    if "user" not in session:
        return redirect(url_for("login"))
    pdf_file = request.form.get("pdf_file")
    if not pdf_file:
        flash("No PDF file to send.", "danger")
        return redirect(url_for("dashboard"))

    pdf_path = os.path.join("static", pdf_file)
    to_email = session["user"]  # send to logged-in user's email

    try:
        send_email_function(to_email, pdf_path)
        flash("Email sent successfully!", "success")
    except Exception as e:
        flash(f"Failed to send email: {e}", "danger")

    return redirect(url_for("dashboard"))

@app.route("/create_meeting", methods=["POST"])
def create_meeting():
    if "user" not in session:
        return redirect(url_for("login"))

    if "credentials" not in session:
        return redirect(url_for("authorize"))

    start_dt_str = request.form.get("start_datetime")
    end_dt_str = request.form.get("end_datetime")

    try:
        start_dt = datetime.datetime.fromisoformat(start_dt_str)
        end_dt = datetime.datetime.fromisoformat(end_dt_str)

        creds = Credentials(**session["credentials"])
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": f"Google Meet by {session['user']}",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created_event = service.events().insert(
            calendarId="primary", body=event, conferenceDataVersion=1
        ).execute()

        meet_link = created_event.get("hangoutLink")
        session["meet_link"] = meet_link
        flash("Google Meet created successfully!", "success")

    except Exception as e:
        flash(f"Failed to create meeting: {e}", "danger")

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for local testing!
    app.run(debug=True)
