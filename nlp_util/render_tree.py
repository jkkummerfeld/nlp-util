#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set ts=2 sw=2 noet:
'''Various string representations of trees.'''

import string

import pstree, parse_errors, head_finder, treebanks

# TODO:todo Fix handling of traces throughout
# Handling of unary order
# Sites that render trees
# http://mshang.ca/syntree/
# http://www.yohasebe.com/rsyntaxtree/

def text_words(tree, show_traces=False):
  '''Print just the words in the tree.'''
  text = []
  for node in tree:
    if node.is_terminal():
      if node.is_trace() and not show_traces:
        continue
      text.append(node.word)
  return ' '.join(text)

def text_POS_tagged(tree, show_traces=False):
  '''Print words and part of speech tags in the tree.'''
  text = []
  for node in tree:
    if node.is_terminal():
      if node.is_trace() and not show_traces:
        continue
      text.append(tree.word + '|' + tree.label)
  return ' '.join(text)

def text_tree(tree, single_line=True, show_traces=False, depth=0):
  if not show_traces:
    tree = treebanks.remove_traces(tree, False)
  ans = ''
  if not single_line and depth > 0:
    ans = '\n' + depth * '\t'
  ans += '(' + tree.label
  if tree.word is not None:
    ans += ' ' + tree.word
  for subtree in tree.subtrees:
    if single_line:
      ans += ' '
    ans += text_tree(subtree, single_line, True, depth + 1)
  ans += ')'
  return ans

def text_ontonotes(tree, filename='filename', words=None, tree_text=None, depth=0):
  resolve = False
  if words is None:
    resolve = True
    words = []
    tree_text = ''

  if tree.word is None:
    tree_text += '(' + tree.label + '_'
  else:
    words.append((tree.word, tree.label))
    tree_text += '*'

  for subtree in tree.subtrees:
    tree_text = text_ontonotes(subtree, filename, words, tree_text, depth)

  if tree.word is None:
    tree_text += ')'

  if resolve:
    ans = ''
    cpos = 0
    cword = 0
    while cpos < len(tree_text):
      ctext = ''
      while cpos < len(tree_text) and tree_text[cpos] != '*':
        ctext += tree_text[cpos]
        cpos += 1
      ctext += tree_text[cpos]
      cpos += 1
      while cpos < len(tree_text) and tree_text[cpos] == ')':
        ctext += tree_text[cpos]
        cpos += 1
      ans += '%s %9s %9d %9s %9s %9s' % (filename, 0, cword, words[cword][0], words[cword][1], ctext)
      for val in ['-', '-', '-', '-', '*', '*', '*', '*', '*', '*', '-']:
        ans += ' %9s' % val
      ans += '\n'
      cword += 1
    return ans
  else:
    return tree_text

def tex_synttree(tree, other_spans=None, depth=0, compressed=True, span=None):
  if tree.label == '.':
    return ''
  if span is not None and (tree.span[1] <= span[0] or tree.span[0] >= span[1]):
    # TODO:todo will give long skinny trees
    return ''
  correct = True
  if other_spans is not None:
    correct = (tree.label, tree.span[0], tree.span[1]) in other_spans
  else:
    compressed = False
  all_in_subtree = False
  if span is not None:
    for subtree in tree.subtrees:
      if subtree.span[0] <= span[0] and span[1] <= subtree.span[1]:
        all_in_subtree = True

  # Clean the label and word
  label = tree.label
  if '$' in label:
    label = '\$'.join(label.split('$'))
  word = tree.word
  if word is not None:
    word = ''.join(word.split('.'))
    word = '\&'.join(word.split('&'))
    word = '\$'.join(word.split('$'))
    word = '\%'.join(word.split('%'))

  # Make the text
  ans = ''
  if tree.parent is None:
    ans += '\synttree'
    if not all_in_subtree:
      ans += '\n'
  elif not all_in_subtree:
    ans += '\n' + '  ' * depth
  if len(tree.subtrees) == 0:
    ans += '[%s [%s]]' % (label, word)
  else:
    if not all_in_subtree:
      if correct:
        ans += '[%s' % (label)
      else:
        ans += '[\wrongnode{%s}' % (label)
    for subtree in tree.subtrees:
      ans += tex_synttree(subtree, other_spans, depth + 1, compressed, span)
    if not all_in_subtree:
      ans += ']'

  # When compressing we only want errors visible
  if compressed and 'wrongnode' not in ans and tree.word is None:
    words = ''.join(tree.word_yield().split('.'))
    words = '\&'.join(words.split('&'))
    words = '\$'.join(words.split('$'))
    if tree.parent is None:
      ans = '\synttree\n'
    else:
      ans = '\n' + '  ' * depth
    ans += '[%s [.t %s]]' % (label, words)
  return ans

