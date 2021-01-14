import olca
import uuid

client = olca.Client(8080)

# find the flow property 'Mass' from the database
mass = client.find(olca.FlowProperty, 'Mass')

# create a flow that has 'Mass' as reference flow property
steel = olca.Flow()
steel.id = str(uuid.uuid4())
steel.flow_type = olca.FlowType.PRODUCT_FLOW
steel.name = "Steel"
steel.description = "Added from the olca-ipc python API..."
# in openLCA, conversion factors between different
# properties/quantities of a flow are stored in
# FlowPropertyFactor objects. Every flow needs at
# least one flow property factor for its reference
# flow property.
mass_factor = olca.FlowPropertyFactor()
mass_factor.conversion_factor = 1.0
mass_factor.flow_property = mass
mass_factor.reference_flow_property = True
steel.flow_properties = [mass_factor]

# save it in openLCA, you may have to refresh
# (close & reopen the database to see the new flow)
client.insert(steel)
