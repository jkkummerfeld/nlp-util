#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
VERSION = open(os.path.join(os.path.dirname(__file__), 'VERSION')).read().strip()

# Note - for reading in data files, etc, from git, the 'setuptools_git' and
# include_... lines are needed (and a way to get those is needed)
setup(
  name='nlp_util',
  version=VERSION,
  description='NLP utils by JKK',
  url='https://github.com/jkkummerfeld/nlp-util',
  packages=['nlp_util'],
  setup_requires=[
    'setuptools_git >= 0.3',
  ],
  include_package_data=True,
  entry_points = {
    'console_scripts': [
        'nlp_util_reprint_trees = nlp_util.tools.reprint_trees:main',
        'nlp_util_gen_table = nlp_util.tools.gen_table:main',
    ],
  },
)
