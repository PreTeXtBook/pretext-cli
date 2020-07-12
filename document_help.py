import subprocess

helps =  subprocess.check_output(['pretext', '--help']).decode("utf-8")
helps += "\n\n"+("-"*79)+"\n\n"
helps += subprocess.check_output(['pretext', 'new', '--help']).decode("utf-8")
helps += "\n\n"+("-"*79)+"\n\n"
helps += subprocess.check_output(['pretext', 'build', '--help']).decode("utf-8")
helps += "\n\n"+("-"*79)+"\n\n"
helps += subprocess.check_output(['pretext', 'view', '--help']).decode("utf-8")
helps += "\n\n"+("-"*79)+"\n\n"
helps += subprocess.check_output(['pretext', 'publish', '--help']).decode("utf-8")

with open("pretext/static/help.txt", 'w') as helpfile:
    helpfile.write(helps)
