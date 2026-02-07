#!/usr/bin/env python3
"""
Code quality check script for the RiverGhost project.
Runs various code quality tools and reports results.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔍 {description}")
    print("-" * 50)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {description}: {e}")
        return False

def main():
    """Run all code quality checks"""
    print("🚀 RiverGhost Code Quality Check")
    print("=" * 50)

    # Define the checks to run
    checks = [
        ("ruff check python/hopilot/ tests/", "Linting with Ruff"),
        ("black --check python/hopilot/ tests/", "Code formatting check with Black"),
        ("isort --check-only python/hopilot/ tests/", "Import sorting check with isort"),
        ("mypy python/hopilot/", "Type checking with mypy"),
        ("bandit -r python/hopilot/", "Security scanning with bandit"),
        ("python -m pytest tests/ -q", "Running tests"),
    ]

    results = []
    for cmd, description in checks:
        success = run_command(cmd, description)
        results.append((description, success))

    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)

    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
        if not success:
            all_passed = False

    print("\n" + ("🎉 All checks passed!" if all_passed else "⚠️  Some checks failed."))

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())