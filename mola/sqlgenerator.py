"""
Module for generating SQL queries for a abstract model in a Specification
"""
from pypika import Query, Table
from pypika.terms import PseudoColumn
import pypika.functions as pf


def build_process_elementary_flow(process_ref_ids):
    """
    Build a query to create a table of processes versus elementary flows from a sqlite db
    sourced from derby.

    :param str[list] process_ref_ids: processes reference ids
    :return: SQL string
    """
    processes = Table('TBL_PROCESSES')
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    # flow_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))
    # e = Table('e')

    # find exchanges corresponding to process ref ids
    exchange_query = exchanges \
        .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))
        # .as_('e')

    # product flows
    product_flows = Query \
        .from_(exchange_query) \
        .left_join(flows).on(flows.ID == exchange_query.F_FLOW) \
        .select(flows.REF_ID, exchange_query.F_OWNER, exchange_query.RESULTING_AMOUNT_VALUE) \
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW') \
        .as_('product_flows')

    # left join exchanges to flow and process tables
    q = Query \
        .from_(exchange_query) \
        .left_join(flows).on(flows.ID == exchange_query.F_FLOW) \
        .left_join(processes).on(processes.ID == exchange_query.F_OWNER) \
        .left_join(product_flows).on(processes.ID == product_flows.F_OWNER) \
        .select(
            flows.REF_ID.as_('E'), product_flows.REF_ID.as_('F'),
            processes.REF_ID.as_('P'), exchange_query.RESULTING_AMOUNT_VALUE.as_('EF')
        ) \
        .where(flows.FlOW_TYPE == 'ELEMENTARY_FLOW')

    return str(q)


def build_impact_category_elementary_flow(ref_ids):
    """
    Build a query to create a table of impact category versus elementary flow from a sqlite openLCA
    database.

    :param str[list] ref_ids: list of impact category reference ids
    :return: SQL string
    """

    # table for joins
    impact_factors = Table('TBL_IMPACT_FACTORS')  # maps impact factors to impact categories
    impact_categories = Table('TBL_IMPACT_CATEGORIES')
    flows = Table('TBL_FLOWS')

    ic = impact_categories \
        .select(impact_categories.ID, impact_categories.REF_ID) \
        .where(impact_categories.REF_ID.isin(ref_ids)) \
        .as_('ic')

    # no need to select ELEMENTARY_FLOW
    q = Query\
        .from_(ic).as_('ic')\
        .left_join(impact_factors)\
        .on(impact_factors.F_IMPACT_CATEGORY == ic.ID) \
        .left_join(flows)\
        .on(impact_factors.F_FLOW == flows.ID)\
        .select(
            ic.REF_ID.as_('KPI'), flows.REF_ID.as_('E'),
            impact_factors.value.as_('Ef')
        )

    return str(q)


def build_location(process_ref_ids=None):
    """
    Create a table of longitudes and latitudes for each material process and its product flow.

    :param list[str] process_ref_ids: list of material process reference ids
    :return: SQL string
    """
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')
    e = Table('e')

    # convert reference ids to openLCA process ids
    process_id = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query exchanges table to limit
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_id)) \
        .as_('e')

    # join exchanges to flows
    q = Query\
        .from_(sq).as_('e') \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(
            processes.REF_ID.as_('P_m'), flows.REF_ID.as_('F_m'),
            locations.LONGITUDE.as_('X'), locations.LATITUDE.as_('Y')
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    return str(q)


# def build_product_flow(process_ref_ids=None):
#     """
#     Build a query to get processes and their product flows
#     :param list[str] process_ref_ids: list of process reference ids
#     :return: SQL string
#     """
#
#     exchanges = Table('TBL_EXCHANGES')
#     flows = Table('TBL_FLOWS')
#     processes = Table('TBL_PROCESSES')
#     locations = Table('TBL_LOCATIONS')
#     e = Table('e')
#
#     # convert reference ids to openLCA process ids
#     process_id = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))
#
#     # sub-query exchanges table to limit
#     sq = Query\
#         .from_(exchanges) \
#         .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
#         .where(exchanges.F_OWNER.isin(process_id)) \
#         .as_('e')
#
#     # join exchanges to flows
#     q = Query\
#         .from_(sq).as_('e') \
#         .left_join(flows).on(flows.ID == sq.F_FLOW) \
#         .left_join(processes).on(processes.ID == sq.F_OWNER) \
#         .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
#         .select(
#             processes.REF_ID.as_('PROCESS_REF_ID'), processes.NAME.as_('PROCESS_NAME'),
#             locations.NAME.as_('LOCATION'),
#             flows.REF_ID.as_('FLOW_REF_ID'), flows.NAME.as_('FLOW_NAME')
#         )\
#         .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')
#
#     return str(q)


def build_product_flow_units(process_ref_ids):
    """
    Build a query to get processes and their product flow units.

    :param list[str] process_ref_ids: list of process reference ids
    :return: SQL string
    """

    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    units = Table('TBL_UNITS')

    # convert reference ids to openLCA process ids
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query the exchanges table to limit join
    sq = Query \
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW,
                exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))

    # join exchanges to flows, processes, units
    q = Query\
        .from_(sq) \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(units).on(units.ID == sq.F_UNIT) \
        .select(
            flows.REF_ID.as_('F'), processes.REF_ID.as_('P'), units.NAME.as_('Units')
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    return str(q)


def build_product_flow_cost(process_ref_ids, time):
    """
    Build a query to get the product flow costs from a list of process reference ids using a sqlite openLCA database.

    :param sqlite3.Connection conn: database connection
    :param list[str] process_ref_ids: list of process reference ids
    :param list time: list of time labels
    :return SQL string
    """
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')

    # get the process ids from the ref ids
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query the exchanges table to limit join
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.COST_VALUE, exchanges.F_CURRENCY, exchanges.F_FLOW,
                exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))

    # join exchanges to flows, processes, locations
    first_time = PseudoColumn("'" + time[0] + "'")
    q = Query\
        .from_(sq) \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(
            flows.REF_ID.as_('F'), processes.REF_ID.as_('P'), first_time.as_('T'), sq.COST_VALUE
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    return str(q)
