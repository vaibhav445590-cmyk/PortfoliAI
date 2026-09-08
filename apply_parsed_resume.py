import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from parser_pipeline import create_default_pipeline


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

# Get latest student with a resume
cursor.execute("""
    SELECT id, resume_text
    FROM students
    WHERE resume_text IS NOT NULL
    AND resume_text <> ''
    ORDER BY id DESC
    LIMIT 1
""")

student = cursor.fetchone()

if not student:
    print("No resume found in the database.")
    cursor.close()
    conn.close()
    exit()

student_id = student[0]
resume_text = student[1]

# Parse resume using pipeline
pipeline = create_default_pipeline()
data, parser_name = pipeline.parse(resume_text)

print("\n===== STRUCTURED RESUME DATA =====\n")
print(f"Parser:     {parser_name}")
print(f"Confidence: {data.confidence}")
print(f"Name:       {data.name}")
print(f"Email:      {data.email}")
print(f"Phone:      {data.phone}")
print(f"Summary:    {data.summary}")
print(f"Skills:     {data.skills}")
print(f"Education:  {data.education}")
print(f"Experience: {data.experience}")
print(f"Achievements: {data.achievements}")
print(f"Projects:   {len(data.projects)}")


# -----------------------------
# UPDATE STUDENT
# -----------------------------

cursor.execute("""
    UPDATE students
    SET
        name         = COALESCE(NULLIF(%s, ''), name),
        email        = COALESCE(NULLIF(%s, ''), email),
        bio          = COALESCE(NULLIF(%s, ''), bio),
        skills       = COALESCE(NULLIF(%s, ''), skills),
        education    = COALESCE(NULLIF(%s, ''), education),
        experience   = COALESCE(NULLIF(%s, ''), experience),
        achievements = COALESCE(NULLIF(%s, ''), achievements),
        parser_used  = COALESCE(NULLIF(%s, ''), parser_used)
    WHERE id = %s
""", (
    data.name or "",
    data.email or "",
    data.summary or "",
    data.skills_text(),
    data.education_text(),
    data.experience_text(),
    data.achievements_text(),
    parser_name,
    student_id
))


# -----------------------------
# UPDATE PROJECTS (preserving existing data)
# -----------------------------

valid_projects = [
    p for p in data.projects
    if p.title and p.title.strip()
]

if valid_projects:
    cursor.execute("""
        SELECT id, title, description, technologies, github_url, live_url
        FROM projects
        WHERE student_id = %s
    """, (student_id,))
    existing_rows = cursor.fetchall()
    existing_by_title = {}
    for row in existing_rows:
        if row[1]:
            existing_by_title[row[1].strip().lower()] = {
                "id": row[0],
                "title": row[1],
                "description": row[2] or "",
                "technologies": row[3] or "",
                "github_url": row[4],
                "live_url": row[5]
            }

    cursor.execute("""
        DELETE FROM projects
        WHERE student_id = %s
    """, (student_id,))

    seen_titles = set()
    for project in valid_projects:
        norm_title = project.title.strip().lower()
        seen_titles.add(norm_title)
        existing = existing_by_title.get(norm_title, {})

        techs = list(project.technologies)
        if not techs and existing.get("technologies"):
            techs = [t.strip() for t in existing["technologies"].split(",") if t.strip()]
        technologies_text = ", ".join(techs)

        description = (
            project.description.strip()
            if project.description and project.description.strip()
            else existing.get("description", "")
        )
        github_url = project.github_url if project.github_url else existing.get("github_url")
        live_url = project.live_url if project.live_url else existing.get("live_url")

        cursor.execute("""
            INSERT INTO projects (
                student_id,
                title,
                description,
                technologies,
                github_url,
                live_url
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            project.title.strip(),
            description,
            technologies_text,
            github_url,
            live_url
        ))

    for norm_title, existing in existing_by_title.items():
        if norm_title not in seen_titles:
            cursor.execute("""
                INSERT INTO projects (
                    student_id,
                    title,
                    description,
                    technologies,
                    github_url,
                    live_url
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                student_id,
                existing["title"],
                existing["description"],
                existing["technologies"],
                existing["github_url"],
                existing["live_url"]
            ))

conn.commit()

cursor.close()
conn.close()

print("\n================================")
print("Resume data applied successfully!")
print("================================")