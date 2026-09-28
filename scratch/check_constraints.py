import os
import psycopg2

password = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""))
conn = psycopg2.connect(dbname="SkillSync", user="postgres", password=password, host="localhost", port="5432")
cur = conn.cursor()
cur.execute("SELECT * FROM alembic_version")
print("alembic_version:", cur.fetchall())

# Let's check if employers table exists in any schema
cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name = 'employers'")
print("employers table:", cur.fetchall())

# Let's check foreign keys on job_postings
cur.execute("""
SELECT
    tc.table_schema,
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'job_postings';
""")
print("job_postings constraints:", cur.fetchall())
