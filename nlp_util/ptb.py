#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

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
		subtrees = [remove_trivial_unaries(tree, False) for tree in tree.subtrees]
		ans = PSTree()
		ans.word = tree.word
		ans.label = tree.label
		ans.span = tree.span
		ans.subtrees = subtrees
		for subtree in subtrees:
			subtree.parent = ans
		return ans

def remove_traces(tree, left=0, in_place=True):
	'''Adjust the tree to remove traces.

	>>> tree = ptbtree_from_text("(ROOT (S (PP (IN By) (NP (CD 1997))) (, ,) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed) (NP (-NONE- *-6))))) (. .)))")
	>>> ctree = remove_traces(tree)
	>>> print ctree
	(ROOT (S (PP (IN By) (NP (CD 1997))) (, ,) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed)))) (. .)))
	'''
	if tree.is_trace():
		return None
	right = left
	if tree.word is not None:
		right = left + 1
	subtrees = []
	for subtree in tree.subtrees:
		nsubtree = remove_traces(subtree, right)
		if nsubtree != None:
			subtrees.append(nsubtree)
			right = nsubtree.span[1]
	if tree.word is None and len(subtrees) == 0:
		return None
	ans = PTB_Tree()
	ans.word = tree.word
	ans.label = tree.label
	ans.span = (left, right)
	ans.subtrees = subtrees
	for subtree in subtrees:
		subtree.parent = ans
	return ans

def remove_function_tags(tree):
	'''Adjust the tree to remove function tags on labels.

	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))")
	>>> ctree = remove_function_tags(tree)
	>>> print ctree
	(ROOT (S (NP (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))

	# don't remove brackets
	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (`` ``) (NP-TTL (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP-PRD (NP (NN anything)) (PP (RB but)))) (. .)))")
	>>> ctree = remove_function_tags(tree)
	>>> print ctree
	(ROOT (S (NP (`` ``) (NP (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP (NP (NN anything)) (PP (RB but)))) (. .)))
	'''
	ans = PTB_Tree()
	ans.word = tree.word
	ans.label = tree.label
	if len(ans.label) > 0 and ans.label[0] != '-':
		ans.label = ans.label.split('-')[0]
	ans.label = ans.label.split('=')[0]
	ans.span = (tree.span[0], tree.span[1])
	ans.subtrees = []
	for subtree in tree.subtrees:
		nsubtree = remove_function_tags(subtree)
		ans.subtrees.append(nsubtree)
		nsubtree.parent = ans
	return ans

# Applies rules to strip out the parts of the tree that are not used in the
# standard evalb evaluation
labels_to_ignore = set(["-NONE-",",",":","``","''","."])
words_to_ignore = set([])
#words_to_ignore = set(["'","`","''","``","--",":",";","-",",",".","...",".","?","!"])
POS_to_convert = {'PRT': 'ADVP'}
def apply_collins_rules(tree, left=0):
	'''Adjust the tree to remove parts not evaluated by the standard evalb
	config.

	# cutting punctuation and -X parts of labels
	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag) ) (VP (VBZ plays) (NP (NNP Elianti) )) (. .) ))")
	>>> ctree = apply_collins_rules(tree)
	>>> print ctree
	(ROOT (S (NP (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti)))))
	>>> print ctree.word_yield()
	Ms. Haag plays Elianti

	# cutting nulls
	>>> tree = ptbtree_from_text("(ROOT (S (PP-TMP (IN By) (NP (CD 1997))) (, ,) (NP-SBJ-6 (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed) (NP (-NONE- *-6))))) (. .)))")
	>>> ctree = apply_collins_rules(tree)
	>>> print ctree
	(ROOT (S (PP (IN By) (NP (CD 1997))) (NP (NP (ADJP (RB almost) (DT all)) (VBG remaining) (NNS uses)) (PP (IN of) (NP (JJ cancer-causing) (NN asbestos)))) (VP (MD will) (VP (VB be) (VP (VBN outlawed))))))

	# changing PRT to ADVP
	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ-41 (DT That) (NN fund)) (VP (VBD was) (VP (VBN put) (NP (-NONE- *-41)) (PRT (RP together)) (PP (IN by) (NP-LGS (NP (NNP Blackstone) (NNP Group)) (, ,) (NP (DT a) (NNP New) (NNP York) (NN investment) (NN bank)))))) (. .)))")
	>>> ctree = apply_collins_rules(tree)
	>>> print ctree
	(ROOT (S (NP (DT That) (NN fund)) (VP (VBD was) (VP (VBN put) (ADVP (RP together)) (PP (IN by) (NP (NP (NNP Blackstone) (NNP Group)) (NP (DT a) (NNP New) (NNP York) (NN investment) (NN bank))))))))

	# not removing brackets
	>>> tree = ptbtree_from_text("(ROOT (S (NP-SBJ (`` ``) (NP-TTL (NNP Funny) (NNP Business)) ('' '') (PRN (-LRB- -LRB-) (NP (NNP Soho)) (, ,) (NP (CD 228) (NNS pages)) (, ,) (NP ($ $) (CD 17.95) (-NONE- *U*)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP-PRD (NP (NN anything)) (PP (RB but) (NP (-NONE- *?*))))) (. .)))")
	>>> ctree = apply_collins_rules(tree)
	>>> print ctree
	(ROOT (S (NP (NP (NNP Funny) (NNP Business)) (PRN (-LRB- -LRB-) (NP (NNP Soho)) (NP (CD 228) (NNS pages)) (NP ($ $) (CD 17.95)) (-RRB- -RRB-)) (PP (IN by) (NP (NNP Gary) (NNP Katzenstein)))) (VP (VBZ is) (NP (NP (NN anything)) (PP (RB but))))))
	'''
	if tree.label in labels_to_ignore:
		return None
	if tree.word in words_to_ignore:
		return None
	ans = PTB_Tree()
	ans.word = tree.word
	ans.label = tree.label
	ans.span = (left, -1)
	right = left
	if ans.word is not None:
		right = left + 1
		ans.span = (left, right)
	subtrees = []
	ans.subtrees = subtrees
	for subtree in tree.subtrees:
		nsubtree = apply_collins_rules(subtree, right)
		if nsubtree != None:
			subtrees.append(nsubtree)
			nsubtree.parent = ans
			right = nsubtree.span[1]
	ans.span = (left, right)
	if ans.word is None and len(ans.subtrees) == 0:
		return None
	if ans.label in POS_to_convert:
		ans.label = POS_to_convert[ans.label]
	try:
		if not ans.label[0] == '-':
			ans.label = ans.label.split('-')[0]
	except:
		raise Exception("Collins rule application issue:" + str(tree.get_root()))
	ans.label = ans.label.split('=')[0]
	return ans

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

