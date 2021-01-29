"""
Module to build a concrete model from a Specification object
"""
import json
from tempfile import NamedTemporaryFile
import re
import importlib

import pandas as pd
from pyomo.environ import units as pu


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


def map_reference_units():
    """
    A dictionary that maps openLCA reference database units for product flows to pyomo units.

    :return: dict
    """

    d = {
       'kg': pu.kg,
        'm3': pu.m**3,
        'MJ': pu.MJ,
        'kBq': pu.kiloBq,
        'm2': pu.m,
        'm2*a': pu.m**2*pu.year,
        'm3*a': pu.m**3*pu.year,
        'Item(s)': pu.count,
        'd': pu.day,
        'kg*a': pu.kg*pu.year,
        't*km': pu.tonne*pu.km,
        'm': pu.meter,
        'p*km': pu.count*pu.km,
        'm*a': pu.m*pu.year,
    }

    return d



