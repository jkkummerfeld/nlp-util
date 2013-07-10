#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

import sys
import ptb, render_tree, coreference_reading, head_finder, coreference, init

from collections import defaultdict

# TODO:
# Add ordering information for the context printing
# Add the ability to print without the newlines (or just return strings?)
# Add the option to print a cluster error group with missing mentions as singletons throughout the rest

CONTEXT = 40
ANSI_WHITE = 15
ANSI_YELLOW = 3
ANSI_RED = 1

def print_conll_style_part(out, text, mentions, doc, part):
	doc_str = doc
	if "tc/ch/00/ch" in doc and '9' not in doc:
		val = int(doc.split('_')[-1]) * 10 - 1
		doc_str = "tc/ch/00/ch_%04d" % val
	print >> out, "#begin document (%s); part %s" % (doc_str, part)
	starts = defaultdict(lambda: [])
	ends = defaultdict(lambda: [])
	singles = defaultdict(lambda: [])
	for mention in mentions:
		cluster_id = mentions[mention]
		if mention[2] - mention[1] == 1:
			singles[mention[0], mention[1]].append(cluster_id)
		else:
			starts[mention[0], mention[1]].append(cluster_id)
			ends[mention[0], mention[2] - 1].append(cluster_id)

	for i in xrange(len(text)):
		for j in xrange(len(text[i])):
			coref = []
			if (i, j) in starts:
				for cluster_id in starts[i, j]:
					coref.append('(' + str(cluster_id))
			if (i, j) in singles:
				for cluster_id in singles[i, j]:
					coref.append('(' + str(cluster_id) + ')')
			if (i, j) in ends:
				for cluster_id in ends[i, j]:
					coref.append(str(cluster_id) + ')')
			if len(coref) == 0:
				coref = '-'
			else:
				coref = '|'.join(coref)
			print >> out, "%s\t%d\t%d\t%s\t%s" % (doc_str, int(part), j, text[i][j], coref)
		print >> out

	print >> out, "#end document"

def print_conll_style(data, gold, out):
	for doc in data:
		for part in data[doc]:
			print_conll_style_part(out, gold[doc][part]['text'], data[doc][part]['mentions'], doc, part)

def mention_text(text, mention, parses=None, heads=None, colour=None):
	sentence, start, end = mention
	head = None
	if parses is not None and heads is not None and end - start > 1:
		node = parses[sentence].get_nodes('lowest', start, end)
		if node is not None:
			head = head_finder.get_head(heads[sentence], node)
	ans = []
	for i in xrange(start, end):
		ans.append(text[sentence][i])
		if head is not None:
			if head[0][0] == i:
				ans[-1] = "\033[4m" + ans[-1] + "\033[0m"
	ans = ' '.join(ans)
	if colour is not None:
		ans = ans.split("\033[0m")
		if len(ans) == 1 or len(ans[1]) == 0:
			ans = colour + ans[0] + "\033[0m"
		else:
			ans = colour + ans[0] + "\033[0m" + colour + ans[1] + "\033[0m"
	return ans

def mention_context(text, mention):
	sentence, start, end = mention
	ans = ['', '']
	cur = [sentence, start - 1]
	while True:
		if cur[1] < 0:
			if cur[0] == 0:
				break
			cur[0] -= 1
			cur[1] = len(text[cur[0]]) - 1
		word = text[cur[0]][cur[1]]
		if len(ans[0]) == 0:
			ans[0] = word
		elif len(ans[0]) + len(word) < CONTEXT - 1:
			ans[0] = word + ' ' + ans[0]
		else:
			break
		cur[1] -= 1

	cur = [sentence, end]
	while True:
		if cur[1] == len(text[cur[0]]):
			if cur[0] == len(text) - 1:
				break
			cur[0] += 1
			cur[1] = 0
		word = text[cur[0]][cur[1]]
		if len(ans[1]) == 0:
			ans[1] = word
		elif len(ans[1]) + len(word) < CONTEXT - 1:
			ans[1] = ans[1] + ' ' + word
		else:
			break
		cur[1] += 1
	return ans

def print_headless_mentions(out, parses, heads, mentions):
	for mention in mentions:
		sentence, start, end = mention
		if end - start > 1:
			node = parses[sentence].get_nodes('lowest', start, end)
			if node is None:
				print >> out, mention_text(text, mention)
				print >> out, render_tree.text_tree(parses[sentence], False)

