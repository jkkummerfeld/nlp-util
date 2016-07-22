#!/usr/bin/env python

import sys

def read_parse(src):
  spines = []
  edges = []
  while True:
    line = src.readline()
    if line == '':
      return None
    elif line.strip() == '':
      break
    if line[0] != '#':
      parts = line.strip().split()
      spines.append(parts[3])
      edges.append(' '.join(parts[5:8]))
  return (spines, edges)

gold = open(sys.argv[1])
auto = open(sys.argv[2])

spine_match = 0.0
edge_match = 0.0
total = 0.0
while True:
  gparse = read_parse(gold)
  aparse = read_parse(auto)
  if gparse is None or aparse is None:
    print spine_match, edge_match, total, spine_match / total, edge_match / total
    break
  if len(gparse[0]) != len(aparse[0]) or len(gparse[1]) != len(aparse[1]):
    continue
  total += len(gparse[0])
  for i in xrange(len(gparse[0])):
    if gparse[0][i] == aparse[0][i]:
      spine_match += 1.0
    if gparse[1][i] == aparse[1][i]:
      edge_match += 1.0
