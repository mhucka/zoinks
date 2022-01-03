'''
Zoinks: a program to print field values from Zotero records

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2022 by Michael Hucka and the California Institute of Technology.
This code is open-source software released under a 3-clause BSD license.
Please see the file "LICENSE" for more information.
'''

import sys
if sys.version_info <= (3, 8):
    print('zoinks requires Python version 3.8 or higher,')
    print('but the current version of Python is ' +
          str(sys.version_info.major) + '.' + str(sys.version_info.minor) + '.')
    exit(1)

# Note: this code uses lazy loading.  Additional imports are made later.
from   commonpy.data_structures import CaseFoldDict
from   os.path import exists, isfile
import plac
from   sidetrack import set_debug, log

from   .exceptions import ZoinksError, ConnectionFailure
from   .exit_codes import ExitCode


# Constants.
# .............................................................................

_BBT_HOST = 'localhost'
_BBT_PORT = 23119
_BBT_JSON_RPC = f'http://{_BBT_HOST}:{int(_BBT_PORT)}/better-bibtex/json-rpc'


# Main program.
# .............................................................................

@plac.annotations(
    list_fields = ('list the names of all fields on the record(s)',     'flag',   'l'),
    source      = ('how to read Zotero identifiers (default: stdin)',   'option', 's'),
    no_gui      = ('do not use macOS GUI dialogs for error messages',   'flag',   'U'),
    version     = ('print version info and exit',                       'flag',   'V'),
    debug       = ('write detailed trace to "OUT" ("-" means console)', 'option', '@'),
    fields      = 'one or more fields to retrieve and print',
)

def main(list_fields = False, source = 'S', no_gui = False,
         version = False, debug = 'OUT', *fields):
    '''Zoinks prints field values from Zotero records.'''

    # Define shortcut functions for common user feedback actions.
    def alert(msg): inform(msg, no_gui)
    def stop(msg, err = ExitCode.exception): inform(msg, no_gui), sys.exit(int(err))

    # Process arguments & handle early exits ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    debugging = (debug != 'OUT')
    if debugging:
        set_debug(True, debug)
        import faulthandler
        faulthandler.enable()

    if version:
        from zoinks import print_version
        print_version()
        sys.exit(int(ExitCode.success))

    fields = ['all'] if fields == () else list(field.lower() for field in fields)

    if source == 'S' or source.lower() in ['stdin', '-']:
        if sys.stdin.isatty():
            stop('Input expected via pipe or redirection.', ExitCode.bad_arg)
        else:
            identifiers = sys.stdin.read().split()
    elif source.lower() in ['clipboard', 'pasteboard']:
        identifiers = clipboard().split()
        if not identifiers:
            stop('The clipboard appears to be empty.', ExitCode.bad_arg)
    elif exists(source) and isfile(source):
        from commonpy.file_utils import readable
        if readable(source):
            with open(source, 'r') as file:
                identifiers = file.readlines()
        else:
            stop('Unable to read file ' + source, ExitCode.file_error)
    else:
        stop('Path does not exist or is not a file: ' + source, ExitCode.bad_arg)
    identifiers = [id.strip() for id in identifiers]

    if not bbt_running():
        stop('Zotero or Better BibTeX service does not appear to be running.',
             ExitCode.zotero_error)

    # Do the real work --------------------------------------------------------

    try:
        # BBT's JSON-RPC interface needs citation keys. Get them if we need to.
        if any(item_key(id).startswith('@') for id in identifiers):
            log('user provided citation keys')
            identifiers = [id.lstrip('@') for id in identifiers]
            mapping = CaseFoldDict(zip(identifiers, identifiers))
        else:
            log('asking BBT for records for ' + str(identifiers))
            mapping = bbt_rpc('item.citationkey', [identifiers])

        single_record = (len(mapping) == 1)
        single_field  = (len(fields) == 1)

        # If we're only getting citation keys, print them & exit.
        if single_field and fields[0] in ['citationkey', 'citekey']:
            if single_record:
                identifier, citationkey = mapping.popitem()
                print(citationkey)
            else:
                print('\n'.join(f'{k}: {v}' for k, v in mapping.items()))
            sys.exit(int(ExitCode.success))

        # Else, call BBT again with the citation keys to get the data of each
        # item, then replace the citation keys in our mapping with the records.
        # (The record has the citation key in it -- we're not losing anything.)
        log('getting record for each citation key from BBT')
        for key, citation_key in mapping.items():
            records = bbt_rpc('item.export', [[citation_key], 'jzon'])
            if records and len(records) == 1:
                mapping[key] = records[0]
            elif records and len(records) > 1:
                stop(f'Unexpectedly got {len(records)} records for {key}')
            else:
                alert(f'did not get a record for {key}')
                mapping[key] = {'Unknown': 'Unknown'}

        log('printing results')
        if list_fields:                 # Only list the field names, w/o values.
            if single_record:
                key, record = mapping.popitem()
                output(', '.join(record.keys()))
            else:
                for key, record in mapping.items():
                    output(key + ': ' + ', '.join(record.keys()) + '\n', 2)
        elif 'all' in fields:           # Print all field values.
            for key, record in mapping.items():
                pretty_print(record)
                output('\n')
        else:                           # Print only selected field values.
            for key, record in mapping.items():
                for name in [field for field in fields if field in record]:
                    prefix = ''
                    if not single_record:
                        prefix = key + ': '
                    if not single_field:
                        prefix = (prefix + name + ': ')
                    output(prefix + str(record.get(name, '')))
    except KeyboardInterrupt:
        log(f'user interrupted program -- exiting')
        sys.exit(int(ExitCode.user_interrupt))
    except ConnectionFailure as ex:
        stop(str(ex))
    except Exception as ex:
        from traceback import format_exception
        exception = sys.exc_info()
        details = ''.join(format_exception(*exception))
        if debugging:
            breakpoint()
        else:
            stop(f'Encountered error: ' + str(ex) + '\n\n' + details)

    log('done.')
    sys.exit(int(ExitCode.success))