def print_mention(out, with_context, gold_parses, gold_heads, text, mention, colour=None, extra=False, return_str=False):
	pre_context, post_context = mention_context(text, mention)
	if extra:
		colour = ANSI_RED
	if colour is None:
		if with_context:
			colour = ANSI_YELLOW
		else:
			colour = ANSI_WHITE
	mtext = mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;%dm" % colour)

	to_print = "{:<15}".format(str(mention))
	if with_context:
		to_print += '%s %s  %s  %s' % (' ' * (CONTEXT - len(pre_context)), pre_context, mtext, post_context)
	else:
		if extra:
			to_print += 'Extra:  '
		to_print += mtext

	if return_str:
		return to_print
	else:
		print >> out, to_print

def print_cluster_errors(groups, out_errors, out_context, text, gold_parses, gold_heads, auto_clusters, gold_clusters, gold_mentions):
	mixed_groups = []
	for i in xrange(len(groups)):
		auto, gold = groups[i]
		if len(auto) == 0:
			# All missing
			continue
		if len(gold) == 0:
			# All extra
			continue
		auto_count = len(auto)
		mention_count = sum([len(c) for c in auto])
		mention_count += sum([len(c) for c in gold])
		earliest_mention = None
		if len(auto) > 0:
			earlisest_mention = min([min(c) for c in auto])
		if len(gold) > 0:
			earliest_gold = min([min(c) for c in gold])
			if earliest_mention is None or earliest_gold < earliest_mention:
				earliest_mention = earliest_gold
		mixed_groups.append((auto_count, mention_count, earliest_mention, i))
	mixed_groups.sort(reverse=True)
	mixed_groups = [groups[gset[-1]] for gset in mixed_groups]
	covered = set()
	for group in mixed_groups:
		print_cluster_error_group(group, out_errors, text, gold_parses, gold_heads, gold_mentions)
		print_cluster_error_group(group, out_context, text, gold_parses, gold_heads, gold_mentions, True)
		print >> out_errors
		print >> out_context
		print >> out_errors, '-' * 60
		print >> out_context, '-' * 60
		print >> out_errors
		print >> out_context
		for part in group:
			for cluster in part:
				covered.update(cluster)
	return covered

def print_cluster_error_group(group, out, text, gold_parses, gold_heads, gold_mentions, with_context=False, colour_map=None):
	auto, gold = group
	if colour_map is None:
		colour_map = {}
	next_colour = 3
	# Check if all in the same gold entity
	auto_count = len(auto)
	gold_count = len(gold)
	all_gold = set()
	for cluster in gold:
		all_gold.update(cluster)
	all_auto = set()
	for cluster in auto:
		all_auto.update(cluster)
	spurious = all_auto.difference(all_gold)
	missing = all_gold.difference(all_auto)

	if auto_count == 1 and gold_count == 1 and len(spurious) == 0 and len(missing) == 0:
		# Perfect match
		for cluster in auto:
			sorted_cluster = list(cluster)
			sorted_cluster.sort()
			for mention in sorted_cluster:
				print_mention(out, with_context, gold_parses, gold_heads, text, mention)
	elif auto_count == 1 and gold_count == 1:
		# Only one eneity present, so print all white (except extra)
		for cluster in auto:
			sorted_cluster = list(cluster)
			sorted_cluster.sort()
			for mention in sorted_cluster:
				if mention not in gold_mentions:
					print_mention(out, with_context, gold_parses, gold_heads, text, mention, extra=True)
				else:
					print_mention(out, with_context, gold_parses, gold_heads, text, mention)
					colour_map[gold_mentions[mention]] = ANSI_WHITE
	else:
		sorted_clusters = [(min(c), c) for c in auto]
		sorted_clusters.sort()
		first = True
		for earliest, cluster in sorted_clusters:
			if first:
				first = False
			else:
				print >> out
			sorted_cluster = list(cluster)
			sorted_cluster.sort()
			for mention in sorted_cluster:
				if mention not in gold_mentions:
					print_mention(out, with_context, gold_parses, gold_heads, text, mention, extra=True)
				else:
					if gold_mentions[mention] not in colour_map:
						colour_map[gold_mentions[mention]] = next_colour
						next_colour += 1
						# Skip shades close to white, red and black
						while next_colour in [7, 9, 15, 16]:
							next_colour += 1
					colour = colour_map[gold_mentions[mention]]
					print_mention(out, with_context, gold_parses, gold_heads, text, mention, colour)

	if len(missing) > 0:
		print >> out
		print >> out, "Missing:"
		for cluster in gold:
			sorted_cluster = list(cluster)
			sorted_cluster.sort()
			for mention in sorted_cluster:
				if mention in missing:
					if auto_count <= 1 and gold_count == 1:
						print_mention(out, with_context, gold_parses, gold_heads, text, mention)
					else:
						print_mention(out, with_context, gold_parses, gold_heads, text, mention, colour_map[gold_mentions[mention]])
	return colour_map

