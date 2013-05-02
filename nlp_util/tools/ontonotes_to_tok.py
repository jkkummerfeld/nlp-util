#!/usr/bin/env python

import sys
try:
	from nlp_util import init, coreference_reading
except ImportError:
	raise Exception("Remember to either install nlp_util or set up a symlink to the nlp_util directory")

if __name__ == '__main__':
	init.argcheck(sys.argv, 3, 3, "Print conll text", "<prefix> <data>")

	prefix = sys.argv[1]
	data = coreference_reading.read_all(sys.argv[2])

	for doc in data:
		for part in data[doc]:
			text = data[doc][part]['text']
			filename = '__'.join(doc.split('/') + [part])
			out = open(prefix + filename, 'w')
			for line in text:
				print >> out, ' '.join(line)
