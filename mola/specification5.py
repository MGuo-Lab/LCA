"""
A Specification object contains a pyomo model and methods to build the model.
- adds binary variable for selection problem
"""
import pygeodesy.formy as pygeo
import math

import pandas as pd
import pyomo.environ as pe
from pyomo.environ import units as pu
import pyomo.dataportal as pyod

import mola.sqlgenerator as sq
import mola.dataimport as di
import mola.build as mb

# units
pu.load_definitions_from_strings([
    'P = [Product_Flow]',
    'P_m = [Material_Product_Flow]',
    'P = [Service_Product_Flow]',
    'P_t = [Transport_Product_Flow]',
    'D = [Demand]'
])


class Specification:
    """Abstract specification class"""
    user_defined_sets: dict
    db_sets: dict
    user_defined_parameters: dict
    controllers: dict
    default_settings: dict

    def __init__(self):
        if type(self) is Specification:
            raise NotImplementedError()

    def populate(self, db_file, json_file):
        raise NotImplementedError()

    def get_default_sets(self):
        raise NotImplementedError()

    def get_default_parameters(self):
        raise NotImplementedError()

    def get_dummy_data(self):
        raise NotImplementedError()


class SimpleSpecification(Specification):
    """
    Alex pyomo specification
    """
    user_defined_sets = {
        'P_m': 'Processes producing material flows in the optimisation problem',
        'P_t': 'Processes producing transport flows in the optimisation problem',
        'F_m': 'Material flows to optimise',
        'F_t': 'Transport flows to optimise',
        'D': 'Demands',
        'KPI': 'Performance indicators for optimisation problem',
    }
    db_sets = {
        'E': 'Elementary Flows in OpenLCA database',
    }
    user_defined_parameters = {
        'C': {'index': ['F_m', 'D'], 'doc': 'Conversion factor for material flows', 'unit': pu.D/pu.P_m},
        'U': {'index': ['F_m', 'F_t'], 'doc': 'Conversion factor for material flow units in transport flow units',
              'unit': pu.P_t / pu.P_m},
        'Demand': {'index': ['D'], 'doc': 'Specific demand', 'unit': pu.D},
        'Total_Demand': {'index': ['D'], 'doc': 'Total demand', 'unit': pu.D},
        'd': {'index': ['P', 'F_m'], 'doc': 'Distance', 'unit': pu.km},
        'J': {'index': ['F_m', 'P_m', 'F_t', 'P_t'],
              'doc': 'Binary conversion factor between material and transport flows', 'within': 'Binary'},
    }
    # db parameters need to be constructed explicitly
    controllers = {"Customised": "CustomController", "Standard": "StandardController"}
    default_settings = {
        'distance_calculated': {'value': False, 'type': 'boolean', 'doc': 'Calculate distance using openLCA data'},
        'test_setting': {'value': False, 'type': 'boolean', 'doc': 'Test Setting'}
    }

    def __init__(self):

        # instance object to hold just the setting values
        self.settings = {k: v['value'] for k, v in self.default_settings.items()}

        # setup abstract model
        abstract_model = self.abstract_model = pe.AbstractModel()

        # user-defined sets
        for var, doc in self.user_defined_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        abstract_model.F = abstract_model.F_m | abstract_model.F_t
        abstract_model.P = abstract_model.P_m | abstract_model.P_t

        # set of objectives
        abstract_model.OBJ = pe.Set(doc='Set of objective functions')

        # Database sets
        for var, doc in self.db_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        # User-defined parameters
        for param, val in self.user_defined_parameters.items():
            idx = [abstract_model.component(i) for i in val['index']]
            if 'within' in val and val['within'] == 'Binary':
                within = pe.Binary
            else:
                within = pe.Reals
            abstract_model.add_component(param, pe.Param(*idx, doc=val['doc'], within=within))

        # Database parameters
        abstract_model.Ef = pe.Param(abstract_model.KPI, abstract_model.E, default=0)
        abstract_model.EF = pe.Param(abstract_model.E, abstract_model.F, abstract_model.P, default=0)

        def ei_rule(model, kpi, f, p):
            return sum(model.Ef[kpi, e]*model.EF[e, f, p] for e in model.E)
        abstract_model.EI = pe.Param(abstract_model.KPI, abstract_model.F, abstract_model.P, rule=ei_rule)

        # Unit conversion factors
        abstract_model.UM = pe.Param(abstract_model.F_m, abstract_model.P_m, within=pe.Reals)
        abstract_model.UT = pe.Param(abstract_model.F_t, abstract_model.P_t, within=pe.Reals)

        # Variables
        abstract_model.Flow = pe.Var(abstract_model.F_m, abstract_model.P_m,
                                     within=pe.NonNegativeReals, doc='Material flow', units=pu.P_m)
        abstract_model.Specific_Material_Transport_Flow = pe.Var(abstract_model.F_m, abstract_model.P_m,
                                                                 abstract_model.F_t, abstract_model.P_t,
                                                                 within=pe.NonNegativeReals,
                                                                 doc='Specific Material Transport Flow',
                                                                 units=pu.P_m)
        abstract_model.Specific_Transport_Flow = pe.Var(abstract_model.F_t, abstract_model.P_t,
                                                        within=pe.NonNegativeReals,
                                                        doc='Specific Transport Flow',
                                                        units=pu.P_t)
        abstract_model.Demand_Selection = pe.Var(abstract_model.D,
                                                 within=pe.Binary,
                                                 doc='Selection of Demand Product')

        # objectives
        def environment_objective_rule(model, kpi):
            return sum(model.Flow[fm, pm]*model.EI[kpi, fm, pm]
                       for fm in model.F_m for pm in model.P_m) + \
                    sum(model.Specific_Transport_Flow[ft, pt] * model.EI[kpi, ft, pt]
                        for ft in model.F_t for pt in model.P_t)

        def objective_rule(model, kpi):
            return environment_objective_rule(model, kpi)

        # FIXME remove the superfluous objectives
        abstract_model.obj1 = pe.Objective()
        abstract_model.obj2 = pe.Objective()
        abstract_model.obj = pe.Objective(abstract_model.KPI, rule=objective_rule)

        # constraints
        def flow_demand_rule(model, d):
            total_demand = sum(
                model.Flow[fm, pm] * model.C[fm, d]
                for fm in model.F_m for pm in model.P_m)
            return total_demand >= model.Total_Demand[d]
        self.abstract_model.total_demand_constraint = pe.Constraint(
            self.abstract_model.D, rule=flow_demand_rule)

        def material_flow_rule(model, fm, pm):
            return model.Flow[fm, pm] == sum(
                model.J[fm, pm, ft, pt] * model.Specific_Material_Transport_Flow[fm, pm, ft, pt]
                for ft in model.F_t for pt in model.P_t)
        self.abstract_model.material_flow_constraint = \
            pe.Constraint(self.abstract_model.F_m, self.abstract_model.P_m, rule=material_flow_rule)

        def specific_transport_flow_rule(model, ft, pt):
            return model.Specific_Transport_Flow[ft, pt] == sum(
                model.J[fm, pm, ft, pt] * model.U[fm, ft] *
                model.Specific_Material_Transport_Flow[fm, pm, ft, pt] *
                model.d[pm, fm]
                for fm in model.F_m for pm in model.P_m)

        self.abstract_model.transport_constraint = pe.Constraint(self.abstract_model.F_t,
                                                                 self.abstract_model.P_t,
                                                                 rule=specific_transport_flow_rule)

        def demand_selection_rule(model):
            return sum(model.Demand_Selection[d] for d in model.D) == 1

        self.abstract_model.demand_selection_constraint = pe.Constraint(rule=demand_selection_rule)

        def specific_demand_rule(model, d):
            total_flow = sum(model.Flow[fm, pm] * model.C[fm, d]
                             for fm in model.F_m for pm in model.P_m)
            return total_flow >= model.Demand[d] * model.Demand_Selection[d]

        self.abstract_model.specific_demand_constraint = pe.Constraint(self.abstract_model.D,
                                                                       rule=specific_demand_rule)

        def service_flow_link_rule(model, fs, ps):
            return model.Storage_Service_Flow[fs, ps] == \
                   sum(model.L[fm, pm, fs, ps] * model.Storage_Service_Flow[fm, pm]
                       for fm in model.F_m for pm in model.P_m)

        # TODO: service_flow_constraint

    def populate(self, json_files=None, elementary_flow_ref_ids=None, db_file=di.get_default_db_file()):

        olca_dp = pyod.DataPortal()

        # user data
        for json_file in json_files:
            if json_file:
                olca_dp.load(filename=json_file)

        # import impact breakdown which needs elementary flows and query generator
        flows = list(olca_dp.data('F_m')) + list(olca_dp.data('F_t'))
        processes = list(olca_dp.data('P_m')) + list(olca_dp.data('P_t'))
        if elementary_flow_ref_ids is None:
            olca_dp.load(filename=db_file, using='sqlite3',
                         query="SELECT REF_ID FROM TBL_FLOWS WHERE FLOW_TYPE='ELEMENTARY_FLOW'",
                         set=self.abstract_model.E)
            ice_sql = sq.build_impact_category_elementary_flow(ref_ids=olca_dp.data('KPI'))
            pe_sql = sq.build_process_elementary_flow(process_ref_ids=processes)
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

        # use DataPortal to build concrete instance
        model_instance = self.abstract_model.create_instance(olca_dp)

        return model_instance

    def get_default_sets(self, d=None):
        user_sets = {
            'F_m': [],
            'F_t': [],
            'D': ['d1'],
            'P_m': [],
            'P_t': [],
            'KPI': [],
            'OBJ': ['environment', 'cost']
        }
        if d is not None:
            user_sets.update(d)
        user_sets.update({'F': user_sets['F_m'] + user_sets['F_t']})
        user_sets.update({'P': user_sets['P_m'] + user_sets['P_t']})

        return user_sets

    def get_default_parameters(self, user_sets):
        user_params = {
            'C': [{'index': [fm, d], 'value': 0}
                  for fm in user_sets['F_m'] for d in user_sets['D']],
            'U': [{'index': [fm, ft], 'value': 0}
                  for fm in user_sets['F_m'] for ft in user_sets['F_t']],
            'd': [{'index': [pm, fm], 'value': 0}
                  for pm in user_sets['P_m'] for fm in user_sets['F_m']],
            'Demand': [{'index': [d], 'value': 0} for d in user_sets['D']],
            'Total_Demand': [{'index': [d], 'value': 0} for d in user_sets['D']],
            'J': [{'index': [fm, pm, ft, pt], 'value': 0} for fm in user_sets['F_m']
                  for pm in user_sets['P_m'] for ft in user_sets['F_t'] for pt in user_sets['P_t']],
        }

        return user_params

    def get_dummy_data(self, d={}):
        user_sets = {
            'F_m': ['fm1'],
            'F_t': ['ft1'],
            'D': ['d1', 'd2'],
            'P_m': ['pm1'],
            'P_t': ['pt1'],
            'E': ['e1', 'e2', 'e3'],
            'KPI': ['kpi1']
        }
        user_sets.update(d)
        user_sets.update({'F': user_sets['F_m'] + user_sets['F_t']})
        user_sets.update({'P': user_sets['P_m'] + user_sets['P_t']})
        user_params = dict()
        user_params['C'] = [{'index': [fm, d], 'value': 2} for fm in user_sets['F_m']
                            for d in user_sets['D']]
        user_params['U'] = [{'index': [fm, ft], 'value': 2} for fm in user_sets['F_m']
                            for ft in user_sets['F_t']]
        user_params['d'] = [{'index': [pm, fm], 'value': 2}
                            for pm in user_sets['P_m'] for fm in user_sets['F_m']]
        user_params['Total_Demand'] = [{'index': [d], 'value': 1} for d in user_sets['D']]
        user_params['Demand'] = [{'index': [d], 'value': 1} for d in user_sets['D']]
        user_params['EI'] = [{'index': [kpi, f, p], 'value': 1} for kpi in user_sets['KPI']
                             for f in user_sets['F'] for p in user_sets['P']]
        user_params['Ef'] = [{'index': [kpi, e], 'value': 4}
                             for kpi in user_sets['KPI'] for e in user_sets['E']]
        user_params['EF'] = [{'index': [e, f, p], 'value': 5}
                             for e in user_sets['E'] for f in user_sets['F'] for p in user_sets['P']]
        user_params['J'] = [{'index': [fm, pm, ft, pt], 'value': 99}
                            for fm in user_sets['F_m'] for pm in user_sets['P_m']
                            for ft in user_sets['F_t'] for pt in user_sets['P_t']]

        return {**user_sets, **user_params}

    def get_param_dfr(self, filename, param_list=['C', 'U', 'Total_Demand', 'd', 'Demand', 'J', 'L']):
        user_dp = pyod.DataPortal()
        user_dp.load(filename=filename)
        config_instance = self.abstract_model.create_instance(user_dp)
        param_dfr = pd.DataFrame(
            ([o.name, o.doc, [index for index in o], [pe.value(o[index]) for index in o]]
             for o in config_instance.component_objects(pe.Param, active=True) if o.name in param_list),
            columns=['Param', 'Description', 'Index', 'Value']
        )

        return param_dfr


