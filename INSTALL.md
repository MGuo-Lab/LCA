# Installation

These are notes on how to install source code and then run mola from your local hard drive. First ensure that you have
the latest versions of Anaconda3, PyCharm and Git installed on your machine.

## OpenLCA Data

Mola uses an Ecoinvent database converted from Apache Derby to sqlite. The script to do
the conversion can be found in the file `mola\scripts\derby_export_import.py`. The paths at the top
 of the file show the expected location of Derby Databases, Derby drivers, and output files. The Derby drivers can be
 found at http://db.apache.org/derby/

It takes about an hour to convert the full Ecoinvent database to sqlite, so it is simplest to use the pre-built version
at https://app.box.com/file/785473640076?s=51zjyp3h5c2x2ftmofd5sqcqp3flb194. Download this
zip file and uncompress it.

## Model Configuration Files

Create a folder `c:\data\openlca\sqlite\system` and put the uncompressed sqlite file into this folder. The
example JSON configuration files for `mola` reference this db file. If you start `mola` without this file 
in place then you will need to explicitly import the compressed database using the GUI and build your own 
configuration files. If you want to use the example configuration files then their internal `db_file` tag needs 
to point to your local uncompressed sqlite file.

## Cloning the Repository

We shall create a directory called `C:\dev` in the root of your local drive to store the contents of the LCA repository. 
Using the Anaconda Prompt, type into the console the following commands:

```
mkdir c:\dev
cd c:\dev
git clone https://github.com/MGuo-Lab/LCA.git
```
This should create a folder `LCA` containing the contents of the Github repository.

## Pycharm

Open PyCharm and create a new PurePython project with Location `c:\dev\LCA`. Select a new environment using conda
and called `LCA`. Make sure you select Python 3.7 for the environment and don't
create a new `main.py` file. Tell PyCharm you want to use existing sources and then the PyCharm IDE should open with 
the LCA project contents.

Close down PyCharm so that it does not interfere with the subsequent package installation. 

## Conda environment

Return to the Anaconda Prompt and type

```
cd c:\dev\LCA
conda activate LCA
conda env update --name LCA --file environment.yml
```

The last command updates the conda environment called `LCA` with packages required by `mola`. It may take a while.

Conda is sometimes unable to delete temporary files during package installs. It might be related to the 
virus checker or the security policy in Windows 10. If you get an access denied error then continue with the
update using

```
conda env update --name LCA --file environment.yml
```

You can ensure that the environment has been created by listing its content.

```
conda activate LCA
conda list
```

To run the GUI, open PyCharm with the LCA project then right click and `Run` on the `main.py` file in the `molaqt`
directory. The GUI should open. You might need to wait till PyCharm has finished indexing for the `Run` option
to appear. 



# Notebooks

In order that Jupyter notebooks can locate modules there should be junction called `mola` in
the notebooks folder that points to `LCA\mola`. Make sure the existing `mola` directory in the notebooks directory is
removed first.

Open a command prompt as Administrator on your machine and type

```
cd c:\dev\LCA
mklink /j c:\dev\LCA\notebooks\mola c:\dev\LCA\mola
```

Be careful if you try and delete this link because may delete the target `mola` folder!

In order to open a notebook go the Anaconda Prompt and type

```
conda activate LCA
jupyer notebook
```

You can then navigate to the notebook using the browser window.