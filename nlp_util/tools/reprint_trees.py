#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:

import sys
from nlp_util import pstree, treebanks, render_tree

#TODO print run information
#TODO Add the ability to print multiple outputs in a single run, to dfferent files

tex_start = '''\\documentclass[11pt]{article}
\\usepackage{times}
\\usepackage{ulem}
\\usepackage{amsmath}
\\usepackage{multirow}
\\usepackage{graphicx}
\\usepackage[landscape, top=0.2cm, bottom=0.2cm, left=0.2cm, right=0.2cm]{geometry}
%\setlength{\\paperheight}{50cm}
%\setlength{\\textheight}{49cm}
%\setlength{\\paperwidth}{20cm}
%\setlength{\\textwidth}{19cm}
\\usepackage{enumerate}
\\usepackage{multirow}
\\usepackage{synttree}

\\newcommand{\\wrongnode}[1]{\\textbf{\\fbox{#1}}}
\\branchheight{0.33in}
\\trianglebalance{50}
\\childsidesep{1em}
\\childattachsep{0.5in}
\\newcommand{\\derivscale}{0.8}
\\newcommand{\\derivspace}{\\vspace{-4mm}}
\\newcommand{\\derivaftercompress}{\\vspace{-2mm}}

\\title{Parses}
\\author{}

\\date{}

\\begin{document}
%%%\\maketitle'''

def get_args():
  args = {}
  i = 1
  while i < len(sys.argv):
    if sys.argv[i][0] == '-':
      name = sys.argv[i][1:]
      i += 1
      if sys.argv[i][0] == '=':
        i += 1
      if sys.argv[i][0] != '-':
        val = sys.argv[i]
      else:
        val = True
      args[name] = val
    i += 1
  return args

if __name__ == '__main__':
  if len(sys.argv) == 1:
    print "Read trees from stdin and print them to stdout."
    print "Options:"
    print "  -(i)nput = (p)enn treebank | (c)onll | (s)plit head"
    print "  -(o)utput = (s)ingle_line [with (t)races] | (m)ulti_line [with (t)races] | (t)ex | (w)ords | (o)ntonotes | (p)os tagged | (h)ead automata"
    print "  -(e)dit = remove (t)races, remove (f)unction tags, apply (c)ollins rules, (h)omogenise top, remove trivial (u)naries"
    print "  -(g)old = <gold filenmae> (can be used by the tex output)"
    print "\ne.g. %s -o s -e tf < trees_in > trees_out" % sys.argv[0]
    sys.exit(0)

  args = get_args()
  in_format = args["i"] if 'i' in args else 'p'
  out_format = args["o"] if 'o' in args else 's'
  edits = args["e"] if 'e' in args else ''
  gold_file = args["g"] if 'g' in args else None
  read_func = treebanks.ptb_read_tree
  if 'c' in in_format:
    read_func = treebanks.conll_read_tree
  elif 's' in in_format:
    read_func = treebanks.shp_read_tree

  if gold_file is not None:
    gold_file = treebanks.generate_trees(gold_file, read_func, allow_empty_labels=True)

  if out_format == 't':
    print tex_start
  for tree in treebanks.generate_trees(sys.stdin, read_func, return_empty=True, allow_empty_labels=True):
    gold_tree = None
    if gold_file is not None:
      gold_tree = gold_file.next()

    if tree is None:
      print
      continue

    # Apply edits
    if 'h' in edits:
      tree = treebanks.homogenise_tree(tree)
      if gold_tree is not None:
        gold_tree = treebanks.homogenise_tree(gold_tree)
    if 't' in edits:
      treebanks.remove_traces(tree)
      if gold_tree is not None:
        treebanks.remove_traces(gold_tree)
    if 'f' in edits:
      treebanks.remove_function_tags(tree)
      if gold_tree is not None:
        treebanks.remove_function_tags(gold_tree)
    if 'c' in edits:
      treebanks.apply_collins_rules(tree)
      if gold_tree is not None:
        treebanks.apply_collins_rules(gold_tree)
    if 'u' in edits:
      # This must be after all other deletion to work properly
      treebanks.remove_trivial_unaries(tree)
      if gold_tree is not None:
        treebanks.remove_trivial_unaries(gold_tree)

    # Print tree
    if out_format == 's':
      print render_tree.text_tree(tree, single_line=True)
    elif out_format == 'm':
      print render_tree.text_tree(tree, single_line=False)
    elif out_format == 'st':
      print render_tree.text_tree(tree, single_line=True, show_traces=True)
    elif out_format == 'mt':
      print render_tree.text_tree(tree, single_line=False, show_traces=True)
    elif out_format == 'o':
      print render_tree.text_ontonotes(tree)
    elif out_format == 'p':
      print render_tree.text_POS_tagged(tree)
    elif out_format == 'h':
      print render_tree.shg_format(tree)
    elif out_format == 't':
      if gold_tree is None:
        print '\\scalebox{\\derivscale}{'
        print render_tree.tex_synttree(tree)
        print '}\n\n\\small\n%%%\\pagebreak'
      else:
        # TODO: Add a flag to allow choosing to print only the error region
        print '\\scalebox{\\derivscale}{'
        other_spans = gold_tree.span_dict()
        print render_tree.tex_synttree(tree, other_spans)
        print '}\n\n\\small\n%%%\\pagebreak'
        print '\\scalebox{\\derivscale}{'
        other_spans = tree.span_dict()
        print render_tree.tex_synttree(gold_tree, other_spans)
        print '}\n\n\\small\n\\pagebreak'
    elif out_format == 'w':
      print render_tree.text_words(tree)
  if out_format == 't':
    print '\\end{document}'

