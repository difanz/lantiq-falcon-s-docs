project = 'Lantiq Falcon (PEB/PEF 98035)'
copyright = '2026'
author = 'Falcon Documentation'
release = '1.0'
version = '1.0'

extensions = [
    'myst_parser',
    'sphinxcontrib.mermaid',
    'sphinx.ext.mathjax',
    'sphinx.ext.autosectionlabel',
    'sphinxcontrib.jquery',
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
html_search_language = 'zh'
exclude_patterns = ['_build', '.venv', 'venv', 'Thumbs.db', '.DS_Store', '**/README.md', 'README.md']

html_theme = 'sphinx_material'
html_baseurl = 'https://difan.org.cn/soc/lantiq-falcon-s/'
html_theme_options = {
    'nav_title': 'Lantiq Falcon',
    'logo_icon': '&#xe869;',
    'base_url': html_baseurl,
    'color_primary': 'blue-grey',
    'color_accent': 'blue',
    'globaltoc_depth': 2,
    'globaltoc_collapse': True,
    'globaltoc_includehidden': True,
    'localtoc_label_text': '本页内容',
    'search_placeholder_text': '搜索文档',
    'version_json': 'versions.json',
    'version_dropdown': False,
}
html_sidebars = {
    '**': ['logo-text.html', 'globaltoc.html', 'localtoc.html', 'searchbox.html'],
}

html_static_path = ['_static']
html_css_files = ['falcon.css']
html_js_files = [('diagrams.js', {'defer': 'defer'})]
autosectionlabel_prefix_document = True


def _material_template_helpers(app):
    if app.builder.format != 'html':
        return
    import sphinx_material

    # Template callables belong to Jinja, outside the cached configuration.
    helpers = sphinx_material.get_html_context()
    app.builder.templates.environment.globals.update(helpers)
    for name in helpers:
        app.config.html_context.pop(name, None)


def setup(app):
    app.connect('builder-inited', _material_template_helpers, priority=800)
