import subprocess

# export --help to file to include in documentation
helps =  subprocess.check_output(['pretext', '--help']).decode("utf-8")
for subcmd in ['new', 'build', 'view', 'publish']:
    helps += "\n\n"+("-"*79)+"\n\n"
    helps += subprocess.check_output(['pretext', subcmd, '--help']).decode("utf-8")

with open("pretext/static/help.txt", 'w') as helpfile:
    helpfile.write(helps)


# Build documentation from PreTeXt
subprocess.run(['pretext', 'build'])
subprocess.run(['pretext', 'publish'])


# Build package
subprocess.run(["python", "setup.py", "sdist", "bdist_wheel"])

# prompt user to upload to PyPI
print("If all is successful, and you have the PyPI token saved to `.pypitoken`:")
print("python -m twine upload dist/* -u __token__ -p $(cat .pypitoken)")