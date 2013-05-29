#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

DEFAULT_LABEL = 'label_not_set'
TRACE_LABEL = '-NONE-'

class TreeIterator:
	'''Iterator for traversal of a tree.
	
	PSTree uses pre-order traversal by default, but this supports post-order too, e.g.:
	>>> tree = tree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag) ) (VP (VBZ plays) (NP (NNP Elianti) )) (. .) ))")
	>>> for node in TreeIterator(tree, 'post'):
	...   print node
	(NNP Ms.)
	(NNP Haag)
	(NP-SBJ (NNP Ms.) (NNP Haag))
	(VBZ plays)
	(NNP Elianti)
	(NP (NNP Elianti))
	(VP (VBZ plays) (NP (NNP Elianti)))
	(. .)
	(S (NP-SBJ (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .))
	(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))
	'''
	def __init__(self, tree, order='pre'):
		self.tree = tree
		self.pos = [0]
		self.order = order

	def __iter__(self):
		return self

	def next(self):
		while True:
			if len(self.pos) == 0:
				raise StopIteration

			# For pre-order traversal, return nodes when first reached
			ans = None
			if self.order == 'pre' and self.pos[-1] == 0:
				ans = self.tree

			# Update internal state to point at the next node in the tree
			if self.pos[-1] < len(self.tree.subtrees):
				self.tree = self.tree.subtrees[self.pos[-1]]
				self.pos[-1] += 1
				self.pos.append(0)
			else:
				if self.order == 'post':
					ans = self.tree
				self.tree = self.tree.parent
				self.pos.pop()

			if ans is not None:
				return ans

