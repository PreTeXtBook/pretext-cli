import setuptools

with open("README.md", "r") as readme_file:
    LONG_DESCRIPTION = readme_file.read()

with open("pretext/static/VERSION", "r") as version_file:
    VERSION = version_file.read().strip()

with open("pretext/static/MINIMUM_PYTHON_VERSION", "r") as mpv_file:
    MINIMUM_PYTHON_VERSION = mpv_file.read().strip()

setuptools.setup(
    name="pretextbook",
    version=VERSION,
    author="PreTeXtBook.org",
    author_email="steven.clontz+PreTeXt@gmail.com",
    description="A package for authoring and building PreTeXt documents.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=[
       'lxml',
       'python-slugify',
       'click>=7.0',
       "importlib_resources ; python_version<'3.7'",
       "pdfCropMargins",
       "click-config-file",
    ],
    url="https://github.com/PreTeXtBook/pretext-cli",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=f">={MINIMUM_PYTHON_VERSION}",
    entry_points={
        'console_scripts': [
            'pretext = pretext.cli:main',
        ],
    },
    package_data = {
        'pretext': ['static/*','static/*/*','static/*/*/*'],
    },
)