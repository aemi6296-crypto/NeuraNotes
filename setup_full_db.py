import sqlite3

db = sqlite3.connect("neuranotes.db")
cursor = db.cursor()

# ===== Create any missing tables (safe: IF NOT EXISTS won't touch existing ones) =====

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        color TEXT,
        total_topics INTEGER DEFAULT 0,
        completed_topics INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        title TEXT,
        content TEXT,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        target_hours INTEGER,
        deadline TEXT,
        completed INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        duration_minutes REAL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcard_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        score INTEGER,
        total INTEGER,
        difficulty TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS youtube_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_title TEXT,
        video_url TEXT,
        video_id TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

print("All tables checked/created.")

# ===== Add any missing columns to existing tables (each wrapped so it's safe to re-run) =====

columns_to_add = [
    ("notes", "image", "TEXT"),
    ("subjects", "completed_topics", "INTEGER DEFAULT 0"),
    ("goals", "completed", "INTEGER DEFAULT 0"),
    ("users", "verified", "INTEGER DEFAULT 1"),
    ("users", "verification_code", "TEXT"),
    ("users", "code_created_at", "TEXT"),
    ("users", "chat_count", "INTEGER DEFAULT 0"),
    ("users", "chat_reset_at", "TEXT"),
]

for table, col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        print(f"Added column: {table}.{col_name}")
    except sqlite3.OperationalError as e:
        print(f"Skipped {table}.{col_name}: {e}")

db.commit()
db.close()
print("Database setup complete.")