#!/usr/bin/env python

import sys
sys.path.insert(0, "util")
try:
	import ptb, render_tree, nlp_eval
except ImportError:
	raise Exception("Remember to set up a symlink to the util directory")

def mprint(text, out_dict, out_name):
	all_stdout = True
	for key in out_dict:
		if out_dict[key] != sys.stdout:
			all_stdout = False
	
	if all_stdout:
		print text
	elif out_name == 'all':
		for key in out_dict:
			print >> out_dict[key], text
	else:
		print >> out_dict[out_name], text


if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "Print trees with colours to indicate errors (red for extra, blue for missing, yellow for crossing missing)"
		print "   %s <gold> <test> <output_prefix>" % sys.argv[0]
		print "Running doctest"
		import doctest
		doctest.testmod()
		sys.exit(0)

	out = {
		'err': sys.stdout,
		'notrace': sys.stdout,
		'nofunc': sys.stdout,
		'post_collins': sys.stdout,
		'tex': sys.stdout
	}
	if len(sys.argv) > 3:
		prefix = sys.argv[3]
		for key in out:
			out[key] = open(prefix + '.' + key, 'w')
	gold_in = open(sys.argv[1])
	test_in = open(sys.argv[2])
	sent_no = 0
	stats = {
		'notrace': [0, 0, 0],
		'nofunc': [0, 0, 0],
		'post_collins': [0, 0, 0]
	}
	
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

\\title{Parser errors}
\\author{}

\\date{}

\\begin{document}
\\maketitle'''
	mprint(tex_start, out, 'tex')

	while True:
		sent_no += 1
		gold_text = gold_in.readline()
		test_text = test_in.readline()
		if gold_text == '' and test_text == '':
			mprint("End of both input files", out, 'err')
			break
		elif gold_text == '':
			mprint("End of gold input", out, 'err')
			break
		elif test_text == '':
			mprint("End of test input", out, 'err')
			break

		mprint("Sentence %d:" % sent_no, out, 'all')

		gold_text = gold_text.strip()
		test_text = test_text.strip()
		if len(gold_text) == 0:
			mprint("No gold tree", out, 'all')
			continue
		elif len(test_text) == 0:
			mprint("Not parsed", out, 'all')
			continue

		gold_complete_tree = ptb.PTB_Tree()
		gold_complete_tree.set_by_text(gold_text)
		gold_nofunc_tree = ptb.remove_function_tags(gold_complete_tree)
		gold_notrace_tree = ptb.remove_traces(gold_complete_tree)
		gold_tree = ptb.apply_collins_rules(gold_complete_tree)
		if gold_tree is None:
			mprint("Empty gold tree", out, 'all')
			mprint(gold_complete_tree.__repr__(), out, 'all')
			mprint(gold_tree.__repr__(), out, 'all')
			continue

		test_complete_tree = ptb.PTB_Tree()
		test_complete_tree.set_by_text(test_text)
		test_nofunc_tree = ptb.remove_function_tags(test_complete_tree)
		test_notrace_tree = ptb.remove_traces(test_complete_tree)
		test_tree = ptb.apply_collins_rules(test_complete_tree)
		if test_tree is None:
			mprint("Empty test tree", out, 'all')
			mprint(test_complete_tree.__repr__(), out, 'all')
			mprint(test_tree.__repr__(), out, 'all')
			continue

		gold_words = gold_tree.word_yield()
		test_words = test_tree.word_yield()
		if len(test_words.split()) != len(gold_words.split()):
			mprint("Sentence lengths do not match...", out, 'all')
			mprint("Gold: " + gold_words.__repr__(), out, 'all')
			mprint("Test: " + test_words.__repr__(), out, 'all')

		mprint("After removing traces:", out, 'notrace')
		mprint(render_tree.text_coloured_errors(test_notrace_tree, gold_notrace_tree).strip(), out, 'notrace')
		match, gold, test = ptb.counts_for_prf(test_notrace_tree, gold_notrace_tree)
		stats['notrace'][0] += match
		stats['notrace'][1] += gold
		stats['notrace'][2] += test
		p, r, f = nlp_eval.calc_prf(match, gold, test)
		mprint("Eval notrace: %.2f  %.2f  %.2f" % (p*100, r*100, f*100), out, 'notrace')

		mprint("After removing traces and function tags:", out, 'nofunc')
		mprint(render_tree.text_coloured_errors(test_nofunc_tree, gold_nofunc_tree).strip(), out, 'nofunc')
		match, gold, test = ptb.counts_for_prf(test_nofunc_tree, gold_nofunc_tree)
		stats['nofunc'][0] += match
		stats['nofunc'][1] += gold
		stats['nofunc'][2] += test
		p, r, f = nlp_eval.calc_prf(match, gold, test)
		mprint("Eval nofunc: %.2f  %.2f  %.2f" % (p*100, r*100, f*100), out, 'nofunc')

		mprint("After applying collins rules:", out, 'post_collins')
		mprint(render_tree.text_coloured_errors(test_tree, gold_tree).strip(), out, 'post_collins')
		match, gold, test = ptb.counts_for_prf(test_tree, gold_tree)
		stats['post_collins'][0] += match
		stats['post_collins'][1] += gold
		stats['post_collins'][2] += test
		p, r, f = nlp_eval.calc_prf(match, gold, test)
		mprint("Eval post collins: %.2f  %.2f  %.2f" % (p*100, r*100, f*100), out, 'post_collins')

		# Work out the minimal span to show all errors
		gold_spans = set([(span[2].label, span[0], span[1]) for span in gold_nofunc_tree.get_spans()])
		test_spans = set([(span[2].label, span[0], span[1]) for span in test_nofunc_tree.get_spans()])
		diff = gold_spans.symmetric_difference(test_spans)
		width = [1e5, -1]
		for span in diff:
			if span[2] - span[1] == 1:
				continue
			if span[1] < width[0]:
				width[0] = span[1]
			if span[2] > width[1]:
				width[1] = span[2]
		mprint('\n\\scalebox{\\derivscale}{', out, 'tex')
		mprint(render_tree.tex_synttree(test_nofunc_tree, gold_spans, span=width), out, 'tex')
		mprint( '}\n\\small\n(a) Parser output\n\n\\vspace{3mm}\n\\scalebox{\\derivscale}{', out, 'tex')
		mprint(render_tree.tex_synttree(gold_nofunc_tree, test_spans, span=width), out, 'tex')
		mprint( '}\n\\small\n(b) Gold tree\n\\pagebreak', out, 'tex')

		mprint("", out, 'all')
	for key in ['notrace', 'nofunc', 'post_collins']:
		match = stats[key][0]
		gold = stats[key][1]
		test = stats[key][2]
		p, r, f = nlp_eval.calc_prf(match, gold, test)
		mprint("Overall %s: %.2f  %.2f  %.2f" % (key, p*100, r*100, f*100), out, key)
	
	mprint('\\end{document}', out, 'tex')
