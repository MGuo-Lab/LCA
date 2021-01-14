# Mathematical Optimisation of Life-Cycle Assessment Models

## Introduction

Life-cycle assessment models consist of a network of processes and flows that describe the full life-cycle of 
a industrial process. Often one can choose how the network is constructed
in order to deliver a particular product or service. 

This project focuses on how we can minimise the environmental impact and cost
of generating a product or service using an openLCA (http://www.openlca.org) database of component
processes and flows. 

The optimisation problem is solved using Python and
[pyomo](http://www.pyomo.org/) in a Python packaged called `mola`. The package is 
named after the ocean sunfish shown below.

![Home Screen](molaqt/images/Sunfish2.jpg?raw=true)
[___Mola mola: Ocean sunfish___](https://en.wikipedia.org/wiki/Ocean_sunfish)

## Repository

This repository contains two Python packages and a collection of Jupyter Notebooks.

* The `mola` (Mathematical Optimisation for Life-cycle Assessment) package
contains a collection of Python classes and functions to carry out the optimisation
of life-cycle assessment in a Python script or a Jupyter notebook.

* The `molaqt` package is a QT front-end to the `mola` package. It allows
a user to configure an optimisation problem using a GUI and
then obtain the results using a solver.

* The `notebooks` directory contains a collection of Jupyter notebooks that describe
Toy optimisation problems that illustrate the use of the `mola` package.
 
 
 