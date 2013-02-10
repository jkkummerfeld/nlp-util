#!/usr/bin/env python
'''Create a bar table from output.

Executed as:
	./gen_table.py <prefix> <data> [mapping]

The data should look as follows:
	<non_num> <input_ID (single word)>
	<num1> <name2>
	<num2> <name2>

And the mapping (if used) should be:
	<input_ID2> <text1 (multiple words allowed)>
	<input_ID2> <text2>'''

import sys
sys.path.insert(0, "util")
try:
	import init
except ImportError:
	raise Exception("Remember to set up a symlink to the util directory")

import string

'''
\begin{tabular}{lcc}
	\hline
		Label & Val1 & Val2 \\
	\hline
	\hline
Best & 1 & 0 \\
Sys1 & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} \\
Sys2 & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} \\
Worst & 1000 & 2000 \\
	\hline
\end{tabular}
'''

def get_data(filename):
	data = []
	cur_name = None
	cur_data = None
	for line in open(filename):
		line = line.strip()
		if len(line) == 0:
			continue
		if line[0] not in string.digits:
			cur_name = line.split()[1]
			cur_data = {}
			data.append((cur_name, cur_data))
		else:
			val = float(line.split()[0])
			cur_data[' '.join(line.split()[1:])] = val
	return data

def get_mapping(filename):
	mapping = {}
	for line in open(filename):
		line = line.strip()
		mapping[line.split()[0]] = ' '.join(line.split()[1:])
	return mapping

if __name__ == '__main__':
	# TODO, shift to a uniform style of module documentation, then just skip all of this!
	desc = __doc__.split('\n')
	arg_info = desc[1]
	further_desc = '\n'.join(desc[2:])
	desc = desc[0]
	init.argcheck(sys.argv, 3, 4, desc, arg_info, further_desc)

	out = open(sys.argv[1] + '.table', 'w')
	log = open(sys.argv[1] + '.table.log', 'w')
	init.header(sys.argv, log)

	data = get_data(sys.argv[2])
	mapping = {}
	if len(sys.argv) == 4:
		mapping = get_mapping(sys.argv[3])
	print data
	print mapping

	out.close()
	log.close()

