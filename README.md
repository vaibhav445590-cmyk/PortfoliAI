# PortfoliAI 🚀

> **Autonomous AI-Powered Portfolio Generator for Software Engineers & Students**
>
> Transform standard PDF resumes into production-ready, interactive 3D portfolios with local-first AI intelligence, robust fallback parsing, and high-performance PostgreSQL persistence.

---

## 🏛️ System Architecture

```text
                                 +-----------------------+
                                 |   Client / Browser    |
                                 +-----------+-----------+
                                             |
                                 +-----------v-----------+
                                 |  Rate Limiter / Auth  |
                                 +-----------+-----------+
                                             |
                      +----------------------+----------------------+
                      |                                             |
             [Legacy Routes]                                [Versioned API v1]
          /upload-resume, etc.                             /api/v1/resume/upload
                      |                                             |
                      +----------------------+----------------------+
                                             |
                                 +-----------v-----------+
                                 |   Resume Processor    |
                                 |  (SHA-256 Hash Cache) |
                                 +-----------+-----------+
                                             |
                               +-------------+-------------+
                               |                           |
                       [PDF Extraction]             [Cache Hit: ⚡]
                       pypdf Magic-Bytes            Return Cached Portfolio
                               |                           |
                               v                           |
                    +--------------------+                 |
                    |   Parser Pipeline  |                 |
                    | (Regex & Fallback) |                 |
                    +----------+---------+                 |
                               |                           |
                               v                           |
                    +--------------------+                 |
                    | AI Enrichment Layer|                 |
                    | Local / Ollama / AI|                 |
                    +----------+---------+                 |
                               |                           |
                               v                           |
                    +--------------------+                 |
                    |  Repository Layer  |                 |
                    | Users / Students / |                 |
                    |     Projects       |                 |
                    +----------+---------+                 |
                               |                           |
                               +-------------+-------------+
                                             |
                                 +-----------v-----------+
                                 |  PostgreSQL Database  |
                                 | (Indexed for Scale)   |
                                 +-----------------------+
```

---

## ✨ Features

- **Local-First & Provider-Agnostic Intelligence**: Zero dependency on paid third-party APIs. Operates seamlessly with built-in heuristic NLP, local Ollama models, or cloud LLMs.
- **Resilient Fallback Parsing**: Multi-stage parsing pipeline guarantees valid resume extraction even on unformatted text.
- **Performance Caching**: SHA-256 content hashing prevents redundant re-parsing and AI enrichment on unchanged resumes.
- **Enterprise-Grade Security**:
  - Magic-byte `%PDF-` validation and strict file extension checking.
  - Path traversal neutralization and UUID-based disk isolation.
  - In-memory sliding-window rate limiting.
  - Werkzeug-backed password hashing (`scrypt` / `pbkdf2`).
  - Strict SQL parameterization with zero inline string interpolation.
- **Repository Pattern**: Clean decoupling of database logic into `UserRepository`, `StudentRepository`, and `ProjectRepository`.
- **Versioned RESTful API**: Structured `/api/v1/...` routes with standardized `{ success, data }` and `{ success, error }` envelopes.
- **Optimized Database Schema**: Safe COALESCE updates, multi-student isolation, user ownership Foreign Keys, and performance indexes.

---

## ⚙️ Configuration & Environment Variables

Configure environment variables via `.env` (refer to `.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Environment mode (`development` or `production`) |
| `FLASK_DEBUG` | `false` | Enable/disable Flask debug mode |
| `SECRET_KEY` | `portfoliai-default...` | Secret key for sessions and cryptographic signing |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `student_portfolio` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | *(Required)* | Database password |
| `UPLOAD_FOLDER` | `uploads/resumes` | Directory where uploaded PDFs are stored |
| `MAX_CONTENT_LENGTH` | `10485760` | Maximum upload size in bytes (default 10 MB) |
| `AI_PROVIDER` | `local` | Active AI provider (`local`, `ollama`, `openai`) |
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable sliding-window rate limiter |
| `RATE_LIMIT_PER_MINUTE` | `60` | Global default requests permitted per minute |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+ running locally or in Docker

### 2. Setup Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env and supply your DB_PASSWORD and configurations
```

### 4. Apply Database Migrations
```bash
python run_migration.py
```

### 5. Start Development Server
```bash
python main.py
```
Open `http://localhost:5000` in your browser.

---

## 🐳 Docker Deployment

Run the complete multi-container setup (Web App + PostgreSQL Database) with one command:

```bash
docker-compose up --build -d
```

Check application logs:
```bash
docker-compose logs -f web
```

Stop services:
```bash
docker-compose down
```

---

## 📡 API Reference (v1)

### Standard Response Envelopes

**Success (`2xx`)**:
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}
```

**Error (`4xx / 5xx`)**:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable explanation of error.",
    "details": null
  }
}
```

### Endpoints

| Method | Endpoint | Description | Rate Limit |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new user account (`email`, `password`) | 20 / min |
| `POST` | `/api/v1/auth/login` | Authenticate user (`email`, `password`) | 20 / min |
| `POST` | `/api/v1/resume/upload` | Upload & process PDF resume (`multipart/form-data`) | 30 / min |
| `GET` | `/api/v1/portfolio` | Retrieve complete portfolio JSON for latest student | Unlimited |
| `GET` | `/api/v1/portfolio/<id>` | Retrieve complete portfolio JSON for student ID | Unlimited |
| `GET` | `/api/v1/enrichment-status` | Status and AI metadata for latest student | Unlimited |
| `GET` | `/api/v1/enrichment-status/<id>` | Status and AI metadata for student ID | Unlimited |

*Note: All legacy endpoints (`/`, `/upload-resume`, `/generate-portfolio`, `/api/portfolio`, `/api/enrichment-status`, `/api/enrich-resume`) remain 100% active and backward-compatible.*

---

## 🧪 Testing & Verification

Run all test suites via `pytest`:

```bash
python -m pytest -v
```

Run specific test modules:
```bash
# Phase 4 Production Engineering & Hardening
python test_phase4.py

# Phase 3 Workflow Verification
python test_phase3.py

# Phase 2 AI Enrichment Verification
python test_phase2.py

# Database Persistence Suite
python test_db_persistence.py

# Phase 1 Pipeline Suite
python test_phase1.py
```
