from datetime import datetime

print("Hello, World!")

# run 3 times
for i in range(3):
    print(f"Run {i+1}: Hello, World! at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# output file with date time stamp
with open("output.txt", "a") as f:
    f.write(f"Generated at: 2026-10-07 14:14:13 (ISO: 2026-10-07T14:14:13.741062)\n")
    f.write(f"Source file: test1533.py\n")
    for i in range(3):
        f.write(f"Run {i+1}: Hello, World! at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("Output saved to output.txt")
