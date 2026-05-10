import subprocess
import sys
import os

project_path = sys.argv[1]

os.chdir(project_path)

subprocess.run(["pip", "install", "-r", "requirements.txt"])
subprocess.run(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])