def print_cluster_missing(out_errors, out_context, out, text, gold_cluster_set, covered, gold_parses, gold_heads):
	print >> out_errors, "Missing:"
	print >> out_context, "Missing:"
	for entity in gold_cluster_set:
		printed = 0
		for mention in entity:
			if mention not in covered:
				print_mention(out, False, gold_parses, gold_heads, text, mention)
				print_mention(out_errors, False, gold_parses, gold_heads, text, mention)
				print_mention(out_context, True, gold_parses, gold_heads, text, mention)
				printed += 1
		if printed > 0 and len(entity) != printed:
			print >> sys.stderr, "Covered isn't being filled correctly", printed, len(entity)
		if printed > 0:
			print >> out_errors
			print >> out_context
			print >> out

def print_cluster_extra(out_errors, out_context, out, text, auto_cluster_set, covered, gold_parses, gold_heads):
	print >> out_errors, "Extra:"
	print >> out_context, "Extra:"
	for entity in auto_cluster_set:
		printed = 0
		for mention in entity:
			if mention not in covered:
				print_mention(out, False, gold_parses, gold_heads, text, mention, extra=True)
				print_mention(out_errors, False, gold_parses, gold_heads, text, mention, extra=True)
				print_mention(out_context, True, gold_parses, gold_heads, text, mention, extra=True)
				printed += 1
		if printed > 0 and len(entity) != printed:
			print >> sys.stderr, "Covered isn't being filled correctly", printed, len(entity)
		if printed > 0:
			print >> out_errors
			print >> out_context
			print >> out
	print >> out_errors, '-' * 60
	print >> out_context, '-' * 60
	print >> out_errors
	print >> out_context

def print_mention_list(out, gold_mentions, auto_mention_set):
	mentions = [(m, True) for m in gold_mentions]
	for mention in auto_mention_set:
		if mention not in gold_mentions:
			mentions.append((mention, False))
	mentions.sort()
	for mention in mentions:
		if not mention[1]:
			print_mention(out, False, gold_parses, gold_heads, text, mention[0], extra=True)
		elif mention[0] not in auto_mention_set:
			print_mention(out, False, gold_parses, gold_heads, text, mention[0], colour=4)
		else:
			print_mention(out, False, gold_parses, gold_heads, text, mention[0])

def print_mention_text(out, gold_mentions, auto_mention_set, gold_parses, gold_heads, text):
	#TODO: Change to use square brackets so all can be shown
	mentions_by_sentence = defaultdict(lambda: [[], []])
	for mention in gold_mentions:
		mentions_by_sentence[mention[0]][0].append(mention)
	for mention in auto_mention_set:
		mentions_by_sentence[mention[0]][1].append(mention)
	
	word_colours = {}
	for mention in gold_mentions:
		if mention in auto_mention_set:
			continue
		for i in xrange(mention[1], mention[2]):
			word_colours[mention[0], i] = [True, False, False]
		node = gold_parses[mention[0]].get_nodes('lowest', mention[1], mention[2])
		if node is not None:
			head = head_finder.get_head(gold_heads[mention[0]], node)
			word_colours[mention[0], head[0][0]][2] = True
	for mention in auto_mention_set:
		if mention in gold_mentions:
			continue
		for i in xrange(mention[1], mention[2]):
			if (mention[0], i) not in word_colours:
				word_colours[mention[0], i] = [False, False, False]
			word_colours[mention[0], i][1] = True
		node = gold_parses[mention[0]].get_nodes('lowest', mention[1], mention[2])
		if node is not None:
			head = head_finder.get_head(gold_heads[mention[0]], node)
			word_colours[mention[0], head[0][0]][2] = True
	# Printing
	for sentence in xrange(len(text)):
		output = []
		coloured = False
		for word in xrange(len(text[sentence])):
			text_word = text[sentence][word]
			if (sentence, word) in word_colours:
				vals = word_colours[(sentence, word)]
				colour = '0'
				if vals[0] and vals[1]:
					colour = '5'
				elif vals[1]:
					colour = '1'
				elif vals[0]:
					colour = '4'
				# head
				if vals[2]:
					colour += ';4'
				coloured = True
				text_word = "\033[38;5;" + colour + "m" + text_word + "\033[0m"
			output.append(text_word)
			word += 1
		if coloured:
			print >> out, ' '.join(output) + '\n'
		else:
			print >> out, ' '.join(output),
		# Check if the sentence hs nested mentions, print them if so
		printed = False
		glist, alist = mentions_by_sentence[sentence]
		done = set()
		for mention1 in glist:
			subset = set([mention1])
			for mention2 in glist:
				if mention1 == mention2 or mention2 in done:
					continue
				if mention1[1] <= mention2[1] and mention2[2] <= mention1[2]:
					subset.add(mention2)
			if len(subset) == 1:
				continue
			done.update(subset)
			for mention in subset:
				if mention in auto_mention_set:
					print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads)
				else:
					print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;4m")
				printed = True

		for mention1 in alist:
			subset = set([mention1])
			for mention2 in alist:
				if mention1 == mention2 or mention2 in done or mention1 in done:
					continue
				if mention1[1] <= mention2[1] and mention2[2] <= mention1[2]:
					subset.add(mention2)
			if len(subset) == 1:
				continue
			done.update(subset)
			for mention in subset:
				if mention in gold_mentions:
					print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads)
				else:
					print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;1m")
				printed = True

		if printed:
			print >> out, '\n'
		sentence += 1

