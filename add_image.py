import sqlite3
db = sqlite3.connect("neuranotes.db")
db.execute("ALTER TABLE notes ADD COLUMN image TEXT")
db.commit()
db.close()
print("Done!")
