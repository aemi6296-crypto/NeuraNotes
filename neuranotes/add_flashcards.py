import sqlite3

db = sqlite3.connect("neuranotes.db")

db.execute("""
CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    difficulty TEXT DEFAULT 'easy'
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS flashcard_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    score INTEGER,
    total INTEGER,
    difficulty TEXT,
    date DATE DEFAULT CURRENT_DATE
)
""")

db.commit()
db.close()
print("Done!")
