import psycopg2

try:
    conn = psycopg2.connect(
        dbname="SkillSync",
        user="postgres",
        password="prajwal@123",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    print("Connected to PostgreSQL SkillSync successfully!")
    
    # Check tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in public schema:", tables)
    
    for t in ["employers", "job_postings", "users"]:
        if t in tables:
            print(f"\n--- Columns in {t} ---")
            cur.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{t}'")
            for c in cur.fetchall():
                print(c)
                
            print(f"--- Rows in {t} ---")
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            for r in cur.fetchall():
                print(r)
except Exception as e:
    print("Error connecting to PostgreSQL:", e)
