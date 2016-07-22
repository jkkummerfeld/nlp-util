#!/usr/bin/env python

import sys
from nlp_util import pstree, treebanks, render_tree

for tree in treebanks.generate_trees(sys.stdin, treebanks.shp_read_tree):
  ans = []
  last_open = True
  for line in render_tree.text_tree(tree, False, True, 0, False, True).split("\n"):
    if last_open and len(line.strip()) > 2 and line.strip()[0] == '(' and line.strip()[-1] == ')':
      ans[-1] += " {}".format(line.strip())
      if line.strip()[-2] != ')':
        last_open = True
      else:
        last_open = False
    else:
      ans.append("# Parse  {}".format(line))
      if line.strip()[-2] != ')':
        last_open = True
      else:
        last_open = False
  words = render_tree.text_words(tree).split()
  ans.append("# Sent")
  for i, w in enumerate(words):
    ans[-1] += "  {} {}".format(i + 1, w)
  print "\n".join(ans)
  print
