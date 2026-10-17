import random
import subprocess
import sys

# Generate a random 4-digit number between 1000 and 9999
rand_num = random.randint(1000, 9999)
filename = f"test{rand_num}.py"

# Hello world script that prints a timestamp
script_content = '''import datetime

print("Hello, World!")
print("Timestamp:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
'''

# Write the hello world script
with open(filename, "w") as f:
    f.write(script_content)

print(f"Created script: {filename}")
print("-" * 40)

output_file = f"test{rand_num}_output.txt"

# Run the script 3 times and save outputs to a file
with open(output_file, "w") as out:
    for i in range(1, 4):
        header = f"Run #{i}:\n"
        print(header, end="")
        out.write(header)

        result = subprocess.run([sys.executable, filename], capture_output=True, text=True)
        print(result.stdout, end="")
        out.write(result.stdout)

        sep = "-" * 40 + "\n"
        print(sep, end="")
        out.write(sep)

print(f"Output saved to: {output_file}")