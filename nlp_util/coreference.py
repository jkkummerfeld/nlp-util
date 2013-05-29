#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict
import string

import head_finder

# TODO: Look into better head finding (e.g. behaviour when brackets come up,
# and for appositives, where it often goes into the constituent in apposition,
# and also for 's)
# Also, should default last be on or not?

def mention_head(mention, text, parses, heads, default_last=True):
	sentence, start, end = mention
	node = parses[sentence].get_nodes('lowest', start, end)
	if node is None:
		if default_last:
			node = parses[sentence].get_nodes('lowest', end - 1, end)
		else:
			return None
	return head_finder.get_head(heads[sentence], node)

def mention_type(mention, text, parses, heads):
	head_span, head_word, head_pos = mention_head(mention, text, parses, heads)
	if mention[2] - mention[1] == 1 and (head_pos in ["PRP", "PRP$", "WP", "WP$", "WDT", "WRB"] or head_word.lower() in pronoun_properties):
		return "pronoun"
	elif head_pos in ["NNP", "NNPS"]:
		return "name"
	else:
		return 'nominal'

def mention_text(mention, text):
	sentence, start, end = mention
	ans = text[sentence][start:end]
	return ' '.join(ans)

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

def match_boundaries(gold_mention_set, auto_mention_set, auto_mentions, auto_clusters, text, parses, heads):
	changed = set()
	# Apply changes for cases where the difference is only leading or trailing punctuation
	mapping = {}
	used_gold = set()
	for amention in auto_mention_set.difference(gold_mention_set):
		sentence, astart, aend = amention
		while len(text[sentence][astart]) == 1 and text[sentence][astart][0] not in string.letters and astart < aend - 1:
			astart += 1
		while len(text[sentence][aend-1]) == 1 and text[sentence][aend-1][0] not in string.letters and astart < aend - 1:
			aend -= 1
		for gmention in gold_mention_set.difference(auto_mention_set):
			if gmention in used_gold:
				continue
			gsentence, gstart, gend = gmention
			if sentence != gsentence:
				continue
			while len(text[sentence][gstart]) == 1 and text[sentence][gstart][0] not in string.letters and gstart < gend - 1:
				gstart += 1
			while len(text[sentence][gend-1]) == 1 and text[sentence][gend-1][0] not in string.letters and gstart < gend - 1:
				gend -= 1
			if astart == gstart and aend == gend:
				mapping[amention] = gmention
				used_gold.add(gmention)
	# Apply mapping to create new auto_mention_set
	for mention in mapping:
		auto_mention_set.remove(mention)
		auto_mention_set.add(mapping[mention])
		cluster_id = auto_mentions.pop(mention)
		auto_mentions[mapping[mention]] = cluster_id
		auto_clusters[cluster_id].remove(mention)
		auto_clusters[cluster_id].append(mapping[mention])
		changed.add((mention, mapping[mention]))
###		print "Changed", mention, mapping[mention]

	# Create a mapping based on heads
	head_dict = defaultdict(lambda: {'auto': [], 'gold': []})
	for mention in auto_mention_set.difference(gold_mention_set):
		sentence, start, end = mention
		head = mention_head(mention, text, parses, heads, default_last=False)
		if head is not None:
			head = (mention[0], head[0])
			head_dict[head]['auto'].append(mention)
	for mention in gold_mention_set.difference(auto_mention_set):
		sentence, start, end = mention
		head = mention_head(mention, text, parses, heads, default_last=False)
		if head is not None:
			head = (mention[0], head[0])
			head_dict[head]['gold'].append(mention)

	mapping = {}
	for head in head_dict:
		amentions = head_dict[head]['auto']
		gmentions = head_dict[head]['gold']
		if len(amentions) == 1 and len(gmentions) == 1:
			mapping[amentions[0]] = gmentions[0]

	# Apply mapping to create new auto_mention_set
	for mention in mapping:
		auto_mention_set.remove(mention)
		auto_mention_set.add(mapping[mention])
		cluster_id = auto_mentions.pop(mention)
		auto_mentions[mapping[mention]] = cluster_id
		auto_clusters[cluster_id].remove(mention)
		auto_clusters[cluster_id].append(mapping[mention])
		changed.add((mention, mapping[mention]))
