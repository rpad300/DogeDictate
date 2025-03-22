#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for DogeDictate
"""

import os
import sys
from setuptools import setup, find_packages

# Read requirements
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Package metadata
setup(
    name="DogeDictate",
    version="0.1.0",
    description="A lightweight voice dictation tool",
    author="DogeDictate Team",
    author_email="info@dogedictate.com",
    url="https://github.com/dogedictate/dogedictate",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'dogedictate=main:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
) 