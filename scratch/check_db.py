import sqlite3

con = sqlite3.connect('backend/test.db')
cur = con.cursor()
print("EMPLOYERS:")
for r in cur.execute("SELECT * FROM employers").fetchall():
    print(r)

print("\nUSERS:")
for r in cur.execute("SELECT id, email, full_name, role FROM users").fetchall():
    print(r)

print("\nJOB_POSTINGS:")
for r in cur.execute("SELECT id, title, company_name, employer_id FROM job_postings").fetchall():
    print(r)
