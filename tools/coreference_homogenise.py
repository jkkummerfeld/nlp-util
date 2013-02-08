#!/usr/bin/env python
'''Converts output from a range of coref systems into the style of the 2011
CoNLL Shared Task.

For some systems the output is in a single file, for others the filenames are
assumed to follow this pattern (easily achievable when running the systems):

source filename:  bn__voa__02__voa_0220__000.<whatever>
equivalent file:  bn/voa/02/voa_0220.v2_auto_conll
intended header:  #begin document (bn/voa/02/voa_0220); part 000
'''

import sys
sys.path.insert(0, "util")
try:
	import init, coreference_reading, coreference_rendering
except:
	raise Exception("Remember to set up a symlink to the util directory")

import os, glob
from collections import defaultdict

def read_bart(auto_src, gold_src):
	'''BART output is in a separate file for each doc.'''
	auto = defaultdict(lambda: {})
	gold = defaultdict(lambda: {})
	for filename in glob.glob(os.path.join(auto_src, '*')):
		head, tail = os.path.split(filename)
		if tail is None or tail == '':
			raise Exception("Impossible filename")
		name = tail.split('.')[0]
		part = name.split('__')[-1]
		name = '/'.join(name.split('__')[:-1])
		coreference_reading.read_conll_matching_file(gold_src, name, gold)
		auto[name][part] = coreference_reading.read_bart_coref(filename, gold[name][part]['text'])
	return auto, gold

def read_cherrypicker(auto_src, gold_src):
	'''Cherrypicker output is in a separate file for each doc.'''
	print "Cherrypicker support is under development."

def read_ims(auto_src, gold_src):
	'''IMS produces CoNLL style output, but with all fields. This will read it as normal.'''
	auto = coreference_reading.read_conll_doc(auto_src, None, True, False, False, True)
	gold = coreference_reading.read_conll_matching_files(auto, gold_src)
	return auto, gold

def read_opennlp(auto_src, gold_src):
	print "OpenNLP support is under development."

def read_reconcile(auto_src, gold_src):
	'''Reconcile output is in a separate file for each doc.'''
	auto = defaultdict(lambda: {})
	gold = defaultdict(lambda: {})
	for filename in glob.glob(os.path.join(auto_src, '*coref')):
		head, tail = os.path.split(filename)
		if tail is None or tail == '':
			raise Exception("Impossible filename")
		name = tail.split('.')[0]
		part = name.split('__')[-1]
		name = '/'.join(name.split('__')[:-1])
		coreference_reading.read_conll_matching_file(gold_src, name, gold)
		auto[name][part] = coreference_reading.read_reconcile_coref(filename, gold[name][part]['text'])
	return auto, gold

def read_relaxcor(auto_src, gold_src):
	print "RelaxCor support is under development."

def read_stanford(auto_src, gold_src):
	auto = coreference_reading.read_conll_doc(auto_src, None, True, False, False, True)
	gold = coreference_reading.read_conll_matching_files(auto, gold_src)
	return auto, gold

def read_uiuc(auto_src, gold_src):
	print "UIUC support is under development."

if __name__ == '__main__':
	init.argcheck(sys.argv, 5, 5, "Translate a system output into the CoNLL format", "<prefix> <[bart,cherrypicker,ims,opennlp,reconcile,relaxcor,stanford.uiuc]> <dir | file> <gold dir>")

	out = open(sys.argv[1] + '.out', 'w')
	log = open(sys.argv[1] + '.log', 'w')
	init.header(sys.argv, log)

	auto_src = sys.argv[3]
	gold_src = sys.argv[4]
	auto, gold = {
		'bart': read_bart,
		'cherrypicker': read_cherrypicker,
		'ims': read_ims,
		'opennlp': read_opennlp,
		'reconcile': read_reconcile,
		'relaxcor': read_relaxcor,
		'stanford': read_stanford,
		'uiuc': read_uiuc
	}[sys.argv[2]](auto_src, gold_src)

	coreference_rendering.print_conll_style(auto, out)

