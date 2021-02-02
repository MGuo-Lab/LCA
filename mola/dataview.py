"""
Views of openLCA data

Functions designed to give reasonable looking output on the console or in a Jupyter script.
"""
import pandas as pd
from pypika import Query, Table, Criterion
import pypika.functions as pf

from mola import Package


def get_df(conn, q, chunk_size=None):
    if Package.config('show.SQL'):
        print(q)
    df = pd.read_sql(str(q), conn, chunksize=chunk_size)
    return df


def get_table_names(conn):
    """
    Get table names from sqlite database.

    :param sqlite3.Connection conn: database connection
    :return: Dataframe
    """
    sqlite_master = Table('sqlite_master')
    q = Query\
        .from_(sqlite_master)\
        .select('name')\
        .where(sqlite_master.type == 'table')\
        .where(sqlite_master.name.not_like('sqlite_'))

    dfr = get_df(conn, q)
    return dfr.iloc[:, 0].to_list()


def get_table(conn, name, chunk_size=None):
    """
    Get table from sqlite database.

    :param sqlite3.Connection conn: database connection
    :param str name: name of table
    :param int chunk_size: if specified, return an iterator where chunk_size
    is the number of rows to include in each chunk.
    :return: Dataframe or iterator
    """
    tbl = Table(name)
    q = Query \
        .from_(tbl) \
        .select('*')
    dfr = get_df(conn, q, chunk_size)
    return dfr


def get_ref_ids(conn, ids, table_name):
    """
    Get reference ids from ids in a table
    :param conn: database connection
    :param ids: list of ids
    :param table_name: name of table
    :return: dict
    """
    tbl = Table(table_name)
    q = tbl.select(tbl.REF_ID).where(tbl.ID.isin(ids))
    # TODO: update these calls to use get_df
    dfr = pd.read_sql(str(q), conn).to_dict('list')
    return dfr


def get_ids(conn, ref_ids, table_name):
    """
    Get ids from ref ids in a table
    :param conn: database connection
    :param ref_ids: list of ref_ids or a ref_id
    :param table_name: name of table
    :return: dict
    """
    if not isinstance(ref_ids, list):
        ref_ids = [ref_ids]
    tbl = Table(table_name)
    q = tbl.select(tbl.ID, tbl.REF_ID).where(tbl.REF_ID.isin(ref_ids))
    dfr = pd.read_sql(str(q), conn)
    return dict(zip(dfr.ID, dfr.REF_ID))


def get_ref_id_dicts(conn, table_dict):
    """
    Get distionary of ref id -> name for each table in table_dict
    :param conn: database connection
    :param table_dict: dict of table names
    :return: dictionary using keys of table_dict
    """
    d = {}
    for k, v in table_dict.items():
        tbl = Table(v)
        q = Query \
            .from_(tbl) \
            .select(tbl.REF_ID, tbl.NAME)
        print(q)
        d[k] = pd.read_sql(str(q), conn, index_col='REF_ID').to_dict()['NAME']

    # additional mappings
    tbl = Table('TBL_FLOWS')
    q = Query \
        .from_(tbl) \
        .select(tbl.REF_ID, tbl.NAME) \
        .where(tbl.FLOW_TYPE == 'PRODUCT_FLOW')
    print(q)
    d['product_flows'] = pd.read_sql(str(q), conn, index_col='REF_ID').to_dict()['NAME']

    return d