### Sketch of new coloured error design:
### 1. Create tokens for current tree, label each with its span, and whether it
###    is extra (or different in the case of POS)
### 2. Introduce missing brackets, placing them in the token list as
###    appropriate
### 3. Introduce crossing brackets, similarly
def get_init_tokens(tree, mapping, tokens):
  tokens.append(('(' + tree.label, tree.span, False, False, False, False))
  mapping[tree] = [len(tokens) - 1]
  for subtree in tree.subtrees:
    get_init_tokens(subtree, mapping, tokens)
  if tree.is_terminal():
    tokens.append((' ' + tree.word + ')', tree.span, False, False, False, False))
  else:
    tokens.append((')', tree.span, False, False, False, False))
  mapping[tree].append(len(tokens) - 1)
  return tokens

def text_coloured_errors(tree, gold=None, unused=0, single_line=False, unused2=None, unused3=None, compressed='words', POS=True, indent='   '):
  # TODO: Work on ordering of unaries, particularly at the root
  if compressed == True:
    compressed = 'words'
  start_missing = "\033[01;36m"
  start_extra = "\033[01;31m"
  start_crossing = "\033[01;33m"
  end_colour = "\033[00m"

  mapping = {}
  tokens = []
  get_init_tokens(tree, mapping, tokens)

  # Mark extra
  errors = parse_errors.Parse_Error_Set(gold, tree, POS)
  for etype, span, label, node in errors.extra:
    for token_loc in mapping[node]:
      cur = tokens[token_loc]
      tokens[token_loc] = (cur[0], cur[1], True, False, False, False)

  # Mark POS
  for etype, span, label, node, gold_label in errors.POS:
    token_loc = mapping[node][0]
    cur = tokens[token_loc]
    ntext = '(' + start_missing + gold_label + ' ' + start_extra + label + end_colour
    tokens[token_loc] = (ntext, cur[1], False, False, False, True)

  # Insert missing
  for etype, span, label, node in errors.missing:
    for i in range(len(tokens)):
      if tokens[i][1][0] == span[0] and tokens[i][1][1] <= span[1]:
        tokens.insert(i, ('(' + label, span, False, True, False, False))
        break
    last = None
    for i in range(len(tokens)):
      if tokens[i][1][1] == span[1] and tokens[i][1][0] >= span[0]:
        last = i
    assert last is not None
    tokens.insert(last + 1, (')', span, False, True, False, False))

  # Insert crossing
  for etype, span, label, node in errors.crossing:
    for i in range(len(tokens)):
      if tokens[i][1][0] == span[0] and tokens[i][1][1] <= span[1]:
        tokens.insert(i, ('(' + label + ' ', span, False, False, True, False))
        break
    last = None
    for i in range(len(tokens)):
      if tokens[i][1][1] == span[1] and tokens[i][1][0] >= span[0]:
        last = i
    assert last is not None
    tokens.insert(last + 1, (' ' + label + ')', span, False, False, True, False))

  # Compressed
  if compressed == 'none':
    pass
  else:
    i = 0
    while i < len(tokens):
      if '(' in tokens[i][0] and not (tokens[i][2] or tokens[i][3] or tokens[i][4] or tokens[i][5]):
        all_correct = True
        depth = 0
        last = None
        for j in range(i, len(tokens)):
          if tokens[j][2] or tokens[j][3] or tokens[j][4] or tokens[j][5]:
            all_correct = False
            break
          if '(' in tokens[j][0]:
            depth += 1
          if ')' in tokens[j][0]:
            depth -= 1
          if depth == 0:
            last = j
            break
        if all_correct:
          assert last is not None
          text = ''
          if compressed == 'words':
            top_label = ''
            words = []
            for token in tokens[i:last + 1]:
              if '(' in token[0] and top_label == '':
                top_label = token[0][1:]
              elif ')' in token[0] and len(token[0]) > 1:
                words.append(token[0].strip()[:-1])
            text = '(' + top_label + ' ' + ' '.join(words) + ')'
          elif compressed == 'single line':
            for token in tokens[i:last + 1]:
              if '(' in token[0]:
                text += ' '
              text += token[0]
            text = text.strip()
          tokens[i] = (text, tokens[i][1], False, False, False, False)
          for j in range(i+1, last+1):
            tokens.pop(i+1)
      i += 1

  # Combine tokens
  ans = []
  depth = 0
  no_indent = False
  for text, span, extra, missing, crossing, POS_error in tokens:
    begin = ''
    if '(' in text:
      if crossing:
        if not no_indent:
          no_indent = True
          begin = '\n' + depth * indent
          depth += 1
      else:
        if not no_indent:
          begin = '\n' + depth * indent
          depth += 1
        else:
          no_indent = False
    if ')' in text and not crossing:
      depth -= 1
    if extra:
      ans.append(begin + start_extra + text + end_colour)
    elif missing:
      ans.append(begin + start_missing + text + end_colour)
    elif crossing:
      ans.append(begin + start_crossing + text + end_colour)
    else:
      ans.append(begin + text)
  return ''.join(ans)

