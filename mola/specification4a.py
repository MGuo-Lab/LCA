# module for building a model from a specification
import pyomo.environ as pe
import pyomo.dataportal as pyod
import mola.sqlgenerator as sq
import mola.dataimport as di
import pandas as pd


class Specification:
    """Abstract specification class"""
    user_defined_sets: dict
    db_sets: dict
    user_defined_parameters: dict

    def __init__(self):
        if type(self) is Specification:
            raise NotImplementedError()

    def build_gui(self):
        raise NotImplementedError()

    def populate(self, db_file, json_file):
        raise NotImplementedError()

    def get_default_sets(self):
        raise NotImplementedError()

    def get_default_parameters(self):
        raise NotImplementedError()

    def get_dummy_data(self):
        raise NotImplementedError()


class SelectionSpecification(Specification):
    """Alex pyomo specification"""


class ScheduleSpecification(Specification):
    """Miao pyomo specification"""
    user_defined_sets = {
        'F_m': 'Material flows to optimise',
        'F_s': 'Service flows to optimise',
        'F_t': 'Transport flows to optimise',
        'P_m': 'Processes producing material flows in the optimisation problem',
        'P_t': 'Processes producing transport flows in the optimisation problem',
        'P_s': 'Processes producing service flows in the optimisation problem',
        'T': 'Time intervals',
        'K': 'Tasks',
        'D': 'Demands',
        'KPI': 'Performance indicators for optimisation problem',
    }
    db_sets = {
        'AF': 'All flows in openLCA database',
        'E': 'Elementary Flows in OpenLCA database',
        'AP': 'All processes from in OpenLCA database',
        'AKPI': 'All key performance indicators in an openLCA database',
    }
    user_defined_parameters = {
        'C': {'index': ['F_m', 'K', 'D', 'T'], 'doc': 'Conversion factor for material flows'},
        'Demand': {'index': ['D', 'K', 'T'], 'doc': 'Specific demand'},
        'Total_Demand': {'index': ['D', 'K'], 'doc': 'Total demand'},
        'L': {'index': ['F_m', 'F_t'], 'doc': 'Binary conversion factor between material and transport flows'},
        'X': {'index': ['K', 'T'], 'doc': 'Latitude'},
        'Y': {'index': ['K', 'T'], 'doc': 'Longitude'},
        'd': {'index': ['P', 'F_m', 'K', 'T'], 'doc': 'Distance'},
        'phi': {'index': ['F', 'P', 'T'], 'doc': 'Cost impact factor'},
        'J': {'index': ['F_m', 'P_m', 'F_t', 'P_t'],
              'doc': 'Binary conversion factor between material and transport flows'},
    }
    # db parameters need to be constructed explicitly

    def __init__(self):

        # setup abstract model
        abstract_model = self.abstract_model = pe.AbstractModel()

        # user-defined sets
        for var, doc in ScheduleSpecification.user_defined_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        abstract_model.F = abstract_model.F_m | abstract_model.F_t | abstract_model.F_s
        abstract_model.P = abstract_model.P_m | abstract_model.P_t | abstract_model.P_s

        # Database sets
        for var, doc in ScheduleSpecification.db_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        # User-defined parameters
        for param, val in ScheduleSpecification.user_defined_parameters.items():
            idx = [abstract_model.component(i) for i in val['index']]
            abstract_model.add_component(param, pe.Param(*idx, doc=val['doc']))

        # Database parameters
        abstract_model.Ef = pe.Param(abstract_model.KPI, abstract_model.E, default=0)
        abstract_model.EF = pe.Param(abstract_model.E, abstract_model.F, abstract_model.P, default=0)

        def ei_rule(model, kpi, f, p):
            return sum(model.Ef[kpi, e]*model.EF[e, f, p] for e in model.E)
        abstract_model.EI = pe.Param(abstract_model.KPI, abstract_model.F, abstract_model.P, rule=ei_rule)
        abstract_model.XI = pe.Param(abstract_model.P, abstract_model.F_m)
        abstract_model.YI = pe.Param(abstract_model.P, abstract_model.F_m)

        # Variables
        abstract_model.Flow = pe.Var(abstract_model.F_m, abstract_model.P_m, abstract_model.K, abstract_model.T,
                                     within=pe.NonNegativeReals, doc='Material flow')
        abstract_model.Storage = pe.Var(abstract_model.F_s, abstract_model.K, abstract_model.T,
                                        within=pe.NonNegativeReals, doc='Storage')
        abstract_model.Specific_Service_Flow = pe.Var(abstract_model.F_s, abstract_model.P, abstract_model.K, abstract_model.T,
                                             within=pe.NonNegativeReals, doc='Service Flow')
        abstract_model.Specific_Material_Transport_Flow = pe.Var(abstract_model.F_m, abstract_model.P_m,
                                                                 abstract_model.F_t, abstract_model.P_t,
                                                                 abstract_model.K, abstract_model.T,
                                                                 within=pe.NonNegativeReals,
                                                                 doc='Specific Material Transport Flow')
        abstract_model.Specific_Transport_Flow = pe.Var(abstract_model.F_t, abstract_model.P_t,
                                                        abstract_model.K, abstract_model.T,
                                                        within=pe.NonNegativeReals,
                                                        doc='Specific Transport Flow')

        # objectives
        def environment_objective_rule(model, kpi):
            return sum(model.Flow[fm, pm, k, t]*model.EI[kpi, fm, pm]
                       for fm in model.F_m for pm in model.P_m for k in model.K for t in model.T) + \
                    sum(model.Specific_Service_Flow[fs, p, k, t] * model.EI[kpi, fs, p]
                        for fs in model.F_s for p in model.P for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, pt, k, t] * model.EI[kpi, ft, pt]
                        for ft in model.F_t for pt in model.P_t for k in model.K for t in model.T)

        def cost_objective_rule(model):
            return sum(model.Flow[fm, pm, k, t]*model.phi[fm, pm, t]
                       for fm in model.F_m for pm in model.P_m for k in model.K for t in model.T) + \
                    sum(model.Specific_Service_Flow[fs, ps, k, t] * model.phi[fs, ps, t]
                        for fs in model.F_s for ps in model.P_s for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, pt, k, t] * model.phi[ft, pt, t]
                        for ft in model.F_t for pt in model.P_t for k in model.K for t in model.T)

        abstract_model.obj1 = pe.Objective(abstract_model.KPI, rule=environment_objective_rule)
        abstract_model.obj2 = pe.Objective(rule=cost_objective_rule)

        # constraints
        def flow_demand_rule(model, d, k):
            total_demand = sum(
                model.Flow[fm, pm, k, t] * model.C[fm, k, d, t]
                for fm in model.F_m for pm in model.P_m for t in model.T)
            return total_demand >= model.Total_Demand[d, k]
        self.abstract_model.total_demand_constraint = pe.Constraint(
            self.abstract_model.D, self.abstract_model.K, rule=flow_demand_rule)

        def material_flow_rule(model, fm, pm, k, t):
            return model.Flow[fm, pm, k, t] == sum(model.J[fm, pm, ft, pt] *
                                                   model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t]
                                                   for ft in model.F_t for pt in model.P_t)
        self.abstract_model.material_flow_constraint = \
            pe.Constraint(self.abstract_model.F_m, self.abstract_model.P_m,
                          self.abstract_model.K, self.abstract_model.T, rule=material_flow_rule)

        def specific_transport_flow_rule(model, ft, pt, k, t):
            return model.Specific_Transport_Flow[ft, pt, k, t] == sum(
                model.J[fm, pm, ft, pt] *
                model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t] *
                model.d[pm, fm, k, t]
                for fm in model.F_m for pm in model.P_m)

        self.abstract_model.transport_constraint = pe.Constraint(self.abstract_model.F_t,
                                                                 self.abstract_model.P_t,
                                                                 self.abstract_model.K,
                                                                 self.abstract_model.T,
                                                                 rule=specific_transport_flow_rule)

    def populate(self, json_files=None, elementary_flow_ref_ids=None, db_file=di.get_default_db_file()):

        olca_dp = pyod.DataPortal()

        # user data
        for json_file in json_files:
            if json_file:
                olca_dp.load(filename=json_file)

        # db data
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_FLOWS",
                     set=self.abstract_model.AF)
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_PROCESSES",
                     set=self.abstract_model.AP)
        olca_dp.load(filename=db_file, using='sqlite3', query="SELECT REF_ID FROM TBL_IMPACT_CATEGORIES",
                     set=self.abstract_model.AKPI)

        # import impact breakdown which needs elementary flows and query generator
        flows = list(olca_dp.data('F_m')) + list(olca_dp.data('F_s')) + list(olca_dp.data('F_t'))
        processes = list(olca_dp.data('P_m')) + list(olca_dp.data('P_s')) + list(olca_dp.data('P_t'))
        if elementary_flow_ref_ids is None:
            olca_dp.load(filename=db_file, using='sqlite3',
                         query="SELECT REF_ID FROM TBL_FLOWS WHERE FLOW_TYPE='ELEMENTARY_FLOW'",
                         set=self.abstract_model.E)
            ice_sql = sq.build_impact_category_elementary_flow(ref_ids=olca_dp.data('KPI'))
            pe_sql = sq.build_process_elementary_flow(flow_ref_ids=flows, process_ref_ids=processes)
            olca_dp.load(filename=db_file, using='sqlite3', query=ice_sql,
                         param=self.abstract_model.Ef, index=(self.abstract_model.KPI, self.abstract_model.E))
            olca_dp.load(filename=db_file, using='sqlite3', query=pe_sql, param=self.abstract_model.EF,
                         index=(self.abstract_model.KPI, self.abstract_model.F, self.abstract_model.P))
        else:
            olca_dp.__setitem__('E', elementary_flow_ref_ids)
            impact_factors = {(kpi, e): 2 for kpi in olca_dp.data('KPI') for e in olca_dp.data('E')}
            process_breakdown = {(e, f, p): 3 for e in olca_dp.data('E') for f in flows for p in processes}
            olca_dp.__setitem__('Ef', impact_factors)
            olca_dp.__setitem__('EF', process_breakdown)

        # use DataPortal to build contrete instance
        model_instance = self.abstract_model.create_instance(olca_dp)

        return model_instance

    def get_default_sets(self, d=None):
        user_sets = {
            'F_m': [],
            'F_s': [],
            'F_t': [],
            'D': ['d1'],
            'T': ['t1'],
            'K': ['k1'],
            'P_m': [],
            'P_t': [],
            'P_s': [],
            'KPI': [],
            'OBJ': ['environment', 'cost']
        }
        if d is not None:
            user_sets.update(d)
        user_sets.update({'F': user_sets['F_m'] + user_sets['F_s'] + user_sets['F_t']})
        user_sets.update({'P': user_sets['P_m'] + user_sets['P_s'] + user_sets['P_t']})

        return user_sets

    def get_default_parameters(self, user_sets):
        user_params = dict()
        user_params['C'] = [{'index': [fm, k, d, t], 'value': 1}
                            for fm in user_sets['F_m'] for d in user_sets['D'] for k in user_sets['K']
                            for t in user_sets['T']]
        user_params['d'] = [{'index': [pm, fm, k, t], 'value': 0}
                            for pm in user_sets['P_m'] for fm in user_sets['F_m'] for k in user_sets['K'] for t in user_sets['T']]
        user_params['Total_Demand'] = [{'index': [d, k], 'value': 0}
                                       for d in user_sets['D'] for k in user_sets['K']]
        user_params['J'] = [{'index': [fm, pm, ft, pt], 'value': 0}
                            for fm in user_sets['F_m'] for pm in user_sets['P_m']
                            for ft in user_sets['F_t'] for pt in user_sets['P_t']]
        flows = list(user_sets['F_m']) + list(user_sets['F_s']) + list(user_sets['F_t'])
        processes = list(user_sets['P_m']) + list(user_sets['P_s']) + list(user_sets['P_t'])
        user_params['phi'] = [{'index': [f, p, t], 'value': 0}
                              for f in flows for p in processes
                              for t in user_sets['T']]

        return user_params

    def get_dummy_data(self, d={}):
        user_sets = {
            'F_m': ['fm1'],
            'F_s': ['fs1'],
            'F_t': ['ft1'],
            'D': ['d1', 'd2'],
            'T': ['t1'],
            'K': ['k1'],
            'P_m': ['pm1'],
            'P_t': ['pt1'],
            'P_s': ['ps1'],
            'E': ['e1', 'e2', 'e3'],
            'KPI': ['kpi1'],
            'OBJ': ['environment', 'cost']
        }
        user_sets.update(d)
        user_sets.update({'F': user_sets['F_m'] + user_sets['F_s'] + user_sets['F_t']})
        user_sets.update({'P': user_sets['P_m'] + user_sets['P_s'] + user_sets['P_t']})
        user_params = dict()
        user_params['C'] = [{'index': [fm, k, d, t], 'value': 2}
                            for fm in user_sets['F_m'] for d in user_sets['D'] for k in user_sets['K']
                            for t in user_sets['T']]
        user_params['d'] = [{'index': [pm, fm, k, t], 'value': 2}
                            for pm in user_sets['P_m'] for fm in user_sets['F_m'] for k in user_sets['K'] for t in user_sets['T']]
        user_params['Total_Demand'] = [{'index': [d, k], 'value': 1}
                                       for d in user_sets['D'] for k in user_sets['K']]
        user_params['EI'] = [{'index': [kpi, f, p], 'value': 1}
                             for kpi in user_sets['KPI'] for f in user_sets['F'] for p in user_sets['P']]
        user_params['phi'] = [{'index': [f, p, t], 'value': 1}
                              for f in user_sets['F'] for p in user_sets['P'] for t in user_sets['T']]
        user_params['Ef'] = [{'index': [kpi, e], 'value': 4}
                             for kpi in user_sets['KPI'] for e in user_sets['E']]
        user_params['EF'] = [{'index': [e, f, p], 'value': 5}
                             for e in user_sets['E'] for f in user_sets['F'] for p in user_sets['P']]
        user_params['J'] = [{'index': [fm, pm, ft, pt], 'value': 99}
                            for fm in user_sets['F_m'] for pm in user_sets['P_m']
                            for ft in user_sets['F_t'] for pt in user_sets['P_t']]

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

