"""
Convert pyomo output to DataFrames
"""
import sys
import pandas as pd
import pyomo.environ as pe
from functools import singledispatch


def get_sets_frame(model_instance):
    sets_dfr = pd.DataFrame(
        ([v.name, v.doc, len(v)] for v in model_instance.component_objects(pe.Set, active=True)),
        columns=['Set', 'Description', 'Number of elements']
    )

    return sets_dfr


def get_parameters_frame(model_instance, max_object_size=100):
    param_df = pd.DataFrame(
        ([o.name, o.doc, len(o), [index for index in o], [pe.value(o[index]) for index in o]] for o in
         model_instance.component_objects(pe.Param, active=True) if len(o) <= max_object_size),
        columns=['Param', 'Description', 'Number of elements', 'Dimension', 'Value']
    )

    return param_df


def get_constraints_frame(model_instance, max_object_size=100):
    constraints_df = pd.DataFrame(
        ([v.name, v.expr] for v in model_instance.component_data_objects(pe.Constraint, active=True)),
        columns=['Constraint', 'Expression']
    )

    return constraints_df


def get_objectives_frame(model_instance, max_object_size=100):
    objectives_df = pd.DataFrame(
        ([v.name, v.expr] for v in model_instance.component_data_objects(pe.Objective, active=True)),
        columns=['Objective', 'Expression']
    )

    return objectives_df


@singledispatch
def get_entity(cpt, drop_index=True, units=None, non_zero=False, distinct_levels=False):
    sys.exit('Type not supported')


@get_entity.register(pe.pyomo.core.base.var.IndexedVar)
@get_entity.register(pe.pyomo.core.base.param.IndexedParam)
def _(cpt, lookup=dict(), drop_index=True, units=None, non_zero=False, distinct_levels=False):
    v = cpt.extract_values()
    idx = cpt._index

    s = pd.Series(v)
    s.index.names = [j.name for j in idx.subsets()]
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
    for pyo_set in idx.subsets():
        if not distinct_levels or len(df.index.get_level_values(pyo_set.name).unique()) > 1:
            if pyo_set.name in lookup:
                set_content = lookup.get_single_column(pyo_set.name)
                set_content.index.names = [pyo_set.name]
                df = df.join(set_content)
            else:
                col_names = df.columns.to_list() + [pyo_set.name]
                df = df.reset_index(pyo_set.name, drop=False).reindex(col_names, axis=1)

    if drop_index:
        df = df.reset_index(drop=drop_index)

    if non_zero:
        numeric_cols = df.select_dtypes('number').columns
        df = df[(df[numeric_cols] > 0).any(axis=1)]

    return df


@get_entity.register(pe.pyomo.core.base.objective.IndexedObjective)
def _(cpt, lookup=dict(), drop_index=True, units=None):
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

