import subprocess

# Call pip to install the packages in editable mode
subprocess.run(["pip", "install", "-e", "./dm4reader"])
subprocess.run(["pip", "install", "-e", "./nornir-shared"])
subprocess.run(["pip", "install", "-e", "./nornir-pools"])
subprocess.run(["pip", "install", "-e", "./nornir-imageregistration"])
subprocess.run(["pip", "install", "-e", "./nornir-buildmanager"])
