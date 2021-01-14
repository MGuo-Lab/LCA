# units tests on the datamodel module
import mola.dataview as dv
import mola.dataimport as di
from pypika import Query, Table, Criterion, CustomFunction
import pypika.functions as pf

# testing from full db
db_file = 'C:/data/openlca/sqlite/system/CSV_juice_ecoinvent_36_apos_lci_20200206_20201029-102818.sqlite'
conn = di.get_sqlite_connection(db_file)

elementary_flows_dfr = dv.get_elementary_flows(conn)

processes_dfr = dv.get_processes(conn, name=['Lemon%', 'Mandarin%', 'Orange%'])

exchanges = Table('TBL_EXCHANGES')
flows = Table('TBL_FLOWS')
e = Table('e')
sq = Query \
    .from_(exchanges) \
    .select(exchanges.F_OWNER, exchanges.F_FLOW, exchanges.F_UNIT, exchanges.RESULTING_AMOUNT_VALUE) \
    .limit(10) \
    .as_('e')

q = Query \
    .from_(sq).as_('e') \
    .left_join(flows)\
    .on(sq.F_FLOW == flows.ID) \
    .select(
    e.F_OWNER, flows.FLOW_TYPE
    ) \
    .where(flows.FlOW_TYPE == 'ELEMENTARY_FLOW')

q

#conn.close()
