#!/usr/bin/env python

import sys
import ptb, head_finder, render_tree
from collections import defaultdict
from StringIO import StringIO
import re
import glob

def read_conll_parses(lines):
	in_file = StringIO(''.join(lines))
	return ptb.read_trees(in_file, input_format='ontonotes')

def read_conll_text(lines):
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

def read_conll_coref(lines):
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

def read_conll_doc(filename, ans=None, rtext=True, rparses=True, rheads=True, rclusters=True):
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
					info = []
					if rtext:
						info.append(read_conll_text(cur))
					if rparses:
						info.append(read_conll_parses(cur))
###						TODO: catch exceptions (or don't raise them) for unknown tags
###						if rheads:
###							info.append([head_finder.collins_find_heads(parse) for parse in info[-1]])
					if rclusters:
						info.append(read_conll_coref(cur))
					ans[keys[0]][keys[1]] = tuple(info)
					keys = None
			cur = []
		else:
			cur.append(line)
	return ans

def read_matching_files(conll_docs, dir_prefix):
	# Read the corresponding file under dir_prefix
	ans = None
	for filename in conll_docs:
		query = dir_prefix + '/' + filename + '*gold*conll'
		filenames = glob.glob(query)
		if len(filenames) == 1:
			ans = read_conll_doc(filenames[0], ans)
		else:
			print "Failed for %s/%s" % (dir_prefix, filename)
	return ans

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "Read conll information:"
		print "   %s <prefix> <gold_dir> <test>" % sys.argv[0]
		sys.exit(0)
	print "# This was generated by the following command:\n# " + ' '.join(sys.argv)

	auto = read_conll_doc(sys.argv[3])
	gold = read_matching_files(auto, sys.argv[2])
	print auto.keys()
	print gold.keys()
