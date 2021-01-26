# TODO functions in utils should go here

# turn openLCA processes and flows into objects to avoid querying attributes in code?
class Process:

    def __init__(self, ref_id):
        self.ref_id = ref_id


class Flow:

    def __init__(self, ref_id):
        self.ref_id = ref_id


