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
       'requests==2.*',
       'watchdog==2.*',
       'GitPython==3.*',
       'click==8.*',
       "pdfCropMargins>=1.0.6,<2",
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
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
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