def get_lookup_tables(conn, single_column=False):
    """
    Get tables of ref id, name etc. for each relevant table in db
    :param sqlite3.Connection conn: database connection
    :param boolean single_column: get lookup as single value
    :return: dictionary using keys of table_dict
    """

    # simple REF_ID, NAME tables
    table_dict = {
        'categories': 'TBL_CATEGORIES'
    }
    d = {}
    for k, v in table_dict.items():
        tbl = Table(v)
        q = Query \
            .from_(tbl) \
            .select(tbl.REF_ID, tbl.NAME)
        d[k] = pd.read_sql(str(q), conn, index_col='REF_ID')

    # flows
    flows = Table('TBL_FLOWS')
    q = Query \
        .from_(flows) \
        .select(flows.REF_ID.as_('FLOW_REF_ID'), flows.NAME)
    d['flows'] = pd.read_sql(str(q), conn, index_col='FLOW_REF_ID')

    # processes
    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')
    q = Query \
        .from_(processes) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(processes.REF_ID.as_('PROCESS_REF_ID'), processes.NAME.as_('PROCESS_NAME'),
                locations.NAME.as_('LOCATION_NAME'))  # FIXME
    d['processes'] = pd.read_sql(str(q), conn, index_col='PROCESS_REF_ID')
    d['P'] = d['P_m'] = d['P_s'] = d['P_t'] = d['processes']

    # product flows
    flows = Table('TBL_FLOWS')
    q = Query \
        .from_(flows) \
        .select(flows.REF_ID, flows.NAME) \
        .where(flows.FLOW_TYPE == 'PRODUCT_FLOW')
    d['product_flows'] = pd.read_sql(str(q), conn, index_col='REF_ID')
    d['F'] = d['F_m'] = d['F_s'] = d['F_t'] = d['product_flows']

    # impact categories
    categories = Table('TBL_IMPACT_CATEGORIES')
    methods = Table('TBL_IMPACT_METHODS')
    q = Query \
        .from_(categories) \
        .left_join(methods).on(categories.F_IMPACT_METHOD == methods.ID) \
        .select(
            methods.NAME.as_('method_NAME'),
            categories.REF_ID.as_('REF_ID'), categories.NAME.as_('category_NAME')
        )
    d['KPI'] = pd.read_sql(str(q), conn, index_col='REF_ID')

    # only return a single joined column in data frame
    if single_column:
        lookup = d
        for k in lookup.keys():
            s = pd.Series(lookup[k].fillna('').values.tolist()).str.join(' | ')
            s.index = lookup[k].index
            lookup[k] = pd.DataFrame({k: s})
        d = lookup

    return d


def get_exchanges(conn, id, columns=['ID', 'F_OWNER', 'F_FLOW', 'F_UNIT', 'RESULTING_AMOUNT_VALUE']):
    """
    Get exchanges from sqlite database.

    :param conn: database connection
    :param id: exchange id
    :param columns: names of columns to retrieve
    :return: Dataframe
    """

    exchanges = Table('TBL_EXCHANGES')
    q = Query \
        .from_(exchanges) \
        .select(*columns) \
        .where(exchanges.ID == id)
    sql_stmt = str(q)
    print(sql_stmt)
    dfr = pd.read_sql(sql_stmt, conn)

    return dfr


def get_impact_category_ref_ids(conn, method_name=None, category_name=None):
    """
    Get impact category reference ids from openLCA database.

    :param conn: database connection
    :param method_name: list of partial method names on which to filter
    :param category_name: list of partial category names on which to filter
    :return: list of reference ids
    """
    dfr = get_impact_categories(conn, method_name=method_name, category_name=category_name,
                                categories_columns=['REF_ID'])
    return dfr['categories_REF_ID'].to_list()


def get_impact_categories(conn, method_name=None, category_name=None,
                          methods_columns=['ID', 'REF_ID', 'NAME'],
                          categories_columns=['ID', 'REF_ID', 'NAME', 'REFERENCE_UNIT']):
    """
    Get impact categories from sqlite openLCA database. Each category is part of a method but it uniquely
    defines the coefficients for elementary flow.

    :param conn: database connection
    :param method_name: list of partial method names on which to filter
    :param category_name: list of partial category names on which to filter
    :param methods_columns: list of table columns to return
    :param categories_columns: list of table columns to return
    :return: Dataframe
    """
    # SELECT m.ID, m.REF_ID, m.NAME, c.ID, c.REF_ID, c.NAME FROM TBL_IMPACT_METHODS AS m LEFT JOIN TBL_IMPACT_CATEGORIES as c
    # ON c.F_IMPACT_METHOD=m.ID
    categories = Table('TBL_IMPACT_CATEGORIES')
    methods = Table('TBL_IMPACT_METHODS')
    methods_fields = [methods.field(c).as_('methods_' + c) for c in methods_columns]
    categories_fields = [categories.field(c).as_('categories_' + c) for c in categories_columns]
    q = Query \
        .from_(categories) \
        .left_join(methods).on(categories.F_IMPACT_METHOD == methods.ID) \
        .select(*methods_fields, *categories_fields)
    if method_name:
        q = q.where(Criterion.any([methods.name.like(p) for p in method_name]))
    if category_name:
        q = q.where(Criterion.any([categories.name.like(p) for p in category_name]))
    # TODO: use a conditional on all prints
    print(q)
    impact_categories_dfr = pd.read_sql(str(q), conn)

    return impact_categories_dfr