def text_coloured_errors_old(tree, gold=None, depth=0, single_line=False, missing=None, extra=None, compressed=True, POS=True):
  '''Pretty print, with errors marked using colour.
  
  'missing' should contain tuples (or be None):
    (start, end, label, crossing-T/F)
  '''
  # TODO: Add the ability to compress the same parts consistently (even after
  # errors are no longer present). This would need to be span based as
  # structure could change.
  ans = ''
  if missing is None or extra is None:
    if gold is None:
      return "Error - no gold tree and no missing list for colour repr"
    # look at gold and work out what missing should be
    errors = parse_errors.get_errors(tree, gold, POS)
    extra = [e[3] for e in errors if e[0] == 'extra' and e[3].word is None]
    extra = set(extra)
    missing = [(e[1][0], e[1][1], e[2], False) for e in errors if e[0] == 'missing' and e[3].word is None]
    missing += [(e[1][0], e[1][1], e[2], True) for e in errors if e[0] == 'crossing' and e[3].word is None]
    POS = [e for e in errors if e[0] == 'diff POS']
  start_missing = "\033[01;36m"
  start_extra = "\033[01;31m"
  start_crossing = "\033[01;33m"
  end_colour = "\033[00m"
  
  if not single_line:
    ans += '\n' + depth * '\t'

  # start of this
  if tree in extra:
    ans += start_extra + '(' + tree.label + end_colour
  elif tree.word is not None and POS is not None:
    found = False
    for error in POS:
      if error[3] == tree:
        found = True
        ans += '(' + start_missing + error[4] + end_colour
        ans += ' ' + start_extra + tree.label + end_colour
        break
    if not found:
      ans += '(' + tree.label
  else:
    ans += '(' + tree.label
  
  # If we are compressing, check for correctness and then just print words
  sub_done = False
  if compressed and tree not in extra and tree.word is None:
    all_right = True
    for error in extra:
      if tree.span[0] <= error.span[0] and error.span[1] <= tree.span[1]:
        all_right = False
        break
    for error in missing:
      if error[3]:
        if tree.span[0] < error[0] < tree.span[1]:
          all_right = False
          break
        if tree.span[0] < error[1] < tree.span[1]:
          all_right = False
          break
      elif tree.span[0] <= error[0] and error[1] <= tree.span[1]:
        all_right = False
        break
    if POS is not None:
      for error in POS:
        if tree.span[0] <= error[1][0] and error[1][1] <= tree.span[1]:
          all_right = False
          break
    if all_right:
      ans += ' ' + text_words(tree) + ')'
      sub_done = True

  # crossing brackets starting
  if tree.parent is None or tree.parent.subtrees[0] != tree:
    # these are marked as high as possible
    labels = []
    for error in missing:
      if error[0] == tree.span[0] and error[3]:
        labels.append((error[1], error[2]))
    labels.sort(reverse=True)
    if len(labels) > 0:
      to_add = start_crossing + ' '.join(['(' + label[1] for label in labels]) + end_colour
      if sub_done:
        nans = ''
        for char in ans:
          if char in '\t\n':
            nans += char
        clen = len(nans)
        nans += to_add
        nans += ' ' + ans[clen:]
        ans = nans
      else:
        ans += ' ' + to_add

  if not sub_done:
    # word
    if tree.word is not None:
      ans += ' ' + tree.word

    # subtrees
    below = []
    for subtree in tree.subtrees:
      text = text_coloured_errors(subtree, gold, depth + 1, single_line, missing, extra, compressed, POS)
      if single_line:
        text = ' ' + text
      below.append([subtree.span[0], subtree.span[1], text])
    # add missing brackets that surround subtrees
    for length in xrange(1, len(below)):
      for i in xrange(len(below)):
        j = i + length
        if i == 0 and j == len(below) - 1:
          continue
        if j >= len(below):
          break
        for error in missing:
          if below[i][0] == error[0] and below[j][1] == error[1] and not error[3]:
            start = ''
            for char in below[i][2]:
              if char not in '\n\t':
                break
              start += char
            for k in xrange(i, j+1):
              below[k][2] = '\n\t'.join(below[k][2].split('\n'))
            below[i][2] = start + start_missing + '(' + error[2] + end_colour + below[i][2]
            below[j][2] += start_missing + ')' + end_colour
    ans += ''.join([part[2] for part in below])

    # end of this
    if tree in extra:
      ans += start_extra + ')' + end_colour
    else:
      ans += ')'

  if tree.parent is None or tree.parent.subtrees[-1] != tree:
    # if there are crossing brackets that end here, mark that
    labels = []
    for error in missing:
      if error[1] == tree.span[1] and error[3]:
        labels.append((-error[0], error[2]))
    labels.sort()
    if len(labels) > 0:
      ans += ' ' + start_crossing + ' '.join([label[1] + ')' for label in labels]) + end_colour

  # TODO: Change so that at the top level, FRAG etc isn't printed outside of ROOT
  # Actually, just have a canonical ordering for unaries (so that NPs end up under FRAGs)
  if tree.parent is None or len(tree.parent.subtrees) > 1:
    # check for missing brackets that go around this node
    for error in missing:
      if error[0] == tree.span[0] and error[1] == tree.span[1] and not error[3]:
        if not tree in extra:
          # Put them on a new level
          extra_text = ''
          if not single_line:
            ans = '\n\t'.join(ans.split('\n'))
            extra_text = '\n' + depth * '\t'
          extra_text += start_missing + '(' + error[2] + end_colour
          if single_line:
            ans = ' ' + ans
          ans = extra_text + ans
          ans += start_missing + ')' + end_colour
        else:
          # Put them on the same line
          start = 0
          for char in ans:
            if char not in '\n\t':
              break
            start += 1
          pretext = ans[:start]
          ans = ans[start:]
          extra_text = start_missing + '(' + error[2] + end_colour + ' '
          ans = pretext + extra_text + ans
          ans += start_missing + ')' + end_colour
  return ans

