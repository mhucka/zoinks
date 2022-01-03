'''
Zoinks: retrieve field values for Zotero records

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2022 by Michael Hucka and the California Institute of Technology.
This code is open-source software released under the MIT license.  Please see
the file "LICENSE" for more information.
'''

# Package metadata ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#  ╭────────────────────── Notice ── Notice ── Notice ─────────────────────╮
#  |    The following values are automatically updated at every release    |
#  |    by the Makefile. Manual changes to these values will be lost.      |
#  ╰────────────────────── Notice ── Notice ── Notice ─────────────────────╯

__version__     = '0.0.3'
__description__ = 'Zoinks: a command-line utility to retrieve Zotero record values'
__url__         = 'https://github.com/mhucka/zoinks'
__author__      = 'Mike Hucka'
__email__       = 'mhucka@caltech.edu'
__license__     = 'BSD 3-clause license'


# Miscellaneous utilities.
# .............................................................................

def print_version():
    print(f'{__name__} version {__version__}')
    print(f'Authors: {__author__}')
    print(f'URL: {__url__}')
    print(f'License: {__license__}')
