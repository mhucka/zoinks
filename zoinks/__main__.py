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
    '''
Zoinks accept one or more Zotero record identifiers together with zero or more
field names, and prints the values of the field names on the standard output.
If no field names are supplied, it prints all the field values it can find for
each record.

Zoinks requires Zotero to be running and have the Better BibTeX (BBT) extension
installed, or it will exit with an error message.

Identifying the desired Zotero records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zoinks understands the following forms of Zotero record identifiers:

  * Zotero item keys (8 character alphanumeric sequences such as "WCKIQ23Y")
  * Zotero select links (of the form "zotero://select/library/items/WCKIQ23Y")
  * Citekeys (as managed by Better BibTeX) with leading '@' characters

Identifiers can be supplied in any of the following ways:

  * via standard input (e.g., from a shell pipe)
  * from the clipboard (by using the value "clipboard" to the --source option)
  * from a file (by using a file path as the value to the --source option)

Here are some examples:

  echo WCKIQ23Y | zoinks
  echo @Smith2018 | zoinks
  echo zotero://select/library/items/WCKIQ23Y | zoinks
  zoinks --source clipboard
  zoinks --source /tmp/zotero-identifiers.txt

Important: Zoinks assumes that if more than one identifier is provided, all of
the identifiers will have the same form. That is, if a Zotero select link is
provided, then all the identifiers must be in the form of Zotero select links;
if citekeys are provided, all the inputs must be citekeys; and so on.

Specifying the field value(s) to be printed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The field(s) whose value(s) is (are) to be printed can be named as arguments to
Zoinks on the command. For example, the following command will print the title
of the work identified by the given Zotero select link:

  echo zotero://select/library/items/WCKIQ23Y | zoinks title

To find out all the fields that are available, using the --list-fields option:

  echo zotero://select/library/items/WCKIQ23Y | zoinks --list-fields

If a single field value is requested, the value will be printed alone. If more
than one field value is requested, each value in the output will be prefixed
by the name of the field.  For example, the command

  echo WCKIQ23Y | zoinks title

might produce

  IFLA Position on Controlled Digital Lending

and the command

  echo WCKIQ23Y | zoinks title date

might produce

  title: IFLA Position on Controlled Digital Lending
  date: 2021

If you do not name one or more fields on the command line, Zoinks will print
all the fields returned by Better BibTeX for a given record. (Technically,
the output will be equivalent to the "jzon" [sic] format provided by BBT.)

Additional command-line arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zoinks will use GUI dialogs for error messages, unless the --no-gui option is
given, in which case it will print messages on standard output.

If given the -V option, this program will print the version and other
information, and exit without doing anything else.

If given the -@ argument, this program will output a detailed trace of what it
is doing. The debug trace will be sent to the given destination, which can
be '-' to indicate console output, or a file path to send the output to a file.

Return values
~~~~~~~~~~~~~

This program exits with a return code of 0 if no problems are encountered.
It returns a nonzero value otherwise. The following table lists the possible
return values:

  0 = success -- program completed normally
  1 = the user interrupted the program's execution
  2 = encountered a bad or missing value for an option
  3 = encountered a problem with a file or directory
  4 = encountered a problem communicating with Zotero or Better BibTeX
  5 = a miscellaneous exception or fatal error occurred

Command-line arguments summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

    # Define shortcut functions for common user feedback actions.
    def alert(msg): inform(msg, no_gui)
    def stop(msg, err = ExitCode.exception): inform(msg, no_gui); sys.exit(int(err))

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
    item_keys = [item_key(id) for id in identifiers]

    if not bbt_running():
        stop('Zotero or Better BibTeX service does not appear to be running.',
             ExitCode.zotero_error)

    # Do the real work --------------------------------------------------------

    try:
        log(f'input from source ' + source + ': ' + ', '.join(identifiers))
        # BBT's JSON-RPC interface needs citation keys. If that's not what the
        # user supplied, start by getting the citation keys from BBT.
        if any(key.startswith('@') for key in item_keys):
            bare_keys = [key.lstrip('@') for key in item_keys]
            mapping = CaseFoldDict(zip(identifiers, bare_keys))
        else:
            log('need to retrieve citation keys from BBT')
            mapping = bbt_rpc('item.citationkey', [item_keys])

        single_record = (len(mapping) == 1)
        single_field  = (len(fields) == 1)

        # If we're only getting citation keys, print them & exit.
        if single_field and fields[0] in ['citationkey', 'citekey']:
            log('user requested only citation keys')
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
    import json

    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    data = json.dumps({'jsonrpc': '2.0', 'method': method, 'params': params})
    log('asking BBT about ' + str(params))
    (response, error) = net('post', _BBT_JSON_RPC, headers = headers, data = data)
    if error:
        raise ConnectionFailure('Better BibTeX API error: ' + str(error))
    result_dict = json.loads(response.text)
    if 'error' in result_dict:
        raise ZoinksError('BBT error: ' + result_dict['error']['message'])
    if 'result' in result_dict:
        payload = result_dict['result']
        if isinstance(payload, list) and isinstance(payload[0], int):
            log('payload is a list; pulling out 3rd element')
            payload = json.loads(payload[2])
        if 'items' in payload:
            log('got items in payload')
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

# The following allows users to invoke this using "python3 -m zoinks" and also
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
