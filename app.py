from flask import Flask, render_template, request, redirect, session, send_file
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import sqlite3
import os
import io
import re
import random
import smtplib
import requests
import html as html_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp"}
Session(app)

os.makedirs("static/uploads", exist_ok=True)

# ===== NEXA CHATBOT CONFIG =====
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-20b"
CHAT_DAILY_LIMIT = 20

NEXA_SYSTEM_PROMPT = (
    "You are Nexa, the friendly AI study assistant built into NeuraNotes, "
    "a student productivity app with subjects, notes, goals, a Pomodoro timer, "
    "flashcards, and study analytics. Help users study effectively: explain "
    "concepts clearly, suggest how to use NeuraNotes features (like the "
    "Pomodoro timer or flashcards), help summarize or organize study material, "
    "and give encouraging, practical study advice. Keep answers concise and "
    "friendly. If asked something completely unrelated to studying or the app, "
    "you can still help, but gently steer back to being a helpful study companion.\n\n"
    "FORMATTING RULES: You are replying inside a small chat widget (about 300px "
    "wide), not a document. Never use markdown tables, headings (#), or horizontal "
    "rules. Do not use markdown at all except **bold** for emphasis and '- ' for "
    "short bullet lists when truly needed. Never use LaTeX or math notation like "
    "\\(x\\), \\[...\\], or $...$ — this widget cannot render it. Write all math "
    "in plain text instead, e.g. 'y = mx + b' or 'x^2 + 3x - 7 = 11', using normal "
    "characters only. Prefer short plain-text paragraphs. Keep responses brief — "
    "a few sentences unless the user asks for more detail."
)

# ===== YOUTUBE-TO-NOTES CONFIG =====
YOUTUBE_NOTES_SYSTEM_PROMPT = (
    "You are an expert study-notes writer. You will be given either the transcript "
    "of a YouTube video, or (when no transcript/captions are available) the video's "
    "description. Convert whichever you are given into clear, well-organized study "
    "notes. Use '## ' followed by a short heading for each key topic/segment, and "
    "under each heading write 3 to 6 short '- ' bullet points summarizing the "
    "important points in your own words. Do not use tables, numbered lists, or "
    "LaTeX. Do not include an introduction like 'Here are the notes' — start "
    "directly with the first '## ' heading. If you were given a video description "
    "instead of a transcript, present the notes as an overview of the video's "
    "topic and content, not as a summary of spoken dialogue."
)

# ===== EMAIL VERIFICATION CONFIG =====
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

