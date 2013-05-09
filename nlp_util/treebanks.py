#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict
from pstree import *

# TODO: Handle malformed input with trees that have random stuff instead of symbols
# For chinese I found:
###	leaf nodes split across lines:
###			(blah
###				 ))
###	lone tags:
###				CP (IP...

tag_set = set(['S', 'SBAR', 'SBARQ', 'SINV', 'SQ', 'ADJP', 'ADVP', 'CONJP',
'FRAG', 'INTJ', 'LST', 'NAC', 'NP', 'NX', 'PP', 'PRN', 'PRT', 'QP', 'RRC',
'UCP', 'VP', 'WHADJP', 'WHADVP', 'WHNP', 'WHPP', 'X'])

word_to_word_mapping = {
	'{': '-LCB-',
	'}': '-RCB-'
}
word_to_POS_mapping = {
	'--': ':',
	'-': ':',
	';': ':',
	':': ':',
	'-LRB-': '-LRB-',
	'-RRB-': '-RRB-',
	'-LCB-': '-LRB-',
	'-RCB-': '-RRB-',
	'{': '-LRB-',
	'}': '-RRB-',
}
bugfix_word_to_POS = {
	'Wa': 'NNP'
}
###	the POS replacement leads to incorrect tagging for some punctuation
def standardise_node(tree):
	if tree.word in word_to_word_mapping:
		tree.word = word_to_word_mapping[tree.word]
	if tree.word in word_to_POS_mapping:
		tree.label = word_to_POS_mapping[tree.word]
	if tree.word in bugfix_word_to_POS:
		tree.label = bugifx_word_to_POS[tree.word]

def ptbtree_from_text(text, allow_empty_labels=False, allow_empty_words=False):
	tree = tree_from_text(text, allow_empty_labels, allow_empty_words)

	for node in tree:
		if '|' in node.label:
			if 'ADVP' in node.label:
				node.label = 'ADVP'
			else:
				node.label = node.label.split('|')[0]
		# Fix some issues with variation in output, and one error in the treebank
		# for a word with a punctuation POS
		standardise_node(node)
	return tree

def remove_trivial_unaries(tree, in_place=True):
	'''Collapse A-over-A unary productions.

	>>> tree = ptbtree_from_text("(ROOT (S (PP (PP (IN By) (NP (CD 1997))))))")
	>>> otree = remove_trivial_unaries(tree, False)
	>>> print otree
	(ROOT (S (PP (IN By) (NP (CD 1997)))))
	>>> print tree
	(ROOT (S (PP (PP (IN By) (NP (CD 1997))))))
	>>> remove_trivial_unaries(tree)
	>>> print tree
	(ROOT (S (PP (IN By) (NP (CD 1997)))))
	'''
	if in_place:
		if len(tree.subtrees) == 1 and tree.label == tree.subtrees[0].label:
			tree.subtrees = tree.subtrees[0].subtrees
			for subtree in tree.subtrees:
				subtree.parent = tree
		for subtree in tree.subtrees:
			remove_trivial_unaries(subtree, True)
		return
	else:
		if len(tree.subtrees) == 1 and tree.label == tree.subtrees[0].label:
			return remove_trivial_unaries(tree.subtrees[0], False)
		subtrees = [remove_trivial_unaries(subtree, False) for subtree in tree.subtrees]
		ans = PSTree(tree.word, tree.label, tree.span, None, subtrees)
		for subtree in subtrees:
			subtree.parent = ans
		return ans

def remove_traces(tree, in_place=True):
	'''Adjust the tree to remove traces.

	>>> tree = ptbtree_from_text("(ROOT (S (PP (IN By) (NP (CD 1997))) (, ,) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed) (NP (-NONE- *-6))))) (. .)))")
	>>> ctree = remove_traces(tree, False)
	>>> print ctree
	(ROOT (S (PP (IN By) (NP (CD 1997))) (, ,) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed)))) (. .)))
	'''
	if tree.is_trace():
		return None
	subtrees = []
	for subtree in tree.subtrees:
		ans = remove_traces(subtree, in_place)
		if ans is not None:
			subtrees.append(ans)
			if in_place:
				ans.parent = tree
	if len(subtrees) == 0 and (not tree.is_terminal()):
		return None
	if in_place:
		tree.subtrees = subtrees
		return tree
	else:
		ans = PSTree(tree.word, tree.label, tree.span, None, subtrees)
		return ans

def remove_function_tags(tree, in_place=True):
	'''Adjust the tree to remove function tags on labels.

	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))")
	>>> ctree = remove_function_tags(tree, False)
	>>> print ctree
	(ROOT (S (NP (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))

	# don't remove brackets
	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (`` ``) (NP-TTL (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP-PRD (NP (NN anything)) (PP (RB but)))) (. .)))")
	>>> remove_function_tags(tree)
	>>> print tree
	(ROOT (S (NP (`` ``) (NP (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP (NP (NN anything)) (PP (RB but)))) (. .)))
	'''
	label = tree.label
	if len(label) > 0 and label[0] != '-':
		label = label.split('-')[0]
	label = label.split('=')[0]
	if in_place:
		for subtree in tree.subtrees:
			remove_function_tags(subtree, True)
		tree.label = label
		return
	else:
		subtrees = [remove_function_tags(subtree, False) for subtree in tree.subtrees]
		ans = PSTree(tree.word, label, tree.span, None, subtrees)
		for subtree in subtrees:
			subtree.parent = ans
		return ans