if __name__ == '__main__':
	#TODO: Add option to resolve span errors first
	init.argcheck(sys.argv, 4, 4, "Print coreference resolution errors", "<prefix> <gold_dir> <test>")

	auto = coreference_reading.read_conll_coref_system_output(sys.argv[3])
	gold = coreference_reading.read_conll_matching_files(auto, sys.argv[2])

	out_cluster_errors = open(sys.argv[1] + '.cluster_errors', 'w')
	out_cluster_context = open(sys.argv[1] + '.cluster_context', 'w')
	out_cluster_missing = open(sys.argv[1] + '.cluster_missing', 'w')
	out_cluster_extra = open(sys.argv[1] + '.cluster_extra', 'w')
	out_mention_list = open(sys.argv[1] + '.mention_list', 'w')
	out_mention_text = open(sys.argv[1] + '.mention_text', 'w')
	out_files = [out_cluster_errors, 
	             out_cluster_context,
	             out_cluster_missing,
	             out_cluster_extra,
	             out_mention_list, 
	             out_mention_text]
	init.header(sys.argv, out_files)

	for doc in auto:
		for part in auto[doc]:
			# Setup
			for out in out_files:
				print >> out, "\n# %s %s\n" % (doc, part)

			text = gold[doc][part]['text']

			gold_parses = gold[doc][part]['parses']
			gold_heads = gold[doc][part]['heads']
			gold_mentions = gold[doc][part]['mentions']
			gold_clusters = gold[doc][part]['clusters']

			auto_mentions = auto[doc][part]['mentions']
			auto_clusters = auto[doc][part]['clusters']
	
			gold_cluster_set = coreference.set_of_clusters(gold_clusters)
			auto_cluster_set = coreference.set_of_clusters(auto_clusters)
			gold_mention_set = coreference.set_of_mentions(gold_clusters)
			auto_mention_set = coreference.set_of_mentions(auto_clusters)
			
			# Coloured mention output
			print_mention_list(out_mention_list, gold_mentions, auto_mention_set)
			print_mention_text(out_mention_text, gold_mentions, auto_mention_set, gold_parses, gold_heads, text)

			# Coloured cluster output, grouped
			groups = coreference.confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters)

			covered = print_cluster_errors(groups, out_cluster_errors, out_cluster_context, text, gold_parses, gold_heads, auto_clusters, gold_clusters, gold_mentions)
			print >> out_cluster_errors, "Entirely missing or extra\n"
			print >> out_cluster_context, "Entirely missing or extra\n"
			print_cluster_missing(out_cluster_errors, out_cluster_context, out_cluster_missing, text, gold_cluster_set, covered, gold_parses, gold_heads)
			print_cluster_extra(out_cluster_errors, out_cluster_context, out_cluster_extra, text, auto_cluster_set, covered, gold_parses, gold_heads)
			
###if __name__ == "__main__":
###	print "Running doctest"
###	import doctest
###	doctest.testmod()

