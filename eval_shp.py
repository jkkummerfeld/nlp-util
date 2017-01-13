#!/usr/bin/env python3

import sys

def read_parse(src):
  summaries = []
  while True:
    line = src.readline()
    if line == '':
      return None
    elif line.strip() == '':
      break
    if line[0] != '#':
      parts = line.strip().split()
      spine = parts[3]
      edge = ' '.join([parts[0], parts[4], parts[5]])
      traces = []
      for i in range(6, len(parts), 6):
###        traces.append(' '.join(parts[i:i+6]))
        traces.append(parts[i])
      summaries.append((spine, edge, traces))
  return summaries

def results(gcounts, acounts, matches):
  for word in matches:
    g = gcounts[word]
    m = matches[word]
    a = acounts[word]
    p = 0.0
    if a > 0:
      p = 100.0 * m / a
    r = 0.0
    if g > 0:
      r = 100.0 * m / g
    f = 0.0
    if (p+r) > 0:
      f = 2 * p * r / (p + r)
    print("{}  {:>4} {:>4} {:>4}  {:.1f} {:.1f} {:.1f}".format(word, m, g, a, p, r, f))

gold = open(sys.argv[1])
auto = open(sys.argv[2])

gcounts = { 'spine': 0, 'edge': 0, 'trace': 0 }
matches = { 'spine': 0, 'edge': 0, 'trace': 0 }
acounts = { 'spine': 0, 'edge': 0, 'trace': 0 }

total = 0
while True:
  gparse = read_parse(gold)
  aparse = read_parse(auto)
  if gparse is None or aparse is None:
    print("Failed on gold {} auto {}".format(gparse, aparse))
    break
  total += 1
  for i in range(len(gparse)):
    gcounts['spine'] += 1
    gcounts['edge'] += 1
    for trace in gparse[i][2]:
      gcounts['trace'] += 1
    if len(aparse) > i:
      if aparse[i][0] == gparse[i][0]:
        matches['spine'] += 1
      if aparse[i][1] == gparse[i][1]:
        matches['edge'] += 1
      for trace in gparse[i][2]:
        if trace in aparse[i][2]:
          matches['trace'] += 1
  for i in range(len(aparse)):
    acounts['spine'] += 1
    acounts['edge'] += 1
    for trace in aparse[i][2]:
      acounts['trace'] += 1

results(gcounts, acounts, matches)
print("Processed", total)
