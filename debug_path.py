import os
import shutil
import sys

print(f"PATH: {os.environ['PATH']}")
print(f"Ollama path: {shutil.which('ollama')}")
