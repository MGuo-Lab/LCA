"""
Module for creating sets and parameters on a notebook.
"""
import pandas as pd
from pathlib import Path
import json


def get_model_user_sets(spec, file_name):
    """
    Load json from model file and updates with defaults then saves to json file.

    :param spec: model specification
    :param file_name: name of sets file
    :return: dict
    """
    model_json_path = Path(file_name)
    set_data = spec.get_default_sets()
    if model_json_path.is_file():
        with open(model_json_path) as p:
            user_data = json.load(p)
            set_data.update(user_data)

    with open(model_json_path, 'w') as p:
        json.dump(set_data, p, indent=4)
    print("Model sets saved")

    return set_data


def get_model_user_parameters(spec, set_data, parameter_file_name, param_list=['Total_Demand', 'C', 'd']):
    """
    Create a DataFrame of parameters using set_data and old parameter file.
    :param spec: model specification
    :param set_data: set data
    :param parameter_file_name: parameter file name
    :return: DataFrame, dict
    """

    # get default parameter data based on current sets
    parameter_data = spec.get_default_parameters(set_data)

    # get current parameters
    current_parameter_data = {}
    model_json_path = Path(parameter_file_name)
    if model_json_path.is_file():
        with open(model_json_path) as fp:
            current_parameter_data.update(json.load(fp))

    # build DataFrame of default parameters
    param_dfr = pd.DataFrame({'Parameter': [], 'Description': [], 'Index': [], 'Value': []})
    for p, element_list in parameter_data.items():
        for el in element_list:
            v = el['value']
            # update if parameter was already defined
            if p in current_parameter_data:
                for item in current_parameter_data[p]:
                    if item['index'] == el['index']:
                        v = item['value']
            new_row = pd.DataFrame({'Parameter': p, 'Description': spec.user_defined_parameters[p]['doc'],
                                    'Index': [el['index']], 'Value': v}, index=[0])
            param_dfr = param_dfr.append(new_row, ignore_index=True)

    # update with existing parameters and save
    # model_json_path = Path(parameter_file_name)
    # if model_json_path.is_file():
    #     with open(model_json_path) as p:
    #         parameter_data.update(json.load(p))
    # with open(model_json_path, 'w') as p:
    #     json.dump(parameter_data, p)
    #     print("New model parameters saved")

    # create a DataFrame of parameters reflecting the current sets
    # param_dfr = pd.DataFrame({'Parameter': [], 'Description': [], 'Index': [], 'Value': []})
    # for p, v in spec.user_defined_parameters.items():
    #     if p in param_list:
    #         index_sets = [set_data[s] for s in v['index']]
    #         elements = list(itertools.product(*index_sets))
    #         for el in elements:
    #             print(p, v['doc'], el, parameter_data[p])

    # update DataFrame to reflect existing parameters

    return param_dfr, current_parameter_data


