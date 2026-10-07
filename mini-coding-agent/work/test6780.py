#!/usr/bin/env python3
"""Hello World script that prints output with a date-time stamp.

Each run appends its output to output6780.txt so all runs are captured.
"""
from datetime import datetime

OUTPUT_FILE = "output6780.txt"


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] Hello, World!"
    print(line)
    with open(OUTPUT_FILE, "a") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    main()
