import requests, zipfile, io, shutil

# grab copy of necessary rbeezer/mathbook files from specified commit
with open("pretext/static/CORE_COMMIT","r") as commitfile:
    commit = commitfile.readline().strip()

#filemap = [
#    ("pretext/pretext.py", "pretext/core.py"),
#]

#for pair in filemap:
#    urllib.request.urlretrieve(
#        f'https://raw.githubusercontent.com/rbeezer/mathbook/{commit}/{pair[0]}',
#        pair[1]
#    )

r = requests.get(f"https://github.com/rbeezer/mathbook/archive/{commit}.zip")
archive = zipfile.ZipFile(io.BytesIO(r.content))
archive.extractall("tmp")
shutil.rmtree("pretext/static/xsl", ignore_errors=True)
shutil.copytree(f"tmp/mathbook-{commit}/xsl", "pretext/static/xsl")
shutil.rmtree("pretext/static/pretext", ignore_errors=True)
shutil.copytree(f"tmp/mathbook-{commit}/pretext", "pretext/static/pretext")
shutil.rmtree("pretext/static/schema", ignore_errors=True)
shutil.copytree(f"tmp/mathbook-{commit}/schema", "pretext/static/schema")
shutil.rmtree("tmp")

print("Copied rbeezer/mathbook Python scripts.")
