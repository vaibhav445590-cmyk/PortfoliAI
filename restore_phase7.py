"""
PortfoliAI — Phase 7 Restoration Script
=======================================
Restores the exact approved Phase 7 UI (Version A) from the immutable backup.
Usage:
    python restore_phase7.py
"""

import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, ".backups", "phase7-approved")

if not os.path.exists(BACKUP_DIR):
    print(f"Error: Backup directory not found at {BACKUP_DIR}")
    sys.exit(1)

print("Restoring PortfoliAI Version A (Phase 7 Approved)...")

# 1. Restore templates
shutil.copytree(os.path.join(BACKUP_DIR, "templates"), os.path.join(BASE_DIR, "templates"), dirs_exist_ok=True)
print("  [OK] templates/ restored")

# 2. Restore static/css
shutil.copytree(os.path.join(BACKUP_DIR, "static", "css"), os.path.join(BASE_DIR, "static", "css"), dirs_exist_ok=True)
print("  [OK] static/css/ restored")

# 3. Restore static/js
shutil.copytree(os.path.join(BACKUP_DIR, "static", "js"), os.path.join(BASE_DIR, "static", "js"), dirs_exist_ok=True)
print("  [OK] static/js/ restored")

# 4. Restore configuration and entrypoint
for fname in ["config.py", "main.py"]:
    src = os.path.join(BACKUP_DIR, fname)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(BASE_DIR, fname))
        print(f"  [OK] {fname} restored")

print("\nRestoration COMPLETE. Version A (Phase 7 Approved) is fully restored.")
