import os
import psycopg2
from resume_parser import parse_resume_text
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="student_portfolio",
        user="postgres",
        password=os.getenv("DB_PASSWORD", "")
    )


conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT resume_text
    FROM students
    WHERE resume_text IS NOT NULL
    ORDER BY id DESC
    LIMIT 1
""")

row = cursor.fetchone()

cursor.close()
conn.close()


if not row:
    print("No resume text found in database.")
else:
    resume_text = row[0]

    parsed_data = parse_resume_text(resume_text)

    print("\n===== DATABASE RESUME PARSED =====\n")

    for key, value in parsed_data.items():
        print(f"{key}: {value}")