from setuptools import setup

import io
import os

def read(fname, encoding='utf-8'):
    here = os.path.dirname(__file__)
    with io.open(os.path.join(here, fname), encoding=encoding) as f:
        return f.read()

setup(
    name='pretext',
    version='1.5.1',

    description='Use doctest with bytes, str & unicode on Python 2.x and 3.x',
    long_description=read('README.rst'),
    long_description_content_type='text/x-rst',
    url='https://github.com/moreati/b-prefix-all-the-doctests',

    author='Alex Willmer',
    author_email='alex@moreati.org.uk',

    license='Apache Software License 2.0',

    py_modules=['pretext'],
    include_package_data=True,

    classifiers=[
        'Development Status :: 7 - Inactive',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Documentation',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Testing',
    ],
    keywords='doctest bytes unicode bytestring prefix literal string str',
)
