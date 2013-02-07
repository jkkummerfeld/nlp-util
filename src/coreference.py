#!/usr/bin/env python

import sys
from collections import defaultdict
import string

import head_finder

# TODO: Look into better head finding (e.g. behaviour when brackets come up,
# and for appositives, where it often goes into the constituent in apposition)
# Also, should default last be on or not?

def mention_head(mention, text, parses, heads, default_last=True):
	sentence, start, end = mention
	node = parses[sentence].get_lowest_span(start, end)
	if node is None:
		if default_last:
			node = parses[sentence].get_lowest_span(end - 1, end)
		else:
			return None
	return head_finder.get_head(heads[sentence], node)

def mention_type(mention, text, parses, heads):
	head_span, head_word, head_pos = mention_head(mention, text, parses, heads)
	if mention[2] - mention[1] == 1 and (head_pos in ["PRP", "PRP$", "WP", "WP$", "WDT", "WRB"] or head_word.lower() in pronouns):
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
	# Create a mapping
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
		if len(head_dict[head]['gold']) == 1 and len(head_dict[head]['auto']) == 1:
			mapping[head_dict[head]['auto'][0]] = head_dict[head]['gold'][0]
	
	# Add mapping for cases where the difference is only leading or trailing punctuation
	for amention in auto_mention_set.difference(gold_mention_set):
		if amention in mapping:
			continue
		sentence, astart, aend = amention
		while len(text[sentence][astart]) == 1 and text[sentence][astart] not in string.letters:
			astart += 1
		while len(text[sentence][aend-1]) == 1 and text[sentence][aend-1] not in string.letters:
			aend -= 1
		for gmention in gold_mention_set.difference(auto_mention_set):
			gsentence, gstart, gend = gmention
			if sentence != gsentence:
				continue
			while len(text[sentence][gstart]) == 1 and text[sentence][gstart] not in string.letters:
				gstart += 1
			while len(text[sentence][gend-1]) == 1 and text[sentence][gend-1] not in string.letters:
				gend -= 1
			if astart == gstart and aend == gend:
				mapping[amention] = gmention

	# TODO: Consider cases where the mention is not a constituent

	# Apply mapping to create new auto_mention_set
	changed = set()
	for mention in mapping:
		print mention_text(mention, text)
		print mention_text(mapping[mention], text)
		auto_mention_set.remove(mention)
		auto_mention_set.add(mapping[mention])
		cluster_id = auto_mentions.pop(mention)
		auto_mentions[mapping[mention]] = cluster_id
		auto_clusters[cluster_id].remove(mention)
		auto_clusters[cluster_id].append(mapping[mention])
		changed.add((mention, mapping[mention]))
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

PRO_PERSON = 1
PRO_PLURAL = 2
PRO_SINGLE = 1
PRO_UNKNOWN = 0
PRO_FEMALE = 1
PRO_MALE = 2
PRO_NEUTER = 3

pronouns = {
###	"'s": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
###	"s": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"that": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"whatever": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"who": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"whom": (PRO_UNKNOWN, PRO_UNKNOWN, PRO_UNKNOWN),
	"how": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"whoever": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"whose": (PRO_UNKNOWN, PRO_SINGLE, PRO_UNKNOWN),
	"i": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"me": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"mine": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"my": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"myself": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"one": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"thyself": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"ya": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"you": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"your": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"yourself": (PRO_UNKNOWN, PRO_SINGLE, PRO_PERSON),
	"her": (PRO_FEMALE, PRO_SINGLE, PRO_PERSON),
	"hers": (PRO_FEMALE, PRO_SINGLE, PRO_PERSON),
	"herself": (PRO_FEMALE, PRO_SINGLE, PRO_PERSON),
	"she": (PRO_FEMALE, PRO_SINGLE, PRO_PERSON),
	"he": (PRO_MALE, PRO_SINGLE, PRO_PERSON),
	"him": (PRO_MALE, PRO_SINGLE, PRO_PERSON),
	"himself": (PRO_MALE, PRO_SINGLE, PRO_PERSON),
	"his": (PRO_MALE, PRO_SINGLE, PRO_PERSON),
###	"half": (PRO_NEUTER, PRO_UNKNOWN, PRO_UNKNOWN),
	"'em": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"all": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"our": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"ours": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"ourselves": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"their": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"theirs": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"them": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"themselves": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"they": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"us": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"we": (PRO_NEUTER, PRO_PLURAL, PRO_UNKNOWN),
	"it": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"its": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"itself": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"what": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"when": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"where": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN),
	"which": (PRO_NEUTER, PRO_SINGLE, PRO_UNKNOWN)
}

if __name__ == '__main__':
	print "Running doctest"
	import doctest
	doctest.testmod()

