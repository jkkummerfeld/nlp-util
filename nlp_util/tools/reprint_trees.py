#!/usr/bin/env python

import sys
from nlp_util import ptb, render_tree

tex_start = '''\\documentclass[11pt]{article}
\\usepackage{times}
\\usepackage{ulem}
\\usepackage{amsmath}
\\usepackage{multirow}
\\usepackage{graphicx}
\\usepackage[landscape, top=0.2cm, bottom=0.2cm, left=0.2cm, right=0.2cm]{geometry}
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
\\maketitle'''

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

def main():
	if len(sys.argv) == 1:
		print "Read trees from stdin and print them to stdout."
		print "Options:"
		print "  -(i)nput = (p)enn treebank | (c)onll or OntoNotes"
		print "  -(f)ormat = (s)ingle_line | (m)ulti_line | (t)ex | (w)ords | (o)ntonotes"
		print "  -(e)dit = remove (t)races, remove (f)unction tags, apply (c)ollins rules, (h)omogenise top"
		print "  -(g)old = <gold filenmae>"
		print "e.g. %s -f t -e tf -g trees_gold < trees_in > trees_out" % sys.argv[0]
		sys.exit(0)

	args = get_args()
	in_format = args["i"] == 'p' if 'i' in args else True
	out_format = args["f"] if 'f' in args else 's'
	edits = args["e"] if 'e' in args else 'c'
	homogenise_top = 'h' in edits
	gold_file = args["g"] if 'g' in args else None
	if gold_file is not None:
		gold_file = ptb.generate_trees(gold_file)

	if out_format == 't':
		print tex_start
	for tree in ptb.generate_trees(sys.stdin, return_empty=True, homogenise=homogenise_top):
		gold_tree = None
		if gold_file is not None:
			gold_tree = gold_file.next()

		if tree is None:
			print
			continue

		# Apply edits
		if 't' in edits:
			tree = ptb.remove_traces(tree)
			if gold_tree is not None:
				gold_tree = ptb.remove_traces(gold_tree)
		if 'f' in edits:
			tree = ptb.remove_function_tags(tree)
			if gold_tree is not None:
				gold_tree = ptb.remove_function_tags(gold_tree)
		if 'c' in edits:
			tree = ptb.apply_collins_rules(tree)
			if gold_tree is not None:
				gold_tree = ptb.apply_collins_rules(gold_tree)

		# Print tree
		if out_format == 's':
			print render_tree.text_tree(tree, single_line=True)
		elif out_format == 'm':
			print render_tree.text_tree(tree, single_line=False)
		elif out_format == 'o':
			print render_tree.text_ontonotes(tree)
		elif out_format == 't':
			if gold_tree is None:
				print '\\scalebox{\\derivscale}{'
				print render_tree.tex_synttree(tree)
				print '}\n\\small\n\\pagebreak'
			else:
				# TODO: Add a flag to allow choosing to print only the error region
				print '\\scalebox{\\derivscale}{'
				other_spans = gold_tree.span_dict()
				print render_tree.tex_synttree(tree, other_spans)
				print '}\n\\small\n\\pagebreak'
				print '\\scalebox{\\derivscale}{'
				other_spans = tree.span_dict()
				print render_tree.tex_synttree(gold_tree, other_spans)
				print '}\n\\small\n\\pagebreak'
		elif out_format == 'w':
			print render_tree.text_words(tree)
	if out_format == 't':
		print '\\end{document}'

if __name__ == '__main__':
    main()
