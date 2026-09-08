"""
PortfoliAI — Security & Hardening Module
Provides rate limiting, path traversal protection, secure filename sanitization,
and standardized API response envelopes.
"""

import os
import re
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Optional, Dict, Any, Callable, Tuple
import jwt
from flask import request, jsonify, g
from werkzeug.utils import secure_filename
from config import Config


# ============================================================
# 1. STANDARDIZED API RESPONSE ENVELOPES
# ============================================================

def api_success(data: Any = None, message: Optional[str] = None, status_code: int = 200):
    """Return standardized API success envelope."""
    payload: Dict[str, Any] = {"success": True}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return jsonify(payload), status_code


def api_error(code: str, message: str, status_code: int = 400, details: Any = None):
    """Return standardized API error envelope."""
    err_body: Dict[str, Any] = {
        "code": code,
        "message": message
    }
    if details is not None:
        err_body["details"] = details

    return jsonify({"success": False, "error": err_body}), status_code


# ============================================================
# 2. PATH TRAVERSAL & FILENAME HARDENING
# ============================================================

DANGEROUS_PATH_CHARS = re.compile(r"[\x00/\\<>\":|?*]")


def sanitize_upload_filename(filename: Optional[str], allowed_extensions: set = None) -> str:
    """
    Sanitize and harden an uploaded filename to prevent directory traversal,
    null-byte injection, and arbitrary filesystem overwrites.
    """
    if allowed_extensions is None:
        allowed_extensions = Config.ALLOWED_EXTENSIONS

    if not filename or not isinstance(filename, str):
        return f"resume_{uuid.uuid4().hex[:10]}.pdf"

    # Reject null bytes immediately
    if "\x00" in filename:
        return f"resume_{uuid.uuid4().hex[:10]}.pdf"

    # Strip dangerous characters and directory separators
    clean = os.path.basename(filename)
    clean = DANGEROUS_PATH_CHARS.sub("", clean)
    clean = secure_filename(clean)

    # Ensure valid extension
    if "." in clean:
        ext = clean.rsplit(".", 1)[1].lower()
        if ext not in allowed_extensions:
            # Enforce allowed extension
            clean = f"{clean.rsplit('.', 1)[0]}.pdf"
    else:
        clean = f"{clean}.pdf"

    # Prevent hidden files or empty base
    base = clean.rsplit(".", 1)[0].lstrip(".")
    if not base or base.lower() in ("con", "prn", "aux", "nul"):  # Windows reserved names
        clean = f"resume_{uuid.uuid4().hex[:10]}.pdf"

    return clean


# ============================================================
# 3. THREAD-SAFE IN-MEMORY SLIDING-WINDOW RATE LIMITER
# ============================================================

class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory rate limiter using a sliding-time window.
    Tracks timestamps per client key (IP address or user ID).
    """

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.records: Dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int) -> bool:
        """Check if the given key has exceeded max_requests within the sliding window."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self.lock:
            timestamps = self.records.get(key, [])
            # Evict timestamps older than cutoff
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                self.records[key] = valid_timestamps
                return False

            valid_timestamps.append(now)
            self.records[key] = valid_timestamps
            return True

    def reset(self):
        """Clear all rate limit tracking records."""
        with self.lock:
            self.records.clear()


# Global rate limiter instance
_global_limiter = SlidingWindowRateLimiter(window_seconds=60)


def rate_limit(
    max_per_minute: Optional[int] = None,
    key_func: Optional[Callable[[], str]] = None
):
    """
    Decorator for Flask route handlers to enforce rate limits.
    Can be configured globally or overridden per-route.
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not Config.RATE_LIMIT_ENABLED:
                return f(*args, **kwargs)

            limit = max_per_minute or Config.RATE_LIMIT_PER_MINUTE
            if limit <= 0:
                return f(*args, **kwargs)

            # Determine client key
            if key_func:
                client_key = key_func()
            else:
                # Default: client IP address
                client_key = (
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                    or request.remote_addr
                    or "unknown_client"
                )

            route_key = f"{request.endpoint or request.path}:{client_key}"

            if not _global_limiter.is_allowed(route_key, limit):
                if request.path.startswith("/api/"):
                    return api_error(
                        code="RATE_LIMIT_EXCEEDED",
                        message=f"Rate limit exceeded. Maximum {limit} requests per minute.",
                        status_code=429
                    )
                return ("Too many requests. Please slow down.", 429)

            return f(*args, **kwargs)
        return wrapped
    return decorator


# ============================================================
# 4. JWT BEARER TOKEN AUTHENTICATION & USER OWNERSHIP
# ============================================================

def generate_auth_token(
    user_id: int,
    email: str,
    expires_in_seconds: Optional[int] = None
) -> str:
    """
    Generate a cryptographically signed JWT Bearer authentication token.
    Uses Config.JWT_SECRET_KEY and Config.JWT_ALGORITHM (HS256).
    """
    now = datetime.now(timezone.utc)
    seconds = (
        expires_in_seconds
        if expires_in_seconds is not None
        else (Config.JWT_EXPIRATION_HOURS * 3600)
    )
    exp = now + timedelta(seconds=seconds)

    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    }

    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_auth_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate signature, structure, and expiration of a JWT Bearer token.
    Returns (is_valid, payload, error_message).
    """
    if not token or not isinstance(token, str):
        return False, None, "Token is missing or invalid."

    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired."
    except (jwt.InvalidTokenError, jwt.DecodeError) as err:
        return False, None, f"Invalid token: {err}"
    except Exception as err:
        return False, None, f"Token verification failed: {err}"