# Applies rules to strip out the parts of the tree that are not used in the
# standard evalb evaluation
labels_to_ignore = set(["-NONE-",",",":","``","''","."])
words_to_ignore = set([])
#words_to_ignore = set(["'","`","''","``","--",":",";","-",",",".","...",".","?","!"])
###POS_to_convert = {'PRT': 'ADVP'}
###def apply_collins_rules(tree, left=0):
###	'''Adjust the tree to remove parts not evaluated by the standard evalb
###	config.

###	# cutting punctuation and -X parts of labels
###	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag) ) (VP (VBZ plays) (NP (NNP Elianti) )) (. .) ))")
###	>>> ctree = apply_collins_rules(tree)
###	>>> print ctree
###	(ROOT (S (NP (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti)))))
###	>>> print ctree.word_yield()
###	Ms. Haag plays Elianti

###	# cutting nulls
###	>>> tree = ptbtree_from_text("(ROOT (S (PP-TMP (IN By) (NP (CD 1997))) (, ,) (NP-SBJ-6 (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed) (NP (-NONE- *-6))))) (. .)))")
###	>>> ctree = apply_collins_rules(tree)
###	>>> print ctree
###	(ROOT (S (PP (IN By) (NP (CD 1997))) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed))))))

###	# changing PRT to ADVP
###	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ-41 (DT That) (NN fund)) (VP (VBD was) (VP (VBN put) (NP (-NONE- *-41)) (PRT (RP together)) (PP (IN by) (NP-LGS (NP (NNP Blackstone) (NNP Group)) (, ,) (NP (DT a) (NNP New) (NNP York) (NN investment) (NN bank)))))) (. .)))")
###	>>> ctree = apply_collins_rules(tree)
###	>>> print ctree
###	(ROOT (S (NP (DT That) (NN fund)) (VP (VBD was) (VP (VBN put) (ADVP (RP together)) (PP (IN by) (NP (NP (NNP Blackstone) (NNP Group)) (NP (DT a) (NNP New) (NNP York) (NN investment) (NN bank))))))))

###	# not removing brackets
###	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (`` ``) (NP-TTL (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95) (-NONE- *U*)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP-PRD (NP (NN anything)) (PP (RB but) (NP (-NONE- *?*))))) (. .)))")
###	>>> ctree = apply_collins_rules(tree)
###	>>> print ctree
###	(ROOT (S (NP (NP (NNP Funny) (NNP Business)) (PRN (-LRB- -LRB-) (NP (NNP Soho)) (NP (CD 228) (NNS pages)) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP (NP (NN anything)) (PP (RB but))))))
###	'''
###	if tree.label in labels_to_ignore:
###		return None
###	if tree.word in words_to_ignore:
###		return None
###	ans = PTB_Tree()
###	ans.word = tree.word
###	ans.label = tree.label
###	ans.span = (left, -1)
###	right = left
###	if ans.word is not None:
###		right = left + 1
###		ans.span = (left, right)
###	subtrees = []
###	ans.subtrees = subtrees
###	for subtree in tree.subtrees:
###		nsubtree = apply_collins_rules(subtree, right)
###		if nsubtree != None:
###			subtrees.append(nsubtree)
###			nsubtree.parent = ans
###			right = nsubtree.span[1]
###	ans.span = (left, right)
###	if ans.word is None and len(ans.subtrees) == 0:
###		return None
###	if ans.label in POS_to_convert:
###		ans.label = POS_to_convert[ans.label]
###	try:
###		if not ans.label[0] == '-':
###			ans.label = ans.label.split('-')[0]
###	except:
###		raise Exception("Collins rule application issue:" + str(tree.get_root()))
###	ans.label = ans.label.split('=')[0]
###	return ans

###def homogenise_tree(tree):
###	tree = tree.root()
###	if tree.label != 'ROOT':
###		while tree.label not in tag_set:
###			if len(tree.subtrees) > 1:
###				break
###			elif len(tree.subtrees) == 0:
###				tree.label = 'ROOT'
###				return tree
###			tree = tree.subtrees[0]
###		if tree.label not in tag_set:
###			tree.label = 'ROOT'
###		else:
###			root = PTB_Tree()
###			root.subtrees.append(tree)
###			root.label = 'ROOT'
###			root.span = tree.span
###			tree.parent = root
###			tree = root
###	return tree

