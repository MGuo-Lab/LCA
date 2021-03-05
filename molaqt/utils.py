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


# TODO: remove this and use mola version?
def get_config(json_file_name, testing=True):
    setting = system_settings(testing=testing)
    config_path = setting['config_path'].joinpath(json_file_name)

    # load configuration file
    with open(str(config_path)) as jf:
        model_config = json.load(jf)

    spec = mb.create_specification(model_config['specification'])

    return model_config, spec


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

# TODO: use this function in the main app rather than just for testing? or move this to testing folder
def build_config(config_path):
    """
    Ensure that a model configuration file has defaults populated.
    :param config_path: path to configuration file
    :return: configuration dict
    """
    with open(str(config_path)) as fp:
        config = json.load(fp)

    # load specification from config file
    spec = mb.create_specification(config['specification'])

    # merge defaults into config then replace config
    sets = spec.get_default_sets()
    sets.update(config['sets'])
    config['sets'] = sets

    indexed_sets = spec.get_default_indexed_sets(config['sets'])
    if 'indexed_sets' in config:
        indexed_sets.update(config['indexed_sets'])
    config['indexed_sets'] = indexed_sets

    parameters = spec.get_default_parameters(config['sets'])
    parameters.update(config['parameters'])
    config['parameters'] = parameters

    return config


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