class ScheduleSpecification(Specification):
    """
    Miao pyomo specification
    """
    user_defined_sets = {
        'P_m': 'Processes producing material flows in the optimisation problem',
        'P_t': 'Processes producing transport flows in the optimisation problem',
        'P_s': 'Processes producing service flows in the optimisation problem',
        'F_m': 'Material flows to optimise',
        'F_t': 'Transport flows to optimise',
        'F_s': 'Service flows to optimise',
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
        'C': {'index': ['F_m', 'K', 'D', 'T'], 'doc': 'Conversion factor for material flows', 'unit': pu.D/pu.P_m},
        'U': {'index': ['F_m', 'F_t'], 'doc': '(NOT USED) Conversion factor for material flow units in transport flow units',
              'unit': pu.P_t / pu.P_m},
        'Demand': {'index': ['D', 'K', 'T'], 'doc': 'Specific demand', 'unit': pu.D},
        'Total_Demand': {'index': ['D', 'K'], 'doc': 'Total demand', 'unit': pu.D},
        'L': {'index': ['F_m', 'P_m', 'F_s', 'P_s'], 'doc': 'Binary conversion factor between service flows',
              'within': 'Binary', 'nodes': ['P_m', 'P_t'], 'edges': ['F_m', 'F_t']},
        'X': {'index': ['K', 'T'], 'doc': 'Longitude', 'unit': pu.degree},
        'Y': {'index': ['K', 'T'], 'doc': 'Latitude', 'unit': pu.degree},
        'd': {'index': ['P', 'F_m', 'K', 'T'], 'doc': 'Distance', 'unit': pu.km},
        'J': {'index': ['F_m', 'P_m', 'F_t', 'P_t'],
              'doc': 'Binary conversion factor between material and transport flows', 'within': 'Binary',
              'nodes': ['P_m', 'P_t'], 'edges': ['F_m', 'F_t']},
        'w': {'index': ['OBJ'], 'doc': 'Objective weights'},
    }
    # db parameters need to be constructed explicitly
    controllers = {"Standard": "StandardController"}
    default_settings = {
        'distance_calculated': {'value': False, 'type': 'boolean', 'doc': 'Calculate distance using openLCA data'},
        'test_setting': {'value': False, 'type': 'boolean', 'doc': 'Test Setting'}
    }

    def __init__(self):

        # instance object to hold just the setting values
        self.settings = {k: v['value'] for k, v in self.default_settings.items()}

        # setup abstract model
        abstract_model = self.abstract_model = pe.AbstractModel()

        # user-defined sets
        for var, doc in self.user_defined_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        abstract_model.F = abstract_model.F_m | abstract_model.F_t | abstract_model.F_s
        abstract_model.P = abstract_model.P_m | abstract_model.P_t | abstract_model.P_s

        # set of objectives
        abstract_model.OBJ = pe.Set(doc='Set of objective functions')

        # Database sets
        for var, doc in self.db_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        # User-defined parameters
        for param, val in self.user_defined_parameters.items():
            idx = [abstract_model.component(i) for i in val['index']]
            if 'within' in val and val['within'] == 'Binary':
                within = pe.Binary
            else:
                within = pe.Reals
            if 'unit' in val:
                unit = val['unit']
            else:
                unit = None
            abstract_model.add_component(param, pe.Param(*idx, doc=val['doc'], within=within, units=unit))

        # Database parameters
        abstract_model.Ef = pe.Param(abstract_model.KPI, abstract_model.E, default=0)
        abstract_model.EF = pe.Param(abstract_model.E, abstract_model.F, abstract_model.P, default=0)
        abstract_model.phi = pe.Param(abstract_model.F, abstract_model.P, abstract_model.T, default=0)

        def ei_rule(model, kpi, f, p):
            return sum(model.Ef[kpi, e]*model.EF[e, f, p] for e in model.E)
        abstract_model.EI = pe.Param(abstract_model.KPI, abstract_model.F, abstract_model.P, rule=ei_rule)
        abstract_model.XI = pe.Param(abstract_model.P_m, abstract_model.F_m, doc="Longitude", units=pu.degree)
        abstract_model.YI = pe.Param(abstract_model.P_m, abstract_model.F_m, doc="Latitude", units=pu.degree)

        # Unit conversion factors
        abstract_model.UU = pe.Param(abstract_model.F, abstract_model.P, within=pe.Any)

        # distances calculated from db
        def distance_rule(model, pm, fm, k, t):
            if self.settings['distance_calculated']:
                # need to strip units for call to pygeo.haversine
                return pygeo.haversine(
                    model.Y[k, t].value, model.X[k, t].value,
                    model.YI[pm, fm].value, model.XI[pm, fm].value) / 1000 * pu.km
            else:
                return model.d[pm, fm, k, t]
        self.abstract_model.dd = pe.Param(abstract_model.P_m, abstract_model.F_m, abstract_model.K,
                                          abstract_model.T, rule=distance_rule, doc='Calculated distance',
                                          units=pu.km)

        # Variables
        abstract_model.Flow = pe.Var(abstract_model.F_m, abstract_model.P_m, abstract_model.K, abstract_model.T,
                                     within=pe.NonNegativeReals, doc='Material flow', units=pu.P_m)
        abstract_model.Storage_Service_Flow = pe.Var(abstract_model.F, abstract_model.P, abstract_model.K,
                                                     abstract_model.T, within=pe.NonNegativeReals,
                                                     doc='Storage Service Flow', units=pu.P)
        abstract_model.Specific_Material_Transport_Flow = pe.Var(abstract_model.F_m, abstract_model.P_m,
                                                                 abstract_model.F_t, abstract_model.P_t,
                                                                 abstract_model.K, abstract_model.T,
                                                                 within=pe.NonNegativeReals,
                                                                 doc='Specific Material Transport Flow',
                                                                 units=pu.P_m)
        abstract_model.Specific_Transport_Flow = pe.Var(abstract_model.F_t, abstract_model.P_t,
                                                        abstract_model.K, abstract_model.T,
                                                        within=pe.NonNegativeReals,
                                                        doc='Specific Transport Flow',
                                                        units=pu.P_t)
        abstract_model.Demand_Selection = pe.Var(abstract_model.D, abstract_model.K, abstract_model.T,
                                                 within=pe.Binary,
                                                 doc='Selection of Demand Product')

        # objectives
        def environment_objective_rule(model, kpi):
            return sum(model.Flow[fm, pm, k, t]*model.EI[kpi, fm, pm]
                       for fm in model.F_m for pm in model.P_m for k in model.K for t in model.T) + \
                    sum(model.Storage_Service_Flow[fs, ps, k, t] * model.EI[kpi, fs, ps]
                        for fs in model.F_s for ps in model.P_s for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, pt, k, t] * model.EI[kpi, ft, pt]
                        for ft in model.F_t for pt in model.P_t for k in model.K for t in model.T)

        def cost_objective_rule(model):
            return sum(model.Flow[fm, pm, k, t] * model.phi[fm, pm, t]
                       for fm in model.F_m for pm in model.P_m for k in model.K for t in model.T) + \
                    sum(model.Storage_Service_Flow[fs, ps, k, t] * model.phi[fs, ps, t]
                        for fs in model.F_s for ps in model.P_s for k in model.K for t in model.T) + \
                    sum(model.Specific_Transport_Flow[ft, pt, k, t] * model.phi[ft, pt, t]
                        for ft in model.F_t for pt in model.P_t for k in model.K for t in model.T)

        def objective_rule(model, kpi):
            return model.w['environment'] * environment_objective_rule(model, kpi) + \
                   model.w['cost'] * cost_objective_rule(model)

        abstract_model.obj1 = pe.Objective(abstract_model.KPI, rule=environment_objective_rule)
        abstract_model.obj2 = pe.Objective(rule=cost_objective_rule)
        abstract_model.obj = pe.Objective(abstract_model.KPI, rule=objective_rule)

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
            rhs = 0
            # sum over connected processes
            for fm in model.F_m:
                for pm in model.P_m:
                    if model.J[fm, pm, ft, pt]:
                        unit_conversion = pu.convert_value(1,
                            from_units=mb.map_units(model.UU[fm, pm]) * pu.km,
                            to_units=mb.map_units(model.UU[ft, pt])
                        )
                        rhs += model.J[fm, pm, ft, pt] * \
                               unit_conversion * \
                               model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t] * \
                               model.dd[pm, fm, k, t]

            return model.Specific_Transport_Flow[ft, pt, k, t] == rhs

        self.abstract_model.transport_constraint = pe.Constraint(self.abstract_model.F_t,
                                                                 self.abstract_model.P_t,
                                                                 self.abstract_model.K,
                                                                 self.abstract_model.T,
                                                                 rule=specific_transport_flow_rule)

        def demand_selection_rule(model, k, t):
            return sum(model.Demand_Selection[d, k, t] for d in model.D) == 1

        self.abstract_model.demand_selection_constraint = pe.Constraint(self.abstract_model.K,
                                                                        self.abstract_model.T,
                                                                        rule=demand_selection_rule)

        def specific_demand_rule(model, d, k, t):
            if t == model.T.first():
                total_flow = sum(model.Flow[fm, pm, k, t] * model.C[fm, k, d, t]
                                 for fm in model.F_m for pm in model.P_m)
            else:
                total_flow = sum((model.Flow[fm, pm, k, t] - model.Storage_Service_Flow[fm, pm, k, t] +
                                 model.Storage_Service_Flow[fm, pm, k, model.T.prev(t)]) * model.C[fm, k, d, t]
                                 for fm in model.F_m for pm in model.P_m)
            return total_flow >= model.Demand[d, k, t] * model.Demand_Selection[d, k, t]

        self.abstract_model.specific_demand_constraint = pe.Constraint(self.abstract_model.D,
                                                                       self.abstract_model.K,
                                                                       self.abstract_model.T,
                                                                       rule=specific_demand_rule)

        def service_flow_link_rule(model, fs, ps, k, t):
            return model.Storage_Service_Flow[fs, ps, k, t] == \
                   sum(model.L[fm, pm, fs, ps] * model.Storage_Service_Flow[fm, pm, k, t]
                       for fm in model.F_m for pm in model.P_m)

        self.abstract_model.service_flow_link_constraint = pe.Constraint(self.abstract_model.F_s,
                                                                         self.abstract_model.P_s,
                                                                         self.abstract_model.K,
                                                                         self.abstract_model.T,
                                                                         rule=service_flow_link_rule)

    def populate(self, json_files=None, elementary_flow_ref_ids=None,
                 db_file=di.get_default_db_file()):

        olca_dp = pyod.DataPortal()

        # user data
        for json_file in json_files:
            if json_file:
                olca_dp.load(filename=json_file)

        # simple set data from db (this data is not currently using in the model)
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
            # elementary flows
            olca_dp.load(filename=db_file, using='sqlite3',
                         query="SELECT REF_ID FROM TBL_FLOWS WHERE FLOW_TYPE='ELEMENTARY_FLOW'",
                         set=self.abstract_model.E)

            # only load KPI if required in optimisation
            if len(olca_dp.data('KPI')) > 0:
                ice_sql = sq.build_impact_category_elementary_flow(ref_ids=olca_dp.data('KPI'))
                olca_dp.load(filename=db_file, using='sqlite3', query=ice_sql,
                             param=self.abstract_model.Ef, index=(self.abstract_model.KPI, self.abstract_model.E))

            # breakdown of process into elementary flows
            pe_sql = sq.build_process_elementary_flow(process_ref_ids=processes)
            olca_dp.load(filename=db_file, using='sqlite3', query=pe_sql, param=self.abstract_model.EF,
                         index=(self.abstract_model.KPI, self.abstract_model.F, self.abstract_model.P))

            # cost of product flow from process
            pfc_sql = sq.build_product_flow_cost(process_ref_ids=processes, time=olca_dp.data('T'))
            olca_dp.load(filename=db_file, using='sqlite3', query=pfc_sql, param=self.abstract_model.phi,
                         index=(self.abstract_model.F, self.abstract_model.P, self.abstract_model.T))

        else:
            # for testing
            olca_dp.__setitem__('E', elementary_flow_ref_ids)
            impact_factors = {(kpi, e): 2 for kpi in olca_dp.data('KPI') for e in olca_dp.data('E')}
            process_breakdown = {(e, f, p): 3 for e in olca_dp.data('E') for f in flows for p in processes}
            olca_dp.__setitem__('Ef', impact_factors)
            olca_dp.__setitem__('EF', process_breakdown)

        # db units
        olca_dp.load(filename=db_file, using='sqlite3',
                     query=sq.build_product_flow_units(process_ref_ids=processes),
                     param=self.abstract_model.UU, index=(self.abstract_model.F, self.abstract_model.P))


        # load locations
        p_m = list(olca_dp.data('P_m'))
        olca_dp.load(filename=db_file, using='sqlite3', query=sq.build_location(process_ref_ids=p_m),
                     param=(self.abstract_model.XI, self.abstract_model.YI))

        # use DataPortal to build concrete instance
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
        user_params = {
            'C': [{'index': [fm, k, d, t], 'value': 0}
                  for fm in user_sets['F_m'] for d in user_sets['D'] for k in user_sets['K']
                  for t in user_sets['T']],
            # kg to tonnes
            'U': [{'index': [fm, ft], 'value': 0.001}
                  for fm in user_sets['F_m'] for ft in user_sets['F_t']],
            'd': [{'index': [pm, fm, k, t], 'value': 0}
                  for pm in user_sets['P_m'] for fm in user_sets['F_m'] for k in user_sets['K']
                  for t in user_sets['T']],
            'X': [{'index': [k, t], 'value': math.inf} for k in user_sets['K'] for t in user_sets['T']],
            'Y': [{'index': [k, t], 'value': math.inf} for k in user_sets['K'] for t in user_sets['T']],
            'Demand': [{'index': [d, k, t], 'value': 0}
                       for d in user_sets['D'] for k in user_sets['K'] for t in user_sets['T']],
            'Total_Demand': [{'index': [d, k], 'value': 0}
                             for d in user_sets['D'] for k in user_sets['K']],
            'J': [{'index': [fm, pm, ft, pt], 'value': 0}
                  for fm in user_sets['F_m'] for pm in user_sets['P_m']
                  for ft in user_sets['F_t'] for pt in user_sets['P_t']],
            'L': [{'index': [fm, pm, fs, ps], 'value': 0}
                  for fm in user_sets['F_m'] for pm in user_sets['P_m']
                  for fs in user_sets['F_s'] for ps in user_sets['P_s']],
            'w': [{'index': [obj], 'value': 0} for obj in user_sets['OBJ']],
        }
        # flows = [f for k in ['F_m', 'F_s', 'F_t'] for f in user_sets[k]]
        # processes = [p for k in ['P_m', 'P_s', 'P_t'] for p in user_sets[k]]

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
        user_params['U'] = [{'index': [fm, ft], 'value': 2}
                            for fm in user_sets['F_m'] for ft in user_sets['F_t']]
        user_params['d'] = [{'index': [pm, fm, k, t], 'value': 2}
                            for pm in user_sets['P_m'] for fm in user_sets['F_m'] for k in user_sets['K'] for t in user_sets['T']]
        user_params['Total_Demand'] = [{'index': [d, k], 'value': 1}
                                       for d in user_sets['D'] for k in user_sets['K']]
        user_params['Demand'] = [{'index': [d, k, t], 'value': 1}
                                 for d in user_sets['D'] for k in user_sets['K'] for t in user_sets['T']]
        user_params['EI'] = [{'index': [kpi, f, p], 'value': 1}
                             for kpi in user_sets['KPI'] for f in user_sets['F'] for p in user_sets['P']]
        user_params['phi'] = [{'index': [f, p, t], 'value': 1}
                              for f in user_sets['F'] for p in user_sets['P'] for t in user_sets['T']]
        user_params['Ef'] = [{'index': [kpi, e], 'value': 4}
                             for kpi in user_sets['KPI'] for e in user_sets['E']]
        user_params['EF'] = [{'index': [e, f, p], 'value': 5}
                             for e in user_sets['E'] for f in user_sets['F'] for p in user_sets['P']]
        user_params['J'] = [{'index': [fm, pm, ft, pt], 'value': 0}
                            for fm in user_sets['F_m'] for pm in user_sets['P_m']
                            for ft in user_sets['F_t'] for pt in user_sets['P_t']]
        user_params['L'] = [{'index': [fm, pm, fs, ps], 'value': 1}
                            for fm in user_sets['F_m'] for pm in user_sets['P_m']
                            for fs in user_sets['F_s'] for ps in user_sets['P_s']]
        user_params['w'] = [{'index': [obj], 'value': 0} for obj in user_sets['OBJ']]

        return {**user_sets, **user_params}

    def get_param_dfr(self, filename, param_list=['C', 'U', 'Total_Demand', 'd', 'Demand', 'J', 'L']):
        user_dp = pyod.DataPortal()
        user_dp.load(filename=filename)
        config_instance = self.abstract_model.create_instance(user_dp)
        param_dfr = pd.DataFrame(
            ([o.name, o.doc, [index for index in o], [pe.value(o[index]) for index in o]]
             for o in config_instance.component_objects(pe.Param, active=True) if o.name in param_list),
            columns=['Param', 'Description', 'Index', 'Value']
        )

        return param_dfr

