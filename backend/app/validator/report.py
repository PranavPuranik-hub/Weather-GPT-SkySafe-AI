"""
Report script for adversarial test suite.
"""
import os
import subprocess
import sys


def main():
    print("Running Adversarial Validator Test Suite...")

    # Try different test paths depending on where we are running from
    test_path = "tests/validator/" if os.path.exists("tests/validator/") else "backend/tests/validator/"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("ERRORS:", result.stderr)

    if result.returncode == 0:
        print("\nSUCCESS: 100% Catch rate achieved for adversarial hallucinations.")
    else:
        print("\nFAILURE: Some hallucinations bypassed the validator.")
        sys.exit(1)

if __name__ == "__main__":
    main()
