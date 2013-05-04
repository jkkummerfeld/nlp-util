#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

DEFAULT_LABEL = 'label_not_set'

class TreeIterator:
	'''Iterator for post-order traversal of a tree'''
	def __init__(self, tree):
		self.tree = tree
		self.pos = [0]

	def next(self):
		if len(self.pos) == 0:
			raise StopIteration
		if self.pos[-1] < len(self.tree.subtrees):
			self.tree = self.tree.subtrees[self.pos[-1]]
			self.pos[-1] += 1
			self.pos.append(0)
			return self.next()
		else:
			ans = self.tree
			self.tree = self.tree.parent
			self.pos.pop()
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
	>>> trace = tree.get_nodes('lowest', 2, 3)
	>>> trace.word = None
	>>> print tree
	(VP (VBD was) (VP (VBN named) (S (NP-SBJ (-NONE- -NONE-)) (NP-PRD (NP (DT a) (JJ nonexecutive) (NN director)) (PP (IN of) (NP (DT this) (JJ British) (JJ industrial) (NN conglomerate)))))))
	'''
	def __init__(self, text=None, label=DEFAULT_LABEL, span=(0, 0), parent=None, subtrees=None):
		'''Create a node.  Note that 'text' can either be the word for this node,
		or an entire tree, in which case the tree is created.'''
		self.word = text
		self.label = label
		self.parent = parent
		self.span = span
		self.subtrees = []
		if subtrees is not None:
			self.subtrees = subtrees
		if text is not None and label == DEFAULT_LABEL and span == (0, 0) and parent is None and subtrees is None:
			self.word = None
			self.set_by_text(text)
	
	def __iter__(self):
		return TreeIterator(self)

	
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
		'''Check if the node has no children.'''
		return len(self.subtrees) == 0

	def root(self):
		'''Follow parents until a node is reached that has no parent.'''
		if self.parent is not None:
			return self.parent.root()
		else:
			return self

	def __repr__(self, depth=0):
		'''Return a bracket notation style representation of the tree.'''
		ans = '(' + self.label
		if self.is_terminal():
			if self.word is None:
				ans += ' -NONE-'
			else:
				ans += ' ' + self.word
		for subtree in self.subtrees:
			ans += ' ' + subtree.__repr__(depth + 1)
		ans += ')'
		return ans

	def calculate_spans(self, left=0):
		right = left
		if self.is_terminal():
			right += 1
		for subtree in self.subtrees:
			right = subtree.calculate_spans(right)
		self.span = (left, right)
		return right

	def check_consistency(self):
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
		if ans is None:
			ans = []
		if len(self.subtrees) > 0:
			cur = (self.label, self.span, tuple([(sub.label, sub.span[1]) for sub in self.subtrees]))
			ans.append(cur)
			for sub in self.subtrees:
				sub.production_list(ans)
		return ans

	def word_yield(self, span=None, as_list=False):
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

def tree_from_text(text):
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
				cur.word = word
				word = ''
				cur.span = (pos, pos + 1)
				pos += 1
			else:
				cur.span = (cur.subtrees[0].span[0], cur.subtrees[-1].span[1])
			cur = cur.parent
		elif char == ' ':
			if cur.label is DEFAULT_LABEL:
				cur.label = word
				word = ''
			else:
				word += char
		else:
			word += char
	if cur is not None:
		raise Exception("Text did not include complete tree\n%s" % text)
	return root

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