# def get_entity(instance, name):
#     """ Retrieve values (or duals) for an entity in a model instance.
#
#     Args:
#         instance: a Pyomo ConcreteModel instance
#         name: name of a Set, Param, Var, Constraint or Objective
#
#     Returns:
#         a Pandas Series with domain as index and values (or 1's, for sets) of
#         entity name. For constraints, it retrieves the dual values
#     """
#     # magic: short-circuit if problem contains a result cache
#     if hasattr(instance, '_result') and name in instance._result:
#         return instance._result[name].copy(deep=True)
#
#     # retrieve entity, its type and its onset names
#     try:
#         entity = instance.__getattribute__(name)
#         labels = _get_onset_names(entity)
#     except AttributeError:
#         return pd.Series(name=name)
#
#     # extract values
#     if isinstance(entity, pyomo.Set):
#         if entity.dimen > 1:
#             results = pd.DataFrame([v + (1,) for v in entity.data()])
#         else:
#             # Pyomo sets don't have values, only elements
#             results = pd.DataFrame([(v, 1) for v in entity.data()])
#
#         # for unconstrained sets, the column label is identical to their index
#         # hence, make index equal to entity name and append underscore to name
#         # (=the later column title) to preserve identical index names for both
#         # unconstrained supersets
#         if not labels:
#             labels = [name]
#             name = name + '_'
#
#     elif isinstance(entity, pyomo.Param):
#         if entity.dim() > 1:
#             results = pd.DataFrame(
#                 [v[0] + (v[1],) for v in entity.iteritems()])
#         elif entity.dim() == 1:
#             results = pd.DataFrame(
#                 [(v[0], v[1]) for v in entity.iteritems()])
#         else:
#             results = pd.DataFrame(
#                 [(v[0], v[1].value) for v in entity.iteritems()])
#             labels = ['None']
#
#     elif isinstance(entity, pyomo.Expression):
#         if entity.dim() > 1:
#             results = pd.DataFrame(
#                 [v[0] + (v[1](),) for v in entity.iteritems()])
#         elif entity.dim() == 1:
#             results = pd.DataFrame(
#                 [(v[0], v[1]()) for v in entity.iteritems()])
#         else:
#             results = pd.DataFrame(
#                 [(v[0], v[1]()) for v in entity.iteritems()])
#             labels = ['None']
#
#     elif isinstance(entity, pyomo.Constraint):
#         if entity.dim() > 1:
#             # check whether all entries of the constraint have
#             # an existing dual variable
#             # in that case add to results
#             results = pd.DataFrame(
#                 [key + (instance.dual[entity.__getitem__(key)],)
#                  for (id, key) in entity.id_index_map().items()
#                  if id in instance.dual._dict.keys()])
#         elif entity.dim() == 1:
#             results = pd.DataFrame(
#                 [(v[0], instance.dual[v[1]]) for v in entity.iteritems()])
#         else:
#             results = pd.DataFrame(
#                 [(v[0], instance.dual[v[1]]) for v in entity.iteritems()])
#             labels = ['None']
#
#     else:
#         # create DataFrame
#         if entity.dim() > 1:
#             # concatenate index tuples with value if entity has
#             # multidimensional indices v[0]
#             results = pd.DataFrame(
#                 [v[0] + (v[1].value,) for v in entity.iteritems()])
#         elif entity.dim() == 1:
#             # otherwise, create tuple from scalar index v[0]
#             results = pd.DataFrame(
#                 [(v[0], v[1].value) for v in entity.iteritems()])
#         else:
#             # assert(entity.dim() == 0)
#             results = pd.DataFrame(
#                 [(v[0], v[1].value) for v in entity.iteritems()])
#             labels = ['None']
#
#     # check for duplicate onset names and append one to several "_" to make
#     # them unique, e.g. ['sit', 'sit', 'com'] becomes ['sit', 'sit_', 'com']
#     for k, label in enumerate(labels):
#         if label in labels[:k] or label == name:
#             labels[k] = labels[k] + "_"
#
#     if not results.empty:
#         # name columns according to labels + entity name
#         results.columns = labels + [name]
#         results.set_index(labels, inplace=True)
#
#         # convert to Series
#         results = results[name]
#     else:
#         # return empty Series
#         results = pd.Series(name=name)
#     return results


# def get_entities(instance, names):
#     """ Return one DataFrame with entities in columns and a common index.
#
#     Works only on entities that share a common domain (set or set_tuple), which
#     is used as index of the returned DataFrame.
#
#     Args:
#         instance: a Pyomo ConcreteModel instance
#         names: list of entity names (as returned by list_entities)
#
#     Returns:
#         a Pandas DataFrame with entities as columns and domains as index
#     """
#
#     df = pd.DataFrame()
#     for name in names:
#         other = get_entity(instance, name)
#
#         if df.empty:
#             df = other.to_frame()
#         else:
#             index_names_before = df.index.names
#
#             df = df.join(other, how='outer')
#
#             if index_names_before != df.index.names:
#                 df.index.names = index_names_before
#
#     return df


