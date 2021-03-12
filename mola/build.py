"""
Module to build a concrete model from a Specification object
"""
import json
from tempfile import NamedTemporaryFile
import re
import importlib

import pandas as pd
from pyomo.environ import units as pu

import mola.utils as mu


def get_config(json_file_name):
    """
    Returns a well-formed model configuration dictionary from json_file_name by
    ensuring that parameters and indexed sets are rebuilt from sets.

    :param json_file_name: path to json configuration file
    :return: config dict
    """

    # load json configuration file
    with open(str(json_file_name)) as jf:
        config = json.load(jf)

    # get the default sets and parameters from the specification
    spec = create_specification(config['specification'])
    sets = spec.get_default_sets()

    # update defaults with saved sets
    sets.update(config['sets'])

    # Update indexed_sets and parameters with new sets and save index sets and parameters to ensure consistency
    indexed_sets = spec.get_default_indexed_sets(sets)
    parameters = spec.get_default_parameters(sets)
    if 'indexed_sets' in config:
        indexed_sets.update(config['indexed_sets'])
    parameters.update(config['parameters'])

    # copy back to config dict
    config['sets'] = sets
    config['indexed_sets'] = indexed_sets
    config['parameters'] = parameters

    return config


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

    # write out temp json files for sets, indexed sets and parameters for DataPortal
    sets_json = NamedTemporaryFile(suffix='.json', delete=False)
    indexed_sets_json = NamedTemporaryFile(suffix='.json', delete=False)
    parameters_json = NamedTemporaryFile(suffix='.json', delete=False)
    json_list = [sets_json.name, parameters_json.name]
    with open(sets_json.name, 'w') as fp:
        json.dump(config['sets'], fp)
    if 'indexed_sets' in config and len(config['indexed_sets']) > 0:
        with open(indexed_sets_json.name, 'w') as fp:
            json.dump(config['indexed_sets'], fp)
        json_list.append(indexed_sets_json.name)
    with open(parameters_json.name, 'w') as fp:
        json.dump(config['parameters'], fp)

    sets_json.close()
    indexed_sets_json.close()
    parameters_json.close()

    # populate sets and parameters using DataPortal and temp files
    concrete_model = spec.populate(json_list)


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


def build_parameters(sets, parameters, spec, index_value=False, indexed_sets=dict()):
    """
    Build a dictionary of DataFrames of default parameters from sets using existing parameter values.

    :param dict sets: sets for optimisation
    :param dict parameters: parameters
    :param Specification spec: Specification object
    :param boolean index_value: return output in index-value form
    :param dict indexed_sets: indexed sets for optimisation
    :return: dict of DataFrames or dict of index-value dicts
    """
    par = {}
    default_parameters = spec.get_default_parameters(sets, user_indexed_sets=indexed_sets)
    for p, element_list in default_parameters.items():
        print(p + ': ' + spec.user_defined_parameters[p]['doc'])
        if 'index' in spec.user_defined_parameters[p]:
            row_list = []
            for el in element_list:
                v = el['value']
                # update if parameter was already defined
                if p in parameters:
                    for item in parameters[p]:
                        if item['index'] == el['index']:
                            v = item['value']
                new_row = pd.DataFrame({'Index': [el['index']], 'Value': v}, index=[0])
                row_list.append(new_row)
            if len(row_list) > 0:
                par[p] = pd.concat(row_list, ignore_index=True)
            else:
                par[p] = pd.DataFrame({'Index': [], 'Value': []})
        else:
            par[p] = pd.DataFrame([parameters[p]], columns=['Value'])
    if index_value:
        par = mu.get_index_value(par)

    return par


def build_indexed_sets(sets, indexed_sets, spec):
    """
    Build a dictionary of DataFrames of default parameters from sets using existing indexed set members.
    Indexed sets are currently stored as dicts which means there can be only one indexing set.

    :param dict sets: sets for optimisation
    :param dict indexed_sets: parameters
    :param Specification spec: Specification object
    :return: dict of DataFrames
    """
    ind_sets = {}
    for default_set, default_dict in spec.get_default_indexed_sets(sets).items():
        if 'within' in spec.user_defined_indexed_sets[default_set]:
            within = spec.user_defined_indexed_sets[default_set]['within'][0]
        else:
            within = None
        row_list = []
        print(default_set + ': ' + spec.user_defined_indexed_sets[default_set]['doc'])
        for ind, members in default_dict.items():
            m = members
            # update members if indexed set was already defined as long as it respects domain
            if default_set in indexed_sets:
                for k, v in indexed_sets[default_set].items():
                    if k == ind:
                        m = set(v)
                        if within:
                            m = list(set(sets[within]).intersection(m))
            new_row = pd.DataFrame({'Index': [ind], 'Members': [m]}, index=[0])
            row_list.append(new_row)
        if len(row_list) > 0:
            ind_sets[default_set] = pd.concat(row_list, ignore_index=True)
        else:
            ind_sets[default_set] = pd.DataFrame({'Index': [], 'Members': []})

    return ind_sets


def map_units(unit=None):
    """
    A dictionary that maps openLCA database units for product flows to pyomo units.

    :return: dict or pyomo unit object
    """
    d = {
        'h': pu.hour,
        'ha': pu.ha,
        'kg': pu.kg,
        'kg*d': pu.kg*pu.day,
        'kg*km': pu.kg*pu.km,
        'KWh': pu.kWh,
        'm3': pu.m**3,
        'MJ': pu.MJ,
        'kBq': pu.kiloBq,
        'l': pu.l,
        'm2': pu.m,
        'm*a': pu.m*pu.year,
        'm2*a': pu.m**2*pu.year,
        'm3*a': pu.m**3*pu.year,
        'Item(s)': pu.count,
        'd': pu.day,
        'kg*a': pu.kg*pu.year,
        't*km': pu.tonne*pu.km,
        'm': pu.meter,
        'km': pu.km,
        'km2*a': pu.km**2*pu.year,
        'p*km': pu.count*pu.km,
        'm*a': pu.m*pu.year,
    }

    if unit is None:
        return d
    else:
        return d[unit]