def check_tree(edges):
  points = set()
  for edge in edges:
    points.add(edge[0])
    points.add(edge[1])
  return len(points) == (len(edges) + 1)

def check_proj(edges):
  for edge1 in edges:
    for edge2 in edges:
      if edge1[0] < edge2[0] < edge1[1] < edge2[1]:
        return False
      if edge2[0] < edge1[0] < edge2[1] < edge1[1]:
        return False
  return True

def check_1ec(edges):
  edge_sets = {}
  for edge1 in edges:
    for edge2 in edges:
      if edge1[0] < edge2[0] < edge1[1] < edge2[1]:
        if edge1 not in edge_sets:
          edge_sets[edge1] = (set(), set())
        edge_sets[edge1][0].add(edge2[0])
        edge_sets[edge1][1].add(edge2[1])
      if edge2[0] < edge1[0] < edge2[1] < edge1[1]:
        if edge1 not in edge_sets:
          edge_sets[edge1] = (set(), set())
        edge_sets[edge1][0].add(edge2[1])
        edge_sets[edge1][1].add(edge2[0])
  ans = True
  for edge in edge_sets:
    edge_set = edge_sets[edge]
    if len(edge_set[0]) > 1 and len(edge_set[1]) > 1:
      ans = False
      print edge, edge_set
  return ans