# def list_entities(instance, entity_type):
#     """ Return list of sets, params, variables, constraints or objectives
#
#     Args:
#         instance: a Pyomo ConcreteModel object
#         entity_type: "set", "par", "var", "con" or "obj"
#
#     Returns:
#         DataFrame of entities
#
#     """
#
#     # helper function to discern entities by type
#     def filter_by_type(entity, entity_type):
#         if entity_type == 'set':
#             return isinstance(entity, pyomo.Set)
#         elif entity_type == 'par':
#             return isinstance(entity, pyomo.Param)
#         elif entity_type == 'var':
#             return isinstance(entity, pyomo.Var)
#         elif entity_type == 'con':
#             return isinstance(entity, pyomo.Constraint)
#         elif entity_type == 'obj':
#             return isinstance(entity, pyomo.Objective)
#         elif entity_type == 'exp':
#             return isinstance(entity, pyomo.Expression)
#         else:
#             raise ValueError("Unknown entity_type '{}'".format(entity_type))
#
#     # create entity iterator, using a python 2 and 3 compatible idiom:
#     # http://python3porting.com/differences.html#index-6
#     try:
#         iter_entities = instance.__dict__.iteritems()  # Python 2 compat
#     except AttributeError:
#         iter_entities = instance.__dict__.items()  # Python way
#
#     # now iterate over all entities and keep only those whose type matches
#     entities = sorted(
#         (name, entity.doc, _get_onset_names(entity))
#         for (name, entity) in iter_entities
#         if filter_by_type(entity, entity_type))
#
#     # if something was found, wrap tuples in DataFrame, otherwise return empty
#     if entities:
#         entities = pd.DataFrame(entities,
#                                 columns=['Name', 'Description', 'Domain'])
#         entities.set_index('Name', inplace=True)
#     else:
#         entities = pd.DataFrame()
#     return entities


# def _get_onset_names(entity):
#     """ Return a list of domain set names for a given model entity
#
#     Args:
#         entity: a member entity (i.e. a Set, Param, Var, Objective, Constraint)
#                 of a Pyomo ConcreteModel object
#
#     Returns:
#         list of domain set names for that entity
#
#     """
#     # get column titles for entities from domain set names
#     labels = []
#
#     if isinstance(entity, pyomo.Set):
#         if isinstance(entity.dimen, int) and entity.dimen > 1:
#             # N-dimensional set tuples, possibly with nested set tuples within
#             if entity.domain:
#                 # retrieve list of domain sets, which itself could be nested
#                 domains = entity.domain.subsets(expand_all_set_operators=True)
#             else:
#                 try:
#                     # if no domain attribute exists, some
#                     domains = entity.set_tuple
#                 except AttributeError:
#                     # if that fails, too, a constructed (union, difference,
#                     # intersection, ...) set exists. In that case, the
#                     # attribute _setA holds the domain for the base set
#                     try:
#                         domains = entity._setA.domain.set_tuple
#                     except AttributeError:
#                         # if that fails, too, a constructed (union, difference,
#                         # intersection, ...) set exists. In that case, the
#                         # attribute _setB holds the domain for the base set
#                         domains = entity._setB.domain.set_tuple
#
#             for domain_set in domains:
#                 labels.extend(_get_onset_names(domain_set))
#
#         elif isinstance(entity.dimen, int) and entity.dimen == 1:
#             if hasattr(entity, 'domain'):
#                 # 1D subset; add domain name
#                 labels.append(entity.domain.name)
#             else:
#                 # unrestricted set; add entity name
#                 labels.append(entity.name)
#         else:
#             # no domain, so no labels needed
#             pass
#
#     elif isinstance(entity, (pyomo.Param, pyomo.Var, pyomo.Expression,
#                              pyomo.Constraint, pyomo.Objective)):
#         if isinstance(entity.dim(), int) and entity.dim() > 0 and entity._index:
#             labels = _get_onset_names(entity._index)
#         else:
#             # zero dimensions, so no onset labels
#             pass
#
#     else:
#         raise ValueError("Unknown entity type!")
#
#     return labels


