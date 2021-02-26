"""
Convert pyomo output to DataFrames
"""
import sys
import pandas as pd
import pyomo.environ as pe
from functools import singledispatch

# TODO remove the unneeded large database sets that affect performance here
def get_sets_frame(model_instance, active=None):
    sets_df = pd.DataFrame(
        ([o.name, o.doc, [], len(o)] for o in model_instance.component_objects(pe.Set, active=active)),
        columns=['Set', 'Description', 'Index', 'Number of elements']
    )

    return sets_df


def get_parameters_frame(model_instance, max_object_size=100, active=None):
    param_df = pd.DataFrame(
        ([o.name, o.doc, len(o), [index for index in o], [pe.value(o[index]) for index in o]] for o in
         model_instance.component_objects(pe.Param, active=active) if len(o) <= max_object_size),
        columns=['Param', 'Description', 'Number of elements', 'Index', 'Value']
    )

    return param_df


def get_constraints_frame(model_instance, explode=False, active=None):
    constraints_df = pd.DataFrame(
        ([o.name, [index for index in o], [str(o[index].expr) for index in o]] for o in
         model_instance.component_objects(pe.Constraint, active=active)),
        columns=['Constraint', 'Index', 'Expression']
    )
    if explode:
        constraints_df = constraints_df.set_index(['Constraint']).apply(pd.Series.explode).reset_index()

    return constraints_df


def get_objectives_frame(model_instance, explode=False, active=None):
    objectives_df = pd.DataFrame(
        ([o.name, [index for index in o], [str(o[index].expr) for index in o]] for o in
         model_instance.component_objects(pe.Objective, active=active)),
        columns=['Objective', 'Index', 'Expression']
    )
    if explode:
        objectives_df = objectives_df.set_index(['Objective']).apply(pd.Series.explode).reset_index()

    return objectives_df


@singledispatch
def get_entity(cpt, lookup=dict(), drop_index=True, units=None, non_zero=False, distinct_levels=False):
    sys.exit('Type not supported')


@get_entity.register(pe.pyomo.core.base.var.IndexedVar)
@get_entity.register(pe.pyomo.core.base.param.IndexedParam)
def _(cpt, lookup=dict(), drop_index=True, units=None, non_zero=False, distinct_levels=False):
    v = cpt.extract_values()
    if len(v) == 0:
        return pd.DataFrame()

    s = pd.Series(v)
    s.index.names = get_onset_names(cpt)
    df = pd.DataFrame(s, columns=[cpt.name])

    if units:
        if type(units) == bool:
            u = str(cpt.get_units())
        else:
            u = units[0]
        if u in df.index.names:
            process_ref_ids = df.index.get_level_values(u).to_list()
            units_dfr = lookup.get_units(process_ref_ids, set_name=u)
            df = df.merge(units_dfr, left_index=True, right_index=True)

    # join text from index onto table
    for pyo_set in s.index.names:
        if not distinct_levels or len(df.index.get_level_values(pyo_set).unique()) > 1:
            if pyo_set in lookup:
                set_content = lookup.get_single_column(pyo_set)
                set_content.index.names = [pyo_set]
                df = df.join(set_content)
            else:
                col_names = df.columns.to_list() + [pyo_set]
                df = df.reset_index(pyo_set, drop=False).reindex(col_names, axis=1)

    if drop_index:
        df = df.reset_index(drop=drop_index)

    if non_zero:
        numeric_cols = set(df.select_dtypes('number').columns) - set(s.index.names)
        df = df[(df[numeric_cols] > 0).any(axis=1)]

    return df


@get_entity.register(pe.pyomo.core.base.objective.IndexedObjective)
def _(cpt, lookup=dict(), drop_index=True, units=None):
    # TODO: this only does simple indexes for now
    idx = cpt._index
    s = pd.Series({i: pe.value(cpt[i]) for i in idx})
    s.index.names = [j.name for j in idx.subsets()]
    df = pd.DataFrame(s, columns=[cpt.name])

    if units:
        if type(units) == bool:
            u = s.index.names[0]
        else:
            u = units[0]
        if u in s.index.names:
            ref_ids = df.index.get_level_values(u).to_list()
            units_dfr = lookup.get(u, ref_ids)[['Unit']]
            df = df.merge(units_dfr, left_index=True, right_index=True)

    if drop_index:
        df = df.reset_index(drop=drop_index)

    return df


@get_entity.register(pe.pyomo.core.base.objective.Objective)
def _(cpt, lookup=dict(), units=None):

    try:
        v = pe.value(cpt)
    except ValueError as e:
        print(e)
        v = None
    df = pd.DataFrame({'Objective': v}, index=[0])

    return df


@singledispatch
def get_onset_names(entity):
    """
    Return a list of domain set names for a given model entity.
    Modified from https://raw.githubusercontent.com/tum-ens/urbs/master/urbs/pyomoio.py
    to use generics.

    :param entity: a member entity (i.e. a Set, Param, Var, Objective, Constraint) of
     a Pyomo ConcreteModel object
    :return: list of domain set names for that entity
    :examples:
    """
    sys.exit('Type not supported')


@get_onset_names.register(pe.pyomo.core.base.set.Set)
def _(entity):
    # get column titles for entities from domain set names
    labels = []

    if isinstance(entity.dimen, int) and entity.dimen > 1:
        # N-dimensional set tuples, possibly with nested set tuples within
        if entity.domain:
            # retrieve list of domain sets, which itself could be nested
            domains = entity.domain.subsets()
        else:
            try:
                # if no domain attribute exists, some
                domains = entity.set_tuple
            except AttributeError:
                # if that fails, too, a constructed (union, difference,
                # intersection, ...) set exists. In that case, the
                # attribute _setA holds the domain for the base set
                try:
                    domains = entity._setA.domain.set_tuple
                except AttributeError:
                    # if that fails, too, a constructed (union, difference,
                    # intersection, ...) set exists. In that case, the
                    # attribute _setB holds the domain for the base set
                    domains = entity._setB.domain.set_tuple

        for domain_set in domains:
            labels.extend(get_onset_names(domain_set))

    elif isinstance(entity.dimen, int) and entity.dimen == 1:
        # if entity.domain == 'Any':
        #     # 1D subset; add domain name
        #     labels.append(entity.domain.name)
        # else:
        # # unrestricted set; add entity name
        labels.append(entity.name)
    else:
        # no domain, so no labels needed
        pass

    return labels


@get_onset_names.register(pe.pyomo.core.base.Constraint)
@get_onset_names.register(pe.pyomo.core.base.Objective)
@get_onset_names.register(pe.pyomo.core.base.Var)
@get_onset_names.register(pe.pyomo.core.base.Param)
@get_onset_names.register(pe.pyomo.core.base.Expression)
def _(entity):
    # get column titles for entities from domain set names
    labels = []

    if isinstance(entity.dim(), int) and entity.dim() > 0 and entity._index:
        labels = get_onset_names(entity._index)
    else:
        # zero dimensions, so no onset labels
        pass

    return labels
