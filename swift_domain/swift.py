# -*- coding: utf-8 -*-
"""
    sphinx.domains.swift
    ~~~~~~~~~~~~~~~~~~~

    The Swift domain.

    :copyright: Copyright 2016 by Johannes Schriewer
    :license: BSD, see LICENSE for details.
"""

import re

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.locale import l_
from sphinx.domains import Domain, ObjType, Index
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, GroupedField, TypedField
from .std import SwiftStandardDomain

def _iteritems(d):
    for k in d:
        yield k, d[k]


class SwiftObjectDescription(ObjectDescription):
    option_spec = {
        'noindex': directives.flag,
    }

    def add_target_and_index(self, name_cls_add, sig, signode):
        fullname, signature, add_to_index = name_cls_add
        if 'noindex' in self.options or not add_to_index:
            return

        # for char in '<>()[]:, ?!':
        #     signature = signature.replace(char, "-")

        # note target
        if fullname not in self.state.document.ids:
            signode['ids'].append(signature)
            self.state.document.note_explicit_target(signode)
            self.env.domaindata['swift']['objects'][fullname] = (self.env.docname, self.objtype, signature)
        else:
            objects = self.env.domaindata['swift']['objects']
            self.env.warn(
                self.env.docname,
                'duplicate object description of %s, ' % fullname +
                'other instance in ' +
                self.env.doc2path(objects[fullname][0]),
                self.lineno)


class SwiftClass(SwiftObjectDescription):

    def handle_signature(self, sig, signode):
        container_class_name = self.env.temp_data.get('swift:class')

        # split on : -> first part is class name, second part is superclass list
        parts = [x.strip() for x in sig.split(':', maxsplit=1)]

        # if the class name contains a < then there is a generic type attachment
        if '<' in parts[0]:
            class_name, generic_type = parts[0].split('<')
            generic_type = generic_type[:-1]
        else:
            class_name = parts[0]
            generic_type = None

        # did we catch a 'where' ?
        type_constraint = None
        class_parts = None
        if ' ' in class_name:
            class_parts = class_name.split(' ')
        elif '\t' in class_name:
            class_parts = class_name.split('\t')
        if class_parts:
            # if a part starts with `where` then we have a type constraint
            for index, p in enumerate(class_parts):
                if p == 'where':
                    type_constraint = " ".join(class_parts[index:]) + ": " + parts.pop()
                    class_name = " ".join(class_parts[:index])
                    break

        if class_name.count('.'):
            class_name = class_name.split('.')[-1]

        # if we have more than one part this class has super classes / protocols
        super_classes = None
        if len(parts) > 1:
            super_classes = [x.strip() for x in parts[1].split(',')]

            # if a part starts with `where` then we have a type constraint
            for index, sup in enumerate(super_classes):
                if sup == 'where':
                    type_constraint = " ".join(super_classes[index:])
                    super_classes = super_classes[:index]
                    break

        # Add class name
        signode += addnodes.desc_addname(self.objtype, self.objtype + ' ')
        signode += addnodes.desc_name(class_name, class_name)

        # if we had super classes add annotation
        if super_classes:
            children = []
            for c in super_classes:
                prefix = ', ' if c != super_classes[0] else ''
                # ref = addnodes.pending_xref(c, reftype='protocol', refdomain='swift', reftarget=c, refwarn=True)
                ref = nodes.Text(prefix + c)
                children.append(ref)
            signode += addnodes.desc_type('', ' : ', *children)

        # add type constraint
        if type_constraint:
            signode += addnodes.desc_type(type_constraint, ' ' + type_constraint)

        add_to_index = True
        if self.objtype == 'extension' and not super_classes:
            add_to_index = False

        if container_class_name:
            class_name = container_class_name + '.' + class_name
        return self.objtype + ' ' + class_name, self.objtype + ' ' + class_name, add_to_index

    def before_content(self):
        if self.names:
            parts = self.names[0][1].split(" ")
            if len(parts) > 1:
                self.env.temp_data['swift:class'] = " ".join(parts[1:])
            else:
                env.temp_data['swift:class'] = self.names[0][1]
            self.env.temp_data['swift:class_type'] = self.objtype
            self.clsname_set = True

    def after_content(self):
        if self.clsname_set:
            self.env.temp_data['swift:class'] = None
            self.env.temp_data['swift:class_type'] = None


