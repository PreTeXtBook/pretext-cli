import os
import shutil
import subprocess


# grab verison number
with open("pretext/static/VERSION") as f:
    version = f.read().strip()

print(f"Building package for version {version}.")

print("Removing any old builds...")
if os.path.isdir("dist"):
    shutil.rmtree("dist")
os.makedirs("dist")

# ensure up-to-date "static" resources
subprocess.run(["python", "scripts/update_core.py"])
subprocess.run(["python", "scripts/zip_templates.py"])
# Build package
subprocess.run(["python", "setup.py", "sdist", "bdist_wheel"])

# prompt user to upload to PyPI
print("If all is successful, and you have the PyPI token saved to `.pypitoken`, run:")
print()
print("  python -m twine upload dist/* -u __token__ -p $(cat .pypitoken)")
print()
