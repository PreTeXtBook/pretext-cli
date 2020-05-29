import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pretext", # Replace with your own username
    version="0.0.1",
    author="Steven Clontz",
    author_email="steven.clontz@gmail.com",
    description="A package for authoring and building PreTeXt documents.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
       'lxml',
       'python-slugify'
    ],
    url="https://github.com/stevenclontz/pretext.py",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.4',
)