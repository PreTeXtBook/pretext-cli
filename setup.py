from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="pretextbook",
    install_requires=[
        "lxml==4.*",
        "requests==2.*",
        "watchdog==2.*",
        "GitPython==3.*",
        "click==8.*",
        "pdfCropMargins>=1.0.6,<2",
        "click-logging==1.*",
        "ghp-import==2.*",
    ],
)
