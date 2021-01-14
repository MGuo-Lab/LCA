# module for optimisation data model

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

