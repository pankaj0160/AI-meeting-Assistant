import sqlite3

conn = sqlite3.connect("meetings.db")

conn.execute(
    "DELETE FROM users WHERE email = ?",
    ("pankaj@gmail.com",)
)

conn.commit()
conn.close()

print("Done")