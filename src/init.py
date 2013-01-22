#!/usr/bin/env python

import sys

def header(args, out=sys.stdout):
	header = "# This output was produced by the following command:"
	header += "\n# %s" % ' '.join(args)
	header += "\n#"
	if type(out) == type(sys.stdout):
		print >> out, header
	elif type(out) == type([]):
		for outfile in out:
			print >> outfile, header
	else:
		print >> sys.stderr, "Invalid list of output files passed to header"
		sys.exit(1)

def argcheck(argv, minargs, maxargs, desc, arg_desc):
	if minargs <= len(argv) <= maxargs:
		return
	print >> sys.stderr, desc
	print >> sys.stderr, ("  %s " + arg_desc) % argv[0]
	sys.exit(1)

if __name__ == "__main__":
	print "Running doctest"
	import doctest
	doctest.testmod()

