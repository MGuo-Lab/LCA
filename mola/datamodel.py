"""
Potential objects for holding network model structure.
"""

class Task:
    """A mola optimisation task"""

    def __init__(self, name):
        self.name = name
        self.input = {}
        self.output = {}

    def method(self):
        return 'method'


class Schedule:
    """An ordered collection of mola tasks"""
    task = []


class Demand:
    """A mola demand"""
    task = []


class Flow:
    """A mola flow"""


class MaterialFlow(Flow):
    """A mola material flow"""


class ServiceFlow(Flow):
    """A mola service flow"""


class TransportFlow(Flow):
    """A mola service flow"""


# turn openLCA processes and flows into objects to avoid querying attributes in code?
class Process:

    def __init__(self, ref_id):
        self.ref_id = ref_id


class Flow:

    def __init__(self, ref_id):
        self.ref_id = ref_id
