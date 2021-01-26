"""
Utility functions for mola
"""
import pandas as pd
import json
from tempfile import NamedTemporaryFile
import re
import importlib


def get_config(json_file_name):
    """
    Returns a well-formed model configuration dictionary from json_file_name by
    ensuring that parameters are rebuilt from sets.

    :param json_file_name: path to json configuration file
    :return: config dict
    """

    # load json configuration file
    with open(str(json_file_name)) as jf:
        config = json.load(jf)

    # get the default sets and parameters from the specification
    spec = create_specification(config['specification'])
    sets = spec.get_default_sets()
    parameters = spec.get_default_parameters(sets)

    # update defaults with saved sets and parameters to ensure consistency
    sets.update(config['sets'])
    parameters.update(config['parameters'])

    # copy back to config dict
    config['sets'] = sets
    config['parameters'] = parameters

    return config


def get_index_value_parameters(parameter_dict):
    """
    Turn dict of dataframes into a dict of lists of index value dicts
    :param parameter_dict:
    :return:
    """
    def f(g): return {'index': g[0], 'value': g[1]}
    param = {p: list(df.apply(f, axis=1)) for p, df in parameter_dict.items() if len(df) > 0}
    return param


def build_instance(config, settings=None):
    """
    Build a model instance from a configuration dictionary using configuration settings.

    The config dict contains a specification settings key, but these are the values on disk.
    The settings dict reflects updated settings in the current python session.
    :param config: dict of configuration data
    :param settings: dict of specification settings
    :return: concreteModel
    """
    # create a Specification object using configuration settings in config if settings is None
    if settings is None and 'settings' in config:
        settings = config['settings']
    spec = create_specification(config['specification'], settings)

    # write out temp json files for set and parameters for DataPortal
    sets_json = NamedTemporaryFile(suffix='.json', delete=False)
    parameters_json = NamedTemporaryFile(suffix='.json', delete=False)
    with open(sets_json.name, 'w') as fp:
        json.dump(config['sets'], fp)
    with open(parameters_json.name, 'w') as fp:
        json.dump(config['parameters'], fp)

    sets_json.close()
    parameters_json.close()

    # populate sets using DataPortal and temp files
    concrete_model = spec.populate([sets_json.name, parameters_json.name])

    return concrete_model


def create_specification(spec_class, settings=None):
    """
    Create a Specification object and update its configuration settings from
    its defaults.
    :param spec_class: name of class
    :param settings: dict of specification settings
    :return: Specification object
    """
    search = re.search("<class '(.*?)\.(.*?)\.(.*?)'>", spec_class)
    module_name = search.group(1) + '.' + search.group(2)
    class_name = search.group(3)
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    spec = class_()

    # update specification settings from stored configuration
    if settings is not None:
        for setting in settings:
            spec.settings[setting] = settings[setting]

    return spec


def unnest(df, explode):
    cols = df.columns.tolist()
    idx = df.index.repeat(df[explode[0]].str.len())
    df1 = pd.concat([pd.Series(sum(df[x].values, []), name=x) for x in explode], axis=1)
    df1.index = idx
    out_dfr = df1.join(df.drop(explode, 1), how='left')
    out_dfr = out_dfr[cols].reset_index(drop=True)

    return out_dfr


def make_config(sets_json, parameters_json, config_json='config/model_config.json'):
    with open(sets_json) as fp:
        sets = json.load(fp)
    with open(parameters_json) as fp:
        parameters = json.load(fp)

    config = {'sets': sets, 'parameters': parameters}
    with open(config_json, 'w') as fp:
        json.dump(config, fp)

    return config


def build_parameters(sets, parameters, spec):
    """
    Build a dictionary of DataFrames of default parameters from sets using existing parameter values
    :param sets: dict of sets
    :param spec: Specification object
    :param parameters: dict of parameters
    :return: dict
    """
    par = {}
    for p, element_list in spec.get_default_parameters(sets).items():
        row_list = []
        print(spec.user_defined_parameters[p]['doc'])
        for el in element_list:
            v = el['value']
            # update if parameter was already defined
            if p in parameters:
                for item in parameters[p]:
                    if item['index'] == el['index']:
                        v = item['value']
            # new_index = pd.DataFrame([el['index']], columns=spec.user_defined_parameters[p]['index'])
            # pd.MultiIndex.from_frame(new_index)
            new_row = pd.DataFrame({'Index': [el['index']], 'Value': v}, index=[0])
            row_list.append(new_row)
        if len(row_list) > 0:
            par[p] = pd.concat(row_list, ignore_index=True)
        else:
            par[p] = pd.DataFrame({'Index': [], 'Value': []})

    return par