def get_current_user_from_request() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract and validate authenticated user identity from the request.
    Reads 'Authorization: Bearer <token>' header.
    Returns (user_dict_or_None, error_code_if_token_failed).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        cookie_token = request.cookies.get("auth_token")
        if cookie_token:
            auth_header = f"Bearer {cookie_token}"

    if not auth_header:
        return None, None

    parts = auth_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, "INVALID_HEADER_FORMAT"

    token = parts[1]
    is_valid, payload, err = decode_auth_token(token)
    if not is_valid or not payload:
        if err and "expired" in err.lower():
            return None, "EXPIRED_TOKEN"
        return None, "INVALID_TOKEN"

    user = {
        "id": int(payload["user_id"]),
        "email": payload.get("email", "")
    }
    return user, None


def require_auth(f):
    """
    Route decorator enforcing valid JWT Bearer token.
    Returns HTTP 401 UNAUTHORIZED if missing, expired, or invalid.
    Attaches authenticated user to request.current_user and g.current_user.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        user, err_code = get_current_user_from_request()
        if not user:
            return api_error(
                code="UNAUTHORIZED",
                message="Authentication required.",
                status_code=401
            )

        g.current_user = user
        request.current_user = user
        return f(*args, **kwargs)
    return wrapped


def check_student_ownership(
    student_id: int,
    current_user: Optional[Dict[str, Any]],
    get_db_connection
) -> Tuple[bool, Optional[Tuple[Any, int]], Optional[Dict[str, Any]]]:
    """
    Enforces authorization and ownership on student resources.
    Returns (allowed, error_response_tuple, student_dict).
    Rules:
        - Student not found -> 404 NOT_FOUND
        - Student is owned by another user -> 403 FORBIDDEN
        - Student is owned by ANY user and current_user is None -> 401 UNAUTHORIZED
        - Student is owned by current_user -> ALLOWED
        - Student is unowned (user_id is None):
            - Authenticated user -> ALLOWED (can claim / update)
            - Unauthenticated user -> ALLOWED (compatibility for legacy test records)
    """
    if not student_id:
        return False, api_error("INVALID_INPUT", "Student ID is required.", 400), None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, user_id, name, email FROM students WHERE id = %s", (student_id,))
        row = cursor.fetchone()
        if not row:
            return False, api_error("NOT_FOUND", f"Student {student_id} not found.", 404), None

        owner_id = row[1]
        student_info = {"id": row[0], "user_id": owner_id, "name": row[2], "email": row[3]}

        if owner_id is not None:
            if current_user is None:
                return False, api_error("UNAUTHORIZED", "Authentication required.", 401), student_info
            if current_user["id"] != owner_id:
                return False, api_error("FORBIDDEN", "You do not have permission to access this resource.", 403), student_info

        return True, None, student_info
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 5. PHASE 5 CUSTOMIZATION & PORTFOLIO VALIDATION
# ============================================================

ALLOWED_TEMPLATES = {"default", "minimal", "glass", "modern", "developer"}
ALLOWED_THEMES = {"glass", "dark", "light"}
ALLOWED_ACCENTS = {"emerald", "blue", "purple", "amber", "rose", "cyan"}
ALLOWED_SECTIONS = {"about", "skills", "education", "experience", "projects", "achievements"}
ALLOWED_STATUSES = {"draft", "published"}

DANGEROUS_URL_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")
SAFE_URL_SCHEMES = ("http://", "https://", "mailto:")


def validate_social_links(links: Any) -> Tuple[bool, Optional[str], Dict[str, str]]:
    """
    Validate and sanitize social media / external links dictionary.
    Rejects unsafe schemes (javascript:, data:, vbscript:, file:).
    Requires http://, https://, or mailto: schemes.
    """
    if links is None:
        return True, None, {}

    if not isinstance(links, dict):
        return False, "Social links must be a JSON object/dictionary.", {}

    cleaned: Dict[str, str] = {}
    for key, val in links.items():
        if not isinstance(key, str) or not key.strip():
            continue
        clean_key = key.strip().lower()

        if val is None:
            continue

        if not isinstance(val, str):
            return False, f"Link for '{clean_key}' must be a string URL.", {}

        clean_val = val.strip()
        if not clean_val:
            continue

        val_lower = clean_val.lower()
        if any(val_lower.startswith(scheme) for scheme in DANGEROUS_URL_SCHEMES):
            return False, f"Unsafe URL scheme detected in link for '{clean_key}'.", {}

        if not any(val_lower.startswith(scheme) for scheme in SAFE_URL_SCHEMES):
            return False, f"URL for '{clean_key}' must start with http://, https://, or mailto:.", {}

        cleaned[clean_key] = clean_val

    return True, None, cleaned


def validate_section_visibility(visibility: Any) -> Tuple[bool, Optional[str], Dict[str, bool]]:
    """
    Validate section visibility settings against ALLOWED_SECTIONS.
    """
    if visibility is None:
        return True, None, {}

    if not isinstance(visibility, dict):
        return False, "section_visibility must be a JSON object/dictionary.", {}

    cleaned: Dict[str, bool] = {}
    for key, val in visibility.items():
        if not isinstance(key, str):
            return False, f"Section name must be a string.", {}
        sec_name = key.strip().lower()
        if sec_name not in ALLOWED_SECTIONS:
            return False, f"Invalid section '{sec_name}'. Allowed sections: {sorted(list(ALLOWED_SECTIONS))}.", {}
        if not isinstance(val, bool):
            return False, f"Visibility for section '{sec_name}' must be a boolean (true/false).", {}
        cleaned[sec_name] = val

    return True, None, cleaned


def validate_project_order(order: Any) -> Tuple[bool, Optional[str], List[int]]:
    """
    Validate project order list. Must be a list of integer project IDs.
    """
    if order is None:
        return True, None, []

    if not isinstance(order, list):
        return False, "project_order must be a list of integer project IDs.", []

    cleaned: List[int] = []
    for item in order:
        if not isinstance(item, int) or isinstance(item, bool):
            return False, f"project_order items must be integers, got {type(item).__name__}.", []
        cleaned.append(item)

    return True, None, cleaned


def check_project_ownership(
    project_id: int,
    current_user: Optional[Dict[str, Any]],
    get_db_connection
) -> Tuple[bool, Optional[Tuple[Any, int]], Optional[Dict[str, Any]]]:
    """
    Enforces authorization and ownership on project resources.
    Returns (allowed, error_response_tuple, project_info).
    Rules:
        - Project not found -> 404 NOT_FOUND
        - Project's student is owned by another user -> 403 FORBIDDEN
        - Project's student is owned by ANY user and current_user is None -> 401 UNAUTHORIZED
        - Project's student is owned by current_user -> ALLOWED
        - Project's student is unowned (user_id is None):
            - Authenticated user -> ALLOWED
            - Unauthenticated user -> ALLOWED (compatibility for legacy test records)
    """
    if not project_id:
        return False, api_error("INVALID_INPUT", "Project ID is required.", 400), None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT p.id, p.student_id, p.title, p.description, p.technologies,
                   p.github_url, p.live_url, p.category, s.user_id
            FROM projects p
            JOIN students s ON p.student_id = s.id
            WHERE p.id = %s
            """,
            (project_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False, api_error("NOT_FOUND", f"Project {project_id} not found.", 404), None

        owner_id = row[8]
        proj_info = {
            "id": row[0],
            "student_id": row[1],
            "title": row[2] or "",
            "description": row[3] or "",
            "technologies": row[4] or "",
            "github_url": row[5],
            "live_url": row[6],
            "category": row[7] or "General",
            "owner_user_id": owner_id
        }

        if owner_id is not None:
            if current_user is None:
                return False, api_error("UNAUTHORIZED", "Authentication required.", 401), proj_info
            if current_user["id"] != owner_id:
                return False, api_error("FORBIDDEN", "You do not have permission to access or modify this project.", 403), proj_info

        return True, None, proj_info
    finally:
        cursor.close()
        conn.close()

