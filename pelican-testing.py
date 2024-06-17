from pelican import Pelican
from pelican.settings import configure_settings, DEFAULT_CONFIG
from pretext.project import Project

config = DEFAULT_CONFIG
config["PATH"] = "foobar-in"
config["THEME"] = "pelican-ptx"
config["OUTPUT_PATH"] = "foobar-out"
config["RELATIVE_URLS"] = True
config["TIMEZONE"] = "Etc/UTC"
config["ARTICLE_PATHS"] = ['updates']
config["ARTICLE_SAVE_AS"] = 'updates/{date:%Y%m%d}-{slug}.html'
config["ARTICLE_URL"] = config["ARTICLE_SAVE_AS"]

p = Project.parse("new-pretext-project")
root = p.get_target().source_element()
for title_ele in root.iterdescendants("title"):
    config["SITENAME"] = title_ele.text
    break
else:
    config["SITENAME"] = "My PreTeXt Project"
for title_ele in root.iterdescendants("subtitle"):
    config["SITESUBTITLE"] = title_ele.text
    break

config["PTX_TARGETS"] = [
    (t.name.capitalize(), t.deploy_dir_path())
    for t in p.deploy_targets()
]

Pelican(configure_settings(config)).run()
