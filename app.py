from flask import Flask, render_template, request, redirect, session, send_file
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp"}
Session(app)

os.makedirs("static/uploads", exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def get_db():
    db = sqlite3.connect("neuranotes.db")
    db.row_factory = sqlite3.Row
    return db

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = ?", (session["user_id"],)).fetchall()
    goals = db.execute("SELECT * FROM goals WHERE user_id = ? AND completed = 0", (session["user_id"],)).fetchall()
    return render_template("index.html", subjects=subjects, goals=goals)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            return render_template("register.html", error="All fields required!")
        if password != confirmation:
            return render_template("register.html", error="Passwords do not match!")
        db = get_db()
        existing = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return render_template("register.html", error="Username already taken!")
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash))
        db.commit()
        return redirect("/login")
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
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

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
        study_data.append({
            "name": subject["name"],
            "color": subject["color"],
            "total_minutes": total["total"] or 0
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
