#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

import sys
from nlp_util import treebanks

for tree in treebanks.generate_trees(sys.stdin, return_empty=True, allow_empty_labels=True):
  for node in tree:
    if 'QP' in node.label:
      print node.label, ' '.join([s.label for s in node.subtrees])
