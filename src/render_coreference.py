#!/usr/bin/env python

import sys
import ptb, render_tree, conll_coref, head_finder, coreference

from collections import defaultdict

CONTEXT = 40

def mention_text(text, mention, parses=None, heads=None, colour=None):
	sentence, start, end = mention
	head = None
	if parses is not None and heads is not None and end - start > 1:
		node = parses[sentence].get_lowest_span(start, end)
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
			node = parses[sentence].get_lowest_span(start, end)
			if node is None:
				print >> out, mention_text(text, mention)
				print >> out, render_tree.text_tree(parses[sentence], False)

def print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, colour=3, extra=False):
	print >> out_errors, str(mention),
	pre_context, post_context = mention_context(text, mention)
	print >> out_context, ' ' * (CONTEXT - len(pre_context)), pre_context,
	if not extra:
		print >> out_errors, '\t' + mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;%sm" % colour)
		print >> out_context, mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;%sm" % colour),
	else:
		print >> out_errors, '\t' + "Extra: " + mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;1m")
		print >> out_context, mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;1m"),
	print >> out_context, post_context

def print_cluster_errors(out_errors, out_context, text, gold_parses, gold_heads, unique_sets, auto_clusters):
	# Print cluster errors
	covered = set()
	for uset in unique_sets:
		colour_map = {}
		next_colour = 3
		# Check if all in the same gold entity
		single_auto = len(uset) == 1
		single_gold = True
		no_spurious = True
		no_missing = True
		if single_auto:
			prev_gold = None
			count = None
			for entity_id in uset:
				for mention in auto_clusters[entity_id]:
					if mention not in gold_mention_set:
						no_spurious = False
						continue
					gold_id = gold_mentions[mention]
					if prev_gold is None:
						count = len(gold_clusters[gold_id])
						prev_gold = gold_id
					elif gold_id == prev_gold:
						count -= 1
					else:
						single_gold = False
						count = 0
			if count != 1:
				no_missing = False

		if single_auto and single_gold and no_spurious and no_missing:
			# Perfect match, just continue
			for mention in auto_clusters[uset[0]]:
				covered.add(mention)
			continue
		elif single_auto and single_gold:
			entity = tuple(auto_clusters[uset[0]])
			for mention in entity:
				if mention not in gold_mentions:
					print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, extra=True)
					covered.add(mention)
				else:
					print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention)
					covered.add(mention)
					if gold_mentions[mention] not in colour_map:
						colour_map[gold_mentions[mention]] = '3'
			print >> out_errors
			print >> out_context
		else:
			for entity_id in uset:
				entity = tuple(auto_clusters[entity_id])
				colour = 2
				for mention in entity:
					if mention not in gold_mentions:
						print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, extra=True)
						covered.add(mention)
					else:
						if gold_mentions[mention] not in colour_map:
							colour_map[gold_mentions[mention]] = str(next_colour)
							next_colour += 1
							# Skip shades close to white, red and black
							while next_colour in [7, 9, 15, 16]:
								next_colour += 1
						print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, colour_map[gold_mentions[mention]])
						covered.add(mention)
				print >> out_errors
				print >> out_context
		first = True
		for num in colour_map:
			for mention in gold_clusters[num]:
				if mention not in covered:
					if first:
						first = False
						print >> out_errors, "Missing:"
						print >> out_context, "Missing:"
					print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, colour_map[num])
					covered.add(mention)
		if not first:
			print >> out_errors
			print >> out_context
		print >> out_errors, '-' * 60
		print >> out_context, '-' * 60
		print >> out_errors
		print >> out_context
	return covered

def print_cluster_missing(out_errors, out_context, out, text, gold_cluster_set, covered, gold_parses, gold_heads):
	print >> out_errors, "Missing:"
	print >> out_context, "Missing:"
	for entity in gold_cluster_set:
		printed = 0
		for mention in entity:
			if mention not in covered:
				print >> out, str(mention) + '\t',
				print >> out, mention_text(text, mention, gold_parses, gold_heads)
				print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention)
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
				print >> out, str(mention) + '\t',
				print >> out, mention_text(text, mention, gold_parses, gold_heads)
				print_mention(out_errors, out_context, gold_parses, gold_heads, text, mention, extra=True)
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

def print_mention_list(out, gold_mentions, auto_mentions):
	for mention in gold_mentions:
		if mention not in auto_mentions:
			print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;4m")
		else:
			print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads)
	for mention in auto_mentions:
		if mention not in gold_mentions:
			print >> out, '\t', mention_text(text, mention, gold_parses, gold_heads, "\033[38;5;1m")

