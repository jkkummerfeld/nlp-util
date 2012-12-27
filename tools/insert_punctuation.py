#!/usr/bin/env python

import sys
sys.path.insert(0, "util")
try:
	import ptb
except:
	raise Exception("Remember to set up a symlink to the util directory")

punct_to_POS = {
"!": ".",
"'": "''",
"''": "''",
",": ",",
"-": ":",
"--": ":",
".": ".",
"...": ":",
":": ":",
";": ":",
"?": ".",
"`": "``",
"``": "``"
}

def peek_at_next_word(node):
	if node.word is not None:
		return node.word
	return peek_at_next_word(node.subtrees[0])

def insert_punctuation(node, words):
	# Reached the bottom
	if node.word == words[0]:
		words.pop(0)
		return

	# Go through subtrees and add punctuation before them
	pos = 0
	if len(node.subtrees) == 1 and len(node.subtrees[pos].subtrees) != 0:
		insert_punctuation(node.subtrees[pos], words)
		return
	while pos < len(node.subtrees):
		if ptb.peek_at_next_word(node.subtrees[pos]) != words[0]:
			nnode = ptb.PTB_Tree()
			nnode.parent = node
			nnode.label = punct_to_POS[words[0]]
			nnode.word = words[0]
			node.subtrees.insert(pos, nnode)
			words.pop(0)
		else:
			insert_punctuation(node.subtrees[pos], words)
		pos += 1

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print "Add punctuation back into trees:"
		print "   %s <parse file> <token file>" % sys.argv[0]
		print "Running doctest"
		import doctest
		doctest.testmod()
	elif len(sys.argv) == 3:
		text_file = open(sys.argv[2])
		for tree in ptb.generate_trees(sys.argv[1], return_empty=True):
			text = text_file.readline().strip().split()
			if tree is None:
				print
				continue
			insert_punctuation(tree, text)
			if len(text) > 0:
				parent = tree
				while len(parent.subtrees) == 1 and len(parent.subtrees[0].subtrees) > 0:
					parent = parent.subtrees[0]
				for word in text:
					nnode = ptb.PTB_Tree()
					nnode.parent = parent
					nnode.label = punct_to_POS[word]
					nnode.word = word
					parent.subtrees.append(nnode)
			tree.calculate_spans()
			print tree