class PSTree:
	'''Phrase Structure Tree

	>>> tree = tree_from_text("(ROOT (NP (NNP Newspaper)))")
	>>> print tree
	(ROOT (NP (NNP Newspaper)))
	>>> tree = tree_from_text("(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag) ) (VP (VBZ plays) (NP (NNP Elianti) )) (. .) ))")
	>>> print tree
	(ROOT (S (NP-SBJ (NNP Ms.) (NNP Haag)) (VP (VBZ plays) (NP (NNP Elianti))) (. .)))
	>>> print tree.word_yield()
	Ms. Haag plays Elianti .
	>>> tree = tree_from_text("(ROOT (NFP ...))")
	>>> print tree
	(ROOT (NFP ...))
	>>> tree.word_yield()
	'...'
	>>> tree = tree_from_text("(VP (VBD was) (VP (VBN named) (S (NP-SBJ (-NONE- *-1) ) (NP-PRD (NP (DT a) (JJ nonexecutive) (NN director) ) (PP (IN of) (NP (DT this) (JJ British) (JJ industrial) (NN conglomerate) ))))))")
	>>> print tree
	(VP (VBD was) (VP (VBN named) (S (NP-SBJ (-NONE- *-1)) (NP-PRD (NP (DT a) (JJ nonexecutive) (NN director)) (PP (IN of) (NP (DT this) (JJ British) (JJ industrial) (NN conglomerate)))))))
	>>> tree.word_yield()
	'was named *-1 a nonexecutive director of this British industrial conglomerate'
	'''
	def __init__(self, word=None, label=DEFAULT_LABEL, span=(0, 0), parent=None, subtrees=None):
		self.word = word
		self.label = label
		self.span = span
		self.parent = parent
		self.subtrees = []
		if subtrees is not None:
			self.subtrees = subtrees
	
	def __iter__(self):
		return TreeIterator(self, 'pre')
	
	def clone(self):
		ans = PSTree()
		ans.word = self.word
		ans.label = self.label
		ans.parent = None
		ans.span = self.span
		ans.subtrees = []
		for subtree in self.subtrees:
			subclone = subtree.clone()
			subclone.parent = ans
			ans.subtrees.append(subclone)
		return ans

	def is_terminal(self):
		'''Check if the tree has no children.'''
		return len(self.subtrees) == 0

	def is_trace(self):
		'''Check if this tree is the end of a trace.'''
		return self.label == TRACE_LABEL

	def root(self):
		'''Follow parents until a node is reached that has no parent.'''
		if self.parent is not None:
			return self.parent.root()
		else:
			return self

	def __repr__(self):
		'''Return a bracket notation style representation of the tree.'''
		ans = '('
		if self.is_trace():
			ans += TRACE_LABEL + ' ' + self.word
		elif self.is_terminal():
			ans += self.label + ' ' + self.word
		else:
			ans += self.label
		for subtree in self.subtrees:
			ans += ' ' + subtree.__repr__()
		ans += ')'
		return ans

	def calculate_spans(self, left=0):
		'''Update the spans for every node in this tree.'''
		right = left
		if self.is_terminal():
			right += 1
		for subtree in self.subtrees:
			right = subtree.calculate_spans(right)
		self.span = (left, right)
		return right

	def check_consistency(self):
		'''Check that the parents and spans are consistent with the tree
		structure.'''
		ans = True
		if len(self.subtrees) > 0:
			for i in xrange(len(self.subtrees)):
				subtree = self.subtrees[i]
				if subtree.parent != self:
					print "bad parent link"
					ans = False
				if i > 0 and self.subtrees[i - 1].span[1] != subtree.span[0]:
					print "Subtree spans don't match"
					ans = False
				ans = ans and subtree.check_consistency()
			if self.span != (self.subtrees[0].span[0], self.subtrees[-1].span[1]):
				print "Span doesn't match subtree spans"
				ans = False
		return ans

	def production_list(self, ans=None):
		'''Get a list of productions as:
		(node label, node span, ((subtree1, end1), (subtree2, end2)...))'''
		if ans is None:
			ans = []
		if len(self.subtrees) > 0:
			cur = (self.label, self.span, tuple([(sub.label, sub.span[1]) for sub in self.subtrees]))
			ans.append(cur)
			for sub in self.subtrees:
				sub.production_list(ans)
		return ans

	def word_yield(self, span=None, as_list=False):
		'''Return the set of words at terminal nodes, either as a space separated
		string, or as a list.'''
		if self.is_terminal():
			if span is None or span[0] <= self.span[0] < span[1]:
				if self.word is None:
					return None
				if as_list:
					return [self.word]
				else:
					return self.word
			else:
				return None
		else:
			ans = []
			for subtree in self.subtrees:
				words = subtree.word_yield(span, as_list)
				if words is not None:
					if as_list:
						ans += words
					else:
						ans.append(words)
			if not as_list:
				ans = ' '.join(ans)
			return ans

	def node_dict(self, depth=0, node_dict=None):
		'''Get a dictionary of labelled nodes. Note that we use a dictionary to
		take into consideration unaries like (NP (NP ...))'''
		if node_dict is None:
			node_dict = defaultdict(lambda: [])
		for subtree in self.subtrees:
			subtree.node_dict(depth + 1, node_dict)
		node_dict[(self.label, self.span[0], self.span[1])].append(depth)
		return node_dict

	def get_nodes(self, request='lowest', start=-1, end=-1, node_list=None):
		'''Get the node(s) that have a given span.  Unspecified endpoints are
		treated as wildcards.  The request can be 'lowest', 'highest', or 'all'.'''
		if request not in ['highest', 'lowest', 'all']:
			raise Exception("%s is not a valid request" % str(request))
		if request == 'lowest' and start < 0 and end < 0:
			raise Exception("Lowest is not well defined when both ends are wildcards")

		if request == 'all' and node_list is None:
			node_list = []
		if request == 'highest':
			if self.span[0] == start or start < 0:
				if self.span[1] == end or end < 0:
					return self

		for subtree in self.subtrees:
			# Skip subtrees with no overlapping range
			if 0 < end <= subtree.span[0] or subtree.span[1] < start:
				continue
			ans = subtree.get_nodes(request, start, end, node_list)
			if ans is not None and request != 'all':
				return ans

		if self.span[0] == start or start < 0:
			if self.span[1] == end or end < 0:
				if request == 'lowest':
					return self
				elif request == 'all':
					node_list.append((self.span[0], self.span[1], self))
					return node_list
		return None

	def get_matching_node(self, node):
		'''Find a node with the same span, label and number of children.'''
		if node.span == self.span:
			if node.label == self.label:
				if len(self.subtrees) == len(node.subtrees):
					return self
			return self.subtrees[0].get_matching_node(node)
		else:
			for subtree in self.subtrees:
				if subtree.span[0] <= node.span[0] and node.span[1] <= subtree.span[1]:
					return subtree.get_matching_node(node)
			return None

