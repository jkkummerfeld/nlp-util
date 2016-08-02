#!/usr/bin/env python

# TODO currently assumes all CoNLL / OntoNotes trees are in the same order

from __future__ import print_function

import sys, string

from nlp_util import pstree, nlp_eval, treebanks, parse_errors, init

options = {
  # 'option_word': ((valid options or type), default, "Long description"),
  "config_file": [str, None, # TODO
    "A file containing option settings.  If options other than this are"
    "specified, they will override settings in the file"],
  # Input
  "gold": [str, "-", # TODO - part
    "The file containing gold trees, if '-', stdin is used"],
  "test": [str, "-", # TODO - part
    "The file containing system produced trees, if '-', stdin is used"],
  "gold_input": [('ptb', 'ontonotes'), 'ptb',
    "Input format for the gold file: PTB (single or multiple lines per parse),"
    "OntoNotes (one file in all cases)"],
  "test_input": [('ptb', 'ontonotes'), 'ptb',
    "Input format for the test file: PTB (single or multiple lines per parse),"
    "OntoNotes (one file in all cases)"],
  # Scoring modification
  "labelled_score": [bool, True, # TODO
    "Labeled or unlabelled score"],
  "include_POS_in_score": [bool, False,
    "Include POS tags in overall score"],
  "include_unparsed_in_score": [bool, True,
    "Include missed sentences in overall score"],
  "summary_cutoffs": [[int], [40], # TODO
    "Cutoff lengths for summaries"],
  "averaging": [('macro', 'micro'), 'macro', # TODO
    "How to calculate the overall scores, with a macro average (score for sums"
    "of counts) or micro average (average of scores for each count)"],
  # Tree modification
  "remove_trivial_unaries": [bool, True,
    "Remove unaries that go from a label to iself,"
    "e.g. (NP (NP (NNP it))) has one"],
  "remove_function_labels": [bool, True,
    "Remove function labels, e.g. NP-TMP, remove the -TMP part"],
  "homogenise_top_label": [bool, True,
    "Homogenise the top labels, so all are ROOT"],
  "labels_to_remove": [[str],
    ["TOP", "ROOT", "S1"],
    "Remove nodes with the given labels, keep subtrees, but remove"
    "parents that now have a span of size 0"],
  "words_to_remove": [[str], [],
    "Remove nodes with the given words, and do as for labels"],
  "equivalent_labels": [[(str, str)], [("ADVP", "PRT")],
    "Labels to treat as equivalent"],
  "equivalent_words": [[(str, str)], [],
    "Words to treat as equivalent"],
}

def get_reference(text, sep='-'):
  if text == '0':
    return None
  for char in text.split(sep)[-1]:
    if char not in string.digits:
      return None
  if len(text.split(sep)[-1]) == 0:
    return None
  return text.split(sep)[-1]

def get_traces(node, mapping=None):
  if mapping is None:
    mapping = (
      {}, # num from [NP]-num mapping to the parse node
      {}, # num from [NP]=num mapping to a list of parse nodes
      {}, # num from (-NONE- [*]-num) to the parse node
      [], # list of parse nodes like (-NONE- [no num])
    )

  # Recurse
  for subnode in node.subtrees:
    get_traces(subnode, mapping)

  plabel = node.label

  # 0 - num from [NP]-num mapping to the parse node
  if '-' in plabel and '=' not in plabel and get_reference(plabel) is not None:
    num = get_reference(plabel)
    over_null = False
    if node.wordspan[0] == node.wordspan[1]:
      over_null = True
    mapping[0][num] = (node, over_null)

  # 1 - num from [NP]=num mapping to a list of parse nodes
  if '=' in plabel and get_reference(plabel, '=') is not None:
    num = get_reference(plabel, '=')
    if num not in mapping[1]:
      mapping[1][num] = []
    mapping[1][num].append(node)

  # 2 - num from (-NONE- [*]-num) to the parse node, e.g. inner node of:
  #       (NP (-NONE- *-1))
  #       (NP-SBJ-3 (-NONE- *T*-5))
  if plabel == '-NONE-' and get_reference(node.word) is not None:
    num = get_reference(node.word)
    if num not in mapping[2]:
      mapping[2][num] = []
    mapping[2][num].append(node)

  # 3 - list of parse nodes like (-NONE- [no num]), e.g. inner node of:
  #        (WHNP (-NONE- *))
  #        (WHADVP-1 (-NONE- 0))
  if plabel == '-NONE-' and get_reference(node.word) is None:
    mapping[3].append(node)

  return mapping

def get_nonzero_span(node):
  if node.wordspan[0] == node.wordspan[1]:
    return get_nonzero_span(node.parent)
  else:
    return node.wordspan

def mapping_to_items(mapping):
  # 0 - num from [NP]-num mapping to the parse node
  # 1 - num from [NP]=num mapping to a list of parse nodes
  # 2 - num from (-NONE- [*]-num) to the parse node
  # 3 - list of parse nodes like (-NONE- [no num])

  items = []

  # Add items without coindexation
  for node in mapping[3]:
    label = ""
    if node.parent.wordspan[0] == node.parent.wordspan[1]:
      label = node.parent.label.split('-')[0]
    items.append((
      "empty",
      node.word.split('-')[0],
      get_nonzero_span(node),
      label
    ))

  # Add items with gapping
  for num in mapping[1]:
    ref = mapping[0][num][0]
    for node in mapping[1][num]:
      items.append((
        "gap",
        get_nonzero_span(node),
        node.label.split('=')[0],
        get_nonzero_span(ref),
        ref.label.split('-')[0]
      ))

  # Add items with coindexation
  for num in mapping[2]:
    for node in mapping[2][num]:
      ref = mapping[0][num]
      while ref[1]:
        child = ref[0].subtrees[0]
        ref_num = get_reference(child.word)
        if ref_num is None:
          break
        ref = mapping[0][ref_num]
      ref = ref[0]
      items.append((
        node.word.split('-')[0],
        get_nonzero_span(node),
        ref.label.split('-')[0],
        get_nonzero_span(ref)
      ))

  return items


