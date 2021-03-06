#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

import sys
from nlp_util import pstree, head_finder

def headed_tree(tree, head_map, depth=0):
	ans = ''
	if depth > 0:
		ans = '\n' + depth * '\t'
	ans += '(' + tree.label + ' ' + str(head_finder.get_head(head_map, tree)[1])
	if tree.word is not None:
		ans += ' ' + tree.word
	for subtree in tree.subtrees:
		ans += headed_tree(subtree, head_map, depth + 1)
	ans += ')'
	return ans

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

	tree = pstree.tree_from_text("(ROOT (SINV (S (NP (PRP It)) (VP (AUX 's) (NP (NP (DT a) (NN problem)) (SBAR (WHNP (WDT that)) (S (ADVP (RB clearly)) (VP (AUX has) (S (VP (TO to) (VP (VB be) (VP (VBN resolved))))))))))) (VP (VBD said)) (NP (NP (NNP David) (NNP Cooke)) (NP (NP (JJ executive) (NN director)) (PP (IN of) (NP (DT the) (NNP RTC)))))))")
	head_map = head_finder.pennconverter_find_heads(tree)
	print headed_tree(tree, head_map)
