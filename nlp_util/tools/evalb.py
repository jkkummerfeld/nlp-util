#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

# TODO currently assumes all CoNLL / OntoNotes trees are in the same order

from __future__ import print_function

import sys

from nlp_util import pstree, nlp_eval, treebanks, parse_errors, init

options = {
	# 'option_word': ((valid options or type), default, "Long description"),
	"config_file": [str, None, # TODO
		"A file containing option settings.  If options other than this are"
		"specified, they will override settings in the file"],
	# Input
	"gold": [str, "-", # TODO - part
		"The file containing gold trees, if '-', stdin is used"],
	"test": [str, "-", # TODO - part
		"The file containing system produced trees, if '-', stdin is used"],
	"gold_input": [('ptb', 'ontonotes'), 'ptb',
		"Input format for the gold file: PTB (single or multiple lines per parse),"
		"OntoNotes (one file in all cases)"],
	"test_input": [('ptb', 'ontonotes'), 'ptb',
		"Input format for the test file: PTB (single or multiple lines per parse),"
		"OntoNotes (one file in all cases)"],
	# Scoring modification
	"labelled_score": [bool, True, # TODO
		"Labeled or unlabelled score"],
	"include_POS_in_score": [bool, False,
		"Include POS tags in overall score"],
	"include_unparsed_in_score": [bool, True,
		"Include missed sentences in overall score"],
	"summary_cutoffs": [[int], [40], # TODO
		"Cutoff lengths for summaries"],
	"averaging": [('macro', 'micro'), 'macro', # TODO
		"How to calculate the overall scores, with a macro average (score for sums"
		"of counts) or micro average (average of scores for each count)"],
	# Tree modification
	"remove_trivial_unaries": [bool, True,
		"Remove unaries that go from a label to iself,"
		"e.g. (NP (NP (NNP it))) has one"],
	"remove_function_labels": [bool, True,
		"Remove function labels, e.g. NP-TMP, remove the -TMP part"],
	"homogenise_top_label": [bool, True,
		"Homogenise the top labels, so all are ROOT"],
	"labels_to_remove": [[str],
		["TOP", "ROOT", "S1", "-NONE-", ",", ":", "``", "''", "."],
		"Remove nodes with the given labels, keep subtrees, but remove"
		"parents that now have a span of size 0"],
	"words_to_remove": [[str], [],
		"Remove nodes with the given words, and do as for labels"],
	"equivalent_labels": [[(str, str)], [("ADVP", "PRT")],
		"Labels to treat as equivalent"],
	"equivalent_words": [[(str, str)], [],
		"Words to treat as equivalent"],
}


# Provide current execution info
out = sys.stdout
init.header(sys.argv, out)


# Handle options
test_in = None
gold_in = None
if len(sys.argv) == 1:
	# TODO
	sys.exit()
elif len(sys.argv) == 2:
	# TODO
	sys.exit()
elif len(sys.argv) == 3:
	# Run with defaults, assume the two arguments are the gold and test files
	options['gold'][1] = sys.argv[1]
	options['test'][1] = sys.argv[2]
else:
	# TODO
	sys.exit()

# Print list of options in use
for option in options:
	print("# {: <28} : {}".format(option, str(options[option][1])))

# Set up reading
test_in = open(options['test'][1])
test_tree_reader = treebanks.ptb_read_tree
if options["test_input"][1] == 'ontonotes':
	test_tree_reader = treebanks.conll_read_tree

gold_in = open(options['gold'][1])
gold_tree_reader = treebanks.ptb_read_tree
if options["gold_input"][1] == 'ontonotes':
	gold_tree_reader = treebanks.conll_read_tree

header = '''
Sentence                          Matched   Bracket    Cross  Correct  Tag
ID    Len    P       R       F    Bracket  gold test  Bracket  Tags  Accracy
============================================================================'''
print(header, file=out)

