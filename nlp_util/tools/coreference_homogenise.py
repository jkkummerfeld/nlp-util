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
except ImportError:
	raise Exception("Remember to set up a symlink to the util directory")

import os, glob
from collections import defaultdict

def convert_underscored_filename(filename):
	head, tail = os.path.split(filename)
	if tail is None or tail == '':
		raise Exception("Impossible filename")
	name = tail.split('.')[0]
	part = name.split('__')[-1]
	name = '/'.join(name.split('__')[:-1])
	return name, part

def multifile_process(path, call):
	auto = defaultdict(lambda: {})
	gold = defaultdict(lambda: {})
	for filename in glob.glob(path):
		name, part = convert_underscored_filename(filename)
		if "tc/ch/00/ch" in name:
			val = int(name.split('_')[-1]) * 10 - 1
			name = "tc/ch/00/ch_%04d" % val
		coreference_reading.read_conll_matching_file(gold_src, name, gold)
		auto[name][part] = call(filename, gold[name][part]['text'])
	return auto, gold

def read_bart(auto_src, gold_src):
	'''BART output is in a separate file for each doc.'''
	path = os.path.join(auto_src, '*')
	call = coreference_reading.read_bart_coref
	return multifile_process(path, call)

def read_cherrypicker(auto_src, gold_src):
	'''Cherrypicker output is in a separate file for each doc.'''
	path = os.path.join(auto_src, '*responses')
	call = coreference_reading.read_cherrypicker_coref
	return multifile_process(path, call)

def read_ims(auto_src, gold_src):
	'''IMS produces CoNLL style output, but with all fields. This will read it as normal.'''
	auto = coreference_reading.read_conll_doc(auto_src, None, True, False, False, True)
	gold = coreference_reading.read_conll_matching_files(auto, gold_src)
	return auto, gold

def read_opennlp(auto_src, gold_src):
	print "OpenNLP support is under development."

def read_reconcile(auto_src, gold_src):
	'''Reconcile output is in a separate file for each doc.'''
	path = os.path.join(auto_src, '*coref')
	call = coreference_reading.read_reconcile_coref
	return multifile_process(path, call)

def read_relaxcor(auto_src, gold_src):
	print "RelaxCor support is under development."

def read_stanford_xml(auto_src, gold_src):
	'''Stanford without conll settings producesone xml file for each input'''
	path = os.path.join(auto_src, '*xml')
	call = coreference_reading.read_stanford_coref
	return multifile_process(path, call)

def read_stanford(auto_src, gold_src):
	'''Stanford produces CoNLL style output, but with all fields. This will read it as normal.'''
	auto = coreference_reading.read_conll_doc(auto_src, None, True, False, False, True)
	gold = coreference_reading.read_conll_matching_files(auto, gold_src)
	return auto, gold

def read_uiuc(auto_src, gold_src):
	'''UIUC output is in a separate file for each doc.'''
	path = os.path.join(auto_src, '*out')
	call = coreference_reading.read_uiuc_coref
	return multifile_process(path, call)

if __name__ == '__main__':
	init.argcheck(sys.argv, 5, 5, "Translate a system output into the CoNLL format", "<prefix> <[bart,cherrypicker,ims,opennlp,reconcile,relaxcor,stanford,stanford_xml,uiuc]> <dir | file> <gold dir>")

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
		'stanford_xml': read_stanford_xml,
		'stanford': read_stanford,
		'uiuc': read_uiuc
	}[sys.argv[2]](auto_src, gold_src)
	
	for doc in auto:
		for part in auto[doc]:
			for mention in auto[doc][part]['mentions']:
				if mention[1] >= mention[2]:
					info = "Invalid mention span %s from %s %s" % (str(mention), doc, part)
					info += '\n' + gold[doc][part]['text'][mention[0]]
					raise Exception(info)

	coreference_rendering.print_conll_style(auto, out)

	out.close()
	log.close()
