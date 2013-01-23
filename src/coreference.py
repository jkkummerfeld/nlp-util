#!/usr/bin/env python

import sys
from collections import defaultdict

def set_of_clusters(clusters):
	ans = set()
	for cluster in clusters:
		mentions = clusters[cluster][:]
		mentions.sort()
		ans.add(tuple(mentions))
	return ans

def set_of_mentions(clusters):
	ans = set()
	for cluster in clusters:
		for mention in clusters[cluster]:
			ans.add(mention)
	return ans

def confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters):
	groups = []
	mentions = set()
	for mention in gold_mentions:
		mentions.add(mention)
	for mention in auto_mentions:
		mentions.add(mention)
	while len(mentions) > 0:
		# Choose a random mention and DFS to create the confusion group
		group = {'auto': [], 'gold': []}
		seed = mentions.pop()
		stack = []
		seen_gold = set()
		seen_auto = set()
		if seed in gold_mentions:
			stack.append((gold_mentions[seed], True))
			seen_gold.add(stack[0][0])
		else:
			stack.append((auto_mentions[seed], False))
			seen_auto.add(stack[0][0])

		while len(stack) > 0:
			cluster, is_gold = stack.pop()
			if is_gold:
				group['gold'].append(set(gold_clusters[cluster]))
				for mention in gold_clusters[cluster]:
					auto_cluster = auto_mentions.get(mention)
					if auto_cluster is not None:
						if auto_cluster not in seen_auto:
							stack.append((auto_cluster, False))
							seen_auto.add(auto_cluster)
					mentions.discard(mention)
			else:
				group['auto'].append(set(auto_clusters[cluster]))
				for mention in auto_clusters[cluster]:
					gold_cluster = gold_mentions.get(mention)
					if gold_cluster is not None:
						if gold_cluster not in seen_gold:
							stack.append((gold_cluster, True))
							seen_gold.add(gold_cluster)
					mentions.discard(mention)
		groups.append(group)
	return groups

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

