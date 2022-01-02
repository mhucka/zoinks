'''
unused.py: currently unused code, kept in case it becomes useful in the future
'''

def bbt_export(ckey):
    '''Call the BBT export interface and return the results.

    This takes a single BBT citation key.
    It returns a tuple: (json dict, error).
    The value of error will be None if no error occurred, else a string.
    '''
    from commonpy.network_utils import net
    from commonpy.exceptions import Interrupted
    import json

    url = _BBT_ENDPOINT + '/export/item?translator=jzon&citationKeys=' + ckey
    (response, error) = net('get', url)
    if error is None:
        results = json.loads(response.text)
        if 'error' in results.keys():
            return [], results['error']['message']
        if len(results['items']) > 1:
            log(f'got more than one record for {ckey}; keeping only 1st')
        return results['items'][0], None
    else:
        return [], str(error)

