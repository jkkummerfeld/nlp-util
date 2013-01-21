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

def confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters, gold_mention_set, auto_mention_set):
	groups = []
	mentions = auto_mention_set.union(gold_mention_set)
	while len(mentions) > 0:
		# Choose a random mention and DFS to create the confusion group
		group = {
			'mentions': {'auto': set(), 'gold': set()},
		  'clusters': {'auto': set(), 'gold': set()}
		}
		seed = mentions.pop()
		stack = []
		cluster = gold_mentions.get(seed)
		if cluster is None:
			cluster = auto_mentions[seed]
		stack.append((cluster, seed in gold_mentions))

		while len(stack) > 0:
			cluster, is_gold = stack.pop()
			if is_gold:
				group['clusters']['gold'].add(cluster)
				for mention in gold_clusters[cluster]:
					group['mentions']['gold'].add(mention)
					auto_cluster = auto_mentions.get(mention)
					if auto_cluster is not None:
						if auto_cluster not in group['clusters']['auto']:
							stack.append((auto_cluster, False))
					mentions.discard(mention)
			else:
				group['clusters']['auto'].add(cluster)
				for mention in auto_clusters[cluster]:
					group['mentions']['auto'].add(mention)
					gold_cluster = gold_mentions.get(mention)
					if gold_cluster is not None:
						if gold_cluster not in group['clusters']['gold']:
							stack.append((gold_cluster, True))
					mentions.discard(mention)
		groups.append(group)
	return groups

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