def print_mention_text(out, gold_mentions, auto_mentions, gold_parses, gold_heads, text, ):
	mentions_by_sentence = defaultdict(lambda: [[], []])
	for mention in gold_mentions:
		mentions_by_sentence[mention[0]][0].append(mention)
	for mention in auto_mentions:
		mentions_by_sentence[mention[0]][1].append(mention)
	
	word_colours = {}
	for mention in gold_mentions:
		if mention in auto_mentions:
			continue
		for i in xrange(mention[1], mention[2]):
			word_colours[mention[0], i] = [True, False, False]
		node = gold_parses[mention[0]].get_lowest_span(mention[1], mention[2])
		if node is not None:
			head = head_finder.get_head(gold_heads[mention[0]], node)
			word_colours[mention[0], head[0][0]][2] = True
	for mention in auto_mentions:
		if mention in gold_mentions:
			continue
		for i in xrange(mention[1], mention[2]):
			if (mention[0], i) not in word_colours:
				word_colours[mention[0], i] = [False, False, False]
			word_colours[mention[0], i][1] = True
		node = gold_parses[mention[0]].get_lowest_span(mention[1], mention[2])
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
				if mention in auto_mentions:
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
			print >> out
			print >> out
		sentence += 1

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "Print coreference resolution errors"
		print "   %s <prefix> <gold_dir> <test>" % sys.argv[0]
		sys.exit(0)

	auto = conll_coref.read_coref_system_output(sys.argv[3])
	gold = conll_coref.read_matching_files(auto, sys.argv[2])

	out_cluster_errors = open(sys.argv[1] + '.cluster_errors', 'w')
	out_cluster_context = open(sys.argv[1] + '.cluster_context', 'w')
	out_cluster_missing = open(sys.argv[1] + '.cluster_missing', 'w')
	out_cluster_extra = open(sys.argv[1] + '.cluster_extra', 'w')
	out_mention_list = open(sys.argv[1] + '.mention_list', 'w')
	out_mention_text = open(sys.argv[1] + '.mention_text', 'w')
	out_stats = open(sys.argv[1] + '.stats', 'w')
	out_files = [out_cluster_errors, 
	             out_cluster_context,
	             out_cluster_missing,
	             out_cluster_extra,
	             out_mention_list, 
	             out_mention_text]

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

			unique_sets, groups = coreference.confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters, gold_mention_set, auto_mention_set)
			
			# Coloured mention output
			print_mention_list(out_mention_list, gold_mentions, auto_mentions)
			print_mention_text(out_mention_text, gold_mentions, auto_mentions, gold_parses, gold_heads, text)

			# Coloured cluster output, grouped
			covered = print_cluster_errors(out_cluster_errors, out_cluster_context, text, gold_parses, gold_heads, unique_sets, auto_clusters)
			print_cluster_missing(out_cluster_errors, out_cluster_context, out_cluster_missing, text, gold_cluster_set, covered, gold_parses, gold_heads)
			print_cluster_extra(out_cluster_errors, out_cluster_context, out_cluster_extra, text, auto_cluster_set, covered, gold_parses, gold_heads)
			
			# Stats
			for cluster_num in auto_clusters:
				cluster = auto_clusters[cluster_num]
				extra = 0
				options = defaultdict(lambda: 0)
				for mention in cluster:
					if mention not in gold_mention_set:
						extra += 1
					else:
						options[gold_mentions[mention]] += 1
				best_score = None
				for option in options:
					others = len(cluster) - options[option]
					missing = len(gold_clusters[option]) - options[option]
					score = others + missing + extra
					if best_score is None or score < best_score[0]:
						best_score = (score, others, missing, extra)
				if best_score is None:
					# All extra
					print >> out_stats, 'auto', len(cluster), -1, 0, 0, extra
				else:
					print >> out_stats, 'auto', len(cluster), ' '.join([str(val) for val in best_score])
			for cluster_num in gold_clusters:
				cluster = gold_clusters[cluster_num]
				missed = 0
				options = defaultdict(lambda: 0)
				for mention in cluster:
					if mention not in auto_mention_set:
						missed += 1
					else:
						options[auto_mentions[mention]] += 1
				best_score = None
				for option in options:
					others = len(cluster) - options[option]
					elsewhere = len(auto_clusters[option]) - options[option]
					score = others + elsewhere + missed
					if best_score is None or score < best_score[0]:
						best_score = (score, others, elsewhere, missed)
				if best_score is None:
					# Completely missed
					print >> out_stats, 'gold', len(cluster), -1, 0, 0, extra
				else:
					print >> out_stats, 'gold', len(cluster), ' '.join([str(val) for val in best_score])

			for uset in unique_sets:
				gold_ids = set()
				for entity_id in uset:
					for mention in auto_clusters[entity_id]:
						if mention in gold_mention_set:
							gold_ids.add(gold_mentions[mention])
				print >> out_stats, 'confusion', len(uset), len(gold_ids)
			for cluster_num in auto_clusters:
				cluster = auto_clusters[cluster_num]
				extra = 0
				for mention in cluster:
					if mention not in gold_mention_set:
						extra += 1
				if extra == len(cluster):
					# Completely extra
					print >> out_stats, 'confusion', 1, 0
			for cluster_num in gold_clusters:
				cluster = gold_clusters[cluster_num]
				missed = 0
				for mention in cluster:
					if mention not in auto_mention_set:
						missed += 1
				if missed == len(cluster):
					# Completely missed
					print >> out_stats, 'confusion', 0, 1
