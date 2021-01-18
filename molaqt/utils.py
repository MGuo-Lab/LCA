from pathlib import Path
import json

import mola.utils as mu


def get_new_config(specification_class, database_path, doc_path):
    new_config = {
        'settings': {},
        'doc_path': str(doc_path),
        'specification': str(specification_class),
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


def build_config(config_path):
    """
    Ensure that a model configuration file has defaults populated.
    :param config_path: path to configuration file
    :return: configuration dict
    """
    with open(str(config_path)) as fp:
        config = json.load(fp)

    # load specification from config file
    spec = mu.create_specification(config['specification'])

    sets = spec.get_default_sets()
    sets.update(config['sets'])
    config['sets'] = sets
    parameters = spec.get_default_parameters(config['sets'])
    config['parameters'].update(parameters)

    return config
