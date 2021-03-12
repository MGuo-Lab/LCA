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
import pyomo.network as pn

import mola.sqlgenerator as sq
import mola.dataimport as di
import mola.build as mb

# units
pu.load_definitions_from_strings([
    'P = [Product_Flow]',
    'P_m = [Material_Product_Flow]',
    'P_s = [Service_Product_Flow]',
    'P_t = [Transport_Product_Flow]',
    'D = [Demand]',
    'KPI = [Key_Performance_Indicator]',
    'KPI_ref = [Reference_Key_Performance_Indicator]',
    'OBJ = [Objective]',
    'Output = [Output]',
])


class Specification:
    """ Abstract Specification of a Pyomo model for configuration in a GUI """
    name: str
    user_defined_sets: dict
    db_sets: dict
    user_defined_indexed_sets: dict
    db_indexed_sets: dict
    user_defined_parameters: dict
    controllers: dict
    default_settings: dict

    def __init__(self):
        if type(self) is Specification:
            raise NotImplementedError()

    def build_network(self):
        """ Dynamically build model network using Ports and Arcs """
        pass

    def populate(self, json_files: list, db_file: str):
        """ Make abstract model concrete using db_file and json files """
        pass

    def get_default_sets(self):
        """ Returns a dict of default sets """
        return {}

    def get_default_indexed_sets(self, sets):
        """ Returns a dict of default indexed sets """
        return {}

    def get_default_parameters(self, sets):
        """ Returns a dict of default parameters in index/value form """
        return {}

    def get_dummy_data(self):
        """ Not required. Returns a dict of sets and parameters that act as dummy data """
        return {}


