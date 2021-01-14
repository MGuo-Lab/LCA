# Direct pyomo implementation of the juice production and transport problem

# Import of the pyomo module
from pyomo.environ import *

# Creation of a concrete model
model = ConcreteModel()

# Define sets
model.fruit = Set(initialize=['Lemon', 'Mandarin', 'Orange'], doc='Fruits')

# Define parameters
D_dict = {'Lemon': 12, 'Mandarin': 8, 'Orange': 15}
model.D = Param(model.fruit, mutable=True, initialize=D_dict,
                doc='Distances for each fruit to its potential processing site in km')
I_dict = {'Lemon': 1, 'Mandarin': 1, 'Orange': 1}
model.I = Param(model.fruit, initialize=I_dict, doc='climate change impact of growing fruit, kgCO2e/kg')
model.T = 1

# Define binary decision variables
model.y = Var(model.fruit, within=Binary, doc='Select this fruit?')


# Define constraints
def one_fruit_rule(model):
    return (sum(model.y[f] for f in model.fruit) == 1)


model.one_fruit = Constraint(rule=one_fruit_rule)


# Define objective
def objective_rule(model):
    return sum(model.y[f] * model.D[f] * model.T + model.y[f] * model.I[f] for f in model.fruit)


model.obj = Objective(rule=objective_rule, sense=minimize)

# Apply solver
opt = SolverFactory("glpk")
results = opt.solve(model)

def pyomo_postprocess(options=None, instance=None, results=None):
  model.y.display()

results.write()
print("\nDisplaying Solution\n" + '-'*60)
pyomo_postprocess(None, model, results)