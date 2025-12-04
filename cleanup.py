#!/usr/bin/env python3
"""
Cleanup script to remove unnecessary files from the project.
Run this before deploying to keep the repository clean.
"""

import os
from pathlib import Path

# Files to remove (test, debug, and temporary files)
FILES_TO_REMOVE = [
    "debug_job.py",
    "download_job_2995978.py",
    "fix_download.py",
    "get_report_params.py",
    "gl_fetcher_updated.py",
    "test_po_fetcher.py",
    "test_processor.py",
    "try_all_methods.py",
    "verify_fallback.py",
    "verify_fix.py",
    "po Old report detailed.ipynb",
    "po_report_old_report.ipynb",
    "test.ipynb",
    "compare_new_old_report.ipynb",
]

# Data files to remove (large files that shouldn't be in repo)
DATA_FILES_PATTERNS = [
    "*.xls",
    "*.xlsx", 
    "*.csv",
]

def main():
    project_dir = Path(__file__).parent
    removed_count = 0
    
    print("🧹 Cleaning up project directory...")
    print("=" * 60)
    
    # Remove specific files
    for filename in FILES_TO_REMOVE:
        filepath = project_dir / filename
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"✅ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {filename}: {e}")
    
    # Remove data files by pattern
    for pattern in DATA_FILES_PATTERNS:
        for filepath in project_dir.glob(pattern):
            if filepath.is_file():
                try:
                    filepath.unlink()
                    print(f"✅ Removed: {filepath.name}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Failed to remove {filepath.name}: {e}")
    
    print("=" * 60)
    print(f"✨ Cleanup complete! Removed {removed_count} files.")
    print("\nEssential files remaining:")
    print("  - app.py")
    print("  - PO_report_fetcher.py")
    print("  - PO_report_processor.py")
    print("  - pyproject.toml")
    print("  - uv.lock")
    print("  - .env (keep this, but don't commit it!)")
    print("  - Dockerfile")
    print("  - fly.toml")
    print("  - DEPLOYMENT.md")
    print("  - README.md")

if __name__ == "__main__":
    main()