###		print "Changed", mention, mapping[mention]
	# TODO: Consider cases where the mention is not a constituent
	return changed

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

PRO_FIRST = 1
PRO_SECOND = 2
PRO_THIRD = 3
PRO_PLURAL = 2
PRO_SINGLE = 1
PRO_UNKNOWN = 0
PRO_FEMALE = 1
PRO_MALE = 2
PRO_NEUTER = 3

pronoun_properties = {
###	"'s": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
###	"s": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
###	"half": (PRO_NEUTER, PRO_UNKNOWN, PRO_UNKNOWN),
	"that": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"whatever": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"who": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"whom": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"how": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"whoever": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"whose": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"i": (PRO_UNKNOWN, PRO_SINGLE, PRO_FIRST),
	"me": (PRO_UNKNOWN, PRO_SINGLE, PRO_FIRST),
	"mine": (PRO_UNKNOWN, PRO_SINGLE, PRO_FIRST),
	"my": (PRO_UNKNOWN, PRO_SINGLE, PRO_FIRST),
	"myself": (PRO_UNKNOWN, PRO_SINGLE, PRO_FIRST),
	"one": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"thyself": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"ya": (PRO_UNKNOWN, PRO_SINGLE, PRO_SECOND),
	"you": (PRO_UNKNOWN, PRO_SINGLE, PRO_SECOND),
	"your": (PRO_UNKNOWN, PRO_SINGLE, PRO_SECOND),
	"yourself": (PRO_UNKNOWN, PRO_SINGLE, PRO_SECOND),
	"her": (PRO_FEMALE, PRO_SINGLE, PRO_THIRD),
	"hers": (PRO_FEMALE, PRO_SINGLE, PRO_THIRD),
	"herself": (PRO_FEMALE, PRO_SINGLE, PRO_THIRD),
	"she": (PRO_FEMALE, PRO_SINGLE, PRO_THIRD),
	"he": (PRO_MALE, PRO_SINGLE, PRO_THIRD),
	"him": (PRO_MALE, PRO_SINGLE, PRO_THIRD),
	"himself": (PRO_MALE, PRO_SINGLE, PRO_THIRD),
	"his": (PRO_MALE, PRO_SINGLE, PRO_THIRD),
	"'em": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"all": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"our": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"ours": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"yours": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"ourselves": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"yourselves": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"their": (PRO_NEUTER, PRO_PLURAL, PRO_THIRD),
	"theirs": (PRO_NEUTER, PRO_PLURAL, PRO_THIRD),
	"them": (PRO_NEUTER, PRO_PLURAL, PRO_THIRD),
	"themselves": (PRO_NEUTER, PRO_PLURAL, PRO_THIRD),
	"they": (PRO_NEUTER, PRO_PLURAL, PRO_THIRD),
	"us": (PRO_NEUTER, PRO_PLURAL, PRO_FIRST),
	"we": (PRO_NEUTER, PRO_PLURAL, PRO_FIRST),
	"it": (PRO_NEUTER, PRO_SINGLE, PRO_THIRD),
	"its": (PRO_NEUTER, PRO_SINGLE, PRO_THIRD),
	"itself": (PRO_NEUTER, PRO_SINGLE, PRO_THIRD),
	"what": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"when": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"where": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"which": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN)
###another
###any
###anybody
###anyone
###anything
###both
###each
###eachother
###either
###em
###everybody
###everyone
###everything
###few
###how
###little
###many
###more
###most
###much
###neither
###nobody
###none
###noone
###nothing
###oneanother
###other
###others
###several
###some
###somebody
###someone
###something
###these
###this
###those
###thyself
###when
###where
###whichever
###whomever
}

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

