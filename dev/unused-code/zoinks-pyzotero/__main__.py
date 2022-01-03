'''
Zoinks: a program to print specific field values from Zotero records

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2020 by Michael Hucka and the California Institute of Technology.
This code is open-source software released under a 3-clause BSD license.
Please see the file "LICENSE" for more information.
'''

from   bun import UI, inform, warn, alert, alert_fatal
from   boltons.debugutils import pdb_on_signal
from   commonpy.data_utils import timestamp
from   commonpy.interrupt import config_interrupt
from   commonpy.string_utils import antiformat
import plac
import signal
import shutil
import sys
from   sys import exit as exit
from   textwrap import wrap

import zoinks
from zoinks import print_version
from .exceptions import UserCancelled, FileError, CannotProceed
from .exit_codes import ExitCode
from .main_body import MainBody

if __debug__:
    from sidetrack import set_debug, log, logr


# Main program.
# .............................................................................

@plac.annotations(
    api_key    = ('API key to access the Zotero API service',          'option', 'a'),
    field      = ('one or more field names separated by commas',       'option', 'f'),
    identifier = ('Zotero user ID for API calls',                      'option', 'i'),
    no_keyring = ('do not store credentials in the keyring service',   'flag',   'K'),
    list       = ('print list of known field names',                   'flag',   'l'),
    version    = ('print version info and exit',                       'flag',   'V'),
    debug      = ('write detailed trace to "OUT" ("-" means console)', 'option', '@'),
    items      = 'one or more items in a Zotero database',
)

def main(api_key = 'A', field = 'F', identifier = 'I', no_keyring = False,
         list = False, version = False, debug = 'OUT', *items):
    '''Zoinks prints field values from Zotero records.'''

    # Set up debug logging as soon as possible, if requested ------------------

    if debug != 'OUT':
        if __debug__: set_debug(True, debug)
        import faulthandler
        faulthandler.enable()
        if not sys.platform.startswith('win'):
            # Even with a different signal, I can't get this to work on Win.
            pdb_on_signal(signal.SIGUSR1)

    # Preprocess arguments and handle early exits -----------------------------

    ui = UI('Zoinks', '', show_banner = False, use_color = not no_color)
    ui.start()

    if version:
        print_version()
        exit(int(ExitCode.success))
    if list:
        inform('Known field names:\n')
        width = (shutil.get_terminal_size().columns - 2) or 78
        # FIXME
        exit(int(ExitCode.success))

    field_list = ['Title'] if field == 'F' else field.lower().split(',')
    bad_name = next((f for f in fields_list if f not in field_names()), None)
    if bad_name:
        alert(f'Unrecognized field name "{bad_name}".')
        alert('The known fields are: ' + ', '.join(field_names()) + '.')
        exit(int(ExitCode.bad_arg))

    # Do the real work --------------------------------------------------------

    if __debug__: log('='*8 + f' started {timestamp()} ' + '='*8)
    body = exception = None
    try:
        body = MainBody(items       = items,
                        api_key     = None if api_key == 'A' else api_key,
                        user_id     = None if identifier == 'I' else identifier,
                        use_keyring = not no_keyring,
                        fields      = field_list)
        config_interrupt(body.stop, UserCancelled(ExitCode.user_interrupt))
        body.run()
        exception = body.exception
    except Exception as ex:
        exception = sys.exc_info()

    # Try to deal with exceptions gracefully ----------------------------------

    exit_code = ExitCode.success
    if exception:
        if __debug__: log(f'main body raised exception: {antiformat(exception)}')
        if exception[0] == CannotProceed:
            exit_code = exception[1].args[0]
        elif exception[0] == FileError:
            alert_fatal(antiformat(exception[1]))
            exit_code = ExitCode.file_error
        elif exception[0] in [KeyboardInterrupt, UserCancelled]:
            warn('Interrupted.')
            exit_code = ExitCode.user_interrupt
        else:
            msg = antiformat(exception[1])
            alert_fatal(f'Encountered error {exception[0].__name__}: {msg}')
            exit_code = ExitCode.exception
            if __debug__:
                from traceback import format_exception
                details = ''.join(format_exception(*exception))
                logr(f'Exception: {msg}\n{details}')
    else:
        inform('Done.')

    # And exit ----------------------------------------------------------------

    if __debug__: log('_'*8 + f' stopped {timestamp()} ' + '_'*8)
    if __debug__: log(f'exiting with exit code {exit_code}')
    exit(int(exit_code))


# Main entry point.
# .............................................................................

# The following entry point definition is for the console_scripts keyword
# option to setuptools.  The entry point for console_scripts has to be a
# function that takes zero arguments.
def console_scripts_main():
    plac.call(main)


# The following allows users to invoke this using "python3 -m zoinks".
if __name__ == '__main__':
    plac.call(main)