class GeneralSpecification(Specification):
    """
    General pyomo specification
    """
    name = "General Specification"
    user_defined_sets = {
        'P_m': {'doc': 'Processes producing material flows in the optimisation problem', 'lookup': True},
        'P_t': {'doc': 'Processes producing transport flows in the optimisation problem', 'lookup': True},
        'P_s': {'doc': 'Processes producing service flows in the optimisation problem', 'lookup': True},
        'F_m': {'doc': 'Material flows to optimise', 'lookup': True},
        'F_t': {'doc': 'Transport flows to optimise', 'lookup': True},
        'F_s': {'doc': 'Service flows to optimise', 'lookup': True},
        'T': {'doc': 'Time intervals'},
        'K': {'doc': 'Tasks'},
        'D': {'doc': 'Demands'},
        'KPI': {'doc': 'Performance indicators for optimisation problem', 'lookup': True},
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
              'within': 'Binary', 'nodes': [1, 3], 'edges': [0, 2]},
        'X': {'index': ['K', 'T'], 'doc': 'Longitude', 'unit': pu.degree},
        'Y': {'index': ['K', 'T'], 'doc': 'Latitude', 'unit': pu.degree},
        'd': {'index': ['P_m', 'F_m', 'K', 'T'], 'doc': 'Distance', 'unit': pu.km},
        'J': {'index': ['F_m', 'P_m', 'F_t', 'P_t'],
              'doc': 'Binary conversion factor between material and transport flows', 'within': 'Binary',
              'nodes': [1, 3], 'edges': [0, 2]},
        'w': {'index': ['KPI'], 'doc': 'Environmental objective weights', 'unit': pu.KPI_ref/pu.KPI},
        'u': {'index': ['OBJ'], 'doc': 'Objective weights', 'unit': pu.Output/pu.OBJ},
        'calA': {'index': ['F_m', 'P_m', 'K', 'T'], 'doc': 'Material flow task coefficient'},
        'calB': {'index': ['F_m', 'P_m', 'K', 'T'], 'doc': 'Service flow task coefficient'},
        'calC': {'index': ['F_m', 'P_m', 'F_t', 'P_t', 'K', 'T'], 'doc': 'Transport flow task coefficient'},
        'Arc': {'index': ['K', 'K'], 'doc': 'Arc to link tasks',
                'within': 'Binary', 'nodes': [0, 1]},
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
        for s, d in self.user_defined_sets.items():
            abstract_model.add_component(s, pe.Set(doc=d['doc']))

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
        abstract_model.UU = pe.Param(abstract_model.F, abstract_model.P, default='', within=pe.Any)

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

        def objective_rule(model):
            return model.u['environment'] * sum(model.w[kpi] * environment_objective_rule(model, kpi)
                                                for kpi in model.KPI) + model.u['cost'] * cost_objective_rule(model)

        abstract_model.Environmental_Impact = pe.Objective(
            abstract_model.KPI, rule=environment_objective_rule,
            doc='Minimise the environmental impact using openLCA data')
        abstract_model.Cost = pe.Objective(rule=cost_objective_rule, doc='Minimise the cost using openLCA data')
        abstract_model.Environmental_Cost_Impact = pe.Objective(rule=objective_rule,
            doc='Minimise the environmental impact and cost using openLCA data')

        # constraints
        def flow_demand_rule(model, d, k):
            total_demand = sum(
                model.Flow[fm, pm, k, t] * model.C[fm, k, d, t]
                for fm in model.F_m for pm in model.P_m for t in model.T)
            return total_demand >= model.Total_Demand[d, k]
        abstract_model.total_demand_constraint = pe.Constraint(
            abstract_model.D, abstract_model.K, rule=flow_demand_rule)

        def material_flow_rule(model, fm, pm, k, t):
            return model.Flow[fm, pm, k, t] == sum(model.J[fm, pm, ft, pt] *
                                                   model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t]
                                                   for ft in model.F_t for pt in model.P_t)
        abstract_model.material_flow_constraint = \
            pe.Constraint(abstract_model.F_m, abstract_model.P_m,
                          abstract_model.K, abstract_model.T, rule=material_flow_rule)

        def specific_transport_flow_rule(model, ft, pt, k, t):
            rhs = 0
            # sum over connected processes
            for fm in model.F_m:
                for pm in model.P_m:
                    if model.J[fm, pm, ft, pt]:
                        unit_conversion = pu.convert_value(
                            1,
                            from_units=mb.map_units(model.UU[fm, pm]) * pu.km,
                            to_units=mb.map_units(model.UU[ft, pt])
                        )
                        rhs += model.J[fm, pm, ft, pt] * \
                               unit_conversion * \
                               model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t] * \
                               model.dd[pm, fm, k, t]

            return model.Specific_Transport_Flow[ft, pt, k, t] == rhs

        abstract_model.transport_constraint = pe.Constraint(abstract_model.F_t,
                                                            abstract_model.P_t,
                                                            abstract_model.K,
                                                            abstract_model.T,
                                                            rule=specific_transport_flow_rule)

        def demand_selection_rule(model, k, t):
            return sum(model.Demand_Selection[d, k, t] for d in model.D) == 1

        abstract_model.demand_selection_constraint = pe.Constraint(abstract_model.K,
                                                                        abstract_model.T,
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

        abstract_model.specific_demand_constraint = pe.Constraint(abstract_model.D,
                                                                  abstract_model.K,
                                                                  abstract_model.T,
                                                                  rule=specific_demand_rule)

        def service_flow_link_rule(model, fs, ps, k, t):
            return model.Storage_Service_Flow[fs, ps, k, t] == \
                   sum(model.L[fm, pm, fs, ps] * model.Storage_Service_Flow[fm, pm, k, t]
                       for fm in model.F_m for pm in model.P_m)

        abstract_model.service_flow_link_constraint = pe.Constraint(
            abstract_model.F_s, abstract_model.P_s, abstract_model.K, abstract_model.T, rule=service_flow_link_rule)

        def task_port_rule(model, k, t):
            port = dict()
            if len(model.calA) > 0:
                rhs1 = sum(model.calA[fm, pm, k, t] * model.Flow[fm, pm, k, t] +
                           model.calB[fm, pm, k, t] * model.Storage_Service_Flow[fm, pm, k, t] for
                           fm in model.F_m for pm in model.P_m)
                rhs2 = sum(model.calC[fm, pm, ft, pt, k, t] *
                           model.Specific_Material_Transport_Flow[fm, pm, ft, pt, k, t] for
                           fm in model.F_m for pm in model.P_m for ft in model.F_t for pt in model.P_t)
                port['flow'] = rhs1 + rhs2
            return port

        abstract_model.task_port = pn.Port(abstract_model.K, abstract_model.T, rule=task_port_rule)

        def task_arc_rule(model, from_k, to_k, t):
            d = dict()
            d['source'] = model.task_port[from_k, t]
            if from_k != to_k and model.Arc[from_k, to_k]:
                d['destination'] = model.task_port[to_k, t]
            else:
                d['destination'] = model.task_port[from_k, t]
            return d

        abstract_model.task_link = pe.Set(within=abstract_model.K * abstract_model.K)

        abstract_model.task_arc = pn.Arc(abstract_model.task_link, abstract_model.T,
                                         rule=task_arc_rule)


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

            # db units TODO: allow the user to define the unit conversion using a setting and model.U
            olca_dp.load(filename=db_file, using='sqlite3',
                         query=sq.build_product_flow_units(process_ref_ids=processes),
                         param=self.abstract_model.UU, index=(self.abstract_model.F, self.abstract_model.P))

        else:
            # for testing
            olca_dp.__setitem__('E', elementary_flow_ref_ids)
            impact_factors = {(kpi, e): 2 for kpi in olca_dp.data('KPI') for e in olca_dp.data('E')}
            process_breakdown = {(e, f, p): 3 for e in olca_dp.data('E') for f in flows for p in processes}
            olca_dp.__setitem__('Ef', impact_factors)
            olca_dp.__setitem__('EF', process_breakdown)

        # load locations
        p_m = list(olca_dp.data('P_m'))
        olca_dp.load(filename=db_file, using='sqlite3', query=sq.build_location(process_ref_ids=p_m),
                     param=(self.abstract_model.XI, self.abstract_model.YI))

        # Generate task edges TODO: use an indexed set rather than a parameter
        edges = [(k1, k2) for k1 in olca_dp.data('K') for k2 in olca_dp.data('K')
                 if 'Arc' in olca_dp.keys() and olca_dp.data('Arc')[k1, k2]]
        olca_dp.__setitem__('task_link', edges)

        # use DataPortal to build concrete instance
        model_instance = self.abstract_model.create_instance(olca_dp)

        # Generate the constraints for the tasks
        pe.TransformationFactory("network.expand_arcs").apply_to(model_instance)

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

    def get_default_parameters(self, user_sets, user_indexed_sets=[]):
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
            'w': [{'index': [kpi], 'value': 0} for kpi in user_sets['KPI']],
            'u': [{'index': [obj], 'value': 1} for obj in user_sets['OBJ']],
            'calA': [{'index': [fm, pm, k, t], 'value': 0}
                     for fm in user_sets['F_m'] for pm in user_sets['P_m']
                     for k in user_sets['K'] for t in user_sets['T']],
            'calB': [{'index': [fm, pm, k, t], 'value': 0}
                     for fm in user_sets['F_m'] for pm in user_sets['P_m']
                     for k in user_sets['K'] for t in user_sets['T']],
            'calC': [{'index': [fm, pm, ft, pt, k, t], 'value': 0}
                     for fm in user_sets['F_m'] for pm in user_sets['P_m']
                     for ft in user_sets['F_t'] for pt in user_sets['P_t']
                     for k in user_sets['K'] for t in user_sets['T']],
            'Arc': [{'index': [k1, k2], 'value': 0}
                    for k1 in user_sets['K'] for k2 in user_sets['K']],
        }

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
        user_params['w'] = [{'index': [kpi], 'value': 0} for kpi in user_sets['KPI']]
        user_params['u'] = [{'index': [obj], 'value': 1} for obj in user_sets['OBJ']]

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


