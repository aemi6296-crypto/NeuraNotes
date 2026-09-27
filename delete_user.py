import sqlite3

# Change this to the exact username/email you want to delete
TARGET_USERNAME = "aimanaliiii2121@gmail.com"

db = sqlite3.connect("neuranotes.db")
db.row_factory = sqlite3.Row

user = db.execute("SELECT * FROM users WHERE username = ?", (TARGET_USERNAME,)).fetchone()

if not user:
    print(f"No user found with username: {TARGET_USERNAME}")
else:
    user_id = user["id"]
    print(f"Found user id={user_id}, deleting all related data...")

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
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    print(f"Deleted user '{TARGET_USERNAME}' (id={user_id}) and all related data.")

db.close()