def is_valid_email_format(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def generate_code():
    return ''.join(random.choices('0123456789', k=6))


def send_verification_email(to_email, code):
    plain_body = (
        f"Welcome to NeuraNotes!\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )

    html_body = f"""\
<html>
  <body style="margin:0; padding:0; background-color:#201A22; font-family: 'Segoe UI', Arial, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#201A22; padding: 40px 20px;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0"
                 style="background-color:#362A39; border:1px solid #5C4B60; border-radius:18px; overflow:hidden;">

            <!-- Header -->
            <tr>
              <td align="center" style="padding: 44px 30px 26px; border-bottom: 1px solid #5C4B60;">
                <div style="font-size:26px; font-weight:800; letter-spacing:0.3px;">
                  <span style="color:#F5F1F6;">Neura</span><span style="color:#D8AEDC;">Notes</span>
                </div>
                <div style="margin-top:8px; font-size:12.5px; color:#8a7a90; letter-spacing:1.5px; text-transform:uppercase;">
                  Your Smart Study Companion
                </div>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding: 32px 40px 10px;">
                <p style="color:#F5F1F6; font-size:17px; margin:0 0 8px;">Hi there,</p>
                <p style="color:#C9B9D1; font-size:14.5px; line-height:1.6; margin:0 0 24px;">
                  Thanks for signing up for NeuraNotes! We're excited to have you on board.
                  Use the verification code below to activate your account.
                </p>
              </td>
            </tr>

            <!-- Code box -->
            <tr>
              <td align="center" style="padding: 0 40px 24px;">
                <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                  <tr>
                    <td align="center" style="background-color:#201A22; border:1px solid #5C4B60;
                               border-radius:12px; padding: 22px;">
                      <span style="font-size:32px; font-weight:700; letter-spacing:10px; color:#D8AEDC;">
                        {code}
                      </span>
                    </td>
                  </tr>
                </table>
                <p style="color:#8a7a90; font-size:12.5px; margin:14px 0 0;">
                  This code expires in 15 minutes.
                </p>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="padding: 20px 40px 32px; border-top:1px solid #5C4B60;">
                <p style="color:#8a7a90; font-size:12px; line-height:1.6; margin:16px 0 0;">
                  If you didn't request this, you can safely ignore this email.
                </p>
                <p style="color:#5C4B60; font-size:11.5px; margin:18px 0 0; text-align:center;">
                  NeuraNotes &middot; Your smart study companion
                </p>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your NeuraNotes account"
    msg["From"] = "NeuraNotes <{}>".format(MAIL_USERNAME)
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, to_email, msg.as_string())
        return True
    except Exception as e:
        print("Email send error:", e)
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def get_db():
    db = sqlite3.connect("neuranotes.db")
    db.row_factory = sqlite3.Row
    return db


def init_youtube_notes_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS youtube_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_title TEXT,
            video_url TEXT,
            video_id TEXT,
            content TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migration for databases created before the 'source' column existed
    try:
        db.execute("ALTER TABLE youtube_notes ADD COLUMN source TEXT")
    except sqlite3.OperationalError:
        pass
    db.commit()
    db.close()


init_youtube_notes_table()


@app.route("/api/chat", methods=["POST"])
def nexa_chat():
    if "user_id" not in session:
        return {"error": "Please log in to chat with Nexa."}, 401

    user_message = (request.json.get("message") or "").strip() if request.is_json else ""
    if not user_message:
        return {"error": "Message cannot be empty."}, 400

    db = get_db()
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    # Reset the daily counter if the last reset was more than 24 hours ago
    now = datetime.now()
    last_reset = user["chat_reset_at"]
    needs_reset = True
    if last_reset:
        try:
            last_reset_dt = datetime.fromisoformat(last_reset)
            needs_reset = (now - last_reset_dt).total_seconds() >= 86400
        except ValueError:
            needs_reset = True

    if needs_reset:
        db.execute("UPDATE users SET chat_count = 0, chat_reset_at = ? WHERE id = ?",
                   (now.isoformat(), user_id))
        db.commit()
        chat_count = 0
        last_reset = now.isoformat()
    else:
        chat_count = user["chat_count"] or 0

    if chat_count >= CHAT_DAILY_LIMIT:
        return {
            "error": f"You've used all {CHAT_DAILY_LIMIT} free messages with Nexa for today. "
                     f"Your limit resets in a bit — come back soon!"
        }, 429

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": NEXA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()
        if not reply:
            reply = "Sorry, I couldn't come up with a response. Try asking again?"
    except Exception as e:
        print("Nexa API error:", e)
        return {"error": "Nexa is having trouble responding right now. Please try again shortly."}, 500

    db.execute("UPDATE users SET chat_count = chat_count + 1 WHERE id = ?", (user_id,))
    db.commit()

    return {"reply": reply, "remaining": CHAT_DAILY_LIMIT - (chat_count + 1)}


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = ?", (session["user_id"],)).fetchall()
    goals = db.execute("SELECT * FROM goals WHERE user_id = ? AND completed = 0", (session["user_id"],)).fetchall()
    raw_name = session.get("username", "")
    name_part = raw_name.split("@")[0]
    display_name = re.match(r"[A-Za-z]+", name_part)
    display_name = display_name.group(0) if display_name else name_part
    return render_template("index.html", subjects=subjects, goals=goals, display_name=display_name)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            return render_template("register.html", error="All fields required!")
        if not is_valid_email_format(username):
            return render_template("register.html", error="Please enter a valid email address!")
        if password != confirmation:
            return render_template("register.html", error="Passwords do not match!")
        db = get_db()
        existing = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return render_template("register.html", error="Username already taken!")
        hash = generate_password_hash(password)
        code = generate_code()
        db.execute(
            "INSERT INTO users (username, password, verified, verification_code, code_created_at) VALUES (?, ?, 0, ?, ?)",
            (username, hash, code, datetime.now().isoformat())
        )
        db.commit()
        sent = send_verification_email(username, code)
        if not sent:
            return render_template("register.html", error="Could not send verification email. Please check the address and try again.")
        return redirect(f"/verify?email={username}")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not check_password_hash(user["password"], password):
            return render_template("login.html", error="Invalid username or password!")
        if not user["verified"]:
            return redirect(f"/verify?email={username}")
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return render_template("login.html")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = request.args.get("email") or request.form.get("email")
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (email,)).fetchone()
        if not user:
            return render_template("verify.html", email=email, error="Account not found.")
        if user["verified"]:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        if not user["verification_code"] or code != user["verification_code"]:
            return render_template("verify.html", email=email, error="Incorrect code. Please try again.")
        created_at = datetime.fromisoformat(user["code_created_at"])
        if (datetime.now() - created_at).total_seconds() > 900:
            return render_template("verify.html", email=email, error="Code expired. Please request a new one.")
        db.execute("UPDATE users SET verified = 1, verification_code = NULL WHERE id = ?", (user["id"],))
        db.commit()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return render_template("verify.html", email=email)


@app.route("/resend-code", methods=["POST"])
def resend_code():
    email = request.form.get("email")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (email,)).fetchone()
    if not user:
        return render_template("verify.html", email=email, error="Account not found.")
    if user["verified"]:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    code = generate_code()
    db.execute("UPDATE users SET verification_code = ?, code_created_at = ? WHERE id = ?",
               (code, datetime.now().isoformat(), user["id"]))
    db.commit()
    sent = send_verification_email(email, code)
    if not sent:
        return render_template("verify.html", email=email, error="Could not resend email. Try again later.")
    return render_template("verify.html", email=email, message="A new code has been sent to your email.")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/account/delete")
def delete_account():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()

    subject_ids = [row["id"] for row in db.execute(
        "SELECT id FROM subjects WHERE user_id = ?", (user_id,)
    ).fetchall()]

    for sid in subject_ids:
        db.execute("DELETE FROM notes WHERE subject_id = ?", (sid,))
        db.execute("DELETE FROM study_sessions WHERE subject_id = ?", (sid,))
        db.execute("DELETE FROM flashcards WHERE subject_id = ?", (sid,))

    db.execute("DELETE FROM subjects WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM goals WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM flashcard_results WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM youtube_notes WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    session.clear()
    return redirect("/register")

@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name")
        color = request.form.get("color")
        total_topics = request.form.get("total_topics")
        db.execute("INSERT INTO subjects (user_id, name, color, total_topics) VALUES (?, ?, ?, ?)",
                   (session["user_id"], name, color, total_topics))
        db.commit()
        return redirect("/")
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = ?", (session["user_id"],)).fetchall()
    return render_template("subjects.html", subjects=subjects)

@app.route("/subject/delete/<int:subject_id>")
def delete_subject(subject_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    db.execute("DELETE FROM notes WHERE subject_id = ?", (subject_id,))
    db.execute("DELETE FROM study_sessions WHERE subject_id = ?", (subject_id,))
    db.execute("DELETE FROM flashcards WHERE subject_id = ?", (subject_id,))
    db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    db.commit()
    return redirect("/subjects")

@app.route("/notes/<int:subject_id>", methods=["GET", "POST"])
def notes(subject_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_filename = filename
        db.execute("INSERT INTO notes (subject_id, title, content, image) VALUES (?, ?, ?, ?)",
                   (subject_id, title, content, image_filename))
        db.commit()
    search = request.args.get("search", "")
    subject = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    if search:
        notes = db.execute("SELECT * FROM notes WHERE subject_id = ? AND title LIKE ? ORDER BY created_at DESC",
                          (subject_id, f"%{search}%")).fetchall()
    else:
        notes = db.execute("SELECT * FROM notes WHERE subject_id = ? ORDER BY created_at DESC",
                          (subject_id,)).fetchall()
    return render_template("notes.html", subject=subject, notes=notes, search=search)

@app.route("/note/<int:note_id>")
def view_note(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        return redirect("/")
    return render_template("note_view.html", note=note)

@app.route("/note/delete/<int:note_id>")
def delete_note(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note and note["image"]:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], note["image"])
        if os.path.exists(image_path):
            os.remove(image_path)
    subject_id = note["subject_id"]
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    return redirect(f"/notes/{subject_id}")

@app.route("/note/export/<int:note_id>")
def export_note_pdf(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        return redirect("/")

    import base64
    from reportlab.platypus import Image as RLImage
    from PIL import Image as PILImage

    content = note["content"] if note["content"] else ""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(note["title"], styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Date: {note['created_at']}", styles["Normal"]))
    story.append(Spacer(1, 20))

    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
    parts = img_pattern.split(content)

    for i, part in enumerate(parts):
        if i % 2 == 0:
            clean = re.sub(r'<[^>]+>', ' ', part)
            clean = re.sub(r'\s+', ' ', clean).strip()
            clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&')
            clean = clean.replace('&lt;', '<').replace('&gt;', '>')
            clean = clean.replace('&quot;', '"')
            if clean:
                for line in clean.split('. '):
                    line = line.strip()
                    if line:
                        try:
                            story.append(Paragraph(line + '.', styles["Normal"]))
                            story.append(Spacer(1, 6))
                        except:
                            pass
        else:
            src = part
            try:
                if src.startswith('data:image'):
                    header, data = src.split(',', 1)
                    img_data = base64.b64decode(data)
                    img_buffer = io.BytesIO(img_data)
                    pil_img = PILImage.open(img_buffer)
                    img_buffer.seek(0)
                    max_width = 400
                    w, h = pil_img.size
                    ratio = h / w
                    pdf_width = min(max_width, w)
                    pdf_height = pdf_width * ratio
                    rl_img = RLImage(img_buffer, width=pdf_width, height=pdf_height)
                    story.append(rl_img)
                    story.append(Spacer(1, 10))
                elif src.startswith('/static/uploads/'):
                    img_path = os.path.join(os.getcwd(), src.lstrip('/'))
                    if os.path.exists(img_path):
                        pil_img = PILImage.open(img_path)
                        max_width = 400
                        w, h = pil_img.size
                        ratio = h / w
                        pdf_width = min(max_width, w)
                        pdf_height = pdf_width * ratio
                        rl_img = RLImage(img_path, width=pdf_width, height=pdf_height)
                        story.append(rl_img)
                        story.append(Spacer(1, 10))
            except:
                story.append(Paragraph("[Image could not be included]", styles["Normal"]))
                story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    safe_title = re.sub(r'[^\w\s-]', '', note['title']).strip()
    return send_file(buffer, as_attachment=True,
                    download_name=f"{safe_title}.pdf",
                    mimetype='application/pdf')

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title")
        target_hours = request.form.get("target_hours")
        deadline = request.form.get("deadline")
        db.execute("INSERT INTO goals (user_id, title, target_hours, deadline) VALUES (?, ?, ?, ?)",
                   (session["user_id"], title, target_hours, deadline))
        db.commit()
    goals = db.execute("SELECT * FROM goals WHERE user_id = ?", (session["user_id"],)).fetchall()
    return render_template("goals.html", goals=goals)

@app.route("/goal/complete/<int:goal_id>")
def complete_goal(goal_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    db.execute("UPDATE goals SET completed = 1 WHERE id = ?", (goal_id,))
    db.commit()
    return redirect("/goals")

@app.route("/study", methods=["POST"])
def study():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subject_id = request.form.get("subject_id")
    duration = request.form.get("duration")
    db.execute("INSERT INTO study_sessions (subject_id, duration_minutes) VALUES (?, ?)",
               (subject_id, duration))
    db.commit()
    return redirect("/")

@app.route("/update_progress/<int:subject_id>", methods=["POST"])
def update_progress(subject_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    completed_topics = request.form.get("completed_topics")
    db.execute("UPDATE subjects SET completed_topics = ? WHERE id = ?",
               (completed_topics, subject_id))
    db.commit()
    return redirect(f"/notes/{subject_id}")

@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = ?", (session["user_id"],)).fetchall()
    study_data = []
    for subject in subjects:
        total = db.execute("SELECT SUM(duration_minutes) as total FROM study_sessions WHERE subject_id = ?",
                          (subject["id"],)).fetchone()
        completed = subject["completed_topics"] or 0
        total_topics = subject["total_topics"] or 0
        progress = int((completed / total_topics) * 100) if total_topics > 0 else 0
        study_data.append({
            "name": subject["name"],
            "color": subject["color"],
            "total_minutes": total["total"] or 0,
            "completed_topics": completed,
            "total_topics": total_topics,
            "progress": progress
        })
    return render_template("analytics.html", study_data=study_data)

@app.route("/flashcards")
def flashcards():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = ?", (session["user_id"],)).fetchall()
    results = db.execute("""
        SELECT fr.*, s.name as subject_name
        FROM flashcard_results fr
        JOIN subjects s ON fr.subject_id = s.id
        WHERE fr.user_id = ?
        ORDER BY fr.date DESC
    """, (session["user_id"],)).fetchall()
    return render_template("flashcards.html", subjects=subjects, results=results)

@app.route("/flashcards/<int:subject_id>", methods=["GET", "POST"])
def flashcard_manage(subject_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    if request.method == "POST":
        question = request.form.get("question")
        answer = request.form.get("answer")
        difficulty = request.form.get("difficulty")
        db.execute("INSERT INTO flashcards (subject_id, question, answer, difficulty) VALUES (?, ?, ?, ?)",
                   (subject_id, question, answer, difficulty))
        db.commit()
    subject = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    easy = db.execute("SELECT * FROM flashcards WHERE subject_id = ? AND difficulty = 'easy'", (subject_id,)).fetchall()
    medium = db.execute("SELECT * FROM flashcards WHERE subject_id = ? AND difficulty = 'medium'", (subject_id,)).fetchall()
    hard = db.execute("SELECT * FROM flashcards WHERE subject_id = ? AND difficulty = 'hard'", (subject_id,)).fetchall()
    return render_template("flashcard_manage.html", subject=subject, easy=easy, medium=medium, hard=hard)

@app.route("/flashcard/delete/<int:card_id>")
def delete_flashcard(card_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    card = db.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    subject_id = card["subject_id"]
    db.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    db.commit()
    return redirect(f"/flashcards/{subject_id}")

@app.route("/flashcards/quiz/<int:subject_id>/<difficulty>")
def flashcard_quiz(subject_id, difficulty):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subject = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    cards = db.execute("SELECT * FROM flashcards WHERE subject_id = ? AND difficulty = ? LIMIT 20",
                      (subject_id, difficulty)).fetchall()
    cards = [dict(c) for c in cards]
    return render_template("flashcard_quiz.html", subject=subject, cards=cards, difficulty=difficulty)

@app.route("/flashcards/result", methods=["POST"])
def flashcard_result():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subject_id = request.form.get("subject_id")
    score = request.form.get("score")
    total = request.form.get("total")
    difficulty = request.form.get("difficulty")
    db.execute("INSERT INTO flashcard_results (user_id, subject_id, score, total, difficulty) VALUES (?, ?, ?, ?, ?)",
               (session["user_id"], subject_id, score, total, difficulty))
    db.commit()
    return redirect("/flashcards")

@app.route("/flashcard/result/delete/<int:result_id>")
def delete_flashcard_result(result_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    db.execute("DELETE FROM flashcard_results WHERE id = ?", (result_id,))
    db.commit()
    return redirect("/flashcards")


import fitz  # pymupdf


def extract_slide_from_page(page, page_num, pdf_filename):
    """
    Build a slide from a single PDF page.

    - Agar page mein readable text hai -> ek 'text' slide banti hai
      (title + bullet points), jo baad mein frontend par PowerPoint
      jaisi style ke sath dikhai/record ki jaati hai.
    - Agar page scanned/image-only hai (bohot kam ya koi text nahi) ->
      purane tareeke se page ka pixmap (screenshot) image ban kar
      fallback ke taur par use hota hai, taake koi bhi slide khaali na rahe.
    """
    raw_text = page.get_text("text").strip()

    if len(raw_text) < 30:
        mat = fitz.Matrix(2, 2)  # 2x zoom for quality
        pix = page.get_pixmap(matrix=mat)
        img_filename = f"slide_{pdf_filename}_{page_num}.png"
        img_path = os.path.join("static/uploads", img_filename)
        pix.save(img_path)
        return {"type": "image", "image": img_filename}

    lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
    title = lines[0][:80] if lines else f"Slide {page_num + 1}"
    body_lines = lines[1:] if len(lines) > 1 else []

    bullets = []
    for line in body_lines:
        if len(line) < 3:
            continue
        bullets.append(line[:150])
        if len(bullets) >= 8:
            break

    if not bullets:
        bullets = [title]
        title = f"Slide {page_num + 1}"

    return {"type": "text", "title": title, "bullets": bullets}


@app.route("/pdf_presentation/<int:subject_id>", methods=["GET", "POST"])
def pdf_presentation(subject_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subject = db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()

    if request.method == "POST":
        if 'pdf_file' not in request.files:
            return redirect(request.url)
        file = request.files['pdf_file']
        if file.filename == '':
            return redirect(request.url)
        if file and file.filename.endswith('.pdf'):
            # Save PDF
            pdf_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
            pdf_path = os.path.join("static/uploads", pdf_filename)
            file.save(pdf_path)

            # Convert PDF pages into slides: text-based (PowerPoint style)
            # by default, falling back to a rendered image for pages
            # without extractable text (e.g. scanned pages).
            doc = fitz.open(pdf_path)
            slides = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                slide = extract_slide_from_page(page, page_num, pdf_filename)
                slides.append(slide)
            doc.close()

            return render_template("pdf_presentation.html",
                                 subject=subject,
                                 slides=slides,
                                 subject_id=subject_id)

    return render_template("pdf_upload.html", subject=subject, subject_id=subject_id)


# ===== YOUTUBE TO NOTES FEATURE =====
# Requires: pip install youtube-transcript-api yt-dlp --break-system-packages
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp


def extract_youtube_id(url):
    """Various YouTube URL formats se 11-character video ID nikalta hai."""
    patterns = [
        r'(?:v=|\/embed\/|\/v\/|youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'\/shorts\/([0-9A-Za-z_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url or "")
        if m:
            return m.group(1)
    return None


def get_youtube_title(video_id):
    """YouTube ke oEmbed API se video ka title leta hai (koi API key nahi chahiye)."""
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=8,
        )
        r.raise_for_status()
        return r.json().get("title", "YouTube Video")
    except Exception:
        return "YouTube Video"


def vtt_to_text(vtt_content):
    """WebVTT caption file se sirf plain spoken text nikalta hai (timestamps/tags hata kar)."""
    lines = vtt_content.splitlines()
    text_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r'^\d+$', line):
            continue
        if '-->' in line:
            continue
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean and clean not in seen:
            text_lines.append(clean)
            seen.add(clean)
    return re.sub(r'\s+', ' ', ' '.join(text_lines)).strip()


def fetch_video_content(video_id):
    """
    Tiered fetch strategy so notes can be generated for almost any video:
      1. youtube-transcript-api (fastest, works when YouTube isn't blocking it)
      2. yt-dlp captions/auto-captions (more resilient, different fetch method)
      3. yt-dlp video description (fallback when no captions exist at all)

    Returns (text, title, source) where source is 'captions', 'description', or None.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Tier 1: youtube-transcript-api
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id)
        raw_data = fetched.to_raw_data()
        text = " ".join(item["text"] for item in raw_data)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) >= 30:
            return text, get_youtube_title(video_id), "captions"
    except Exception as e:
        print("youtube-transcript-api failed:", e)

    # Tier 2 & 3: yt-dlp (captions first, then description)
    title = None
    try:
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB", "en-orig"],
            "subtitlesformat": "vtt",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title") or get_youtube_title(video_id)
        description = (info.get("description") or "").strip()

        subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}

        sub_url = None
        for lang_map in (subs, auto_subs):
            for lang in ("en", "en-US", "en-GB", "en-orig"):
                if lang in lang_map:
                    entries = lang_map[lang]
                    vtt_entry = next((e for e in entries if e.get("ext") == "vtt"), entries[0])
                    sub_url = vtt_entry.get("url")
                    break
            if sub_url:
                break

        if sub_url:
            r = requests.get(sub_url, timeout=15)
            r.raise_for_status()
            text = vtt_to_text(r.text)
            if len(text) >= 30:
                return text, title, "captions"

        if len(description) >= 30:
            return description, title, "description"

    except Exception as e:
        print("yt-dlp fallback failed:", e)

    return "", title or get_youtube_title(video_id), None


