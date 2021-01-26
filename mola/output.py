"""
Convert pyomo output to DataFrames
"""
import pandas as pd
import pyomo.environ as pe
import mola.dataview as dv
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
def get_entity(cpt, lookup=dict(), drop=False):
    print('Type not supported')


@get_entity.register(pe.pyomo.core.base.var.IndexedVar)
@get_entity.register(pe.pyomo.core.base.param.IndexedParam)
def _(cpt, lookup=dict(), drop=False, units=None):
    v = cpt.extract_values()
    idx = cpt._index

    s = pd.Series(v)
    s.index.names = [j.name for j in idx.subsets()]
    df = pd.DataFrame(s, columns=[cpt.name])

    # join text onto table from lookup
    for pyo_set in idx.subsets():
        if pyo_set.name in lookup:
            set_content = lookup.get_single_column(pyo_set.name)
            set_content.index.names = [pyo_set.name]
            df = df.join(set_content)

    if units:
        process_ref_ids = df.index.get_level_values(units[0]).to_list()
        units_dfr = lookup.get_units(process_ref_ids, set_name=units[0])
        df = df.merge(units_dfr, left_index=True, right_index=True)

    if drop:
        df = df.reset_index(drop=drop)

    return df


