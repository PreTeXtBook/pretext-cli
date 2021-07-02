import subprocess
import os

# ensure up-to-date "static" resources
subprocess.run(["python", "scripts/update_core.py"])
subprocess.run(["python", "scripts/zip_templates.py"])
# Build package
subprocess.run(["python", "setup.py", "sdist", "bdist_wheel"])

# prompt user to upload to PyPI
print("If all is successful, and you have the PyPI token saved to `.pypitoken`:")
print("python -m twine upload dist/* -u __token__ -p $(cat .pypitoken)")