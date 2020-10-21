extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]
# html_theme = 'nature'
html_theme = 'classic'
html_theme_options = {
    'stickysidebar': True
}
html_last_updated_fmt = '%d-%b-%Y'

# Napoleon settings
napoleon_google_docstring = False
# napoleon_numpy_docstring = True
# napoleon_include_init_with_doc = False
# napoleon_include_private_with_doc = False
# napoleon_include_special_with_doc = True
# napoleon_use_admonition_for_examples = False
# napoleon_use_admonition_for_notes = False
# napoleon_use_admonition_for_references = False
# napoleon_use_ivar = False
# napoleon_use_param = True
# napoleon_use_keyword = True
napoleon_use_rtype = False

# The name of the entry point, without the ".rst" extension.
# By convention this will be "index"
master_doc = "index"
# This values are all used in the generated documentation.
# Usually, the release and version are the same,
# but sometimes we want to have the release have an "rc" tag.
project = "SublimeEnv"
copyright = "2020, TPO"
author = "TPO (tpo.pomgom@gmail.com)"
version = release = "2020.0.1"