def markdown_notes_to_html(text):
   
    lines = text.split('\n')
    html_parts = []
    in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        heading_match = re.match(r'^#{1,3}\s+(.*)', line)
        bullet_match = re.match(r'^[-*]\s+(.*)', line)

        if heading_match:
            content = heading_match.group(1).strip()
        elif bullet_match:
            content = bullet_match.group(1).strip()
        else:
            content = line

        escaped = html_lib.escape(content)
        escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)

        if heading_match:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<h3>{escaped}</h3>')
        elif bullet_match:
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
            html_parts.append(f'<li>{escaped}</li>')
        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<p>{escaped}</p>')

    if in_list:
        html_parts.append('</ul>')

    return '\n'.join(html_parts)


def generate_notes_from_transcript(transcript_text, video_title, source):
    """Groq API ko transcript/description bhej kar organized study notes generate karwata hai."""
    max_chars = 14000
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars] + "\n...[content truncated for length]"

    label = "Video description (no captions were available for this video)" if source == "description" else "Video transcript"
    user_prompt = f"Video title: {video_title}\n\n{label}:\n{transcript_text}"

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": YOUTUBE_NOTES_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


@app.route("/youtube_notes", methods=["GET", "POST"])
def youtube_notes():
    if "user_id" not in session:
        return redirect("/login")

    error = None
    generated = None

    if request.method == "POST":
        url = (request.form.get("youtube_url") or "").strip()
        video_id = extract_youtube_id(url)

        if not video_id:
            error = "That doesn't look like a valid YouTube link. Please check it and try again."
        else:
            try:
                transcript_text, video_title, source = fetch_video_content(video_id)

                if not transcript_text or len(transcript_text) < 30:
                    error = ("Couldn't find any captions or description for this video "
                              "to generate notes from. Please try a different video.")
                else:
                    raw_notes = generate_notes_from_transcript(transcript_text, video_title, source)
                    content_html = markdown_notes_to_html(raw_notes)

                    generated = {
                        "title": video_title,
                        "content": content_html,
                        "video_url": url,
                        "video_id": video_id,
                        "source": source,
                    }
            except Exception as e:
                print("YouTube notes error:", e)
                error = "Something went wrong while generating notes. Please try again."

    db = get_db()
    saved_notes = db.execute(
        "SELECT * FROM youtube_notes WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    return render_template("youtube_notes.html", saved_notes=saved_notes, error=error, generated=generated)


@app.route("/youtube_notes/save", methods=["POST"])
def save_youtube_note():
    if "user_id" not in session:
        return redirect("/login")

    title = (request.form.get("title") or "Untitled Video").strip()
    content = request.form.get("content") or ""
    video_url = request.form.get("video_url") or ""
    video_id = request.form.get("video_id") or ""
    source = request.form.get("source") or ""

    db = get_db()
    db.execute(
        "INSERT INTO youtube_notes (user_id, video_title, video_url, video_id, content, source) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], title, video_url, video_id, content, source)
    )
    db.commit()
    return redirect("/youtube_notes")


@app.route("/youtube_notes/view/<int:note_id>")
def view_youtube_note(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    note = db.execute(
        "SELECT * FROM youtube_notes WHERE id = ? AND user_id = ?",
        (note_id, session["user_id"])
    ).fetchone()
    if not note:
        return redirect("/youtube_notes")
    return render_template("youtube_note_view.html", note=note)


@app.route("/youtube_notes/edit/<int:note_id>", methods=["POST"])
def edit_youtube_note(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    note = db.execute(
        "SELECT * FROM youtube_notes WHERE id = ? AND user_id = ?",
        (note_id, session["user_id"])
    ).fetchone()
    if not note:
        return redirect("/youtube_notes")

    title = (request.form.get("title") or note["video_title"]).strip()
    content = request.form.get("content") or note["content"]

    db.execute(
        "UPDATE youtube_notes SET video_title = ?, content = ? WHERE id = ?",
        (title, content, note_id)
    )
    db.commit()
    return redirect(f"/youtube_notes/view/{note_id}")


@app.route("/youtube_notes/delete/<int:note_id>")
def delete_youtube_note(note_id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    db.execute("DELETE FROM youtube_notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"]))
    db.commit()
    return redirect("/youtube_notes")


if __name__ == "__main__":
    app.run(debug=True)