class SwiftClassmember(SwiftObjectDescription):

    doc_field_types = [
        TypedField('parameter', label=l_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='obj', typenames=('paramtype', 'type')),
        GroupedField('errors', label=l_('Throws'), rolename='obj',
                     names=('raises', 'raise', 'exception', 'except', 'throw', 'throws'),
                     can_collapse=True),
        Field('returnvalue', label=l_('Returns'), has_arg=False,
              names=('returns', 'return')),
    ]

    def _parse_parameter_list(self, parameter_list):
        parameters = []
        parens = {'[]': 0, '()': 0, '<>': 0}
        last_split = 0
        for i, c in enumerate(parameter_list):
            for key, value in parens.items():
                if c == key[0]:
                    value += 1
                    parens[key] = value
                if c == key[1]:
                    value -= 1
                    parens[key] = value

            skip_comma = False
            for key, value in parens.items():
                if value != 0:
                    skip_comma = True

            if c == ',' and not skip_comma:
                parameters.append(parameter_list[last_split:i].strip())
                last_split = i + 1
        parameters.append(parameter_list[last_split:].strip())

        result = []
        for parameter in parameters:
            name, rest = [x.strip() for x in parameter.split(':', maxsplit=1)]
            name_parts = name.split(' ', maxsplit=1)
            if len(name_parts) > 1:
                name = name_parts[0]
                variable_name = name_parts[1]
            else:
                name = name_parts[0]
                variable_name = name_parts[0]
            equals = rest.rfind('=')
            if equals >= 0:
                default_value = rest[equals + 1:].strip()
                param_type = rest[:equals].strip()
            else:
                default_value = None
                param_type = rest
            result.append({
                "name": name,
                "variable_name": variable_name,
                "type": param_type,
                "default": default_value
            })
        return result

    def handle_signature(self, sig, signode):
        container_class_name = self.env.temp_data.get('swift:class')
        container_class_type = self.env.temp_data.get('swift:class_type')

        # split into method name and rest
        first_anglebracket = sig.find('<')
        first_paren = sig.find('(')
        if first_anglebracket >= 0 and first_paren > first_anglebracket:
            split_point = sig.find('>')+1
        else:
            split_point = first_paren

        # calculate generics
        if first_anglebracket >= 0:
            sp = sig[first_anglebracket:]
            np = sp.find('>')
            generics = sp[:np+1]
        else:
            generics = None

        method_name = sig[0:split_point]

        # find method specialization
        angle_bracket = method_name.find('<')
        if angle_bracket >= 0:
            method_name = method_name[:angle_bracket]

        rest = sig[split_point:]

        # split parameter list
        parameter_list = None
        depth = 0
        for i, c in enumerate(rest):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            if depth == 0:
                parameter_list = rest[1:i]
                rest = rest[i + 1:]
                break

        if len(parameter_list) > 0:
            parameters = self._parse_parameter_list(parameter_list)
        else:
            parameters = []

        # check if it throws
        throws = rest.find('throws') >= 0

        # check for return type
        return_type = None
        arrow = rest.find('->')
        if arrow >= 0:
            return_type = rest[arrow + 2:].strip()

        # build signature and add nodes
        signature = ''
        if self.objtype == 'static_method':
            signode += addnodes.desc_addname("static", "static func ")
        elif self.objtype == 'class_method':
            signode += addnodes.desc_addname("class", "class func ")
        elif self.objtype != 'init':
            signode += addnodes.desc_addname("func", "func ")

        if self.objtype == 'init':
            signode += addnodes.desc_name('init', 'init')
            signature += 'init('
            for p in parameters:
                signature += p['name'] + ':'
            signature += ')'
        else:
            signode += addnodes.desc_name(method_name, method_name)
            signature += method_name
            signature += '('
            for p in parameters:
                signature += p['name'] + ':'
            signature += ')'

        if generics:
            signode += addnodes.desc_addname(generics,generics)

        params = []
        sig = ''
        for p in parameters:
            param = p['name'] + ': ' + p['type']
            sig += p['name'] + ':'
            if p['default']:
                param += ' = ' + p['default']
            params.append(addnodes.desc_parameter(param, param))

        signode += addnodes.desc_parameterlist(sig, "", *params)

        title = signature
        if throws:
            signode += addnodes.desc_annotation("throws", "throws")
            # signature += "throws"

        if return_type:
            signode += addnodes.desc_returns(return_type, return_type)
            #signature += "-" + return_type

        #if container_class_type == 'protocol':
        #    signature += "-protocol"

        #if self.objtype == 'static_method':
        #    signature += '-static'
        #elif self.objtype == 'class_method':
        #    signature += '-class'

        if container_class_name:
            return (container_class_name + '.' + title), (container_class_name + '.' + signature), True
        return title, signature, True


