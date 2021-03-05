"""
Utility functions for mola
"""
import pandas as pd
import json


def get_index_value(df_dict, value_key='value'):
    """
    Turn dict of DataFrames into a dict of lists of index value dicts.

    :param dict df_dict: dictionary of DataFrames
    :param str value_key: name of value key in dicts
    :return: dict
    """
    def f(g): return {'index': g[0], value_key: g[1]}
    d = {k: list(df.apply(f, axis=1)) for k, df in df_dict.items() if len(df) > 0}
    return d


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


class Package:
    """
    Package settings
    """

    __conf = {
        'show.SQL': True,
    }
    __setters = ["show.SQL"]

    @staticmethod
    def config(name):
        return Package.__conf[name]

    @staticmethod
    def set(name, value):
        if name in Package.__setters:
            Package.__conf[name] = value
        else:
            raise NameError("Name not accepted in set() method")
