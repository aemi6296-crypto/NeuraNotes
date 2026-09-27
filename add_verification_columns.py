import sqlite3

db = sqlite3.connect("neuranotes.db")
cursor = db.cursor()

# verified defaults to 1 so EXISTING users aren't locked out of their accounts.
# New registrations will explicitly be inserted with verified = 0.
columns_to_add = [
    ("verified", "INTEGER DEFAULT 1"),
    ("verification_code", "TEXT"),
    ("code_created_at", "TEXT"),
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