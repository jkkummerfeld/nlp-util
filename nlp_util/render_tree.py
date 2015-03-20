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

def text_tree(tree, single_line=True, show_traces=False, depth=0, dense=True, newline=True):
  if not show_traces:
    tree = treebanks.remove_traces(tree, False)
  ans = ''
  if not single_line and depth > 0:
    if newline or (not dense) or tree.word is None:
      ans = '\n' + depth * '\t'
    else:
      ans = ' '
  ans += '(' + tree.label
  if tree.word is not None:
    ans += ' ' + tree.word
    newline = True
  else:
    newline = False
  for subtree in tree.subtrees:
    if single_line:
      ans += ' '
    ans += text_tree(subtree, single_line, True, depth + 1, dense, newline)
    newline = subtree.word is None
  if tree.word is None and dense and tree.subtrees[-1].word is not None:
    ans += ' '
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

def label_level(parse, head_map, label=None):
  head = head_finder.get_head(head_map, parse, True)
  if label is None:
    label = treebanks.remove_coindexation_from_label(parse.label)
  count = 0
  done = False
  while not done:
    done = True
    for subparse in parse.subtrees:
      slabel = treebanks.remove_coindexation_from_label(subparse.label)
      if head == head_finder.get_head(head_map, subparse, True):
        done = False
        parse = subparse
        if slabel == label:
          count += 1
        break
  return count

def get_edges(parse, edges, spines, head_map, traces):
  # Add spine
  chead = head_finder.get_head(head_map, parse, True)
  if parse.is_terminal() and not parse.is_trace():
    chain = []
    cur = parse.parent
    while cur is not None and chead == head_finder.get_head(head_map, cur, True):
      chain.append(treebanks.remove_coindexation_from_label(cur.label))
      signature = (cur.span, cur.label)
      target, null_cur = None, None
      if signature in traces[3]:
        target, null_cur, onum = traces[3][signature]
      if signature in traces[4]:
        target, null_cur = traces[4][signature]
      if target is not None:
        null = [null_cur.word]
        null_cur = null_cur.parent
        while null_cur != target:
          null.append(treebanks.remove_coindexation_from_label(null_cur.label))
          null_cur = null_cur.parent
        null.reverse()
        chain[-1] += "({})".format("_".join(null))
      cur = cur.parent
    spines.append((parse.wordspan[1], parse.label, chain, parse.word))

  # Add edges
  if not parse.is_terminal():
    # Normal edges
    for subparse in parse.subtrees:
      shead = head_finder.get_head(head_map, subparse, True)
      if shead is not None and chead is not None:
        if shead[0] != chead[0]:
          plabel = treebanks.remove_coindexation_from_label(parse.label)
          clabel = treebanks.remove_coindexation_from_label(subparse.label)
          plevel = label_level(parse, head_map)
          clevel = label_level(subparse, head_map)
          edges.append((shead[0][1], plabel + '_' + str(plevel), chead[0][1], clabel + "_" + str(clevel), "_"))

    # Traces
    signature = (parse.span, parse.label)

    # A trace where both locations are NONE
    if signature in traces[3]:
      cparent, cparse, num = traces[3][signature]
      chead = head_finder.get_head(head_map, parse, True)
      clabel = treebanks.remove_coindexation_from_label(cparse.parent.label)
      clevel = label_level(cparse.parent, head_map)
      if num in traces[1]:
        for subparse in traces[1][num]:
          trace_type = clabel + '_' + str(clevel)
          parent = subparse
          while head_finder.get_head(head_map, parent, True) is None and parent.parent is not None:
            parent = parent.parent
          phead = head_finder.get_head(head_map, parent, True)
          plabel = treebanks.remove_coindexation_from_label(parent.label)
          ilabel = treebanks.remove_coindexation_from_label(subparse.parent.label)
          ilabel += "_"+ '-'.join(subparse.word.split('-')[:-1])
          level = label_level(parent, head_map)
          edges.append((chead[0][1], plabel + '_' + str(level), phead[0][1], trace_type, ilabel))

    # The realisation point of the trace (either with or without an observed word)
    if signature in traces[0]:
      num = traces[0][signature][0]
      if num in traces[1]:
        # If this is the middle of a chain of traces, follow the chain
        thead = chead
        tparse = parse
        in_chain = False
        working = True
        while thead is None and working:
          working = False
          word = tparse.subtrees[0].word
          if word is None:
            # Ugh, these are messy cases, just find something to follow
            for option in tparse.word_yield(None, True):
              if '-' in option:
                word = option
          if '-' in word:
            onum = word.split('-')[-1]
            for signature in traces[0]:
              if traces[0][signature][0] == onum:
                tparse = traces[0][signature][1]
                thead = head_finder.get_head(head_map, tparse, True)
                working = True
                in_chain = True

        for subparse in traces[1][num]:
          slabel = treebanks.remove_coindexation_from_label(tparse.label)
          slevel = label_level(tparse, head_map)
          trace_type = "{}_{}".format(slabel, slevel)
          parent = subparse.parent # Attachment point
          plabel = treebanks.remove_coindexation_from_label(parent.parent.label)
          plevel = label_level(parent.parent, head_map)
          null_wrap = treebanks.remove_coindexation_from_label(parent.label)
          null_wrap += "_"+ '-'.join(subparse.word.split('-')[:-1])
          while head_finder.get_head(head_map, parent, True) is None and parent.parent is not None:
            parent = parent.parent
          phead = head_finder.get_head(head_map, parent, True)
          if thead is not None:
            edges.append((thead[0][1], plabel + '_' + str(plevel), phead[0][1], trace_type, null_wrap))
          elif in_chain:
            # Not handled by the null - null case above
            tparse = tparse.parent
            slevel = label_level(tparse, head_map, slabel)
            thead = head_finder.get_head(head_map, tparse, True)
            trace_type = "{}_{}".format(slabel, slevel)
            if thead is not None:
              edges.append((thead[0][1], plabel + '_' + str(plevel), phead[0][1], trace_type, null_wrap))

      # For each (P-# ... ) add a link from all (P=# ... ) that match
      if num in traces[2]:
        phead = head_finder.get_head(head_map, parse, True)
        for subparse in traces[2][num]:
          shead = head_finder.get_head(head_map, subparse, True)
          plabel = treebanks.remove_coindexation_from_label(parse.label)
          clabel = treebanks.remove_coindexation_from_label(subparse.label)
          plevel = label_level(parse, head_map)
          clevel = label_level(subparse, head_map)
          if phead is None:
            phead = head_finder.get_head(head_map, parse.parent, True)
            plabel = treebanks.remove_coindexation_from_label(parse.parent.label)
            plevel = label_level(parse.parent, head_map)
          if shead is None:
            print "# Failed on = with (P=# (NONE))"
          else:
            edges.append((shead[0][1], plabel + '_' + str(plevel), phead[0][1], clabel + "_" + str(clevel), "="))

    for subparse in parse.subtrees:
      get_edges(subparse, edges, spines, head_map, traces)

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
      print "# 1EC_violation", edge, edge_set
  return ans

