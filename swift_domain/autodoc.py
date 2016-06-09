from sphinx.ext.autodoc import Documenter, bool_option, members_option, members_set_option
from swift_domain.indexer import SwiftFileIndex, SwiftObjectIndex

file_index = None
def build_index(app):
    global file_index
    file_index = SwiftFileIndex(app.config.swift_search_path)


class SwiftAutoDocumenter(Documenter):
    objtype = 'swift'
    option_spec = {
        'noindex': bool_option,                 # do not add to index
        'noindex-members': bool_option,         # do not index members
        'members': members_option,              # document members, optional: list
        'recursive-members': bool_option,       # recursively document members
        'undoc-members': bool_option,           # include members without docstring
        'nodocstring': bool_option,             # do not show the docstring
        'file-location': bool_option,           # add a paragraph with the file location
        'exclude-members': members_set_option,  # exclude these members
        'private-members': bool_option          # show private members
    }

    def __init__(self, *args, **kwargs):
        super(SwiftAutoDocumenter, self).__init__(*args, **kwargs)
        self.append_at_end = []

    def generate(self, **kwargs):
        global file_index
        all_members = kwargs.get('all_members', False)

        emit_warning = True
        for index in file_index.find(self.name):
            self.document(index)
            emit_warning = False

        if emit_warning:
            self.env.warn(
                self.env.docname,
                'can not find "%s" in any Swift file!' % self.name)

    def document(self, item, indent=''):

        doc = SwiftFileIndex.documentation(
            item,
            indent=self.content_indent,
            location=('file-location' in self.options),
            nodocstring=('nodocstring' in self.options),
            noindex=('noindex' in self.options)
        )
        for line in doc:
            content = indent + line
            self.add_line(content, '<autodoc>')

        # only document members when asked to
        if 'members' not in self.options:
            return

        member_list = self.options.members if isinstance(self.options.members, list) else None
        exclude_list = self.options.exclude_members if isinstance(self.options.exclude_members, list) else []
        for member in item['members'].index:
            add = False
            if not member_list or member['name'] in member_list:
                add = True
            if member['name'] in exclude_list:
                add = False
            if 'undoc-members' in self.options and len(member['docstring']) == 0:
                add = False
            if 'private-members' not in self.options and member['scope'] != 'public':
                add = False
            if add:
                loc = item['file'] if 'file-location' in self.options else None
                doc = SwiftObjectIndex.documentation(
                    member,
                    indent=self.content_indent,
                    location=loc,
                    nodocstring=('nodocstring' in self.options),
                    noindex=('noindex' in self.options or 'noindex-members' in self.options)
                )
                for line in doc:
                    content = indent + self.content_indent + line
                    self.add_line(content, '<autodoc>')

        if 'recursive-members' in self.options:
            for child in item['children']:
                self.document(child, indent=indent + self.content_indent)