def get_process_elementary_flow(conn, ref_ids=None, units=True, limit_exchanges=None):
    """
    Create a table of processes versus elementary flows from sqlite db sourced from derby.
    :param conn: sqlite database connection
    :param ref_ids: limit the processes in the table to these ref ids
    :param units: boolean return units of each exchange flow?
    :param limit_exchanges: limit the number of exchanges in the table
    :return: Dataframe
    """

    process_dict = get_ids(conn, ref_ids=ref_ids, table_name="TBL_PROCESSES")
    process_id = list(process_dict.keys())

    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    e = Table('e')

    # sub-query exchanges table to limit
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .limit(limit_exchanges) \
        .as_('e')

    if ref_ids:
        sq = sq.where(exchanges.F_OWNER.isin(process_id))

    # join exchanges to flows
    q = Query\
        .from_(sq).as_('e') \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .select(
            sq.F_OWNER, sq.F_FLOW, sq.F_UNIT, sq.RESULTING_AMOUNT_VALUE,
            flows.FLOW_TYPE, flows.REF_ID
        )\
        .where(flows.FlOW_TYPE == 'ELEMENTARY_FLOW')

    # get elementary exchanges using left join with flow table
    print(q)
    elementary_exchanges_dfr = pd.read_sql(str(q), conn)

    # spread table to row column format
    # row ids are the elementary flow ids, columns are process owning exchange containing the flow
    columns = ['F_OWNER', 'F_UNIT'] if units else 'F_OWNER'
    exchange_process_pivot_dfr = pd.DataFrame.pivot(elementary_exchanges_dfr,
                                                    index='REF_ID', columns=columns,
                                                    values='RESULTING_AMOUNT_VALUE')

    # remap the first level of column index to process ref ids if units included
    if units:
        exchange_process_pivot_dfr.columns.set_levels(
            map(process_dict.get, exchange_process_pivot_dfr.columns.levels[0]), level=0, inplace=True)
    else:
        exchange_process_pivot_dfr.columns = map(process_dict.get, exchange_process_pivot_dfr.columns)

    return exchange_process_pivot_dfr


def get_product_flow_in_process(conn, product_id=None, limit_exchanges=None):
    """
    Create a table of product flows versus their breakdown into elementary flows from sqlite db sourced from derby.

    :param conn: sqlite database connection
    :param product_id: limit the product flows in the table to these ids
    :param limit_exchanges: limit the number of exchanges in the table
    :return: Dataframe
    """

    exchanges = Table('TBL_EXCHANGES')
    processes = Table('TBL_PROCESSES')
    flows = Table('TBL_FLOWS')

    # sub-query exchanges table to limit
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .limit(limit_exchanges)

    # limit exchanges to just the product flows
    if product_id:
        sq = sq.where(exchanges.F_FLOW.isin(product_id))

    # join exchanges to flows
    q = Query\
        .from_(sq) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(flows).on(flows.ID == sq.F_FLOW)\
        .select(
            processes.ID.as_('PROCESS_ID'), processes.NAME.as_('PROCESS_NAME'), sq.F_FLOW.as_('FLOW_ID'),
            flows.NAME.as_('FLOW_NAME'), processes.F_LOCATION.as_('PROCESS_LOCATION')
        )

    print(q)
    process_exchanges_dfr = pd.read_sql(str(q), conn)

    return process_exchanges_dfr


