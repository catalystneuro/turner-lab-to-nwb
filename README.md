# turner-lab-to-nwb
NWB conversion scripts for Turner lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.


## Installation
The package can be installed directly from GitHub, which has the advantage that the source code can be modified if you need to amend some of the code we originally provided to adapt to future experimental differences.
To install the conversion from GitHub you will need to use `git` ([installation instructions](https://github.com/git-guides/install-git)). We also recommend the installation of `conda` ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)) as it contains
all the required machinery in a single and simple install.

From a terminal (note that conda should install one in your system) you can do the following:

```
git clone https://github.com/catalystneuro/turner-lab-to-nwb
cd turner-lab-to-nwb
conda env create --file make_env.yml
conda activate turner_lab_to_nwb_env
```

This creates a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) which isolates the conversion code from your system libraries.
We recommend that you run all your conversion related tasks and analysis from the created environment in order to minimize issues related to package dependencies.

Alternatively, if you want to avoid conda altogether (for example if you use another virtual environment tool)
you can install the repository with the following commands using only pip:

```
git clone https://github.com/catalystneuro/turner-lab-to-nwb
cd turner-lab-to-nwb
pip install -e .
```

Note:
both of the methods above install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

    turner-lab-to-nwb/
    ├── LICENSE
    ├── make_env.yml
    ├── pyproject.toml
    ├── README.md
    ├── requirements.txt
    ├── setup.py
    └── src
        ├── turner_lab_to_nwb
        │   ├── asap_embargo
        │   └── asap_tdt
        │       ├── extractors
        │       │   ├── __init__.py
        │       │   ├── asap_tdt_filtered_recordingextractor.py
        │       │   └──  asap_tdt_sortingextractor.py
        │       ├── interfaces
        │       │   ├── __init__.py
        │       │   ├── asap_tdt_eventsinterface.py
        │       │   ├── asap_tdt_filtered_recordinginterface.py
        │       │   ├── asap_tdt_recordinginterface.py
        │       │   └── asap_tdt_sortinginterface.py
        │       ├── metadata
        │       │   ├── ecephys_metadata.yaml
        │       │   ├── embargo_metadata.yaml
        │       │   ├── public_metadata.yaml
        │       │   ├── subjects_metadata.yaml
        │       ├──tutorials
        │       │   └── asap_tdt_demo.ipynb
        │       ├── asap_tdt_convert_all_sessions.py
        │       ├── asap_tdt_convert_session.py
        │       ├── asap_tdt_notes.md
        │       ├── asap_tdt_requirements.txt
        │       ├── asap_tdtnwbconverter.py
        │       └── __init__.py
        └── __init__.py

For the conversion `asap_tdt` you can find a directory located in `src/turner-lab-to-nwb/asap_tdt`. Inside the conversion directory you can find the following files:

* `asap_tdt_convert_all_sessions.py`: this script defines the function to convert all sessions of the conversion. (Note: this script requires the expected folder structure)
* `asap_tdt_convert_sesion.py`: this script defines the function to convert one full session of the conversion.
* `asap_tdt_notes.md`: notes and comments concerning this specific conversion.
* `asap_tdt_requirements.txt`: dependencies specific to this conversion.
* `asap_tdtnwbconverter.py`: the place where the `NWBConverter` class is defined.
* `extractors`: a directory containing the recording and sorting extractors for this specific conversion.
* `interfaces`: a directory containing the recording and sorting interfaces for this specific conversion.
* `metadata`: a directory containing the metadata for this specific conversion.
* `tutorials`: a directory containing tutorials and examples for this specific conversion.

### Notes on the conversion

The conversion [notes](https://github.com/catalystneuro/turner-lab-to-nwb/blob/7fb10ded4850eeff6ddb688a5f1f8a77b8a98f01/src/turner_lab_to_nwb/asap_tdt/asap_tdt_notes.md)
contain information about the expected folder structure and the conversion process.

### Running a specific conversion
To run a specific conversion, you might need to install first some conversion specific dependencies that are located in each conversion directory:
```
pip install -r src/turner_lab_to_nwb/asap_tdt/asap_tdt_requirements.txt
```

You can run a specific conversion with the following command:
```
python src/turner_lab_to_nwb/asap_tdt/asap_tdt_convert_sesion.py
```

## NWB tutorials

The `tutorials` directory contains Jupyter notebooks that demonstrate how to use the NWB files created by the conversion scripts.

You might need to install `jupyter` before running the notebooks:

```
pip install jupyter
cd src/turner_lab_to_nwb/asap_tdt/tutorials
jupyter lab
```
