from pathlib import Path
import json

import pandas as pd

import mola.build as mb


def get_new_config(specification_class, database_path, doc_file, controller_class):
    new_config = {
        'settings': {},
        'doc_path': doc_file,
        'specification': str(specification_class),
        'controller': str(controller_class),
        'db_file': str(database_path),
        'sets': [],
        'parameters': [],
    }
    return new_config


def system_settings(development=False, testing=False):
    d = dict()
    d['app_name'] = 'molaqt'
    d['package_path'] = Path('.')
    d['home_path'] = Path.home().joinpath(d['app_name'])
    d['home_path'].mkdir(parents=True, exist_ok=True)
    d['data_path'] = Path('C:/data/openlca/sqlite/system')
    if testing:
        d['config_path'] = Path('../../config/')
        d['doc_path'] = Path('../../molaqt/doc/')
        d['package_path'] = Path('..')
    elif development:
        d['config_path'] = Path('../config/')
        d['doc_path'] = Path('../molaqt/doc/')
    else:
        d['config_path'] = d['home_path'].joinpath('config')
        d['config_path'].mkdir(parents=True, exist_ok=True)
        d['doc_path'] = d['home_path'].joinpath('doc')
        d['doc_path'].mkdir(parents=True, exist_ok=True)

    return d


def chunker(seq, size):
    for pos in range(0, len(seq), size):
        yield seq.iloc[pos:pos + size]


def ref_id_to_text(index_sets, ref_id, spec, lookup):
    """
    Convert a list of ref ids tuples from a parameter to text via lookup tables.
    :param list[str] index_sets: index set names
    :param list ref_id: ref id tuples
    :param Specification spec: object
    :param LookupTables lookup: object
    :return: DataFrame
    """

    df = pd.DataFrame(ref_id, columns=index_sets)
    lookup_sets = [n for n, d in spec.user_defined_sets.items() if 'lookup' in d and d['lookup']]
    for k in index_sets:
        if k in lookup_sets and k in lookup:
            df[k] = df[k].map(lookup.get_single_column(k)[k])

    return df