def get_impact_category_elementary_flow(conn, ref_ids=None, units=True):
    """
    Create a table of impact category versus elementary flow from a sqlite openLCA database.

    :param conn: database connection
    :param ref_ids: list of impact category reference ids
    :param units: boolean add units to column index?
    :return: Dataframe
    """

    # table for joins
    impact_factors = Table('TBL_IMPACT_FACTORS')  # maps impact factors to impact categories
    impact_categories = Table('TBL_IMPACT_CATEGORIES')
    flows = Table('TBL_FLOWS')

    ic = impact_categories \
        .select(impact_categories.ID, impact_categories.REF_ID) \
        .as_('ic')

    if ref_ids:
        ic = ic.where(impact_categories.REF_ID.isin(ref_ids))

    # no need to select ELEMENTARY_FLOW
    q = Query\
        .from_(ic).as_('ic')\
        .left_join(impact_factors)\
        .on(impact_factors.F_IMPACT_CATEGORY == ic.ID) \
        .left_join(flows)\
        .on(impact_factors.F_FLOW == flows.ID)\
        .select(
            ic.REF_ID.as_('IMPACT_CATEGORY_REF_ID'), flows.REF_ID.as_('FLOW_REF_ID'),
            impact_factors.VALUE, impact_factors.F_UNIT
        )

    print(q)
    impact_factors_dfr = pd.read_sql(str(q), conn)

    # pivot the impact factors table, rows are elementary flow REF_IDS,
    # columns are impact category REF_IDs with unit
    columns = ['IMPACT_CATEGORY_REF_ID', 'F_UNIT'] if units else 'IMPACT_CATEGORY_REF_ID'
    flow_impact_pivot_dfr = pd.DataFrame.pivot(impact_factors_dfr,
                                               index='FLOW_REF_ID',
                                               columns=columns,
                                               values='VALUE')

    return flow_impact_pivot_dfr


def get_elementary_flow_ref_ids(conn):
    """
    Get elementary flow reference ids from openLCA database.

    :param conn: database connection
    :return: list of reference ids
    """
    dfr = get_elementary_flows(conn, columns=['REF_ID'])
    return dfr['REF_ID'].to_list()


def get_elementary_flows(conn, columns=['ID', 'REF_ID', 'NAME']):
    """
    Get elementary flows from sqlite openLCA database.
    :param conn: database connection
    :param columns: list of table columns to return
    :return: Dataframe
    """
    flows = Table('TBL_FLOWS')
    q = Query \
        .from_(flows) \
        .select(*columns) \
        .where(flows.FLOW_TYPE == 'ELEMENTARY_FLOW')
    print(q)
    elementary_flows_dfr = pd.read_sql(str(q), conn)

    return elementary_flows_dfr


def get_process_ref_ids(conn, name=None, location=None):
    """
    Get process reference ids from openLCA database.

    :param conn: database connection
    :param name: list of partial names of processes to retrieve
    :param location: list of partial locations of processes to retrieve
    :return: list of reference ids
    """
    dfr = get_processes(conn, name=name, location=location, fields=['REF_ID'])
    return dfr['REF_ID'].to_list()


def get_processes(conn, name=None, location=None,
                  fields=['ID', 'REF_ID', 'NAME', 'PROCESS_TYPE', 'LOCATION',
                          'F_QUANTITATIVE_REFERENCE']):
    """
    Get processes from sqlite openLCA database.

    :param conn: database connection
    :param name: list of partial names of processes to retrieve
    :param location: list of partial locations of processes to retrieve
    :param fields: list of fields in table to return
    :return: Dataframe
    """

    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')
    fields = [f if f != 'LOCATION' else locations.NAME.as_('LOCATION') for f in fields]
    q = Query \
        .from_(processes) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(*fields)  # FIXME
    if name:
        q = q.where(Criterion.any([processes.NAME.like(p) for p in name]))
    if location:
        q = q.where(Criterion.any([locations.NAME.like(p) for p in location]))

    print(q)
    processes_dfr = pd.read_sql(str(q), conn)

    return processes_dfr


def get_process_locations(conn, ref_ids=None):
    """
    Get process locations from sqlite openLCA database.

    :param conn: database connection
    :param ref_ids: list of process reference ids
    :return: Dataframe of process id with longitude and latitude
    """

    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')
    q = Query \
        .from_(processes) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(processes.REF_ID, processes.NAME, locations.LATITUDE, locations.LONGITUDE)\
        .where(processes.REF_ID.isin(ref_ids)) # FIXME

    return get_df(conn, q)


