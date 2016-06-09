
*********************************************
AnarchyTools Sphinx Theme and Swift Extension
*********************************************

.. contents::

This is a simplistic theme used for the AnarchyTools Swift documentation.

Installation
============

Via package
-----------

Download the package or add it to your ``requirements.txt`` file:

.. code:: bash

    $ pip install anarchy_sphinx

In your ``conf.py`` file:

.. code:: python

    import anarchy_theme

    html_theme = "anarchy_theme"

    html_theme_path = [anarchy_theme.get_html_theme_path()]

Via git or download
-------------------

Symlink or subtree the ``anarchy_sphinx/anarchy_theme`` repository into your documentation at
``docs/_themes/anarchy_theme`` then add the following two settings to your Sphinx
conf.py file:

.. code:: python

    html_theme = "anarchy_theme"
    html_theme_path = ["_themes", ]

Changelog
=========

0.2.0:
------

- Add ``anarchysphinx`` command line tool to bootstrap documentation


Swift auto documentation extractor
==================================

If you want to use the doc-string extractor for Swift you'll need to inform Sphinx about
where you keep your ``*.swift`` files.

.. code:: python

    swift_search_path = [ "../src" ]

If you've set that up you can use ``.. autoswift:: <symbol>`` to let the documenter search
for a Swift symbol and import the documentation in place.

You may set some flags to configure documentation behaviour:

- ``:noindex:`` do not add to index
- ``:noindex-members:`` do not index members
- ``:members:`` document members, optional: list of members to include
- ``:recursive-members:`` recursively document members (enums nested in classes, etc.)
- ``:undoc-members:`` include members without docstring
- ``:nodocstring:`` do not show the docstring
- ``:file-location:`` add a paragraph with the file location
- ``:exclude-members:`` exclude these members
- ``:private-members:`` show private members


Manual documentation for Swift types
====================================

The Swift Domain contains the following directives, if the directive declares what you
document you can skip the corresponding Swift keyword (Example: ``.. swift:class:: Classname``)

- ``.. swift:function::`` toplevel functions
- ``.. swift:class::`` class definitions
- ``.. swift:struct::`` struct definitions
- ``.. swift:enum::`` enum definitions
- ``.. swift:protocol::`` protocol definitions
- ``.. swift:extension::`` extensions and default implementations for protocols
- ``.. swift:method::`` func signatures
- ``.. swift:class_method::`` class functions
- ``.. swift:static_method::`` static methods in structs or protocols
- ``.. swift:init::`` initializers
- ``.. swift:enum_case::`` enum cases
- ``.. swift:let::`` let constants
- ``.. swift:var::`` variables
- ``.. swift:static_let::`` static let constants
- ``.. swift:static_var::`` static variables

all of those have a ``:noindex:`` parameter to keep it out of the index.


``anarchysphinx`` command line tool
===================================

.. code::

    usage: anarchysphinx [-h] [--private] [--overwrite] [--undoc-members]
                         [--no-members] [--file-location] [--no-index]
                         [--no-index-members] [--exclude-list file]
                         [--use-autodocumenter]
                         source_path documentation_path

    Bootstrap ReStructured Text documentation for Swift code.

    positional arguments:
      source_path           Path to Swift files
      documentation_path    Path to generate the documentation in

    optional arguments:
      -h, --help            show this help message and exit
      --private             Include private and internal members
      --overwrite           Overwrite existing documentation
      --undoc-members       Include members without documentation block
      --no-members          Do not include member documentation
      --file-location       Add a paragraph with file location where the member
                            was defined
      --no-index            Do not add anything to the index
      --no-index-members    Do not add members to the index, just the toplevel
                            items
      --exclude-list file   File with exclusion list for members
      --use-autodocumenter  Do not dump actual documentation but rely on the auto
                            documenter, may duplicate documentation in case you
                            have defined extensions in multiple files
