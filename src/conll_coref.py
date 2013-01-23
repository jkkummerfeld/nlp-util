#!/usr/bin/env python

import sys
import ptb, head_finder, render_tree
from collections import defaultdict
from StringIO import StringIO
import re
import glob

def read_parses(lines):
	in_file = StringIO(''.join(lines))
	return ptb.read_trees(in_file, input_format='ontonotes')

def read_text(lines):
	text = [[]]
	for line in lines:
		fields = line.strip().split()
		if len(fields) == 0:
			text.append([])
		else:
			text[-1].append(fields[3])
	if len(text[-1]) == 0:
		text.pop()
	return text

def read_coref(lines):
	# Assumes:
	#  - Reading a single part
	#  - Each mention has a unique span
	#  - No crossing mentions (where s1 < s2 < e1 < e2)
	regex = "([(][0-9]*[)])|([(][0-9]*)|([0-9]*[)])"
	mentions = {} # (start, end+1) -> ID
	clusters = defaultdict(lambda: []) # ID -> list of (start, end+1)s
	unmatched_mentions = defaultdict(lambda: [])

	sentence = 0
	word = 0
	for line in lines:
		if len(line) > 0 and line[0] =='#':
			continue
		line = ''.join(line.strip().split('|'))
		if len(line) == 0:
			sentence += 1
			word = 0
			continue
		fields = line.strip().split()
		for triple in re.findall(regex, fields[-1]):
			if triple[1] != '':
				val = int(triple[1][1:])
				unmatched_mentions[(sentence, val)].append(word)
			elif triple[0] != '' or triple[2] != '':
				start = word
				val = -1
				if triple[0] != '':
					val = int(triple[0][1:-1])
				else:
					val = int(triple[2][:-1])
					if (sentence, val) not in unmatched_mentions:
						print >> sys.stderr, "Ending mention with no start:", val
						sys.exit(1)
					start = unmatched_mentions[(sentence, val)].pop()
				end = word + 1
				mentions[(sentence, start, end)] = val
				clusters[val].append((sentence, start, end))
		word += 1
	return mentions, clusters

def read_doc(filename, ans=None, rtext=True, rparses=True, rheads=True, rclusters=True):
	# Read entire file, inserting into a dictionary:
	#  key - the #begin <blah> info
	#  value - a dict, one entry per part, each entry contains:
	#     - text
	#     - parses
	#     - heads
	#     - coreference clusters
	if ans is None:
		ans = defaultdict(lambda: {})
	cur = []
	keys = None
	for line in open(filename):
		if len(line) > 0 and line[0] == '#':
			if 'begin' in line:
				desc = line.split()
				location = desc[2].strip('();')
				keys = (location, desc[-1])
			if len(cur) > 0:
				if keys is None:
					print >> sys.stderr, "Error reading conll file - invalid #begin statement"
				else:
					info = {}
					if rtext:
						info['text'] = read_text(cur)
					if rparses:
						info['parses'] = read_parses(cur)
						if rheads:
							info['heads'] = [head_finder.collins_find_heads(parse) for parse in info['parses']]
					if rclusters:
						info['mentions'], info['clusters'] = read_coref(cur)
					ans[keys[0]][keys[1]] = info
					keys = None
			cur = []
		else:
			cur.append(line)
	return ans

def read_coref_system_output(filename, ans=None):
	return read_doc(filename, ans, False, False, False, True)

def read_matching_files(conll_docs, dir_prefix):
	# Read the corresponding file under dir_prefix
	ans = None
	for filename in conll_docs:
		query = dir_prefix + '/' + filename + '*gold*conll'
		filenames = glob.glob(query)
		if len(filenames) == 1:
			ans = read_doc(filenames[0], ans)
		else:
			print "Reading matching doc failed for %s/%s as %d files were found." % (dir_prefix, filename, len(filenames))
	return ans

if __name__ == "__main__":
	print "Running doctest"
	import doctest
	doctest.testmod()
