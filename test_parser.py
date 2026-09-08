from resume_parser import parse_resume_text


sample_resume = """
Alex Sharma
BCA Student | Aspiring Software Developer
Email: alex.sharma@example.com
Phone: +91 9000000000

Summary
Motivated BCA student interested in backend development, APIs, databases, and software engineering.

Skills
Python, FastAPI, PostgreSQL, Git, REST APIs, HTML, SQL

Education
BCA

Projects
Student Portfolio
A portfolio website built using Flask and PostgreSQL.

Experience
Backend Development Intern

Achievements
Completed Python certification
"""


result = parse_resume_text(sample_resume)

print("\n===== PARSED RESUME =====\n")

for key, value in result.items():
    print(f"{key}: {value}")