#!/usr/bin/env python3
import argparse
import sys
import os

# Ensure cli package is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.validator import run_validate
from cli.hirr_harness import run_replay

def main():
    parser = argparse.ArgumentParser(description="ADK CLI - The Integrity Gate")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: validate
    parser_validate = subparsers.add_parser("validate", help="Validate artifacts against schemas")
    parser_validate.add_argument("path", nargs="?", default=".", help="Path to validate (default: .)")

    # Command: replay
    parser_replay = subparsers.add_parser("replay", help="Run HIRR Harness to verify determinism")
    parser_replay.add_argument("path", nargs="?", default=".", help="Path to replay (default: .)")

    # Command: commit
    parser_commit = subparsers.add_parser("commit", help="Secure commit wrapper")
    parser_commit.add_argument("-m", "--message", required=True, help="Commit message")

    args = parser.parse_args()

    if args.command == "validate":
        print(f"ADK: Validating {args.path}...")
        if run_validate(args.path):
            print("ADK: Validation PASSED")
            sys.exit(0)
        else:
            print("ADK: Validation FAILED")
            sys.exit(1)

    elif args.command == "replay":
        print(f"ADK: Replaying history in {args.path}...")
        if run_replay(args.path):
            print("ADK: Replay PASSED")
            sys.exit(0)
        else:
            print("ADK: Replay FAILED")
            sys.exit(1)

    elif args.command == "commit":
        print("ADK: Running Pre-Commit Integrity Check (Node 6)...")
        # 1. Run validation
        if not run_validate("."):
            print("ADK: Commit REJECTED (Validation Failed)")
            sys.exit(1)
        # 2. Run replay
        if not run_replay("."):
            print("ADK: Commit REJECTED (Determinism Check Failed)")
            sys.exit(1)
            
        print("ADK: Integrity Verified. Executing git commit...")
        # In a real environment, we would use subprocess to call git
        # subprocess.run(["git", "commit", "-m", args.message])
        print(f"[MOCK GIT COMMIT] {args.message}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
