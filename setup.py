from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

requires_list = []
long_description = ''

setup(
    name='exlauncher',
    description='A Python toolkit for launching experiments.',
    long_description=long_description,
    license='MIT',
    packages=[package for package in find_packages()
              if package.startswith('exlauncher')],
    extras_require={},
    classifiers=["Programming Language :: Python :: 3",
                 "License :: OSI Approved :: MIT License",
                 "Operating System :: OS Independent",
                 ]
)

