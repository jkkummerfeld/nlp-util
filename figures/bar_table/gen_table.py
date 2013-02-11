#!/usr/bin/env python
'''Create a bar table from output.

Executed as:
	./gen_table.py <prefix> <data> [name mapping] [error order] [system order and maybe extra columns]

The data should look as follows:
	<non_num> <input_ID (a filename, we use the file, without path)>
	<num1> <name2>
	<num2> <name2>

If used, the other files should be as follows.  If unused, files will be
generated.  One easy approach is to run once without these, then edit the files
produced.
Name mapping:
	<input_ID1> <text1 (multiple words allowed)>
	<input_ID2> <text2>

Error order:
	<error name1> [| first line | second line | ...]
	<error name2> [| first line | second line | ...]
	line with just a '|' indiactes a vertical bar at that point in the table

System order and possibly extra columns:
	Titles <column name> <column name> ...
	<input_ID1> <val> <val>
	<input_ID2> <val> <val>'''

#TODO: Use extra column info for system order

import sys
sys.path.insert(0, "util")
try:
	import init
except ImportError:
	raise Exception("Remember to set up a symlink to the util directory")

import string, os

'''
\begin{tabular}{lcc}
	\hline
		Label & Val1 & Val2 \\
	\hline
	\hline
Best & 1 & 0 \\
Sys1 & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(0.000000,1)\end{pspicture}}\hspace{1.5mm} \\
Sys2 & \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(4.000000,1)\end{pspicture}}\hspace{1.5mm}& \scalebox{0.23}{\begin{pspicture}(0,0)(4,1)\psframe(0,0)(4,1)\psframe*[linecolor=black](0,0)(3.971480,1)\end{pspicture}}\hspace{1.5mm} \\
Worst & 1000 & 2000 \\
	\hline
\end{tabular}
'''

def print_top(error_order, out):
	col_format = ''.join(['|' if val == '|' else 'c' for val in error_order])
	print >> out, "\\begin{tabular}{l%s}" % (col_format)
	print >> out, "\t\\hline"
	parts_present = 1
	for error in error_order:
		if len(error) > 3:
			parts_present = len(error[3])
	if parts_present == 1:
		print >> out, "\tSystem & %s \\\\" % ' & '.join([val[0] for val in error_order if val != '|'])
	else:
		print >> out, "\tSystem & %s \\\\" % ' & '.join([val[0] if len(val) == 3 else val[3][0] for val in error_order if val != '|'])
		for i in xrange(1, parts_present):
			print >> out, "\t & %s \\\\" % ' & '.join(['' if len(val) == 3 else val[3][i] for val in error_order if val != '|'])
	print >> out, "\t\\hline"
	print >> out, "\t\\hline"
	print >> out, "\tBest & %s \\\\" % ' & '.join([str(int(val[1])) for val in error_order if val != '|'])

def print_data(system_order, error_order, data, mapping, out):
	entry_template = "\\scalebox{0.23}{\\begin{pspicture}(0,0)(4,1)\\psframe(0,0)(4,1)\\psframe*[linecolor=black](0,0)(%f,1)\\end{pspicture}}\\hspace{1.5mm}"
	text = {}
	for name, info in data:
		text[name] = []
		for error in error_order:
			if error == '|':
				continue
			emin = error[1]
			emax = error[2]
			val = info[error[0]] 
			text[name].append(4 * (val - emin) / (emax - emin))
	for system in system_order:
		name = os.path.split(system)[1]
		if name in mapping:
			name = mapping[name]
		print >> out, "\t%s & %s \\\\" % (name, ' & '.join([entry_template % val for val in text[system]]))

def print_bottom(error_order, out):
	print >> out, "\tWorst & %s \\\\" % ' & '.join([str(int(val[2])) for val in error_order if val != '|'])
	print >> out, "\t\\hline"
	print >> out, "\\end{tabular}"

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

def get_order(data, system_order_file, error_order_file):
	# Order the columns so that the most common is first
	ranges = {}
	for name, info in data:
		for label in info:
			if label not in ranges:
				ranges[label] = ((info[label], name), (info[label], name))
			elif info[label] < ranges[label][0][0]:
				ranges[label] = ((info[label], name), ranges[label][1])
			elif info[label] > ranges[label][1][0]:
				ranges[label] = (ranges[label][0], (info[label], name))
	error_order = []
	if error_order_file is not None:
		for line in open(error_order_file):
			line = line.strip()
			if line == '|':
				error_order.append(line)
			else:
				if '|' in line:
					key = line.split('|')[0].strip()
					parts = [part.strip() for part in line.split('|')[1:]]
					error_order.append((key, ranges[key][0][0], ranges[key][1][0], parts))
				else:
					error_order.append((line, ranges[line][0][0], ranges[line][1][0]))
	else:
		ranges = [(ranges[val], val) for val in ranges]
		ranges.sort(reverse=True)
		error_order = [(val[1], val[0][0][0], val[0][1][0]) for val in ranges]

	# Order the systems so that the best is at the top
	system_order = []
	if system_order_file is not None:
		system_order = [name.strip().split()[0] for name in open(system_order_file)][1:]
	else:
		first_error = error_order[0]
		for name, info in data:
			if first_error[0] not in info:
				raise Exception("Inconsistent sets of errors!")
			system_order.append((info[first_error[0]], name))
		system_order.sort()
		system_order = [val[1] for val in system_order]
	return system_order, error_order

def print_error_order(error_order, out):
	for val in error_order:
		if val == '|':
			print >> out, val
		else:
			print >> out, val[0]

if __name__ == '__main__':
	# TODO, shift to a uniform style of module documentation, then just skip all of this!
	desc = __doc__.split('\n')
	arg_info = desc[1]
	further_desc = '\n'.join(desc[2:])
	desc = desc[0]
	init.argcheck(sys.argv, 3, 7, desc, arg_info, further_desc)

	out = open(sys.argv[1] + '.table', 'w')
	log = open(sys.argv[1] + '.table.log', 'w')
	init.header(sys.argv, log)

	data = get_data(sys.argv[2])
	mapping = {}
	if len(sys.argv) > 3:
		mapping = get_mapping(sys.argv[3])

	system_order_file = None
	if len(sys.argv) > 5:
		system_order_file = sys.argv[5]
	error_order_file = None
	if len(sys.argv) > 4:
		error_order_file = sys.argv[4]
	system_order, error_order = get_order(data, system_order_file, error_order_file)
	print >> log, "System order:", system_order
	print >> log, "Error order:", error_order

	print_top(error_order, out)
	print_data(system_order, error_order, data, mapping, out)
	print_bottom(error_order, out)

	if len(sys.argv) < 6:
		pass #TODO: print system order file
	if len(sys.argv) < 5:
		error_out = open(sys.argv[1] + '.table.error_order', 'w')
		print_error_order(error_order, error_out)
		error_out.close()
	if len(sys.argv) < 4:
		pass #TODO: print name mapping file

	out.close()
	log.close()