class SwiftEnumCase(SwiftObjectDescription):

    def handle_signature(self, sig, signode):
        container_class_name = self.env.temp_data.get('swift:class')
        enum_case = None
        assoc_value = None
        raw_value = None

        # split on ( -> first part is case name
        parts = [x.strip() for x in sig.split('(', maxsplit=1)]
        enum_case = parts[0].strip()
        if len(parts) > 1:
            parts = parts[1].rsplit('=', maxsplit=1)
            assoc_value = parts[0].strip()
            if len(parts) > 1:
                raw_value = parts[1].strip()
            if assoc_value == "":
                assoc_value = None
            else:
                assoc_value = "(" + assoc_value
        else:
            parts = [x.strip() for x in sig.split('=', maxsplit=1)]
            enum_case = parts[0].strip()
            if len(parts) > 1:
                raw_value = parts[1].strip()

        # Add class name
        signode += addnodes.desc_name(enum_case, enum_case)
        if assoc_value:
            signode += addnodes.desc_type(assoc_value, assoc_value)
        if raw_value:
            signode += addnodes.desc_addname(raw_value, " = " + raw_value)

        if container_class_name:
            enum_case = container_class_name + '.' + enum_case
        return enum_case, enum_case, True


var_sig = re.compile(r'^\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*\b)(\s*:\s*(?P<type>[a-zA-Z_[(][a-zA-Z0-9_<>[\]()?!:, \t-\.]*))?(\s*=\s*(?P<value>[^{]*))?')


class SwiftClassIvar(SwiftObjectDescription):

    doc_field_types = [
        Field('defaultvalue', label=l_('Default'), has_arg=False,
              names=('defaults', 'default')),
    ]

    def handle_signature(self, sig, signode):
        container_class_name = self.env.temp_data.get('swift:class')

        match = var_sig.match(sig)
        if not match:
            self.env.warn(
                self.env.docname,
                'invalid variable/constant documentation string "%s", ' % sig,
                self.lineno)
            return

        match = match.groupdict()

        if self.objtype == 'static_var':
            signode += addnodes.desc_addname("static var", "static var ")
        elif self.objtype == 'static_let':
            signode += addnodes.desc_addname("static let", "static let ")
        elif self.objtype == 'var':
            signode += addnodes.desc_addname("var", "var ")
        elif self.objtype == 'let':
            signode += addnodes.desc_addname("let", "let ")

        name = match['name'].strip()
        signature = name
        signode += addnodes.desc_name(name, name)
        if match['type']:
            typ = match['type'].strip()
            #signature += '-' + typ
            signode += addnodes.desc_type(typ, " : " + typ)
        if match['value'] and len(match['value']) > 0:
            value = match['value'].strip()
            signode += addnodes.desc_addname(value, " = " + value)
        elif match['value']:
            signode += addnodes.desc_addname('{ ... }', ' = { ... }')

        #signature += "-" + self.objtype

        if container_class_name:
            name = container_class_name + '.' + name
            signature = container_class_name + '.' + signature

        return name, signature, True


class SwiftXRefRole(XRefRole):

    def __init__(self,tipe):
        super().__init__()
        self.tipe = tipe

    def process_link(self, env, refnode, has_explicit_title, title, target):
        if "." in target:
            return title, target
        return title, self.tipe+" "+target


type_order = ['class', 'struct', 'enum', 'protocol', 'extension']

class SwiftModuleIndex(Index):
    """
    Index subclass to provide the Swift module index.
    """

    name = 'modindex'
    localname = l_('Swift Module Index')
    shortname = l_('Index')

    @staticmethod
    def indexsorter(a):
        global type_order
        for i, t in enumerate(type_order):
            if a[0].startswith(t):
                return '{:04d}{}'.format(i, a[0])
        return a[0]

    @staticmethod
    def sigsorter(a):
        global type_order

        start = 0
        for t in type_order:
            if a[3].startswith(t):
                start = len(t) + 1
                break
        return a[3][start]

    def generate(self, docnames=None):
        global type_order
        content = []
        collapse = 0

        entries = []
        for refname, (docname, typ, signature) in _iteritems(self.domain.data['objects']):
            info = typ.replace("_", " ")
            entries.append((
                refname,
                0,
                docname,
                signature,
                info,
                '',
                ''
            ))

        entries = sorted(entries, key=self.sigsorter)
        current_list = []
        current_key = None
        for entry in entries:
            start = 0
            for t in type_order:
                if entry[3].startswith(t):
                    start = len(t) + 1
                    break

            if entry[3][start].upper() != current_key:
                if len(current_list) > 0:
                    content.append((current_key, current_list))
                current_key = entry[3][start].upper()
                current_list = []
            current_list.append(entry)
        content.append((current_key, current_list))

        result = []
        for key, entries in content:
            e = sorted(entries, key=self.indexsorter)
            result.append((key, e))

        return result, collapse


