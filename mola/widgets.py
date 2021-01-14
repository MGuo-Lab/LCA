import pandas as pd, IPython.display as d, ipywidgets as widgets
import mola.utils as mu
from pathlib import Path
import qgrid
import functools
import json


def get_set(dfr):
    """
    Widget to populate a single set.
    :param dfr: Dataframe of set contents
    :return: qgrid widget
    """
    in_df = dfr
    in_qg = qgrid.show_grid(in_df, grid_options={'maxVisibleRows': 10})
    out_df = pd.DataFrame()
    out_qg = qgrid.show_grid(out_df, grid_options={'maxVisibleRows': 10})
    button1 = widgets.Button(description='Add to set')
    button2 = widgets.Button(description='Remove from set')

    def on_button_clicked1(b):
        df = out_qg.df.append(in_qg.get_selected_df())
        out_qg.df = df

    button1.on_click(on_button_clicked1)

    def on_button_clicked2(b):
        rows = out_qg.get_selected_rows()
        if len(rows) > 0:
            df = out_qg.df.drop(out_qg.df.index[rows])
            out_qg.df = df

    button2.on_click(on_button_clicked2)

    d.display(button1)
    d.display(in_qg)
    d.display(button2)
    d.display(out_qg)

    return out_qg


def get_sets(spec, lookups, model_sets_file_name):

    # main widget
    tab = widgets.Tab()

    # sets that don't need a lookup table
    non_lookups = spec.user_defined_sets - lookups.keys()

    # lists for widget content
    lookup_name = list(lookups.keys())
    lookup_dfr = list(lookups.values())
    tab_contents = []
    out_dfr = []
    add_buttons = []
    remove_buttons = []
    out_qgs = []
    in_qgs = []

    # get current user data from file
    user_data = spec.get_default_sets()
    with open(model_sets_file_name) as p:
        user_data.update(json.load(p))

    # callbacks for events
    def add_element(b, out_qg):
        current_df = out_qg.get_changed_df()  # what is currently visible
        new_row = pd.DataFrame({'Name': [""]})
        df = current_df.append(new_row, ignore_index=True)
        out_qg.df = df

    def add_element_from_lookup(b, out_qg, in_qg):
        df = out_qg.df.append(in_qg.get_selected_df())
        out_qg.change_selection([])
        out_qg.df = df

    def remove_element(b, out_qg):
        current_df = out_qg.get_changed_df()  # what is currently visible
        rows = out_qg.get_selected_rows()
        if len(rows) > 0:
            new_df = current_df.drop(out_qg.df.index[rows])
            out_qg.df = new_df

    def save_configuration(b):
        out_dict = {}
        for j in range(len(lookup_name)):
            out_dict[lookup_name[j]] = out_qgs[j].df.index.to_list()
        for l in non_lookups:
            j += 1
            current_df = out_qgs[j].get_changed_df()  # what is currently visible
            out_dict[l] = current_df['Name'].to_list()
        with open(model_sets_file_name, 'w') as fp:
            json.dump(out_dict, fp)
        print("Model sets saved to", model_sets_file_name, out_dict)

    # build tab_content for each lookup tab
    for i in range(len(lookup_dfr)):
        if lookup_name[i] in user_data:
            dfr = lookups[lookup_name[i]].loc[user_data[lookup_name[i]], :]
            out_dfr.append(dfr)
        else:
            out_dfr.append(pd.DataFrame())
        add_buttons.append(widgets.Button(description='Add to set'))
        remove_buttons.append(widgets.Button(description='Remove from set'))
        out_qgs.append(qgrid.show_grid(out_dfr[i], grid_options={'maxVisibleRows': 5}))
        in_qgs.append(qgrid.show_grid(lookup_dfr[i], grid_options={'maxVisibleRows': 10}))
        tab_content = widgets.AppLayout(
            header=None,
            left_sidebar=widgets.VBox([add_buttons[i], remove_buttons[i]]),
            center=widgets.VBox([out_qgs[i], in_qgs[i]]),
            right_sidebar=None,
            footer=None)
        tab_contents.append(tab_content)

        # add callbacks
        add_buttons[i].on_click(functools.partial(add_element_from_lookup, out_qg=out_qgs[i], in_qg=in_qgs[i]))
        remove_buttons[i].on_click(functools.partial(remove_element, out_qg=out_qgs[i]))

        # set tab name
        tab.set_title(i, lookup_name[i])

    # build tab content for non-lookup sets
    for k in non_lookups:
        i += 1
        if k in user_data.keys():
            df = pd.DataFrame({'Name': user_data[k]})
        else:
            pd.DataFrame({'Name': [""]})
        add_buttons.append(widgets.Button(description='Add to set'))
        remove_buttons.append(widgets.Button(description='Remove from set'))
        out_qgs.append(qgrid.show_grid(df, grid_options={'maxVisibleRows': 10}))
        tab_content = widgets.AppLayout(
            header=None,
            left_sidebar=widgets.VBox([add_buttons[i], remove_buttons[i]]),
            center=widgets.Box([out_qgs[i]]),
            right_sidebar=None,
            footer=None)
        tab_contents.append(tab_content)

        # add callbacks
        add_buttons[i].on_click(functools.partial(add_element, out_qg=out_qgs[i]))
        remove_buttons[i].on_click(functools.partial(remove_element, out_qg=out_qgs[i]))

        # set tab name
        tab.set_title(i, k)

    # build tab widget
    save_button = widgets.Button(description="Save configuration")
    save_button.on_click(save_configuration)
    v_box = widgets.VBox([save_button, tab])
    tab.children = tab_contents

    return v_box, tab


def get_parameters(param_dfr, model_parameters_file_name):

    col_defs = {
        'index': {
            'maxWidth': 50, 'minWidth': 50, 'width': 50
        },
        'Index': {
            'width': 1000,
        }
    }
    param_qg = qgrid.show_grid(param_dfr, grid_options={'maxVisibleRows': 10, 'forceFitColumns': False},
                               column_definitions=col_defs)
    #get_parameters.param = param_dfr.loc[0, 'Parameter']

    def save_configuration(b):
        dfr = param_qg.df.copy()
        dfr.update(param_qg.get_changed_df())
        dfr = dfr[['Parameter', 'Index', 'Value']]
        dfr.set_index('Parameter').to_dict('split')

        def x(l):
            return {'index': l[0], 'value': l[1]}

        updated_parameters_dict = dfr.groupby('Parameter')[['Index', 'Value']].apply(
            lambda g: list(map(x, g.values.tolist()))).to_dict()

        with open(model_parameters_file_name, 'w') as fp:
            json.dump(updated_parameters_dict, fp, indent=4)
        print("Model parameters saved to", model_parameters_file_name)

    save_button = widgets.Button(description="Save configuration")
    save_button.on_click(save_configuration)

    def change_parameter(change):
        get_parameters.param = change.new

    # dropdown = widgets.Dropdown(options=param_dfr['Parameter'].drop_duplicates().to_list(), description='Parameter:',
    #                             layout=widgets.Layout(height='30px'))
    # dropdown.observe(change_parameter, names='value')

    h_box = widgets.Box([save_button])
    box = widgets.VBox([h_box, param_qg])

    return box

