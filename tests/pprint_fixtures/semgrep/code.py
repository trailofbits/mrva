import subprocess

API_KEY = "abc123"

subprocess.call("ls", shell=True)

subprocess.call(
    "grep foo",
    shell=True,
)
