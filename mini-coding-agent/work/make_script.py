import random
from datetime import datetime

# generate random number between 1000 and 9999
num = random.randint(1000, 9999)
filename = f"test{num}.py"

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
iso = datetime.now().isoformat()

# content of the generated hello world script
content = f'''from datetime import datetime

print("Hello, World!")

# run 3 times
for i in range(3):
    print(f"Run {{i+1}}: Hello, World! at {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}")

# output file with date time stamp
with open("output.txt", "a") as f:
    f.write(f"Generated at: {timestamp} (ISO: {iso})\\n")
    f.write(f"Source file: {filename}\\n")
    for i in range(3):
        f.write(f"Run {{i+1}}: Hello, World! at {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}\\n")

print("Output saved to output.txt")
'''

with open(filename, "w") as f:
    f.write(content)

print(f"Created {filename}")