def ptb_read_tree(source, return_empty=False):
	'''Read a single tree from the given file.
	
	>>> from StringIO import StringIO
	>>> file_text = """(ROOT (S
	...   (NP-SBJ (NNP Scotty) )
	...   (VP (VBD did) (RB not)
	...     (VP (VB go)
	...       (ADVP (RB back) )
	...       (PP (TO to)
	...         (NP (NN school) ))))
	...   (. .) ))"""
	>>> in_file = StringIO(file_text)
	>>> tree = ptb_read_tree(in_file)
	>>> print tree
	(ROOT (S (NP-SBJ (NNP Scotty)) (VP (VBD did) (RB not) (VP (VB go) (ADVP (RB back)) (PP (TO to) (NP (NN school))))) (. .)))'''
	cur_text = ''
	depth = 0
	while True:
		line = source.readline()
		# Check if we are out of input
		if line == '':
			return None

		line = line.strip()
		for char in line:
			cur_text += char
			if char == '(':
				depth += 1
			elif char == ')':
				depth -= 1
			if depth == 0:
				if '()' in cur_text:
					if return_empty:
						return "Empty"
					cur_text = ''
					continue
				tree = ptbtree_from_text(cur_text)
				return tree
	return None

###def read_tree(source, return_empty=False, input_format='ptb'):
###	'''Read a single tree from the given file.
###	
###	>>> from StringIO import StringIO
###	>>> file_text = """(ROOT (S
###	...   (NP-SBJ (NNP Scotty) )
###	...   (VP (VBD did) (RB not)
###	...     (VP (VB go)
###	...       (ADVP (RB back) )
###	...       (PP (TO to)
###	...         (NP (NN school) ))))
###	...   (. .) ))"""
###	>>> in_file = StringIO(file_text)
###	>>> tree = read_tree(in_file)
###	>>> print tree
###	(ROOT (S (NP-SBJ (NNP Scotty)) (VP (VBD did) (RB not) (VP (VB go) (ADVP (RB back)) (PP (TO to) (NP (NN school))))) (. .)))'''
###	cur_text = []
###	depth = 0 if input_format == 'ptb' else -1
###	while True:
###		line = source.readline()
###		# Check if we are out of input
###		if line == '':
###			return None
###		# strip whitespace and only use if this contains something
###		line = line.strip()
###		if line == '':
###			# Check for OntoNotes style input
###			if input_format == 'ontonotes':
###				text = ''
###				for line in cur_text:
###					if len(line) == 0 or line[0] == '#':
###						continue
###					line = line.split()
###					word = line[3]
###					pos = line[4]
###					tree = line[5]
###					tree = tree.split('*')
###					text += '%s(%s %s)%s' % (tree[0], pos, word, tree[1])
###				text = ' '.join(text.split('_')).strip()
###				tree = PTB_Tree()
###				tree = ptbtree_from_text(text)
###				tree.label = 'ROOT'
###				return tree
###			elif return_empty:
###				return "Empty"
###			continue
###		cur_text.append(line)

###		# Update depth
###		if depth >= 0:
###			for char in line:
###				if char == '(':
###					depth += 1
###				elif char == ')':
###					depth -= 1

###		# PTB style - At depth 0 we have a complete tree
###		if depth == 0:
###			cur_text = ' '.join(cur_text)
###			if '()' in cur_text:
###				cur_text = []
###				if return_empty:
###					return "Empty"
###				continue
###			tree = ptbtree_from_text(cur_text)
###			return tree
###	return None

###def generate_trees(source, max_sents=-1, return_empty=False, input_format='ptb', homogenise=True):
###	'''Read trees from the given file (opening the file if only a string is given).

###	This version is a generator, yielding one tree at a time.
###	
###	>>> from StringIO import StringIO
###	>>> file_text = """(ROOT (S
###	...   (NP-SBJ (NNP Scotty) )
###	...   (VP (VBD did) (RB not)
###	...     (VP (VB go)
###	...       (ADVP (RB back) )
###	...       (PP (TO to)
###	...         (NP (NN school) ))))
###	...   (. .) ))
###	...
###	... (ROOT (S 
###	... 		(NP-SBJ (DT The) (NN bandit) )
###	... 		(VP (VBZ laughs) 
###	... 			(PP (IN in) 
###	... 				(NP (PRP$ his) (NN face) )))
###	... 		(. .) ))"""
###	>>> in_file = StringIO(file_text)
###	>>> for tree in generate_trees(in_file):
###	...   print tree
###	(ROOT (S (NP-SBJ (NNP Scotty)) (VP (VBD did) (RB not) (VP (VB go) (ADVP (RB back)) (PP (TO to) (NP (NN school))))) (. .)))
###	(ROOT (S (NP-SBJ (DT The) (NN bandit)) (VP (VBZ laughs) (PP (IN in) (NP (PRP$ his) (NN face)))) (. .)))'''
###	if type(source) == type(''):
###		source = open(source)
###	count = 0
###	while True:
###		tree = read_tree(source, return_empty, input_format)
###		if tree == "Empty":
###			yield None
###			continue
###		if tree is None:
###			return
###		yield tree
###		count += 1
###		if count >= max_sents > 0:
###			return

###def read_trees(source, max_sents=-1, return_empty=False, input_format='ptb'):
###	return [tree for tree in generate_trees(source, max_sents, return_empty, input_format)]

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

