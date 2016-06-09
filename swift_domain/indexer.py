import re
import fnmatch
import os

# member patterns
func_pattern      = re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<static>class\s|static\s+|mutating\s+)?(?P<type>func)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)')
init_pattern      = re.compile(r'\s*(final\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+|convenience\s+)*(?P<type>init\??)\s*(?P<rest>[^{]*)')
var_pattern       = re.compile(r'\s*(final\s+)?(?P<add_scope>private\s*\(set\)\s+|private\s*\(get\)\s+)?(?P<scope>private\s+|public\s+|internal\s+)?(final\s+)?(?P<static>static\s+)?(?P<type>var\s+|let\s+)(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)(?P<computed>\s*{\s*)?')
proto_var_pattern = re.compile(r'\s*(?P<static>static\s+)?(?P<type>var\s+)(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(?P<rest>[^{]*)(?P<computed>\s*{(?:\s*get\s+set\s*|\s*get\s*|\s*set\s*)}\s*)?')
case_pattern      = re.compile(r'\s*(?P<type>case)\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(\s*(?P<assoc_type>\([a-zA-Z_[(][a-zA-Z0-9_<>[\]()?!:, \t-]*\))\s*)?(\s*=\s*(?P<raw_value>.*))?')

# markdown doc patterns
param_pattern   = re.compile(r'^\s*- [pP]arameter\s*(?P<param>[^:]*):\s*(?P<desc>.*)')
return_pattern  = re.compile(r'^\s*- [rR]eturn[s]?\s*:\s*(?P<desc>.*)')
throws_pattern  = re.compile(r'^\s*- [tT]hrow[s]?\s*:\s*(?P<desc>.*)')
default_pattern = re.compile(r'^\s*- [dD]efault[s]?\s*:\s*(?P<desc>.*)')

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
from pprint import PrettyPrinter
pp = PrettyPrinter(indent=1)
def pprint(*args):
    pp.pprint(*args)

# brace balancing for determining in which depth we are
string_pattern = re.compile(r'"(?:[^"\\]*(?:\\.)?)*"')
line_comment_pattern = re.compile(r'(// .*$)')
comment_pattern = re.compile(r'/\*(?:.)*\*/')
def balance_braces(line, brace_count):
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
        if l.startswith('///'):
            converted = l[4:].rstrip()
            converted = converted.replace('`', '``')
            doc_block.insert(0, converted)
            continue
        break
    return doc_block

def doc_block_to_rst(doc_block):
    def emit_item(item):
        if item[0] == 'param':
            return ':parameter '+ item[1] +': ' + item[2]
        elif item[0] == 'return':
            return ':returns: ' + item[1]
        elif item[0] == 'throws':
            return ':throws: ' + item[1]
        elif item[0] == 'defaults':
            return ':defaults: ' + item[1]

    last_item = None
    for l in doc_block:
        match = param_pattern.match(l)
        if match:
            if last_item:
                yield emit_item(last_item)
            match = match.groupdict()
            last_item = ['param', match['param'], match['desc']]
            continue
        match = return_pattern.match(l)
        if match:
            if last_item:
                yield emit_item(last_item)
            match = match.groupdict()
            last_item = ['return', match['desc']]
            continue
        match = throws_pattern.match(l)
        if match:
            if last_item:
                yield emit_item(last_item)
            match = match.groupdict()
            last_item = ['throws', match['desc']]
            continue
        match = default_pattern.match(l)
        if match:
            if last_item:
                yield emit_item(last_item)
            match = match.groupdict()
            last_item = ['defaults', match['desc']]
            continue
        if last_item and l == '':
            yield emit_item(last_item)
            yield ''
            last_item = None
            continue
        if not last_item:
            yield l
            continue
        last_item[len(last_item) - 1] += ' ' + l.strip()

    if last_item:
        yield emit_item(last_item)


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
            with open(file, "r") as fp:
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
            item_name = '.'.join([*name_prefix, item['name']])
            if name == item_name:
                yield item
            if len(item['children']) > 0:
                for result in self.find(name, index=item['children'], name_prefix=[*name_prefix, item['name']]):
                    yield result

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
                    self.index.append({
                        'scope': scope,
                        'line': i,
                        'type': match['type'].strip(),
                        'name': match['name'].strip() if match['type'] != 'init' and match['type'] != 'init?' else 'init',
                        'static': match['static'].strip() if 'static' in match and match['static'] else None,
                        'docstring': get_doc_block(content, i - 1),
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
                else:
                    yield '.. swift:method:: ' + sig

        if noindex:
            yield indent + ':noindex:'
        yield ''

        if not nodocstring:
            for line in doc_block_to_rst(item['docstring']):
                yield indent + line
            yield ''

        if location:
            yield indent + 'Defined in :doc:`' + location + '`:' + str(item['line'])
            yield ''