# Miscellaneous helpers.
# .............................................................................

def clipboard():
    '''Return the clipboard/pasteboard contents as a string.'''
    # The pasteboard code come from a 2011-11-29 posting by "MagerValp"
    # to Stack Overflow at https://stackoverflow.com/a/8317794/743730
    from AppKit import NSPasteboard, NSStringPboardType
    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_(NSStringPboardType)


def item_key(x):
    return x.rsplit('/', 1)[-1] if x.startswith('zotero://') else x


def bbt_running():
    '''Return True if it looks like BBT is listening on the socket.'''
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((_BBT_HOST, _BBT_PORT)) == 0


def bbt_rpc(method, params):
    '''Call BBT's JSON-RPC interface and return the results.

    Returns a CaseFoldDict containing a dictionary version of the JSON
    data returned by BBT for the query. If the query is for records (items) in
    Zotero, returns a list of dictionaries.

    Throws exceptions if something goes wrong.
    '''
    from   commonpy.network_utils import net
    from   commonpy.exceptions import Interrupted
    import json

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    data = json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params})
    (response, error) = net('post', _BBT_JSON_RPC, headers = headers, data = data)
    if error:
        raise ConnectionFailure('Better BibTeX API error: ' + str(error))
    result_dict = json.loads(response.text)
    if 'error' in result_dict.keys():
        raise ZoinksError('BBT error: ' + result_dict['error']['message'])
    if 'result' in result_dict.keys():
        payload = result_dict['result']
        if isinstance(payload, list) and isinstance(payload[0], int):
            payload = json.loads(payload[2])
        if 'items' in payload:
            return [CaseFoldDict(item) for item in payload['items']]
        return CaseFoldDict(payload)
    return CaseFoldDict(result_dict)


def pretty_print(record, indent = 0):
    for field, value in record.items():
        if isinstance(value, list):
            print(field + ':')
            for el in value:
                pretty_print(el, indent + 2)
        elif isinstance(value, dict):
            pretty_print(value, indent + 2)
        else:
            print(' '*indent +  field + ': ' + str(value))


def output(text, indent = 0):
    import shutil
    from textwrap import wrap
    width = (shutil.get_terminal_size().columns - 2) or 78
    print('\n'.join(wrap(text, width = width, subsequent_indent = ' '*indent)))


def inform(msg, no_gui):
    '''Print an error message or show an error dialog.'''
    log('inform: ' + msg)
    if no_gui:
        print(msg)
    else:
        from osax import OSAX
        sa = OSAX("StandardAdditions", name = "System Events")
        sa.activate()
        # The text below uses Unicode characters to produce bold text.
        sa.display_dialog('𝗭𝗼𝗶𝗻𝗸𝘀 𝗲𝗿𝗿𝗼𝗿:\n\n' + msg, buttons = ["OK"],
                          default_button = 'OK', with_icon = 0)


# Main entry point.
# .............................................................................

# The following entry point definition is for the console_scripts keyword
# option to setuptools. The entry point for console_scripts has to be a
# function that takes zero arguments.
def console_scripts_main():
    plac.call(main)

# The following allows users to invoke this using "python3 -m urial" and also
# pass it an argument of "help" to get the help text.
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'help':
        plac.call(main, ['-h'])
    else:
        plac.call(main)


# For Emacs users
# .............................................................................
# Local Variables:
# mode: python
# python-indent-offset: 4
# End:
