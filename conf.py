project = 'Lantiq Falcon (PEB/PEF 98035)'
copyright = '2026'
author = 'Falcon Analysis'
release = '1.0'
version = '1.0'

extensions = [
    'myst_parser',
    'sphinxcontrib.mermaid',
    'sphinx.ext.mathjax',
    'sphinx.ext.autosectionlabel',
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 4
myst_fence_as_directive = ["mermaid"]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

master_doc = 'index'
language = 'zh_CN'
exclude_patterns = ['_build', '.venv', 'venv', 'Thumbs.db', '.DS_Store', '**/README.md', 'README.md']

html_theme = 'lumina'
html_baseurl = 'https://difan.org.cn/soc/lantiq-falcon-s/'

html_static_path = []
autosectionlabel_prefix_document = True