# Provide current execution info
out = sys.stdout
init.header(sys.argv, out)


# Handle options
test_in = None
gold_in = None
if len(sys.argv) == 1:
  sys.exit()
elif len(sys.argv) == 2:
  sys.exit()
elif len(sys.argv) == 3:
  # Run with defaults, assume the two arguments are the gold and test files
  options['gold'][1] = sys.argv[1]
  options['test'][1] = sys.argv[2]
else:
  sys.exit()

# Print list of options in use
for option in options:
  print("# {: <28} : {}".format(option, str(options[option][1])))

# Set up reading
test_in = open(options['test'][1])
test_tree_reader = treebanks.ptb_read_tree
if options["test_input"][1] == 'ontonotes':
  test_tree_reader = treebanks.conll_read_tree

gold_in = open(options['gold'][1])
gold_tree_reader = treebanks.ptb_read_tree
if options["gold_input"][1] == 'ontonotes':
  gold_tree_reader = treebanks.conll_read_tree

# Process sentences
scores = []
sent_id = 0
match_by_type = {}
gold_by_type = {}
test_by_type = {}
while True:
  sent_id += 1

  # Read trees
  test_tree = test_tree_reader(test_in, True, True, True, True)
  gold_tree = gold_tree_reader(gold_in, True, True, True, True)
  if test_tree is None or gold_tree is None:
    break
  if test_tree == "Empty":
    test_tree = None

  # Coverage error
  gwords = len(gold_tree.word_yield().split())
  if test_tree is None:
    print("Gold", gold_tree)
    print("Test", "none")
    gold_traces = get_traces(gold_tree)
    gold_items = mapping_to_items(gold_traces)
    print(0, 0, len(gold_items))
    continue

  # Modify as per options
  if options["remove_function_labels"][1]:
    treebanks.remove_function_tags(test_tree)
    treebanks.remove_function_tags(gold_tree)
###  if options["homogenise_top_label"][1]:
###    test_tree = treebanks.homogenise_tree(test_tree)
###    gold_tree = treebanks.homogenise_tree(gold_tree)
###  if len(options['labels_to_remove'][1]) > 0:
###    treebanks.remove_nodes(test_tree, lambda(n): n.label in options['labels_to_remove'][1], True, True)
###   treebanks.remove_nodes(gold_tree, lambda(n): n.label in options['labels_to_remove'][1], True, True)
###  if len(options['words_to_remove'][1]) > 0:
###    treebanks.remove_nodes(test_tree, lambda(n): n.word in options['words_to_remove'][1], True, True)
###    treebanks.remove_nodes(gold_tree, lambda(n): n.word in options['words_to_remove'][1], True, True)
  if len(options['equivalent_labels'][1]) > 0:
    for tree in [gold_tree, test_tree]:
      for node in gold_tree:
        for pair in options['equivalent_labels'][1]:
          if node.label in pair:
            node.label = pair[0]
  if len(options['equivalent_words'][1]) > 0:
    for tree in [gold_tree, test_tree]:
      for node in gold_tree:
        for pair in options['equivalent_words'][1]:
          if node.word in pair:
            node.word = pair[0]
###  if options['remove_trivial_unaries'][1]:
###    treebanks.remove_trivial_unaries(test_tree)
###    treebanks.remove_trivial_unaries(gold_tree)

  # Score and report
  print("Gold", gold_tree)
  gold_traces = get_traces(gold_tree)
  gold_items = mapping_to_items(gold_traces)

  print("Test", test_tree)
  test_traces = get_traces(test_tree)
  test_items = mapping_to_items(test_traces)

  match = 0
  for item in gold_items:
    if item in test_items:
      match += 1
      print("  Match", item)
      if item[0] not in match_by_type:
        match_by_type[item[0]] = 0
      match_by_type[item[0]] += 1
  for item in gold_items:
    if item[0] not in gold_by_type:
      gold_by_type[item[0]] = 0
    gold_by_type[item[0]] += 1
    if item not in test_items:
      print("  Missing gold", item)
  for item in test_items:
    if item[0] not in test_by_type:
      test_by_type[item[0]] = 0
    test_by_type[item[0]] += 1
    if item not in gold_items:
      print("  Extra test", item)
  print(match, len(test_items), len(gold_items))

done = set()
for sym in match_by_type:
  done.add(sym)
  match = match_by_type[sym]
  gold = 0
  test = 0
  if sym in gold_by_type:
    gold = gold_by_type[sym]
  if sym in test_by_type:
    test = test_by_type[sym]
  print(sym, match, gold, test)
for sym in gold_by_type:
  if sym not in done:
    done.add(sym)
    match = 0
    test = 0
    gold = gold_by_type[sym]
    if sym in test_by_type:
      test = test_by_type[sym]
    print(sym, match, gold, test)
for sym in test_by_type:
  if sym not in done:
    done.add(sym)
    match = 0
    gold = 0
    test = test_by_type[sym]
    print(sym, match, gold, test)
