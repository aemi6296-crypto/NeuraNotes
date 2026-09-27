import sqlite3

db = sqlite3.connect("neuranotes.db")
cursor = db.cursor()

columns_to_add = [
    ("chat_count", "INTEGER DEFAULT 0"),
    ("chat_reset_at", "TEXT"),
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        print(f"Added column: {col_name}")
    except sqlite3.OperationalError as e:
        print(f"Skipped {col_name}: {e}")

db.commit()
db.close()
print("Migration complete.")