def get_flow_reference_units(conn, flow_ref_ids=None):
    """
    Build a query to get flows and reference units from an openLCA database.

    :param sqlite3.Connection conn: database connection
    :param list[str] | str flow_ref_ids: flow reference id or list of flow reference IDs
    :return: DataFrame
    """

    flows = Table('TBL_FLOWS')
    flow_properties = Table('TBL_FLOW_PROPERTIES')
    unit_groups = Table('TBL_UNIT_GROUPS')
    units = Table('TBL_UNITS')

    # convert reference ids to openLCA flow ids
    if flow_ref_ids:
        if isinstance(flow_ref_ids, str):
            flow_ref_ids = [flow_ref_ids]
        flow_id = flows.select(flows.ID).where(flows.REF_ID.isin(flow_ref_ids))
    else:
        flow_id = flows.select(flows.ID)

    # join flows to properties and units
    q = Query\
        .from_(flows) \
        .left_join(flow_properties).on(flows.F_REFERENCE_FLOW_PROPERTY == flow_properties.ID) \
        .left_join(unit_groups).on(flow_properties.F_UNIT_GROUP == unit_groups.ID) \
        .left_join(units).on(unit_groups.F_REFERENCE_UNIT == units.ID) \
        .select(flows.ID, flows.NAME, flows.F_REFERENCE_FLOW_PROPERTY, unit_groups.F_REFERENCE_UNIT,
                units.NAME.as_('UNITS_NAME')) \
        .where(flows.ID.isin(flow_id))

    return get_df(conn, q)


def get_product_flow_units(conn, flow_ref_ids=None):
    """
    Get product flows and units from the exchanges table in an openLCA database.

    :param sqlite3.Connection conn: database connection
    :param list[str] flow_ref_ids: list of flow reference IDs
    :return: SQL string
    """

    flows = Table('TBL_FLOWS')
    exchanges = Table('TBL_EXCHANGES')
    units = Table('TBL_UNITS')

    # convert reference ids to openLCA product flow ids
    flow_id = flows.select(flows.ID).where(flows.FLOW_TYPE == 'PRODUCT_FLOW')
    if flow_ref_ids:
        flow_id = flow_id.where(flows.REF_ID.isin(flow_ref_ids))

    # sub-query to restrict to exchanges to product flows
    sq = Query \
        .from_(exchanges) \
        .select(exchanges.ID, exchanges.F_FLOW, exchanges.F_UNIT) \
        .where(exchanges.F_FLOW.isin(flow_id))

    q = Query \
        .from_(sq) \
        .left_join(flows).on(sq.F_FLOW == flows.ID) \
        .left_join(units).on(sq.F_UNIT == units.ID) \
        .select(flows.NAME, units.NAME.as_('UNITS_NAME'))

    return get_df(conn, q)


