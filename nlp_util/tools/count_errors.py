#!/usr/bin/env python

import sys
try:
	from nlp_util import ptb
except ImportError:
	raise Exception("Remember to either install nlp_util or set up a symlink to the nlp_util directory")

def update_span_errors(gold_tree, test_tree, errors):
	gold_spans = gold_tree.get_spans()
	test_spans = test_tree.get_spans()

	gold_span_set = {}
	for span in gold_spans:
		span = (span[2].label, span[0], span[1])
		if span not in gold_span_set:
			gold_span_set[span] = 0
		gold_span_set[span] += 1

	for span in test_spans:
		span = (span[2].label, span[0], span[1])
		is_error = True
		if span in gold_span_set:
			if gold_span_set[span] > 0:
				is_error = False
				gold_span_set[span] -= 1
		if is_error:
			if span[0] not in errors:
				errors[span[0]] = {'extra': 0, 'missing': 0}
			errors[span[0]]['extra'] += 1

	for span in gold_span_set:
		for i in xrange(gold_span_set[span]):
			if span[0] not in errors:
				errors[span[0]] = {'extra': 0, 'missing': 0}
			errors[span[0]]['missing'] += 1

def production_to_string(production):
	ans = production[0] + ' -> '
	ans += ', '.join([sub[0] for sub in production[2]])
	return ans

def update_production_errors(gold_tree, test_tree, errors):
	gold_productions = gold_tree.production_list()
	test_productions = test_tree.production_list()

	gold_set = {}
	for prod in gold_productions:
		if prod not in gold_set:
			gold_set[prod] = 0
		gold_set[prod] += 1

	for prod in test_productions:
		is_error = True
		if prod in gold_set:
			if gold_set[prod] > 0:
				is_error = False
				gold_set[prod] -= 1
		if is_error:
			prod = production_to_string(prod)
			if prod not in errors:
				errors[prod] = {'extra': 0, 'missing': 0}
			errors[prod]['extra'] += 1

	for prod in gold_set:
		for i in xrange(gold_set[prod]):
			prod = production_to_string(prod)
			if prod not in errors:
				errors[prod] = {'extra': 0, 'missing': 0}
			errors[prod]['missing'] += 1

if __name__ == '__main__':
	if len(sys.argv) == 1:
		print "Print counts of the number of bracket errors:"
		print "   %s <gold> [<test> or stdin]" % sys.argv[0]
		print "Options:"
		print "  -p, print production error counts"
		print "  -b, print bracket error counts"
		print "  If neither option is given, brackets are the default"
		print "Running doctest"
		import doctest
		doctest.testmod()
		sys.exit(0)

	args = [val for val in sys.argv if val[0] != '-']
	gold_in = ptb.generate_trees(args[1], return_empty=True)
	test_src = args[2] if len(args) == 3 else sys.stdin
	test_in = ptb.generate_trees(test_src, return_empty=True)

	span_errors = {}
	production_errors = {}
	while True:
		try:
			gold_tree = gold_in.next()
			test_tree = test_in.next()
			if test_tree is None:
				continue
		except StopIteration:
			break

		gold_tree = ptb.apply_collins_rules(gold_tree)
		test_tree = ptb.apply_collins_rules(test_tree)

		update_span_errors(gold_tree, test_tree, span_errors)
		update_production_errors(gold_tree, test_tree, production_errors)

	if '-p' in sys.argv:
		for error in production_errors:
			print "%d %d\t%s" % (production_errors[error]['extra'], production_errors[error]['missing'], error)

	# By default, do this
	if '-b' in sys.argv or '-p' not in sys.argv:
		for error in span_errors:
			print "%d %d\t%s" % (span_errors[error]['extra'], span_errors[error]['missing'], error)
