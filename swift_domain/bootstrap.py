import argparse
import os

from swift_domain.indexer import SwiftFileIndex, SwiftObjectIndex, pprint

parser = argparse.ArgumentParser(description='Bootstrap ReStructured Text documentation for Swift code.')
parser.add_argument(
    'source_path',
    type=str,
    help='Path to Swift files'
)
parser.add_argument(
    'documentation_path',
    type=str,
    help='Path to generate the documentation in'
)
parser.add_argument(
    '--private',
    dest='private',
    action='store_true',
    help='Include private and internal members',
    required=False,
    default=False
)
parser.add_argument(
    '--overwrite',
    dest='overwrite',
    action='store_true',
    help='Overwrite existing documentation',
    required=False,
    default=False
)
parser.add_argument(
    '--undoc-members',
    dest='undoc',
    action='store_true',
    help='Include members without documentation block',
    required=False,
    default=False
)
parser.add_argument(
    '--no-members',
    dest='members',
    action='store_false',
    help='Do not include member documentation',
    required=False,
    default=True
)
parser.add_argument(
    '--file-location',
    dest='location',
    action='store_true',
    help='Add a paragraph with file location where the member was defined',
    required=False,
    default=False
)
parser.add_argument(
    '--no-index',
    dest='noindex',
    action='store_true',
    help='Do not add anything to the index',
    required=False,
    default=False
)
parser.add_argument(
    '--no-index-members',
    dest='noindex_members',
    action='store_true',
    help='Do not add members to the index, just the toplevel items',
    required=False,
    default=False
)
parser.add_argument(
    '--exclude-list',
    dest='exclusion_list',
    metavar='file',
    type=str,
    required=False,
    default=None,
    help='File with exclusion list for members'
)
parser.add_argument(
    '--use-autodocumenter',
    dest='autodocumenter',
    action='store_true',
    help='Do not dump actual documentation but rely on the auto documenter, may duplicate documentation in case you have defined extensions in multiple files',
    required=False,
    default=False
)

def main():
    args = parser.parse_args()
    source_path = os.path.abspath(args.source_path)
    file_index = SwiftFileIndex([source_path])

    try:
        os.makedirs(args.documentation_path)
    except FileExistsError:
        pass

    # check for overwrite
    for file, members in file_index.by_file().items():
        destfile = get_dest_file(file, args.source_path, args.documentation_path)
        if os.path.exists(destfile) and not args.overwrite:
            print("ERROR: {} already exists, to overwrite existing documentation use the '--overwrite' flag".format(file))
            exit(1)

    exclusion_list = []
    if args.exclusion_list:
        exclusion_list = open(args.exclusion_list, 'r').readlines()

    for file, members in file_index.by_file().items():
        destfile = get_dest_file(file, args.source_path, args.documentation_path)
        print("Writing documentation for '{}'...".format(os.path.relpath(file, source_path)))
        try:
            os.makedirs(os.path.dirname(destfile))
        except FileExistsError:
            pass
        with open(destfile, "w") as fp:
            heading = 'Documentation for {}'.format(os.path.relpath(file, source_path))
            fp.write(('=' * len(heading))+ '\n')
            fp.write(heading + '\n')
            fp.write(('=' * len(heading))+ '\n\n\n')
            if args.autodocumenter:
                auto_document(members, args, exclusion_list, fp)
            else:
                document(members, args, exclusion_list, file, fp, '')


def get_dest_file(filename, search_path, doc_path):
    rel = os.path.relpath(filename, search_path)
    return os.path.join(doc_path, rel)[:-6] + '.rst'


def auto_document(members, args, exclusion_list, fp):
    for member in members:
        add = True
        if member['name'] in exclusion_list:
            add = False
        if args.undoc == False and len(member['docstring']) == 0:
            add = False
        if args.private == False and member['scope'] != 'public':
            add = False
        if not add:
            continue

        fp.write('.. autoswift:: {}\n'.format(member['name']))
        if args.noindex:
            fp.write('   :noindex:\n')
        if args.noindex_members:
            fp.write('   :noindex-members:\n')
        if args.members:
            fp.write('   :members:\n')
        if args.undoc:
            fp.write('   :undoc-members:\n')
        if args.location:
            fp.write('   :file-location:\n')
        if args.private:
            fp.write('   :private-members:\n')


def document(members, args, exclusion_list, file, fp, indent):
    for member in members:
        add = True
        if member['name'] in exclusion_list:
            add = False
        if args.undoc == False and len(member['docstring']) == 0:
            add = False
        if args.private == False and member['scope'] != 'public':
            add = False
        if not add:
            continue

        doc = SwiftFileIndex.documentation(
            member,
            indent=indent,
            location=args.location,
            nodocstring=args.undoc,
            noindex=args.noindex
        )
        for line in doc:
            content = indent + line + "\n"
            fp.write(content)

        if args.members:
            document_member(member, args, exclusion_list, file, fp, indent)
        fp.write('\n')


def document_member(parent, args, exclusion_list, file, fp, indent):
    for member in parent['members'].index:
        add = True
        if member['name'] in exclusion_list:
            add = False
        if args.undoc == False and len(member['docstring']) == 0:
            add = False
        if args.private == False and member['scope'] != 'public':
            add = False
        if not add:
            continue

        doc = SwiftObjectIndex.documentation(
            member,
            indent=indent,
            location=file if args.location else None,
            nodocstring=False,
            noindex=(args.noindex or args.noindex_members)
        )
        for line in doc:
            content = indent + '   ' + line + "\n"
            fp.write(content)

    document(parent['children'], args, exclusion_list, file, fp, indent + '   ')


if __name__ == "__main__":
    main()