class SimpleSpecification(Specification):
    """
    Simple pyomo specification
    """
    name = "Simple Specification"
    user_defined_sets = {
        'P_m': {'doc': 'Processes producing material flows in the optimisation problem', 'lookup': True},
        'P_t': {'doc': 'Processes producing transport flows in the optimisation problem', 'lookup': True},
        'F_m': {'doc': 'Material flows to optimise', 'lookup': True},
        'F_t': {'doc': 'Transport flows to optimise', 'lookup': True},
        'D': {'doc': 'Demands'},
        'KPI': {'doc': 'Performance indicators for optimisation problem', 'lookup': True},
    }
    db_sets = {
        'E': 'Elementary Flows in OpenLCA database',
    }
    user_defined_parameters = {
        'C': {'index': ['F_m', 'D'], 'doc': 'Conversion factor for material flows', 'unit': pu.D/pu.P_m},
        'U': {'index': ['F_m', 'F_t'],
              'doc': '(NOT USED) Conversion factor for material flow units in transport flow units',
              'unit': pu.P_t / pu.P_m},
        'Demand': {'index': ['D'], 'doc': 'Specific demand', 'unit': pu.D},
        'Total_Demand': {'index': ['D'], 'doc': 'Total demand', 'unit': pu.D},
        'd': {'index': ['P', 'F_m'], 'doc': 'Distance', 'unit': pu.km},
        'J': {'index': ['F_m', 'P_m', 'F_t', 'P_t'],
              'doc': 'Binary conversion factor between material and transport flows', 'within': 'Binary',
              'nodes': [1, 3], 'edges': [0, 2]},
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
        for s, d in self.user_defined_sets.items():
            abstract_model.add_component(s, pe.Set(doc=d['doc']))

        abstract_model.F = abstract_model.F_m | abstract_model.F_t
        abstract_model.P = abstract_model.P_m | abstract_model.P_t

        # set of objectives
        abstract_model.OBJ = pe.Set(doc='Set of objective functions')

        # database sets
        for var, doc in self.db_sets.items():
            abstract_model.add_component(var, pe.Set(doc=doc))

        # user-defined parameters
        for param, val in self.user_defined_parameters.items():
            idx = [abstract_model.component(i) for i in val['index']]
            if 'within' in val and val['within'] == 'Binary':
                within = pe.Binary
            else:
                within = pe.Reals
            abstract_model.add_component(param, pe.Param(*idx, doc=val['doc'], within=within))

        # database parameters
        abstract_model.Ef = pe.Param(abstract_model.KPI, abstract_model.E, default=0)
        abstract_model.EF = pe.Param(abstract_model.E, abstract_model.F, abstract_model.P, default=0)

        def ei_rule(model, kpi, f, p):
            return sum(model.Ef[kpi, e]*model.EF[e, f, p] for e in model.E)
        abstract_model.EI = pe.Param(abstract_model.KPI, abstract_model.F, abstract_model.P, rule=ei_rule)

        # unit conversion factors
        abstract_model.UU = pe.Param(abstract_model.F, abstract_model.P, within=pe.Any)

        # variables
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
        abstract_model.Environmental_Impact = pe.Objective(abstract_model.KPI, rule=objective_rule,
                                                           doc='Minimise the environmental impact using openLCA data')

        # constraints
        def flow_demand_rule(model, d):
            total_demand = sum(
                model.Flow[fm, pm] * model.C[fm, d]
                for fm in model.F_m for pm in model.P_m)
            return total_demand >= model.Total_Demand[d]
        abstract_model.total_demand_constraint = pe.Constraint(abstract_model.D, rule=flow_demand_rule)

        def material_flow_rule(model, fm, pm):
            return model.Flow[fm, pm] == sum(
                model.J[fm, pm, ft, pt] * model.Specific_Material_Transport_Flow[fm, pm, ft, pt]
                for ft in model.F_t for pt in model.P_t)
        abstract_model.material_flow_constraint = \
            pe.Constraint(abstract_model.F_m, abstract_model.P_m, rule=material_flow_rule)

        def specific_transport_flow_rule(model, ft, pt):
            rhs = 0
            # sum over connected processes
            for fm in model.F_m:
                for pm in model.P_m:
                    if model.J[fm, pm, ft, pt]:
                        unit_conversion = pu.convert_value(
                            1,
                            from_units=mb.map_units(model.UU[fm, pm]) * pu.km,
                            to_units=mb.map_units(model.UU[ft, pt])
                        )
                        rhs += model.J[fm, pm, ft, pt] * \
                               unit_conversion * \
                               model.Specific_Material_Transport_Flow[fm, pm, ft, pt] * \
                               model.d[pm, fm]
            return model.Specific_Transport_Flow[ft, pt] == rhs

        abstract_model.transport_constraint = pe.Constraint(abstract_model.F_t,
                                                            abstract_model.P_t,
                                                            rule=specific_transport_flow_rule)

        def demand_selection_rule(model):
            return sum(model.Demand_Selection[d] for d in model.D) == 1

        abstract_model.demand_selection_constraint = pe.Constraint(rule=demand_selection_rule)

        def specific_demand_rule(model, d):
            total_flow = sum(model.Flow[fm, pm] * model.C[fm, d]
                             for fm in model.F_m for pm in model.P_m)
            return total_flow >= model.Demand[d] * model.Demand_Selection[d]

        abstract_model.specific_demand_constraint = pe.Constraint(abstract_model.D,
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

        # db units
        olca_dp.load(filename=db_file, using='sqlite3',
                     query=sq.build_product_flow_units(process_ref_ids=processes),
                     param=self.abstract_model.UU, index=(self.abstract_model.F, self.abstract_model.P))


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

    def get_default_parameters(self, user_sets, user_indexed_sets=[]):
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


class AIMMSExampleSpecification(Specification):
    """
    A Mola Specification class containing an abstract model to solve the AIMMS simple tutorial problem.
    """
    name = "AIMMS Example Specification"
    user_defined_sets = {
        'P': {'doc': 'Plants'},
        'C': {'doc': 'Customers'},
    }
    user_defined_parameters = {
        'S': {'index': ['P'], 'doc': 'Supply available at plant p'},
        'D': {'index': ['C'], 'doc': 'Demand required by customer c'},
        'U': {'index': ['P', 'C'], 'doc': 'Cost per unit'},
    }
    # db parameters need to be constructed explicitly
    controllers = {"Standard": "StandardController"}
    default_settings = {
    }

    def __init__(self):

        # instance object to hold just the setting values
        self.settings = {k: v['value'] for k, v in self.default_settings.items()}

        # setup abstract model
        abstract_model = self.abstract_model = pe.AbstractModel()

        # user-defined sets
        for var, d in self.user_defined_sets.items():
            abstract_model.add_component(var, pe.Set(doc=d['doc']))

        # user-defined parameters
        for param, val in self.user_defined_parameters.items():
            idx = [abstract_model.component(i) for i in val['index']]
            abstract_model.add_component(param, pe.Param(*idx, doc=val['doc'], within=pe.Reals))

        # variables
        abstract_model.x = pe.Var(abstract_model.P, abstract_model.C,
                                  within=pe.NonNegativeIntegers, doc='Number of units')

        # objective
        def objective_rule(model):
            return sum(model.U[p, c] * model.x[p, c] for p in model.P for c in model.C)
        abstract_model.Minimise_Cost = pe.Objective(rule=objective_rule, doc="Minimise the cost of moving beer")

        # constraints
        def supply_rule(model, p):
            return sum([model.x[p, c] for c in model.C]) <= model.S[p]
        abstract_model.supply_constraint = pe.Constraint(abstract_model.P, rule=supply_rule)

        def demand_rule(model, c):
            return sum([model.x[p, c] for p in model.P]) >= model.D[c]
        abstract_model.demand_constraint = pe.Constraint(abstract_model.C, rule=demand_rule)

    def populate(self, json_files=None, elementary_flow_ref_ids=None, db_file=None):

        olca_dp = pyod.DataPortal()

        # user data
        for json_file in json_files:
            if json_file:
                olca_dp.load(filename=json_file)

        # use DataPortal to build concrete instance
        model_instance = self.abstract_model.create_instance(olca_dp)

        return model_instance

    def get_default_sets(self, d=None):
        user_sets = {
            'P': [],
            'C': [],
        }
        if d is not None:
            user_sets.update(d)

        return user_sets

    def get_default_parameters(self, user_sets, user_indexed_sets=[]):
        user_params = {
            'S': [{'index': [p], 'value': 0} for p in user_sets['P']],
            'D': [{'index': [c], 'value': 0} for c in user_sets['C']],
            'U': [{'index': [p, c], 'value': 0}
                  for p in user_sets['P'] for c in user_sets['C']],
        }

        return user_params


class KondiliSpecification(Specification):
    """
    A Mola Specification class containing the abstract state task model in Kondili et al. 1993.
    """
    name = "Kondili Specification"
    user_defined_sets = {
        'States': {'doc': 'States'},
        'I': {'doc': 'Tasks'},
        'J': {'doc': 'Units'},
    }
    user_defined_indexed_sets = {
        'SI': {'index': ['I'], 'doc': 'States that feed task i', 'within': ['States']},
        'S_barI': {'index': ['I'], 'doc': 'States produced by task i', 'within': ['States']},
        'KI': {'index': ['I'], 'doc': 'Units capable of performing task i', 'within': ['J']},
    }
    user_defined_parameters = {
        'H': {'doc': 'Time horizon'},
        'C': {'index': ['States'], 'doc': 'Maximum storage capacity dedicated to state s'},
        'M': {'doc': 'Allocation constraint parameter'},
        'P': {'index': ['States', 'I'], 'doc': 'Processing time for the output of task i to state s'},
        'rho': {'index': ['States', 'I'], 'doc': 'Proportion of input of task i from state s'},
        'rho_bar': {'index': ['States', 'I'], 'doc': 'Proportion of output of task i to state s'},
        'V_min': {'index': ['I', 'J'], 'doc': 'Minimum capacity of unit j when used for performing task i'},
        'V_max': {'index': ['I', 'J'], 'doc': 'Maximum capacity of unit j when used for performing task i'},
    }
    # db parameters need to be constructed explicitly
    controllers = {"Standard": "StandardController"}
    default_settings = {
    }

    def __init__(self):

        # instance object to hold just the setting values
        self.settings = {k: v['value'] for k, v in self.default_settings.items()}

        # setup abstract model
        abstract_model = self.abstract_model = pe.AbstractModel()

        # user-defined sets
        for s, d in self.user_defined_sets.items():
            abstract_model.add_component(s, pe.Set(doc=d['doc']))

        # user-defined indexed sets
        for s, val in self.user_defined_indexed_sets.items():
            idx = [abstract_model.component(i) for i in val['index']]
            abstract_model.add_component(s, pe.Set(*idx, doc=val['doc'],
                                                   within=abstract_model.component(val['within'][0])))

        # built in model sets
        abstract_model.T = pe.Set(doc='Time Periods')
        abstract_model.K_I = pe.Set(within=abstract_model.J * abstract_model.I,
                                    doc='Units capable of performing task i')
        abstract_model.S_I = pe.Set(within=abstract_model.States * abstract_model.I,
                                    doc='States that feed task i')
        abstract_model.S_bar_I = pe.Set(within=abstract_model.States * abstract_model.I,
                                        doc='States produced by task i')

        abstract_model.TS = pe.Set(abstract_model.States, within=abstract_model.I)
        abstract_model.T_S = pe.Set(within=abstract_model.I * abstract_model.States,
                                    doc='Tasks receiving material from state s')

        abstract_model.T_barS = pe.Set(abstract_model.States, within=abstract_model.I)
        abstract_model.T_bar_S = pe.Set(within=abstract_model.I * abstract_model.States,
                                        doc='Tasks producing material in state s')

        abstract_model.IJ = pe.Set(abstract_model.J, within=abstract_model.I)
        abstract_model.I_J = pe.Set(within=abstract_model.I * abstract_model.J,
                                    doc='Tasks that can be performed by unit j')

        # user-defined parameters
        for param, val in self.user_defined_parameters.items():
            print(param)
            if 'index' in val:
                idx = [abstract_model.component(i) for i in val['index']]
                abstract_model.add_component(param, pe.Param(*idx, doc=val['doc'], within=pe.Reals))
            else:
                abstract_model.add_component(param, pe.Param(doc=val['doc'], within=pe.Reals))

        def p_rule(model, i):
            return max(model.P[s, i] for s in model.S_barI[i])
        abstract_model.p = pe.Param(abstract_model.I, initialize=p_rule, doc='Completion time for task i')

        # variables
        abstract_model.W = pe.Var(abstract_model.I_J, abstract_model.T,
                                  doc='Start task k using unit j at time t', within=pe.Binary)

        abstract_model.B = pe.Var(abstract_model.I_J, abstract_model.T,
                                  doc='Amount of material which starts undergoing task i in unit j at beginning of t',
                                  within=pe.NonNegativeReals)

        abstract_model.S = pe.Var(abstract_model.States, abstract_model.T,
                                  doc='Amount of material stored in state s at beginning of t',
                                  within=pe.NonNegativeReals)

        abstract_model.Q = pe.Var(abstract_model.J, abstract_model.T,
                                  doc='Amount of material in unit j at the beginning of time t',
                                  within=pe.NonNegativeReals)

        # objective TODO: set as a parameter
        def cost_rule(model, s, t):
            if s in ['Feed A', 'Feed B', 'Feed C']:
                cost = 0.0
            elif s in ['Hot A', 'Int BC', 'Int AB', 'Impure E']:
                cost = -1.0
            elif s in ['Product 1', 'Product 2']:
                cost = 10.0
            return cost

        abstract_model.Cost = pe.Param(abstract_model.States, abstract_model.T, initialize=cost_rule,
                                       doc='Unit price of material in state s at time t')

        abstract_model.D = pe.Param(abstract_model.States, abstract_model.T, default=0,
                                    doc='Delivery of material in state s at time t')
        abstract_model.R = pe.Param(abstract_model.States, abstract_model.T, default=0,
                                    doc='Receipt of material in state s at time t')

        def profit_rule(model):
            value_products = sum(model.Cost[s, model.H] * model.S[s, model.H] +
                             sum(model.Cost[s, t] * model.D[s, t] for t in model.T if t < model.H)
                                 for s in model.States)
            return value_products

        abstract_model.obj = pe.Objective(rule=profit_rule, doc='Maximisation of Profit', sense=pe.maximize)

        # constraints
        def allocation_constraints_rule(model, i, j, t):
            lhs = sum(model.W[idash, j, tdash] for tdash in model.T for idash in model.IJ[j]
                      if tdash >= t and tdash <= t + model.p[i] - 1) - 1
            rhs = model.M * (1 - model.W[i, j, t])
            return lhs <= rhs

        abstract_model.allocation_constraints = pe.Constraint(abstract_model.I_J, abstract_model.T,
                                                              rule=allocation_constraints_rule)

        def capacity_limitations_rule1a(model, j, i, t):
            return model.W[i, j, t] * model.V_min[i, j] <= model.B[i, j, t]

        abstract_model.capacity_limitations1a = pe.Constraint(abstract_model.K_I, abstract_model.T,
                                                              rule=capacity_limitations_rule1a)

        def capacity_limitations_rule1b(model, j, i, t):
            return model.B[i, j, t] <= model.W[i, j, t] * model.V_max[i, j]

        abstract_model.capacity_limitations1b = pe.Constraint(abstract_model.K_I, abstract_model.T,
                                                              rule=capacity_limitations_rule1b)

        def capacity_limitations_rule2(model, s, t):
            return pe.inequality(0, model.S[s, t], model.C[s])

        abstract_model.capacity_limitations2 = pe.Constraint(abstract_model.States, abstract_model.T,
                                                             rule=capacity_limitations_rule2)

        def unit_balances_rule(model, j, t):
            if t == model.T.first():
                rhs = 0
            else:
                rhs = model.Q[j, t - 1]
            rhs += sum(model.B[i, j, t] for i in model.IJ[j])
            for i in model.IJ[j]:
                for s in model.S_barI[i]:
                    if t >= model.P[s, i]:
                        rhs -= model.rho_bar[s, i] * model.B[i, j, t - model.P[s, i]]
            return model.Q[j, t] == rhs

        abstract_model.unit_balances = pe.Constraint(abstract_model.J, abstract_model.T, rule=unit_balances_rule)

        def terminal_unit_rule(model, j):
            return model.Q[j, model.H] == 0

        abstract_model.terminal_unit = pe.Constraint(abstract_model.J, rule=terminal_unit_rule)

        # TODO: set as a parameter
        init_S = {
            'Feed A': 200, 'Feed B': 200, 'Feed C': 200,
            'Hot A': 0, 'Int BC': 0, 'Int AB': 0, 'Impure E': 0,
            'Product 1': 0, 'Product 2': 0
        }

        def material_balances_rule(model, s, t):
            if t == model.T.first():
                rhs = init_S[s]
            else:
                rhs = model.S[s, t - 1]
            if s in model.T_barS.keys():
                for i in model.T_barS[s]:
                    rhs += model.rho_bar[s, i] * sum(model.B[i, j, t - model.P[s, i]]
                                                     for j in model.KI[i] if t >= model.P[s, i])
            if s in model.TS.keys():
                for i in model.TS[s]:
                    rhs -= model.rho[s, i] * sum(model.B[i, j, t] for j in model.KI[i])
            return model.S[s, t] == rhs + model.R[s, t] - model.D[s, t]

        abstract_model.material_balances = pe.Constraint(abstract_model.States, abstract_model.T,
                                                         rule=material_balances_rule)


    def populate(self, json_files=None, elementary_flow_ref_ids=None, db_file=None):

        olca_dp = pyod.DataPortal()

        # user data
        for json_file in json_files:
            if json_file:
                olca_dp.load(filename=json_file)

        # built-in sets
        map_I_J = {}
        for i, units in olca_dp.data('KI').items():
            for j in units:
                map_I_J.setdefault(j, []).append(i)
        olca_dp.__setitem__('IJ', map_I_J)
        olca_dp.__setitem__('I_J', [(i, j) for j in map_I_J.keys() for i in map_I_J[j]])

        map_T_S = {}
        for i, states in olca_dp.data('SI').items():
            for s in states:
                map_T_S.setdefault(s, []).append(i)
        olca_dp.__setitem__('TS', map_T_S)
        olca_dp.__setitem__('T_S', [(t, s) for s in map_T_S.keys() for t in map_T_S[s]])

        map_T_bar_S = {}
        for i, states in olca_dp.data('S_barI').items():
            for s in states:
                map_T_bar_S.setdefault(s, []).append(i)
        olca_dp.__setitem__('T_barS', map_T_bar_S)
        olca_dp.__setitem__('T_bar_S', [(t, s) for s in map_T_bar_S.keys() for t in map_T_bar_S[s]])

        olca_dp.__setitem__('S_I', [(s, i) for i in olca_dp.data('SI').keys() for s in olca_dp.data('SI')[i]])
        olca_dp.__setitem__('S_bar_I',
                            [(s, i) for i in olca_dp.data('S_barI').keys() for s in olca_dp.data('S_barI')[i]])
        olca_dp.__setitem__('K_I', [(j, i) for i in olca_dp.data('KI').keys() for j in olca_dp.data('KI')[i]])

        # built-in parameters
        olca_dp.__setitem__('T', range(0, int(olca_dp.data('H')) + 1))

        # use DataPortal to build concrete instance
        model_instance = self.abstract_model.create_instance(olca_dp)

        return model_instance

    def get_default_sets(self, d=None):
        user_sets = {
            'States': ['Feed A', 'Feed B', 'Feed C', 'Hot A', 'Int BC', 'Int AB', 'Impure E', 'Product 1', 'Product 2'],
            'I': ['Heating', 'Reaction 1', 'Reaction 2', 'Reaction 3', 'Separation'],
            'J': ['Heater', 'Reactor 1', 'Reactor 2', 'Still']
        }
        if d is not None:
            user_sets.update(d)

        return user_sets

    def get_default_indexed_sets(self, user_sets, d=None):
        map_S_I = {
            'Heating': ['Feed A'],
            'Reaction 1': ['Feed B', 'Feed C'],
            'Reaction 2': ['Hot A', 'Int BC'],
            'Reaction 3': ['Int AB', 'Feed C'],
            'Separation': ['Impure E']
        }
        map_S_bar_I = {
            'Heating': ['Hot A'],
            'Reaction 1': ['Int BC'],
            'Reaction 2': ['Product 1', 'Int AB'],
            'Reaction 3': ['Impure E'],
            'Separation': ['Product 2', 'Int AB']
        }
        map_K_I = {
            'Heating': ['Heater'],
            'Reaction 1': ['Reactor 1', 'Reactor 2'],
            'Reaction 2': ['Reactor 1', 'Reactor 2'],
            'Reaction 3': ['Reactor 1', 'Reactor 2'],
            'Separation': ['Still']
        }

        user_indexed_sets = {
            'SI': {i: map_S_I.setdefault(i, []) for i in user_sets['I']},
            'S_barI': {i: map_S_bar_I.setdefault(i, []) for i in user_sets['I']},
            'KI': {i: map_K_I.setdefault(i, []) for i in user_sets['I']},
        }
        if d is not None:
            user_indexed_sets.update(d)

        return user_indexed_sets

    def get_default_parameters(self, user_sets, user_indexed_sets=[]):
        map_C = {
            'Feed A': float('inf'), 'Feed B': float('inf'), 'Feed C': float('inf'),
            'Hot A': 100, 'Int BC': 150, 'Int AB': 200, 'Impure E': 100,
            'Product 1': float('inf'), 'Product 2': float('inf')}
        map_P = {
            ('Hot A', 'Heating'): 1,
            ('Int BC', 'Reaction 1'): 2,
            ('Product 1', 'Reaction 2'): 2,
            ('Int AB', 'Reaction 2'): 2,
            ('Impure E', 'Reaction 3'): 1,
            ('Product 2', 'Separation'): 1,
            ('Int AB', 'Separation'): 2
        }
        map_rho = {
            ('Feed A', 'Heating'): 1,
            ('Feed B', 'Reaction 1'): 0.5,
            ('Feed C', 'Reaction 1'): 0.5,
            ('Hot A', 'Reaction 2'): 0.4,
            ('Int BC', 'Reaction 2'): 0.6,
            ('Feed C', 'Reaction 3'): 0.2,
            ('Int AB', 'Reaction 3'): 0.8,
            ('Impure E', 'Separation'): 1
        }
        map_rho_bar = {
            ('Hot A', 'Heating'): 1,
            ('Int BC', 'Reaction 1'): 1,
            ('Product 1', 'Reaction 2'): 0.4,
            ('Int AB', 'Reaction 2'): 0.6,
            ('Impure E', 'Reaction 3'): 1,
            ('Product 2', 'Separation'): 0.9,
            ('Int AB', 'Separation'): 0.1
        }
        map_V_max = {
            ('Heating', 'Heater'): 100,
            ('Reaction 1', 'Reactor 1'): 80,
            ('Reaction 2', 'Reactor 1'): 80,
            ('Reaction 3', 'Reactor 1'): 80,
            ('Reaction 1', 'Reactor 2'): 50,
            ('Reaction 2', 'Reactor 2'): 50,
            ('Reaction 3', 'Reactor 2'): 50,
            ('Separation', 'Still'): 200
        }
        # ensure the indexed sets are well-defined using their dataframe representation
        indexed_sets = mb.build_indexed_sets(user_sets, user_indexed_sets, self)
        map_I_J = {}
        for r, row in indexed_sets['KI'].iterrows():
            for j in row['Members']:
                map_I_J.setdefault(j, []).append(row['Index'])
        user_params = {
            'C': [{'index': [s], 'value': map_C.setdefault(s, 0)} for s in user_sets['States']],
            'H': 10.0,
            'M': 40.0,
            'P': [{'index': [member, row['Index']], 'value': map_P[member, row['Index']]}
                  for i, row in indexed_sets['S_barI'].iterrows()
                  for member in row['Members']],
            'rho': [{'index': [member, row['Index']], 'value': map_rho[member, row['Index']]}
                    for i, row in indexed_sets['SI'].iterrows()
                    for member in row['Members']],
            'rho_bar': [{'index': [member, row['Index']], 'value': map_rho_bar[member, row['Index']]}
                        for i, row in indexed_sets['S_barI'].iterrows()
                        for member in row['Members']],
            'V_min': [{'index': [t, unit], 'value': 0} for unit, tasks in map_I_J.items() for t in tasks],
            'V_max': [{'index': [t, unit], 'value': map_V_max[t, unit]}
                      for unit, tasks in map_I_J.items() for t in tasks],
        }

        return user_params

