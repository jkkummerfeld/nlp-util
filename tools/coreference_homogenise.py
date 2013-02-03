#!/usr/bin/env python
'''Converts output from a range of coref systems into the style of the 2011
CoNLL Shared Task.

For some systems the output is in a single file, for others the filenames are
assumed to follow this pattern (easily achievable when running the systems):

source filename:  bn__voa__02__voa_0220__000.bart.out
equivalent file:  bn/voa/02/voa_0220.v2_auto_conll
intended header:  #begin document (bn/voa/02/voa_0220); part 000
'''

import sys
sys.path.insert(0, "util")
try:
	import init, coreference_reading
except:
	raise Exception("Remember to set up a symlink to the util directory")

from collections import defaultdict

def read_bart(src):
	'''BART output is in a separate file for each doc.
	'''
	print "BART support is under development."

def read_cherrypicker(src):
	'''Cherrypicker output is in a separate file for each doc.
	'''
	print "Cherrypicker support is under development."

def read_ims(src):
	'''IMS produces CoNLL style output, but with all fields. This will read it as normal.
	'''
	return coreference_reading.read_coref_system_output(src)

def read_opennlp(src):
	print "OpenNLP support is under development."

def read_reconcile(src):
	print "Reconcile support is under development."

def read_relaxcor(src):
	print "RelaxCor support is under development."

def read_stanford(src):
	print "Stanford support is under development."

def read_uiuc(src):
	print "UIUC support is under development."

def print_data(data, out):
	pass

if __name__ == '__main__':
	init.argcheck(sys.argv, 4, 4, "Translate a system output into the CoNLL format", "<prefix> <[bart,cherrypicker,ims,opennlp,reconcile,relaxcor,stanford.uiuc]> <dir>")

	out = open(sys.argv[1] + '.out', 'w')
	log = open(sys.argv[1] + '.log', 'w')
	init.header(sys.argv, log)

	src = sys.argv[3]
	data = {
		'bart': read_bart,
		'cherrypicker': read_cherrypicker,
		'ims': read_ims,
		'opennlp': read_opennlp,
		'reconcile': read_reconcile,
		'relaxcor': read_relaxcor,
		'stanford': read_stanford,
		'uiuc': read_uiuc
	}[sys.argv[2]](src)

	print_data(data, out)

