# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(".."))

from recommonmark.parser import CommonMarkParser

import openapi

# -- Project information -----------------------------------------------------

year = date.today().year
project = "aio-openapi"
author = "Quantmind"
copyright = f"{year}, {author}"

release = openapi.__version__
source_suffix = [".rst", ".md"]
source_parsers = {
    ".md": CommonMarkParser,
}
# The master toctree document.
master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
extensions = [
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.blockdiag",
]

try:
    import sphinxcontrib.spelling

    extensions.append("sphinxcontrib.spelling")
except ImportError:
    pass

templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = "alabaster"
html_theme = "aiohttp_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
html_static_path = ["_static"]


intersphinx_mapping = {
    "python": ("http://docs.python.org/3", None),
    "asyncpg": ("https://magicstack.github.io/asyncpg/current/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/", None),
}

highlight_language = "python3"

html_theme_options = {
    "description": "Async web middleware for aiohttp, asyncpg and OpenAPI",
    "canonical_url": "https://aio-openapi.readthedocs.io/en/latest/",
    "github_user": "quantmind",
    "github_repo": "aio-openapi",
    "github_button": True,
    "github_type": "star",
    "github_banner": True,
    "badges": [
        {
            "image": "https://badge.fury.io/py/aio-openapi.svg",
            "target": "https://pypi.org/project/aio-openapi",
            "height": "20",
            "alt": "Latest PyPI package version",
        },
        {
            "image": "https://img.shields.io/pypi/pyversions/aio-openapi.svg",
            "target": "https://pypi.org/project/aio-openapi",
            "height": "20",
            "alt": "Supported python versions",
        },
        {
            "image": "https://github.com/quantmind/aio-openapi/workflows/build/badge.svg",
            "target": "https://github.com/quantmind/aio-openapi/actions?query=workflow%3Abuild",
            "height": "20",
            "alt": "Build status",
        },
        {
            "image": "https://coveralls.io/repos/github/quantmind/aio-openapi/badge.svg?branch=HEAD",
            "target": "https://coveralls.io/github/quantmind/aio-openapi?branch=HEAD",
            "height": "20",
            "alt": "Coverage status",
        },
    ],
}

html_sidebars = {"**": ["about.html", "navigation.html", "searchbox.html",]}
