# Copyright 2016 by Johannes Schriewer
# Copyright 2016 Drew Crawford
# BSD license, see LICENSE for details

import re
import fnmatch
import os
from pprint import PrettyPrinter
from fuzzywuzzy import process


# member patterns
func_pattern      = re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<static>class\s|static\s+|mutating\s+)?(?P<type>func)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)')
init_pattern      = re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+|convenience\s+)*(?P<type>init\??)\s*(?P<rest>[^{]*)')
var_pattern       = re.compile(r'\s*(final\s+)?(?P<add_scope>private\s*\(set\)\s+|private\s*\(get\)\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<static>static\s+)?(?P<type>var\s+|let\s+)(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)(?P<computed>\s*{\s*)?')
proto_var_pattern = re.compile(r'\s*(?P<static>static\s+)?(?P<type>var\s+)(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)(?P<computed>\s*{(?:\s*get\s+set\s*|\s*get\s*|\s*set\s*)}\s*)?')
case_pattern      = re.compile(r'\s*(?P<type>case)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(\s*(?P<assoc_type>\([a-zA-Z_[(][a-zA-Z0-9_<>[\]()?!:, \t-]*\))\s*)?(\s*=\s*(?P<raw_value>.*))?')

# markdown doc patterns
param_pattern   = re.compile(r'^\s*- [pP]arameter\s*(?P<param>[^:]*):\s*(?P<desc>.*)')
param_abbreviated_pattern = re.compile(r'^(?P<indent>\s*)- (?P<param>.*):\s*(?P<desc>.*)')

attention_pattern  = re.compile(r'^\s*- [aA]ttention\s*:\s*(?P<desc>.*)')
author_pattern  = re.compile(r'^\s*- [aA]uthor\s*:\s*(?P<desc>.*)')
authors_pattern  = re.compile(r'^\s*- [aA]uthors\s*:\s*(?P<desc>.*)')
bug_pattern  = re.compile(r'^\s*- [bB]ug\s*:\s*(?P<desc>.*)')
complexity_pattern  = re.compile(r'^\s*- [cC]omplexity\s*:\s*(?P<desc>.*)')
copyright_pattern  = re.compile(r'^\s*- [cC]opyright\s*:\s*(?P<desc>.*)')
date_pattern  = re.compile(r'^\s*- [dD]ate\s*:\s*(?P<desc>.*)')
example_pattern  = re.compile(r'^\s*- [eE]xample\s*:\s*(?P<desc>.*)')
experiment_pattern  = re.compile(r'^\s*- [eE]xperiment\s*:\s*(?P<desc>.*)')
important_pattern  = re.compile(r'^\s*- [iI]mportant\s*:\s*(?P<desc>.*)')
invariant_pattern  = re.compile(r'^\s*- [iI]nvariant\s*:\s*(?P<desc>.*)')
note_pattern  = re.compile(r'^\s*- [nN]ote\s*:\s*(?P<desc>.*)')
precondition_pattern  = re.compile(r'^\s*- [pP]recondition\s*:\s*(?P<desc>.*)')
postcondition_pattern  = re.compile(r'^\s*- [pP]ostcondition\s*:\s*(?P<desc>.*)')
remark_pattern  = re.compile(r'^\s*- [rR]emark\s*:\s*(?P<desc>.*)')
requires_pattern  = re.compile(r'^\s*- [rR]equires\s*:\s*(?P<desc>.*)')
returns_pattern  = re.compile(r'^\s*- [rR]eturns\s*:\s*(?P<desc>.*)')
seealso_pattern  = re.compile(r'^\s*- [sS]eealso\s*:\s*(?P<desc>.*)')
since_pattern  = re.compile(r'^\s*- [sS]ince\s*:\s*(?P<desc>.*)')
version_pattern  = re.compile(r'^\s*- [vV]ersion\s*:\s*(?P<desc>.*)')
warning_pattern  = re.compile(r'^\s*- [wW]arning\s*:\s*(?P<desc>.*)')
throws_pattern  = re.compile(r'^\s*- [tT]hrow[s]?\s*:\s*(?P<desc>.*)')
default_pattern = re.compile(r'^\s*- [dD]efault[s]?\s*:\s*(?P<desc>.*)')

typical_patterns = {"attention":attention_pattern,"author":author_pattern,"authors":authors_pattern,
"bug":bug_pattern,"complexity":complexity_pattern,"copyright":copyright_pattern,
"date":date_pattern,"example":example_pattern,"experiment":experiment_pattern,
"important":important_pattern,"invariant":invariant_pattern,"note":note_pattern,"precondition":precondition_pattern,
"postcondition":postcondition_pattern,"remark":remark_pattern,"requires":requires_pattern,"returns":returns_pattern,
"see also":seealso_pattern,"since":since_pattern,"version":version_pattern,
"warning":warning_pattern,"throws":throws_pattern,"default":default_pattern}

codeblock_pattern = re.compile(r'```')
code_pattern = re.compile(r'`(?P<code>[^`]*)\`')

# signatures
def class_sig(name=r'[a-zA-Z_][a-zA-Z0-9_]*'):
    return re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<struct>class)\s+(?!func)(?P<name>' + name + r'\b)(\s*:\s*(?P<type>[^{]*))*')


def enum_sig(name=r'[a-zA-Z_][a-zA-Z0-9_]*'):
    return re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<struct>enum)\s+(?P<name>' + name + r'\b)(\s*:\s*(?P<type>[^{]*))*')


def struct_sig(name=r'[a-zA-Z_][a-zA-Z0-9_]*'):
    return re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<struct>struct)\s+(?P<name>' + name + r'\b)(\s*:\s*(?P<type>[^{]*))*')


def protocol_sig(name=r'[a-zA-Z_][a-zA-Z0-9_]*'):
    return re.compile(r'\s*(?P<scope>private\s+|public\s+|internal\s+)?(?P<struct>protocol)\s+(?P<name>' + name + r'\b)(\s*:\s*(?P<type>[^{]*))*')


def extension_sig(name=r'[a-zA-Z_][a-zA-Z0-9_]*'):
    return re.compile(r'\s*(?P<scope>private\s+|public\s+|internal\s+)?(?P<struct>extension)\s+(?P<name>' + name + r'\b)(\s*:\s*(?P<type>[^{]*))*(\s*where\s+(?P<where>[^{]*))?')


# debug printer
pp = PrettyPrinter(indent=1)


def pprint(*args):
    pp.pprint(*args)

# brace balancing for determining in which depth we are
string_pattern = re.compile(r'"(?:[^"\\]*(?:\\.)?)*"')
line_comment_pattern = re.compile(r'(// .*$)')
comment_pattern = re.compile(r'/\*(?:.)*\*/')

def balance_braces(line, brace_count):
    if line.startswith("//"): return brace_count
    line = string_pattern.sub("", line)
    line = comment_pattern.sub("", line)
    line = line_comment_pattern.sub("", line)
    open_braces = line.count('{')
    close_braces = line.count('}')
    braces = brace_count + open_braces - close_braces
    return braces


# fetch documentation block
def get_doc_block(content, line):

    # search upwards for documentation lines
    doc_block = []
    for i in range(line, 0, -1):
        l = content[i].strip()
        if l.strip().startswith('///'):
            converted = l[3:].rstrip()
            doc_block.insert(0, converted)
            continue
        break

    #did we find a standard comment?
    if doc_block: return doc_block
    block_detected = False

    for i in reversed(content[:line+1]):
        l = i.rstrip()
        startsComment = False
        endsComment = False
        if l.endswith("*/"):
            endsComment = True
            l = l[:-2]
            block_detected = True
        if l.strip().startswith("/**"):
            startsComment = True
            l = l.strip()[3:]
        elif l.startswith("/*"):
            return [] #not a doc comment

        if not block_detected: #don't go searching arbitrarily far back
            break 

        #insert on top
        doc_block.insert(0,l)

        if startsComment:
            break
    return doc_block


def doc_block_to_rst(doc_block):
    # sphinx requires a newline between documentation and directives
    # but Swift does not
    global was_doc
    was_doc = True

    def emit_doc():
        global was_doc
        if not was_doc:
            was_doc = True
            return True
        return False

    def emit_directive():
        global was_doc
        if was_doc:
            was_doc = False
            return True
        return False

    code_mode = False
    parameter_mode = False
    parameter_indent = None
    for l in doc_block:
        if codeblock_pattern.match(l):
            if not code_mode:
                code_mode = True
                yield '.. code-block:: swift'
                yield ''
                continue
            else:
                code_mode = False
                continue
        if code_mode:
            yield '    ' + l
            continue
        if parameter_mode:

            match = param_abbreviated_pattern.match(l)
            if match == None:
                parameter_mode = False
                parameter_indent = None
            else:
                match = match.groupdict()
                if parameter_indent and parameter_indent != match['indent']:
                    parameter_mode = False
                    parameter_indent = None
                else:
                    parameter_indent = match['indent']
                    yield ':parameter ' + match['param'] + ': ' + match['desc']
                    continue

        l = l.replace('\\','\\\\')
        l = code_pattern.sub(r':literal:`\g<code>` ',l)

        #l = emphasis_pattern.sub(r'**\g<emphasis>**',l)

        if l == "- parameters:":
           parameter_mode = True
           yield ''
           continue

        match = param_pattern.match(l)
        if match:
            match = match.groupdict()
            if emit_directive(): yield ''
            yield ':parameter ' + match ['param'] + ': ' + match['desc']
            continue

        c = False #continue if required
        for name,pattern in typical_patterns.items():
            match = pattern.match(l)
            if match:
                match = match.groupdict()
                if emit_directive(): yield ''
                yield ':' + name + ': ' + match['desc']
                c = True
                break
        if c: continue

        if not was_doc and l.strip() != "":
            yield "    " + l.strip()
            continue

        #if we've got here, assume it's doc
        if emit_doc(): yield ''
        yield l.strip()


class SwiftFileIndex(object):
    symbol_signatures = [class_sig(), enum_sig(), struct_sig(), extension_sig(), protocol_sig()]

    def __init__(self, search_path):
        self.index = []

        # find all files
        self.files = []
        for path in search_path:
            for root, dirnames, filenames in os.walk(path):
                for filename in fnmatch.filter(filenames, '*.swift'):
                    self.files.append(os.path.join(root, filename))

        for file in self.files:
            print("Indexing swift file: %s" % file)
            symbol_stack = []
            braces = 0
            with open(file, "r",encoding="utf-8") as fp:

                content = fp.readlines()
                for (index, line) in enumerate(content):
                    braces = balance_braces(line, braces)
                    # track boxed context
                    for pattern in self.symbol_signatures:
                        match = pattern.match(line)
                        if match:
                            match = match.groupdict()

                            struct = match['struct'].strip()
                            if 'scope' in match and match['scope']:
                                scope = match['scope'].strip()
                            else:
                                if struct == 'extension':
                                    scope = 'public'
                                else:
                                    scope = 'internal'
                            item = {
                                'file': file,
                                'line': index,
                                'depth': braces,
                                'type': struct,
                                'scope': scope,
                                'name': match['name'].strip(),
                                'docstring': get_doc_block(content, index - 1),
                                'param': match['type'].strip() if match['type'] else None,
                                'where': match['where'].strip() if 'where' in match and match['where'] else None,
                                'children': [],
                                'raw': line
                            }
                            if len(symbol_stack) > 0 and braces > symbol_stack[-1]['depth']:
                                symbol_stack[-1]['children'].append(item)
                            else:
                                symbol_stack.append(item)

                            # find members
                            start = index
                            if line.rstrip()[-1] == '{':
                                start = index + 1
                            else:
                                for i in range(index + 1, len(content)):
                                    l = content[i].lstrip()
                                    if len(l) > 0 and l[0] == '{':
                                        start = i
                                        break
                            item['members'] = SwiftObjectIndex(content, start, item['type'])

            self.index.extend(symbol_stack)

    def find(self, name, index=None, name_prefix=[]):
        if not index:
            index = self.index

        for item in index:
            item_name = ".".join(name_prefix + [item['name']])
            if name == item_name:
                yield item
            if len(item['children']) > 0:
                new_prefix = list(name_prefix)
                new_prefix.append(item['name'])
                for result in self.find(name, index=item['children'], name_prefix=new_prefix):
                    yield result

    def __names(self,index,name_prefix):
        """Return all names the receiver could find."""
        for item in index:
            yield ".".join(name_prefix + [item['name']])
            for child in item['children']:
                new_prefix = list(name_prefix)
                new_prefix.append(item['name'])
                for name in child.__names(item['children'],name_prefix=new_prefix):
                    yield name

                

    def find_fuzz(self,name,index=None,name_prefix=[]):
        if not index:
            index = self.index
        """Returns the best match with a score like ("Foo",90)"""
        return process.extractOne(name,self.__names(index,name_prefix))



    def by_file(self, index=None):
        result = {}

        if not index:
            index = self.index

        for item in index:
            if item['file'] not in result:
                result[item['file']] = []
            result[item['file']].append(item)

        return result

    @staticmethod
    def documentation(item, indent="    ", noindex=False, nodocstring=False, location=False):
        if item['param']:
            line = '.. swift:' + item['type'] + ':: ' + item['name'] + ' : ' + item['param']
        else:
            line = '.. swift:' + item['type'] + ':: ' + item['name']

        if item['where']:
            line += ' where ' + item['where']

        yield line

        if noindex:
            yield indent + ':noindex:'
        yield ''

        if not nodocstring:
            for line in doc_block_to_rst(item['docstring']):
                yield indent + line
            yield ''

        if location:
            yield indent + 'Defined in :doc:`' + item['file'] + '`:' + str(item['line'])
            yield ''


class SwiftObjectIndex(object):

    def __init__(self, content, line, typ):
        signatures = [func_pattern, init_pattern, var_pattern]
        if typ == 'enum':
            signatures = [func_pattern, init_pattern, case_pattern]
        elif typ == 'protocol':
            signatures = [func_pattern, init_pattern, proto_var_pattern]

        self.index = []
        braces = 1
        for i in range(line, len(content)):
            l = content[i]

            # balance braces
            old_braces = braces
            braces = balance_braces(l, braces)
            if braces <= 0:
                break
            if braces > 1 and old_braces == braces:
                continue

            for pattern in signatures:
                match = pattern.match(l)
                if match:
                    match = match.groupdict()
                    if 'scope' in match:
                        if match['scope']:
                            scope = match['scope'].strip()
                        else:
                            if typ == 'protocol':
                                scope = 'public'
                            else:
                                scope = 'internal'
                    else:
                        scope = 'public'
                    docstring = get_doc_block(content, i - 1)
                    if "- noindex: true" in docstring:
                        continue
                    self.index.append({
                        'scope': scope,
                        'line': i,
                        'type': match['type'].strip(),
                        'name': match['name'].strip() if match['type'] != 'init' and match['type'] != 'init?' else 'init',
                        'static': match['static'].strip() if 'static' in match and match['static'] else None,
                        'docstring': docstring,
                        'rest': match['rest'].strip() if 'rest' in match and match['rest'] else None,
                        'assoc_type': match['assoc_type'].strip() if 'assoc_type' in match and match['assoc_type'] else None,
                        'raw_value': match['raw_value'].strip() if 'raw_value' in match and match['raw_value'] else None,
                        'raw': l
                    })

    @staticmethod
    def documentation(item, indent="    ", noindex=False, nodocstring=False, location=None):
        sig = item['name']
        if item['rest']:
            sig += item['rest']

        if item['type'] == 'case':
            # enum case
            if item['assoc_type']:
                yield '.. swift:enum_case:: ' + sig + item['assoc_type']
            elif item['raw_value']:
                yield '.. swift:enum_case:: ' + sig + ' = ' + item['raw_value']
            else:
                yield '.. swift:enum_case:: ' + sig
        elif item['type'] == 'var' or item['type'] == 'let':
            # variables
            if item['static'] == 'static':
                yield '.. swift:static_' + item['type'] + ':: ' + sig
            else:
                yield '.. swift:' + item['type'] + ':: ' + sig
        else:
            if item['name'] == 'init' or item['name'] == 'init?':
                yield '.. swift:init:: ' + sig
            else:
                if item['static'] == 'class':
                    yield '.. swift:class_method:: ' + sig
                if item['static'] == 'static':
                    yield '.. swift:static_method:: ' + sig
                else:
                    yield '.. swift:method:: ' + sig

        if noindex:
            yield indent + ':noindex:'
        yield ''

        if not nodocstring:
            for line in doc_block_to_rst(item['docstring']):
                yield indent + ' ' + line
            yield ''

        if location:
            yield indent + 'Defined in :doc:`' + location + '`:' + str(item['line'])
            yield ''