def tree_from_text(text, allow_empty_labels=False, allow_empty_words=False):
	'''Construct a PSTree from the provided string, which is assumed to represent
	a tree with nested round brackets.  Nodes are labeled by the text between the
	open bracket and the next space (possibly an empty string).  Words are the
	text after that space and before the close bracket.'''
	root = None
	cur = None
	pos = 0
	word = ''
	for char in text:
		# Consume random text up to the first '('
		if cur is None:
			if char == '(':
				root = PSTree()
				cur = root
			continue

		if char == '(':
			word = word.strip()
			if cur.label is DEFAULT_LABEL:
				if len(word) == 0 and not allow_empty_labels:
					raise Exception("Empty label found\n%s" % text)
				cur.label = word
				word = ''
			if word != '':
				raise Exception("Stray '%s' while processing\n%s" % (word, text))
			sub = PSTree()
			cur.subtrees.append(sub)
			sub.parent = cur
			cur = sub
		elif char == ')':
			word = word.strip()
			if word != '':
				if len(word) == 0 and not allow_empty_words:
					raise Exception("Empty word found\n%s" % text)
				cur.word = word
				word = ''
				cur.span = (pos, pos + 1)
				pos += 1
			else:
				cur.span = (cur.subtrees[0].span[0], cur.subtrees[-1].span[1])
			cur = cur.parent
		elif char == ' ':
			if cur.label is DEFAULT_LABEL:
				if len(word) == 0 and not allow_empty_labels:
					raise Exception("Empty label found\n%s" % text)
				cur.label = word
				word = ''
			else:
				word += char
		else:
			word += char
	if cur is not None:
		raise Exception("Text did not include complete tree\n%s" % text)
	return root

def get_errors(test, gold, include_terminals=False):
	ans = []

	if include_terminals:
		for tnode in test:
			if tnode.is_terminal():
				gnode = gold.get_nodes('lowest', tnode.span[0], tnode.span[1])
				if gnode is not None and gnode.label != tnode.label:
					ans.append(('extra', tnode.span, tnode.label, tnode))
					ans.append(('missing', gnode.span, gnode.label, gnode))

	gold_spans = gold.get_nodes('all')
	test_spans = test.get_nodes('all')
	gold_spans.sort()
	test_spans.sort()
	test_span_set = {}
	for span in test_spans:
		if span[2].is_terminal():
			continue
		key = (span[0], span[1], span[2].label) 
		if key not in test_span_set:
			test_span_set[key] = 0
		test_span_set[key] += 1
	gold_span_set = {}
	for span in gold_spans:
		if span[2].is_terminal():
			continue
		key = (span[0], span[1], span[2].label) 
		if key not in gold_span_set:
			gold_span_set[key] = 0
		gold_span_set[key] += 1

	# Extra
	for span in test_spans:
		key = (span[0], span[1], span[2].label)
		if key in gold_span_set and gold_span_set[key] > 0:
			gold_span_set[key] -= 1
		else:
			ans.append(('extra', span[2].span, span[2].label, span[2]))

	# Missing and crossing
	for span in gold_spans:
		key = (span[0], span[1], span[2].label)
		if key in test_span_set and test_span_set[key] > 0:
			test_span_set[key] -= 1
		else:
			name = 'missing'
			for tspan in test_span_set:
				if tspan[0] < span[0] < tspan[1] < span[1]:
					name = 'crossing'
					break
				if span[0] < tspan[0] < span[1] < tspan[1]:
					name = 'crossing'
					break
			ans.append((name, span[2].span, span[2].label, span[2]))
	return ans

def counts_for_prf(test, gold, include_root=False, include_terminals=False):
	tcount = 0
	for node in test:
		if node.is_terminal() and not include_terminals:
			continue
		if node.parent is None and not include_root:
			continue
		tcount += 1
	gcount = 0
	for node in gold:
		if node.is_terminal() and not include_terminals:
			continue
		if node.parent is None and not include_root:
			continue
		gcount += 1
	gcount = len(gold_spans)
	match = tcount
	errors = get_errors(test, gold, include_terminals)
	for error in errors:
		if error[3].parent is None or include_root:
			if error[0] == 'extra':
				match -= 1
	return match, gold_count, test_count

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