def get_process_product_flow(conn, process_ref_ids):
    """
    Get the product flows from a list of process reference ids using a sqlite openLCA database.

    Using the process id get its exchanges and from those extract the product flow.

    :param sqlite3.Connection conn: database connection
    :param list[str] | str process_ref_ids: list of process reference ids
    :return: Dataframe of process ref id and product flow id
    """
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')

    # get the process ids from the ref ids
    if isinstance(process_ref_ids, str):
        process_ref_ids = [process_ref_ids]
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query exchanges table to limit join
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))

    # join exchanges to flows, processes, locations
    q = Query\
        .from_(sq) \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .select(
            processes.REF_ID.as_('PROCESS_REF_ID'), processes.NAME.as_('PROCESS_NAME'),
            locations.NAME.as_('LOCATION'),
            flows.REF_ID.as_('FLOW_REF_ID'), flows.NAME.as_('FLOW_NAME')
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    return get_df(conn, q)


def get_process_product_flow_costs(conn, process_ref_ids):
    """
    Get the product flow costs from a list of process reference ids using a sqlite openLCA database.

    Using the process id get its exchanges and from those extract the product flows and their cost.

    :param sqlite3.Connection conn: database connection
    :param list[str] | str process_ref_ids: list of process reference ids
    :return DataFrame of costs
    """
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    locations = Table('TBL_LOCATIONS')
    units = Table('TBL_UNITS')
    currencies = Table('TBL_CURRENCIES')

    # get the process ids from the ref ids
    if isinstance(process_ref_ids, str):
        process_ref_ids = [process_ref_ids]
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query the exchanges table to limit join
    sq = Query\
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.COST_VALUE, exchanges.F_CURRENCY, exchanges.F_FLOW,
                exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))

    # join exchanges to flows, processes, locations, units, currencies
    q = Query\
        .from_(sq) \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(locations).on(pf.Cast(processes.F_LOCATION, 'int') == locations.ID) \
        .left_join(units).on(units.ID == sq.F_UNIT) \
        .left_join(currencies).on(currencies.ID == sq.F_CURRENCY) \
        .select(
            processes.REF_ID.as_('PROCESS_REF_ID'), processes.NAME.as_('PROCESS_NAME'),
            locations.NAME.as_('LOCATION'),
            flows.REF_ID.as_('FLOW_REF_ID'), flows.NAME.as_('FLOW_NAME'), \
            sq.COST_VALUE, currencies.NAME.as_('CURRENCY'), units.NAME.as_('UNITS')
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    return get_df(conn, q)


def get_process_product_flow_units(conn, process_ref_ids, set_name='P'):
    """
    Get the product flow units from a list of process reference ids using a sqlite openLCA database.

    Using the process id get its exchanges and from those extract the product flows and their units.

    :param sqlite3.Connection conn: database connection
    :param list[str] process_ref_ids: list of process reference ids
    :param list[str] | str set_name: column name of the index in the returned table
    :return DataFrame of units indexed by set_name
    """
    exchanges = Table('TBL_EXCHANGES')
    flows = Table('TBL_FLOWS')
    processes = Table('TBL_PROCESSES')
    units = Table('TBL_UNITS')

    # get the process ids from the ref ids
    if isinstance(process_ref_ids, str):
        process_ref_ids = [process_ref_ids]
    process_ids = processes.select(processes.ID).where(processes.REF_ID.isin(process_ref_ids))

    # sub-query the exchanges table to limit join
    sq = Query \
        .from_(exchanges) \
        .select(exchanges.F_OWNER, exchanges.F_FLOW,
                exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
        .where(exchanges.F_OWNER.isin(process_ids))

    # join exchanges to flows, processes, units
    q = Query \
        .from_(sq) \
        .left_join(flows).on(flows.ID == sq.F_FLOW) \
        .left_join(processes).on(processes.ID == sq.F_OWNER) \
        .left_join(units).on(units.ID == sq.F_UNIT) \
        .select(
            processes.REF_ID.as_(set_name), units.NAME.as_('Units')
        )\
        .where(flows.FlOW_TYPE == 'PRODUCT_FLOW')

    product_flow_dfr = get_df(conn, q)
    product_flow_dfr.set_index(set_name, inplace=True)

    return product_flow_dfr


def get_product_flow_ref_ids(conn, name=None):
    """
    Get product flow reference ids from openLCA database.

    :param conn: database connection
    :param name: list of partial names of flows to retrieve
    :return: list of reference ids
    """
    dfr = get_product_flows(conn, name=name, fields=['REF_ID'])
    return dfr['REF_ID'].to_list()


def get_product_flows(conn, name=None, fields=['ID', 'REF_ID', 'NAME']):
    """
    Get product flows from sqlite openLCA database.

    :param conn: database connection
    :param name: list of partial names of flows to retrieve
    :param fields: list of fields in table to return
    :return: Dataframe
    """

    flows = Table('TBL_FLOWS')
    q = Query\
        .from_(flows)\
        .select(*fields)\
        .where(flows.FLOW_TYPE == 'PRODUCT_FLOW')
    if name:
        q = q.where(Criterion.any([flows.name.like(p) for p in name]))

    return get_df(conn, q)


class LookupTables:
    """
    Caches lookups to a database using a dict of DataFrames.
    Contains tables of ref id, name etc. for each relevant table in db.
    Dynamic lookups are methods of LookupTables.
    """

    def __init__(self, conn):
        self.d = get_lookup_tables(conn)
        self.conn = conn

    def __iter__(self):
        return iter(self.d)

    def get(self, table_name, index=None):
        """
        Get lookup table from cache.

        :param table_name: name of table
        :param index: DataFrame index
        :return: DataFrame
        """
        if index is None:
            return self.d[table_name]
        else:
            return self.d[table_name].loc[index, :]

    def get_single_column(self, table_name, index=None, join_char=' | '):
        """
        Get lookup table as a single joined column in a data frame from cache.

        :param table_name:  name of table
        :param index: DataFrame index
        :param join_char: character to join columns
        :return: DataFrame
        """
        s = pd.Series(self.d[table_name].fillna('').values.tolist()).str.join(join_char)
        s.index = self.d[table_name].index
        tbl = pd.DataFrame({table_name: s})

        if index is None:
            return tbl
        else:
            return tbl.loc[index, :]

    def keys(self):
        return self.d.keys()

    def get_units(self, process_ref_ids, set_name='P_m'):
        """
        :param list[str] process_ref_ids: list of process reference ids
        :param list[str] set_name: column name of process set for index
        :return: DataFrame
        """
        units_dfr = get_process_product_flow_units(self.conn, process_ref_ids, set_name)
        return units_dfr