def shg_format(parse, depth=0, head_map=None, traces=None, edges=None):
  parse.calculate_spans()
  traces = treebanks.resolve_traces(parse)
  base_parse = treebanks.remove_traces(parse, False)
  head_map = head_finder.pennconverter_find_heads(base_parse)
  edges = []
###  for node in pstree.TreeIterator(parse):
###    head = head_finder.get_head(head_map, node, True)
###    print head, node.span, node.label, text_words(node)

  # Prefix
  ans = []
  ans = ["# Parse  " + line for line in text_tree(parse, False, True).split("\n")]
  words = text_words(parse).split()
  ans.append("# Sent")
  for i, w in enumerate(words):
    ans[-1] += "  {} {}".format(i + 1, w)

  # Trace info (for debugging)
  for i in range(6):
    if i in [0, 3, 4]:
      for signature in traces[i]:
        ans.append("# Trace {} {} {}".format(i, signature, traces[i][signature]))
    if i in [1, 2]:
      for num in traces[i]:
        for tparse in traces[i][num]:
          ans.append("# Trace {} {} {} {}".format(i, num, tparse, tparse.span))

  edges = []
  spines = []
  label = treebanks.remove_coindexation_from_label(parse.label)
  head = head_finder.get_head(head_map, parse, True)
  level = label_level(parse, head_map)
  edges.append((head[0][1], '_', 0, label + "_" + str(level), "_"))

  get_edges(parse, edges, spines, head_map, traces)

  # Graph properties
  nedges = []
  for edge in edges:
    a = int(edge[0])
    b = int(edge[2])
    if a < b:
      nedges.append((a, b))
    else:
      nedges.append((b, a))
  graph_type = '# Graph type - '
  if check_proj(nedges):
    graph_type += " proj"
  elif check_1ec(nedges):
    graph_type += "  1ec"
  else:
    graph_type += "other"
  graph_type += ' tree' if check_tree(nedges) else ' graph'
  ans.append(graph_type)

  # Spines and edges
  spines.sort()
  for spine in spines:
    word, POS, chain, token = spine
    chain = '_'.join(chain) if len(chain) > 0 else '_'
    line = "{} {} {} {}".format(word, token, POS, chain)
    to_add = []
    for edge in edges:
      if edge[0] == word:
        parent = edge[2]
        label = edge[1]
        etype = edge[3]
        trace_info = edge[4]
        part = " | {} {} {} {}".format(parent, label, etype, trace_info)
        if trace_info == '_':
          to_add.insert(0, part)
        else:
          to_add.append(part)
    ans.append(line + ''.join(to_add))
  ans.append('')
  return "\n".join(ans)

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

