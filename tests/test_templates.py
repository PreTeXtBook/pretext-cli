from pretext.templates import resource_path


def test_resource_path() -> None:
    resources = [
        ".devcontainer.json",
        ".gitignore",
        "article.zip",
        "book.zip",
        "codechat_config.yaml",
        "demo.zip",
        "hello.zip",
        "project.ptx",
        "publication.ptx",
        "slideshow.zip"
    ]
    for filename in resources:
        with resource_path(filename) as path:
            assert path.name == filename
    try:
        with resource_path("does-not-exist.foo-bar") as path:
            assert False
    except FileNotFoundError:
        assert True