def hag_format(parse, used=None, depth=0, head_map=None, traces=None):
  init = used is None
  if init:
    used = set()
    parse.calculate_wordspans()
    traces = treebanks.resolve_traces(parse)
    base_parse = treebanks.remove_traces(parse, False)
    head_map = head_finder.pennconverter_find_heads(base_parse)
###    for node in pstree.TreeIterator(parse):
###      head = head_finder.get_head(head_map, node, True)
###      print head, node.span, node.label, text_words(node)

  # Prefix
  ans = ['']
  if depth == 0:
    last_open = True
    for line in text_tree(parse, False, True).split("\n"):
      if last_open and len(line.strip()) > 2 and line.strip()[0] == '(' and line.strip()[-1] == ')':
        ans[-1] += " {}".format(line.strip())
        if line.strip()[-2] != ')':
          last_open = True
        else:
          last_open = False
      else:
        ans.append("# ::ptb  {}".format(line))
        last_open = True
    words = text_words(parse).split()
    ans.append("# ::snt")
    for i, w in enumerate(words):
      ans[-1] += "  {} {}".format(i + 1, w)
    ans.append("")

  if init:
    label = treebanks.remove_coindexation_from_label(parse.label)
    head = head_finder.get_head(head_map, parse, True)
    ans.append("{}.{} --{}--> 0".format(head[0][1], head[2], label))

  # Print unary chain
  chead = head_finder.get_head(head_map, parse, True)
  top_of_chain = True
  if parse.parent is not None:
    phead = head_finder.get_head(head_map, parse.parent, True)
    if chead == phead:
      top_of_chain = False
  if top_of_chain and (not parse.is_terminal()):
    chain = [treebanks.remove_coindexation_from_label(parse.label)]
    sub = parse
    while not sub.is_terminal():
      for subtree in sub.subtrees:
        if chead == head_finder.get_head(head_map, subtree, True):
          sub = subtree
          break
      chain.append(treebanks.remove_coindexation_from_label(sub.label))
    if not sub.is_trace():
      ans.append("{}.{} {}".format(sub.span[1], chain[-1], '_'.join(chain[:-1])))

  if parse.word is None:
    # Normal edges
    for subparse in parse.subtrees:
      shead = head_finder.get_head(head_map, subparse, True)
      if shead is not None and chead is not None:
        if shead[0] != chead[0]:
          plabel = treebanks.remove_coindexation_from_label(parse.label)
          ans.append("{}.{} --{}--> {}".format(shead[0][1], shead[2], plabel, chead[0][1]))
      else:
        ans.append("Fail 1 on {} {} {} <--- {} {} {} {}".format(chead, parse.span, parse.label, shead, subparse.span, subparse.label, subparse.word_yield()))
    signature = (parse.span, parse.word, parse.label)

    # Traces
    if signature in traces[0]:
      num = traces[0][signature][0]
      if num in traces[1]:
        thead = chead
        # If this is the middle of a chain of traces, follow the chain
        if thead is None:
          words = parse.word_yield(as_list = True)
          if len(words) == 1 and words[0].startswith("*T*-"):
            onum = words[0].split('-')[-1]
            for signature in traces[0]:
              if traces[0][signature][0] == onum:
                thead = head_finder.get_head(head_map, traces[0][signature][1], True)

        for subparse in traces[1][num]:
          parent = subparse
          phead = head_finder.get_head(head_map, parent, True)
          while phead is None and parent is not None:
            parent = parent.parent
            phead = head_finder.get_head(head_map, parent, True)
          if phead is not None and thead is not None:
            ilabel = treebanks.remove_coindexation_from_label(subparse.parent.label)
            plabel = treebanks.remove_coindexation_from_label(parent.label)
            ans.append("{}.{} --{}_{}--> {} (trace)".format(thead[0][1], thead[2], ilabel, plabel, phead[0][1]))
          else:
            ans.append("Fail 2 on {} {} {} <--- {} {} {}  {} (trace)".format(thead, parse.span, parse.label, shead, subparse.span, subparse.label, subparse.word_yield()))
      if num in traces[2]:
        parent = parse.parent
        phead = head_finder.get_head(head_map, parent, True)
        for subparse in traces[2][num]:
          shead = head_finder.get_head(head_map, subparse, True)
          if phead is not None and shead is not None:
            ilabel = treebanks.remove_coindexation_from_label(subparse.parent.label)
            plabel = treebanks.remove_coindexation_from_label(parent.label)
            ans.append("{}.{} --{}_{}--> {} (trace)".format(shead[0][1], shead[2], ilabel, plabel, phead[0][1]))
          else:
            ans.append("Fail 3 on {} {} {} <--- {} {} {} {} (trace)".format(phead, parent.span, parent.label, shead, subparse.span, subparse.label, subparse.word_yield()))
    for subparse in parse.subtrees:
      for part in hag_format(subparse, used, depth + 1, head_map, traces):
        if part.strip() != '':
          ans.append(part)
  if init:
    to_sort = {}
    to_retain = []
    for part in ans:
      if part.startswith('#') or 'Fail' in part:
        to_retain.append(part)
      else:
        if len(part) == 0 or part[0] not in string.digits:
          to_retain.append(part)
        else:
          num = int(part.split()[0].split('.')[0])
          if '--' in part:
            if num not in to_sort:
              to_sort[num] = []
            to_sort[num].append(part)
    ans = '\n'.join(to_retain) + '\n'
    keys = to_sort.keys()
    keys.sort()
    edges = []
    for key in keys:
      ans += to_sort[key][0].split()[0]
      for part in to_sort[key]:
        part = ' '.join(part.split()[1:])
        ans += ' ' + part
        num = part.split()[-1]
        if num == '(trace)':
          num = part.split()[-2]
        edges.append((int(key), int(num)))
      ans += '\n'
    graph_type = 'Graph type - '
    if check_proj(edges):
      graph_type += " proj"
    elif check_1ec(edges):
      graph_type += "  1ec"
    else:
      graph_type += "other"
    if check_tree(edges):
      graph_type += " tree"
    else:
      graph_type += " graph"
    ans += graph_type + '\n'
    ans += '-->\n'
    return ans
  else:
    return ans

