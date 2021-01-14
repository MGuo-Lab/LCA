# module for building a model from a specification
import pyomo.environ as pe
import pyomo.dataportal as pyod
import pandas as pd
import numpy as np


class Specification:
    """Abstract pyomo specification"""

    def build_gui(self):
        return False

    def populate(self, db_file, json_file):
        return False

    def get_dummy_data(self):
        return False


class FlowSelectionSpecification(Specification):
    """Alex pyomo specification"""


class ScheduleSpecification(Specification):
    """Miao pyomo specification"""

    def __init__(self):

        # user-defined sets
        abstract_model = self.abstract_model = pe.AbstractModel()
        abstract_model.F_m = pe.Set(doc='Material flows to optimise')
        abstract_model.F_s = pe.Set(doc='Service flows to optimise')
        abstract_model.F_t = pe.Set(doc='Transport flows to optimise')
        abstract_model.F = abstract_model.F_m | abstract_model.F_t | abstract_model.F_s
        abstract_model.P = pe.Set(doc='Processes in the optimisation problem')
        abstract_model.T = pe.Set(doc='Time intervals')
        abstract_model.K = pe.Set(doc='Tasks')
        abstract_model.D = pe.Set(doc='Demands')
        abstract_model.KPI = pe.Set(doc='Performance indicators for optimisation problem')

        # Database sets
        abstract_model.AF = pe.Set(doc='All flows in openLCA database')
        abstract_model.E = pe.Set(doc='Elementary Flows in OpenLCA database')
        abstract_model.AP = pe.Set(doc='All processes from in OpenLCA database')
        abstract_model.AKPI = pe.Set(doc='All key performance indicators in an openLCA database')

        # User-defined parameters
        abstract_model.C = pe.Param(abstract_model.F_m, abstract_model.K, abstract_model.D, abstract_model.T,
                                    doc='Conversion factor for material flows')
        abstract_model.Demand = pe.Param(abstract_model.D, abstract_model.K, abstract_model.T)
        abstract_model.Total_Demand = pe.Param(abstract_model.D, abstract_model.K)
        abstract_model.L = pe.Param(abstract_model.F_m, abstract_model.F_t)
        abstract_model.X = pe.Param(abstract_model.K, abstract_model.T)
        abstract_model.Y = pe.Param(abstract_model.K, abstract_model.T)
        abstract_model.d = pe.Param(abstract_model.P, abstract_model.F_m, abstract_model.K, abstract_model.T)
        abstract_model.phi = pe.Param(abstract_model.F, abstract_model.P, abstract_model.T)

        #
        # Database parameters
        abstract_model.Ef = pe.Param(abstract_model.KPI, abstract_model.E)
        abstract_model.EF = pe.Param(abstract_model.E, abstract_model.F, abstract_model.P)

        def ei_rule(model, kpi, f, p):
            return sum(model.Ef[kpi, e]*model.EF[e, f, p] for e in model.E)
        abstract_model.EI = pe.Param(abstract_model.KPI, abstract_model.F, abstract_model.P, rule=ei_rule)
        # abstract_model.XI = pe.Param(abstract_model.P, abstract_model.F_m)
        # abstract_model.YI = pe.Param(abstract_model.P, abstract_model.F_m)

        # Variables
        abstract_model.Flow = pe.Var(abstract_model.F_m, abstract_model.P, abstract_model.K, abstract_model.T)
        abstract_model.Storage = pe.Var(abstract_model.F_s, abstract_model.K, abstract_model.T)
        abstract_model.Specific_Service_Flow = pe.Var(abstract_model.F_s, abstract_model.P, abstract_model.K, abstract_model.T)
        abstract_model.Specific_Material_Transport_Flow = pe.Var(abstract_model.F_m, abstract_model.P,
                                                                 abstract_model.F_t, abstract_model.K, abstract_model.T)
        abstract_model.Transport_Flow = pe.Var(abstract_model.F_t, abstract_model.K, abstract_model.T)
        abstract_model.Specific_Transport_Flow = pe.Var(abstract_model.F_t, abstract_model.P,
                                                        abstract_model.K, abstract_model.T)

        # objectives
        def environment_objective_rule(model, kpi):
            return sum(model.Flow[fm, p, k, t]*model.EI[kpi, fm, p]
                       for fm in model.F_m for p in model.P for k in model.K for t in model.T) + \
                    sum(model.Specific_Service_Flow[fs, p, k, t] * model.EI[kpi, fs, p]
                        for fs in model.F_s for p in model.P for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, p, k, t] * model.EI[kpi, ft, p]
                        for ft in model.F_t for p in model.P for k in model.K for t in model.T)

        def cost_objective_rule(model):
            return sum(model.Flow[fm, p, k, t]*model.phi[fm, p, t]
                       for fm in model.F_m for p in model.P for k in model.K for t in model.T) + \
                    sum(model.Specific_Service_Flow[fs, p, k, t] * model.phi[fs, p, t]
                        for fs in model.F_s for p in model.P for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, p, k, t] * model.phi[ft, p, t]
                        for ft in model.F_t for p in model.P for k in model.K for t in model.T)

        abstract_model.obj1 = pe.Objective(abstract_model.KPI, rule=environment_objective_rule)
        abstract_model.obj2 = pe.Objective(rule=cost_objective_rule)

        # constraints
        def flow_demand_rule(model, d, k):
            total_demand = sum(
                model.Flow[fm, pm, k, t] * model.C[fm, k, d, t]
                for fm in model.F_m for pm in model.P for t in model.T)
            return total_demand >= model.Total_Demand[d, k]
        self.abstract_model.total_demand_constraint = pe.Constraint(
            self.abstract_model.D, self.abstract_model.K, rule=flow_demand_rule)

        def material_flow_rule(model, fm, pm, k, t):
            return model.Flow[fm, pm, k, t] == sum(model.Specific_Material_Transport_Flow[fm, pm, ft, k, t] for ft in model.F_t)
        self.abstract_model.material_flow_constraint = \
            pe.Constraint(self.abstract_model.F_m, self.abstract_model.P,
                          self.abstract_model.K, self.abstract_model.T, rule=material_flow_rule)

        def transport_flow_rule(model, ft, k, t):
            return model.Transport_Flow[ft, k, t] == sum(
                model.Specific_Material_Transport_Flow[fm, p, ft, k, t] * model.d[p, fm, k, t]
                for fm in model.F_m for p in model.P)

        self.abstract_model.transport_constraint = pe.Constraint(self.abstract_model.F_t,
                                                                 self.abstract_model.K,
                                                                 self.abstract_model.T,
                                                                 rule=transport_flow_rule)

        def specific_transport_flow_rule(model, ft, k, t):
            return model.Transport_Flow[ft, k, t] == sum(model.Specific_Transport_Flow[ft, p, k, t]
                                                         for p in model.P)
        abstract_model.specific_transport_constraint = pe.Constraint(abstract_model.F_t,
                                                                     abstract_model.K,
                                                                     abstract_model.T,
                                                                     rule=specific_transport_flow_rule)

    def populate(self, db_file, json_file):

        olca_dp = pyod.DataPortal()

        # user data
        olca_dp.load(filename=json_file)

        # db data
        user_data_names = [k for k in olca_dp.keys()]
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_FLOWS", set=self.abstract_model.AF)
        if 'E' not in user_data_names:
            olca_dp.load(filename=db_file, using='sqlite3',
                         query="SELECT REF_ID FROM TBL_FLOWS WHERE FLOW_TYPE='ELEMENTARY_FLOW'", set=self.abstract_model.E)
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_PROCESSES", set=self.abstract_model.AP)
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_IMPACT_CATEGORIES",
                     set=self.abstract_model.AKPI)

        # calculated environmental impacts

        model_instance = self.abstract_model.create_instance(olca_dp)

        return model_instance

    def get_dummy_data(self, d={}):
        user_sets = {
            'F_m': ['fm1'],
            'F_s': ['ft1'],
            'F_t': ['fs1'],
            'D': ['d1', 'd2'],
            'T': ['t1'],
            'K': ['k1'],
            'P': ['p1'],
            'E': ['e1', 'e2', 'e3'],
            'KPI': ['kpi1'],
            'OBJ': ['environment', 'cost']
        }
        user_sets.update(d)
        set_f = user_sets['F_m'] + user_sets['F_s'] + user_sets['F_t']
        user_params = dict()
        user_params['C'] = [{'index': [fm, k, d, t], 'value': 2}
                            for fm in user_sets['F_m'] for d in user_sets['D'] for k in user_sets['K']
                            for t in user_sets['T']]
        user_params['d'] = [{'index': [p, fm, k, t], 'value': 2}
                            for p in user_sets['P'] for fm in user_sets['F_m'] for k in user_sets['K'] for t in user_sets['T']]
        user_params['Total_Demand'] = [{'index': [d, k], 'value': 1}
                                       for d in user_sets['D'] for k in user_sets['K']]
        user_params['EI'] = [{'index': [kpi, f, p], 'value': 1}
                             for kpi in user_sets['KPI'] for f in set_f for p in user_sets['P']]
        user_params['phi'] = [{'index': [f, p, t], 'value': 1}
                              for f in set_f for p in user_sets['P'] for t in user_sets['T']]
        user_params['Ef'] = [{'index': [kpi, e], 'value': 4}
                             for kpi in user_sets['KPI'] for e in user_sets['E']]
        user_params['EF'] = [{'index': [e, f, p], 'value': 5}
                             for e in user_sets['E'] for f in set_f for p in user_sets['P']]

        return {**user_sets, **user_params}

    def get_param_dfr(self, filename, param_list=['C', 'Total_Demand', 'd']):
        user_dp = pyod.DataPortal()
        user_dp.load(filename=filename)
        config_instance = self.abstract_model.create_instance(user_dp)
        param_dfr = pd.DataFrame(
            ([o.name, o.doc, [index for index in o], [pe.value(o[index]) for index in o]]
             for o in config_instance.component_objects(pe.Param, active=True) if o.name in param_list),
            columns=['Param', 'Description', 'Index', 'Value']
        )

        return param_dfr

#
# def get_user_data(abstract_model, olca_data_portal):
#     model_instance = abstract_model.create_instance(olca_data_portal)
#     # generate a molaqt pane
#     # populate dropdowns and request what sets/parameters are missing in model_instance
#     # fail if user data incomplete
#     # return partially concrete model with complete user data
#     return model_instance
#
# def solve_concrete_model(concrete_model, solver="glpk"):
#     # return pyomo model object for results
#     opt = SolverFactory(solver)
#     results = opt.solve(concrete_model)
#     return results
#
#
# def output_model(pyomo_model_results):
#     # long form data by interating over sets, params, vars


def unnest(df, explode):
    cols = df.columns.tolist()
    idx = df.index.repeat(df[explode[0]].str.len())
    df1 = pd.concat([pd.Series(sum(df[x].values, []), name=x) for x in explode], axis=1)
    df1.index = idx
    out_dfr = df1.join(df.drop(explode, 1), how='left')
    out_dfr = out_dfr[cols].reset_index(drop=True)

    return out_dfr
