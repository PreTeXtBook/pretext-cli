import setuptools

with open("README.md", "r") as readme_file:
    LONG_DESCRIPTION = readme_file.read()

with open("pretext/static/VERSION", "r") as version_file:
    VERSION = version_file.read().strip()

setuptools.setup(
    name="pretextbook",
    version=VERSION,
    author="PreTeXtBook.org",
    author_email="steven.clontz+PreTeXt@gmail.com",
    description="A package for authoring and building PreTeXt documents.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=[
       'lxml==4.*',
       'python-slugify==6.*',
       'requests>=2.28,<3',
       'watchdog==2.*',
       'GitPython==3.*',
       'click==7.*',
       "pdfCropMargins==1.*",
       "pypdf2==1.*",
       "click-logging==1.*",
    ],
    extras_require={
        'dev': [
            "setuptools",
            "wheel",
            "twine",
            "secretstorage",
        ]
    },
    url="https://github.com/PreTeXtBook/pretext-cli",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=f">=3.8.5",
    entry_points={
        'console_scripts': [
            'pretext = pretext.cli:main',
        ],
    },
    package_data = {
        'pretext': ['static/*','static/*/*','static/*/*/*'],
    },
)