def cut_text_below(text, depth):
  '''Simplify text to only show the top parts of a tree
  >>> print cut_text_below("(ROOT (NP (PRP I)) (VP (VBD ran) (NP (NN home))))", 1)
  (ROOT)
  >>> print cut_text_below("(ROOT (NP (PRP I)) (VP (VBD ran) (NP (NN home))))", 2)
  (ROOT (NP) (VP))
  >>> print cut_text_below("(ROOT (NP (PRP I)) (VP (VBD ran) (NP (NN home))))", 3)
  (ROOT (NP (PRP I)) (VP (VBD ran) (NP)))
  >>> print cut_text_below("(ROOT (NP (PRP I)) (VP (VBD ran) (NP (NN home))))", 20)
  (ROOT (NP (PRP I)) (VP (VBD ran) (NP (NN home))))
  '''

  # Cut lower content
  cdepth = 0
  ntext = ''
  for char in text:
    if char == '(':
      cdepth += 1
    if cdepth <= depth:
      ntext += char
    if char == ')':
      cdepth -= 1

  # Walk back and remove extra whitespace
  text = ntext
  ntext = ''
  ignore = False
  for char in text[::-1]:
    if char == ')':
      ignore = True
      ntext += char
    elif ignore:
      if char != ' ':
        ntext += char
        ignore = False
    else:
      ntext += char
  return ntext[::-1]

if __name__ == '__main__':
  print "Running doctest"
  import doctest
  doctest.testmod()

