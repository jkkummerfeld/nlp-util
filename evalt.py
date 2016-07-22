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

def get_traces(parse, mapping=None):
  if mapping is None:
    mapping = ({}, {}, {}, {}, {}, {})
  # 0 - The observed position of words
  # 1 - Null position that can be traced somewhere
  # 2 - The observed position of words that match other observed words
  # 3 - The null position of unobserved words that are referenced
  # 4 - The null position of unobserved words

  # 0 - The observed position of words, e.g. NP-1
  plabel = parse.label
  if '-' in plabel and '=' not in plabel and get_reference(plabel) is not None:
    signature = (parse.span, plabel)
    num = plabel.split('-')[-1]
    if signature not in mapping[0]:
      mapping[0][signature] = []
    mapping[0][signature].append((num, parse))

  # 1 - Null position that can be traced somewhere, e.g. (-NONE- *-1)
  if plabel == '-NONE-' and get_reference(parse.word) is not None:
    num = parse.word.split('-')[-1]
    if num not in mapping[1]:
      mapping[1][num] = []
    mapping[1][num].append(parse)

  # 2 - The observed position of words that match other observed words e.g. NP=1
  if '=' in plabel and get_reference(plabel, '=') is not None:
    num = plabel.split('=')[-1]
    if num not in mapping[2]:
      mapping[2][num] = []
    mapping[2][num].append(parse)

  # 3 and 4 - The null position of unobserved words e.g. (-NONE- *), and (NP-SBJ-3 (-NONE- *T*-5) )
  if plabel == '-NONE-' and get_reference(parse.word) is None:
    ref = None
    parent = parse
    while parent.parent is not None and parent.wordspan[0] == parent.wordspan[1]:
      if ref is None:
        ref = get_reference(parent.label)
      parent = parent.parent
    signature = (parent.span, parent.label)
    if signature not in mapping[4]:
      mapping[4][signature] = []
    mapping[4][signature].append((parent, parse))
    # 3 - The null position of unobserved words that are referenced
    if ref is not None:
      if signature not in mapping[3]:
        mapping[3][signature] = []
      mapping[3][signature].append((parent, parse, ref))

  for subparse in parse.subtrees:
    get_traces(subparse, mapping)

  return mapping

def get_span(node):
  if node.wordspan[0] == node.wordspan[1]:
    return get_span(node.parent)
  else:
    return node.wordspan

def mapping_to_items(mapping):
  # 0 - The observed position of words
  # 1 - Null position that can be traced somewhere
  # 2 - The observed position of words that match other observed words
  # 3 - The null position of unobserved words that are referenced
  # 4 - The null position of unobserved words

  items = []

  # Add items without coindexation
  for signature in mapping[4]:
    for parent, node in mapping[4][signature]:
      label = ""
      if node.parent.wordspan[0] == node.parent.wordspan[1]:
        label = node.parent.label.split('-')[0]
      items.append((node.word.split('-')[0], get_span(node), label))

  # Add items with simple coindexation
  for num in mapping[1]:
    for node in mapping[1][num]:
      # Find referent
      refs = []
      for signature in mapping[0]:
        for onum, onode in mapping[0][signature]:
          if onum == num:
            refs.append(onode)
      if len(refs) != 1:
        print("Error - could not resolve trace", num, node, refs)
      ref = refs[0]
      label = ""
      if node.parent.wordspan[0] == node.parent.wordspan[1]:
        label = node.parent.label.split('-')[0]
      items.append((node.word.split('-')[0], get_span(node), label, get_span(ref), ref.label.split('-')[0]))

  # Add items with gapping
  for num in mapping[2]:
    for node in mapping[2][num]:
      # Find referent
      refs = []
      for signature in mapping[0]:
        for onum, onode in mapping[0][signature]:
          if onum == num:
            refs.append(onode)
      if len(refs) != 1:
        for info in mapping:
          print(info)
        raise Exception("Error - could not resolve trace", num, node, refs)
      ref = refs[0]
      items.append(("gapping", get_span(node), node.label.split('=')[0], get_span(ref), ref.label.split('-')[0]))

  # Add items with chained coindexation
  for signature in mapping[3]:
    for parent, node, num in mapping[3][signature]:
      # Follow chain
      in_chain = True
      while in_chain:
        in_chain = False
        for osignature in mapping[3]:
          if '=' not in osignature[1]:
            for oparent, onode, onum in mapping[3][signature]:
              oref = get_reference(onode.word)
              if oref == num:
                in_chain = True
                num = onum
      refs = []
      for signature in mapping[0]:
        for onum, onode in mapping[0][signature]:
          if onum == num:
            refs.append(onode)
      if len(refs) != 1:
        print("Error - could not resolve trace", num, node, refs)
      ref = refs[0]
      label = ""
      if node.parent.wordspan[0] == node.parent.wordspan[1]:
        label = node.parent.label.split('-')[0]
      items.append((node.word.split('-')[0], get_span(node), label, get_span(ref), ref.label.split('-')[0]))

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
  print("Test", test_tree)
  gold_traces = get_traces(gold_tree)
  test_traces = get_traces(test_tree)

  gold_items = mapping_to_items(gold_traces)
  test_items = mapping_to_items(test_traces)

  match = 0
  for item in gold_items:
    if item in test_items:
      match += 1
      print("  Match", item)
      if item[0] not in match_by_type:
        match_by_type[item[0]] = 1
      else:
        match_by_type[item[0]] += 1
  for item in gold_items:
    if item[0] not in gold_by_type:
      gold_by_type[item[0]] = 1
    else:
      gold_by_type[item[0]] += 1
    if item not in test_items:
      print("  Missing gold", item)
  for item in test_items:
    if item[0] not in test_by_type:
      test_by_type[item[0]] = 1
    else:
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
