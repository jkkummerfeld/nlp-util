#!/usr/bin/env python

import sys
try:
	from nlp_util import ptb
except ImportError:
	raise Exception("Remember to either install nlp_util or set up a symlink to the nlp_util directory")

from collections import defaultdict

def update_span_errors(gold_tree, test1_tree, test2_tree, errors):
	# Record errors for first tree
	extra = defaultdict(lambda: 0)
	missing = defaultdict(lambda: 0)
	gold_span_set = gold_tree.span_dict()
	for node in test1_tree:
		span = (node.label, node.span[0], node.span[1])
		if span in gold_span_set and gold_span_set[span] > 0:
			gold_span_set[span] -= 1
		else:
			extra[span] += 1
	for span in gold_span_set:
		for i in xrange(gold_span_set[span]):
			missing[span] += 1

	# Look at errors from the second tree
	gold_span_set = gold_tree.span_dict()
	for node in test2_tree:
		span = (node.label, node.span[0], node.span[1])
		if span in gold_span_set and gold_span_set[span] > 0:
			gold_span_set[span] -= 1
		else:
			if span in extra:
				errors[span[0]]['extra'][2] += 1
				extra[span] -= 1
			else:
				errors[span[0]]['extra'][0] += 1
	for span in extra:
		for i in xrange(extra[span]):
			errors[span[0]]['extra'][1] += 1
	for span in gold_span_set:
		for i in xrange(gold_span_set[span]):
			if span in missing:
				errors[span[0]]['missing'][2] += 1
				extra[span] -= 1
			else:
				errors[span[0]]['missing'][0] += 1
	for span in missing:
		for i in xrange(missing[span]):
			errors[span[0]]['missing'][1] += 1

if __name__ == '__main__':
	if len(sys.argv) == 1:
		print "Measure correlation in errors made by systems"
		print "   %s <gold> <test1> <test2>" % sys.argv[0]
		print "Running doctest"
		import doctest
		doctest.testmod()
		sys.exit(0)

	args = [val for val in sys.argv if val[0] != '-']
	gold_in = ptb.generate_trees(args[1], return_empty=True)
	test1_in = ptb.generate_trees(args[2], return_empty=True)
	test2_in = ptb.generate_trees(args[3], return_empty=True)

	span_errors = defaultdict(lambda: {'extra': [0, 0, 0], 'missing': [0, 0, 0]})
	while True:
		try:
			gold_tree = gold_in.next()
			test1_tree = test1_in.next()
			test2_tree = test2_in.next()
			if test1_tree is None or test2_tree is None:
				continue
		except StopIteration:
			break

		gold_tree = ptb.apply_collins_rules(gold_tree)
		test1_tree = ptb.apply_collins_rules(test1_tree)
		test2_tree = ptb.apply_collins_rules(test2_tree)

		update_span_errors(gold_tree, test1_tree, test2_tree, span_errors)

	for label in span_errors:
		for val in ['extra', 'missing']:
			print ' '.join([str(val) for val in span_errors[label][val]]),
		print label
