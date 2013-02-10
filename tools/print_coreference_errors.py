#!/usr/bin/env python

import sys
sys.path.insert(0, "util")
try:
	import render_coreference
except ImportError:
	raise Exception("Remember to set up a symlink to the util directory")

if __name__ == '__main__':
	init.argcheck(sys.argv, 4, 4, "Print coreference resolution errors", "<prefix> <gold_dir> <test>")

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
			print_mention_list(out_mention_list, gold_mentions, auto_mentions)
			print_mention_text(out_mention_text, gold_mentions, auto_mentions, gold_parses, gold_heads, text)

			# Coloured cluster output, grouped
			groups = coreference.confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters, gold_mention_set, auto_mention_set)

			covered = print_cluster_errors(out_cluster_errors, out_cluster_context, text, gold_parses, gold_heads, groups, auto_clusters, gold_clusters, gold_mentions)
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

###			for uset in unique_sets:
###				gold_ids = set()
###				for entity_id in uset:
###					for mention in auto_clusters[entity_id]:
###						if mention in gold_mention_set:
###							gold_ids.add(gold_mentions[mention])
###				print >> out_stats, 'confusion', len(uset), len(gold_ids)
###			for cluster_num in auto_clusters:
###				cluster = auto_clusters[cluster_num]
###				extra = 0
###				for mention in cluster:
###					if mention not in gold_mention_set:
###						extra += 1
###				if extra == len(cluster):
###					# Completely extra
###					print >> out_stats, 'confusion', 1, 0
###			for cluster_num in gold_clusters:
###				cluster = gold_clusters[cluster_num]
###				missed = 0
###				for mention in cluster:
###					if mention not in auto_mention_set:
###						missed += 1
###				if missed == len(cluster):
###					# Completely missed
###					print >> out_stats, 'confusion', 0, 1

###if __name__ == "__main__":
###	print "Running doctest"
###	import doctest
###	doctest.testmod()