# Process sentences
scores = []
sent_id = 0
while True:
	sent_id += 1

	# Read trees
	test_tree = test_tree_reader(test_in, True, True, True, True)
	gold_tree = gold_tree_reader(gold_in, True, True, True, True)
	if test_tree is None or gold_tree is None:
		break
	if test_tree == "Empty":
		test_tree = None

	# Coverage error
	gwords = len(gold_tree.word_yield().split())
	if test_tree is None:
		match, gcount, tcount, crossing, POS = parse_errors.counts_for_prf(gold_tree,
			gold_tree, include_terminals=options['include_POS_in_score'][1])
		scores.append((sent_id, twords, 0, 0, 0, 0, gcount, 0, 0, 0, 0))
		print("{:4} {:4} {: >7.2f} {: >7.2f} {: >7.2f} {:5} {:6} {:4} {:7}"
			" {:7} {: >8.2f}".format(sent_id, gwords, 0, 0, 0, 0, gcount, 0, 0, 0, 0))
		continue

	# Simple check for consistency
	twords = len(test_tree.word_yield().split())
	if twords != gwords:
		print("Sentence lengths do not match: {} {}".format(twords, gwords))
		continue

	# Modify as per options
	if options["remove_function_labels"][1]:
		treebanks.remove_function_tags(test_tree)
		treebanks.remove_function_tags(gold_tree)
	if options["homogenise_top_label"][1]:
		test_tree = treebanks.homogenise_tree(test_tree)
		gold_tree = treebanks.homogenise_tree(gold_tree)
	if len(options['labels_to_remove'][1]) > 0:
		treebanks.remove_nodes(test_tree, lambda(n): n.label in options['labels_to_remove'][1], True, True)
		treebanks.remove_nodes(gold_tree, lambda(n): n.label in options['labels_to_remove'][1], True, True)
	if len(options['words_to_remove'][1]) > 0:
		treebanks.remove_nodes(test_tree, lambda(n): n.word in options['words_to_remove'][1], True, True)
		treebanks.remove_nodes(gold_tree, lambda(n): n.word in options['words_to_remove'][1], True, True)
	if len(options['equivalent_labels'][1]) > 0:
		for tree in [gold_tree, test_tree]:
			for node in gold_tree:
				for pair in options['equivalent_labels'][1]:
					if node.label in pair:
						node.label = pair[0]
	if len(options['equivalent_words'][1]) > 0:
		for tree in [gold_tree, test_tree]:
			for node in gold_tree:
				for pair in options['equivalent_words'][1]:
					if node.word in pair:
						node.word = pair[0]
	if options['remove_trivial_unaries'][1]:
		treebanks.remove_trivial_unaries(test_tree)
		treebanks.remove_trivial_unaries(gold_tree)

	# Score and report
	match, gcount, tcount, crossing, POS = parse_errors.counts_for_prf(test_tree,
		gold_tree, include_terminals=options['include_POS_in_score'][1])
	POS = twords - POS
	p, r, f = nlp_eval.calc_prf(match, gcount, tcount)
	f *= 100
	r *= 100
	p *= 100
	POS_acc = 100.0 * POS / twords

	print("{:4} {:4} {: >7.2f} {: >7.2f} {: >7.2f} {:5} {:6} {:4} {:7}"
		" {:7} {: >8.2f}".format(sent_id, gwords, p, r, f, match, gcount, tcount, crossing, POS, POS_acc))
	scores.append((sent_id, gwords, p, r, f, match, gcount, tcount, crossing, POS, POS_acc))
sent_id -= 1

# Work out summary
sents = float(sent_id)
parsed = len(filter(lambda x: x[7] != 0, scores))
if not options["include_unparsed_in_score"][1]:
	scores = filter(lambda x: x[7] > 0, scores)
	sents = float(parsed)
words = sum([val[1] for val in scores])
match = sum([val[5] for val in scores])
gcount = sum([val[6] for val in scores])
tcount = sum([val[7] for val in scores])
crossing = sum([val[8] for val in scores])
POS = sum([val[9] for val in scores])
p, r, f = nlp_eval.calc_prf(match, gcount, tcount)
f *= 100
r *= 100
p *= 100
POS_acc = 100.0 * POS / words
skipped = len(filter(lambda x: x[7] == 0, scores))
all_brackets_match = 100.0 * len(filter(lambda x: x[7] == x[6] == x[5], scores)) / sents
perfect = 100.0 * len(filter(lambda x: x[7] == x[6] == x[5] and x[1] == x[9], scores)) / sents
av_crossing = float(crossing) / sents
no_crossing = 100.0 * len(filter(lambda x: x[8] == 0, scores)) / sents
max2_crossing = 100.0 * len(filter(lambda x: x[8] <= 2, scores)) / sents

# Print Summary
print("============================================================================")
print("{:4} {:4} {: >7.2f} {: >7.2f} {: >7.2f} {:5} {:6} {:4} {:7}"
		" {:7} {: >8.2f}".format(sent_id, words, p, r, f, match, gcount, tcount, crossing, POS, POS_acc))
print('''=== Summary ===

-- All --''')
print("Number of sentence        = {:6}".format(sent_id))
print("Number of Skip  sentence  = {:6}".format(skipped))
print("Number of Valid sentence  = {:6}".format(parsed))
print("Bracketing Recall         = {:6.2f}".format(r))
print("Bracketing Precision      = {:6.2f}".format(p))
print("Bracketing FMeasure       = {:6.2f}".format(f))
print("Complete match            = {:6.2f}".format(all_brackets_match))
print("Perfect (match POS too)   = {:6.2f}".format(perfect))
print("Average crossing          = {:6.2f}".format(av_crossing))
print("No crossing               = {:6.2f}".format(no_crossing))
print("2 or less crossing        = {:6.2f}".format(max2_crossing))
print("Tagging accuracy          = {:6.2f}".format(sent_id)) #  93.66
