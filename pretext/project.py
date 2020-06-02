from . import utils,document

def new(title,doc_type,project_path):
    import slugify
    utils.ensure_directory(project_path)
    with utils.working_directory(project_path):
        utils.ensure_directory("source")
        document.new(title,doc_type).write(
            "source/main.ptx",
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8"
        )
        document.publisher().write(
            "publisher.ptx",
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8"
        )
        with open(".gitignore", mode='w') as gitignore:
            print("output", file=gitignore)
        with open("README.md", mode='w') as readme:
            print(f"# {title}", file=readme)
            print("", file=readme)
            print("Authored with [PreTeXt](https://pretextbook.org).", file=readme)