#!/usr/bin/env python

import sys
try:
	from nlp_util import ptb
except ImportError:
	raise Exception("Remember to either install nlp_util or set up a symlink to the nlp_util directory")

from collections import defaultdict

def print_span_errors(gold_tree, test_trees):
	errors = defaultdict(lambda: [0 for i in xrange(len(test_trees))])
	for i in xrange(len(test_trees)):
		tree = test_trees[i]
		gold_span_set = gold_tree.span_dict()
		for node in tree:
			span = (node.label, node.span[0], node.span[1])
			if span in gold_span_set and gold_span_set[span] > 0:
				gold_span_set[span] -= 1
				if span[0] in ptb.tag_set:
					errors[(span, 'correct')][i] += 1
			else:
				if span[0] in ptb.tag_set:
					errors[(span, 'extra')][i] += 1
		for span in gold_span_set:
			for j in xrange(gold_span_set[span]):
				if span[0] in ptb.tag_set:
					errors[(span, 'missing')][i] += 1
	
	for error in errors:
		count = 0
		text = []
		for val in errors[error]:
			if val != 0:
				text.append('1')
				count += 1
			else:
				text.append('.')
		text = ' '.join(text)
		print error[1], error[0][0], count, text

if __name__ == '__main__':
	if len(sys.argv) == 1:
		print "Print counts of the number of bracket errors:"
		print "   %s <gold> <test1> [<test2>, <test3>...]" % sys.argv[0]
		print "Options:"
		print "  -p, print production errors"
		print "  -b, print bracket errors"
		print "  If neither option is given, brackets are the default"
		print "Running doctest"
		import doctest
		doctest.testmod()
		sys.exit(0)

	args = [val for val in sys.argv if val[0] != '-']
	gold_in = ptb.generate_trees(args[1], return_empty=True)
	test_in = []
	for arg in args[2:]:
		test_in.append(ptb.generate_trees(arg, return_empty=True))

	done = 0
	while True:
		done += 1
		try:
			gold_tree = gold_in.next()
			test_trees = [src.next() for src in test_in]
			skip = False
			for tree in test_trees:
				if tree is None:
					skip = True
					continue
			if skip:
				continue
		except StopIteration:
			break

		gold_tree = ptb.apply_collins_rules(gold_tree)
		test_trees = [ptb.apply_collins_rules(tree) for tree in test_trees]

		# By default, do this
		if '-b' in sys.argv or '-p' not in sys.argv:
			print_span_errors(gold_tree, test_trees)
###		if '-p' in sys.argv:
###			print_production_errors(gold_tree, test_trees)