class SwiftDomain(Domain):
    """Swift language domain."""
    name = 'swift'
    label = 'Swift'
    object_types = {
        'function':        ObjType(l_('function'),            'function',     'obj'),
        'method':          ObjType(l_('method'),              'method',       'obj'),
        'class_method':    ObjType(l_('class method'),        'class_method', 'obj'),
        'static_method':   ObjType(l_('static method'),       'static_method','obj'),
        'class':           ObjType(l_('class'),               'class',        'obj'),
        'enum':            ObjType(l_('enum'),                'enum',         'obj'),
        'enum_case':       ObjType(l_('enum case'),           'enum_case',    'obj'),
        'struct':          ObjType(l_('struct'),              'struct',       'obj'),
        'init':            ObjType(l_('initializer'),         'init',         'obj'),
        'protocol':        ObjType(l_('protocol'),            'protocol',     'obj'),
        'extension':       ObjType(l_('extension'),           'extension',    'obj'),
        'default_impl':    ObjType(l_('extension'),           'default_impl', 'obj'),
        'let':             ObjType(l_('constant'),            'let',          'obj'),
        'var':             ObjType(l_('variable'),            'var',          'obj'),
        'static_let':      ObjType(l_('static/class constant'),     'static_let',   'obj'),
        'static_var':      ObjType(l_('static/class variable'),     'static_var',   'obj'),
    }

    directives = {
        'function':        SwiftClassmember,
        'method':          SwiftClassmember,
        'class_method':    SwiftClassmember,
        'static_method':   SwiftClassmember,
        'class':           SwiftClass,
        'enum':            SwiftClass,
        'enum_case':       SwiftEnumCase,
        'struct':          SwiftClass,
        'init':            SwiftClassmember,
        'protocol':        SwiftClass,
        'extension':       SwiftClass,
        'default_impl':    SwiftClass,
        'let':             SwiftClassIvar,
        'var':             SwiftClassIvar,
        'static_let':      SwiftClassIvar,
        'static_var':      SwiftClassIvar,
    }

    roles = {
        'function':      SwiftXRefRole("function"),
        'method':        SwiftXRefRole("method"),
        'class':         SwiftXRefRole("class"),
        'enum':          SwiftXRefRole("enum"),
        'enum_case':     SwiftXRefRole("enum_case"),
        'struct':        SwiftXRefRole("struct"),
        'init':          SwiftXRefRole("init"),
        'static_method': SwiftXRefRole("static_method"),
        'class_method':  SwiftXRefRole("class_method"),
        'protocol':      SwiftXRefRole("protocol"),
        'extension':     SwiftXRefRole("extension"),
        'default_impl':  SwiftXRefRole("default_impl"),
        'let':           SwiftXRefRole("let"),
        'var':           SwiftXRefRole("var"),
        'static_let':    SwiftXRefRole("static_let"),
        'static_var':    SwiftXRefRole("static_var")
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }
    indices = [
        SwiftModuleIndex,
    ]

    def clear_doc(self, docname):
        for fullname, (fn, _, _) in list(self.data['objects'].items()):
            if fn == docname:
                del self.data['objects'][fullname]

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        for refname, (docname, type, signature) in _iteritems(self.data['objects']):
            if refname == target:
                node = make_refnode(builder, fromdocname, docname, signature, contnode, target)
                return node
        return None

    def get_objects(self):
        for refname, (docname, type, signature) in _iteritems(self.data['objects']):
            yield (refname, refname, type, docname, refname, 1)

def make_index(app,*args):
    from .autodoc import build_index
    build_index(app)

def setup(app):
    from .autodoc import SwiftAutoDocumenter, ProtocolAutoDocumenter, ExtensionAutoDocumenter, EnumAutoDocumenter
    app.connect('builder-inited', make_index)

    app.override_domain(SwiftStandardDomain)
    app.add_autodocumenter(SwiftAutoDocumenter)
    app.add_autodocumenter(ProtocolAutoDocumenter)
    app.add_autodocumenter(ExtensionAutoDocumenter)
    app.add_autodocumenter(EnumAutoDocumenter)


    app.add_domain(SwiftDomain)
    app.add_config_value('swift_search_path', ['../src'], 'env')
    app.add_config_value('autodoc_default_flags', [], True)
