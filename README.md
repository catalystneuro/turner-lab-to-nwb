# turner-lab-to-nwb
NWB conversion scripts for Turner lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.

**Requirements:** Python 3.12+

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

Or using [uv](https://docs.astral.sh/uv/) (recommended for faster dependency resolution):

```
git clone https://github.com/catalystneuro/turner-lab-to-nwb
cd turner-lab-to-nwb
uv sync
```

Note:
both pip and uv methods install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

    turner-lab-to-nwb/
    ├── LICENSE
    ├── make_env.yml
    ├── pyproject.toml
    ├── README.md
    ├── notebooks/
    │   └── turner_m1_usage.ipynb
    └── src/
        └── turner_lab_to_nwb/
            ├── asap_tdt/
            │   ├── extractors/
            │   ├── interfaces/
            │   ├── metadata/
            │   ├── tutorials/
            │   ├── asap_tdt_convert_all_sessions.py
            │   ├── asap_tdt_convert_session.py
            │   ├── asap_tdt_notes.md
            │   └── asap_tdtnwbconverter.py
            └── asap_m1_mptp/
                ├── assets/
                ├── documentation/
                ├── interfaces/
                ├── conversion_script.py
                ├── conversion_notes.md
                └── metadata.yaml

### asap_tdt

For the `asap_tdt` conversion, you can find a directory located in `src/turner_lab_to_nwb/asap_tdt`. This conversion handles TDT (Tucker-Davis Technologies) recording systems. Inside the conversion directory you can find the following files:

* `asap_tdt_convert_all_sessions.py`: script to convert all sessions (requires expected folder structure)
* `asap_tdt_convert_session.py`: script to convert one full session
* `asap_tdt_notes.md`: notes and comments concerning this specific conversion
* `asap_tdtnwbconverter.py`: the `NWBConverter` class definition
* `extractors/`: recording and sorting extractors
* `interfaces/`: recording and sorting interfaces
* `metadata/`: metadata YAML files
* `tutorials/`: tutorials and examples (including `asap_tdt_demo.ipynb`)

The conversion [notes](src/turner_lab_to_nwb/asap_tdt/asap_tdt_notes.md) contain information about the expected folder structure and the conversion process.

### asap_m1_mptp

For the `asap_m1_mptp` conversion, you can find a directory located in `src/turner_lab_to_nwb/asap_m1_mptp`. This conversion handles the Turner-Delong MPTP dataset (MATLAB-based single-unit recordings). Inside the conversion directory you can find the following files:

* `conversion_script.py`: main conversion script
* `conversion_notes.md`: detailed notes about data streams, experimental design, and technical specifications
* `metadata.yaml`: session-level metadata template
* `interfaces/`: data stream interfaces (spike times, trials, EMG, LFP, manipulandum, electrodes, antidromic stimulation)
* `documentation/`: technical documentation (trial structure, anatomical coordinates, electrode configurations, etc.)
* `assets/`: supporting materials including data exploration scripts, paper summaries, and HED documentation

### Running a specific conversion

You can run a specific conversion with the following commands:

**asap_tdt:**
```
python src/turner_lab_to_nwb/asap_tdt/asap_tdt_convert_session.py
```

**asap_m1_mptp:**
```
python src/turner_lab_to_nwb/asap_m1_mptp/conversion_script.py
```

## NWB tutorials

Jupyter notebooks demonstrate how to use the NWB files created by the conversion scripts:

* **asap_tdt**: `src/turner_lab_to_nwb/asap_tdt/tutorials/asap_tdt_demo.ipynb`
* **asap_m1_mptp**: `notebooks/turner_m1_usage.ipynb`

You might need to install `jupyter` before running the notebooks:

```
pip install jupyter
jupyter lab
```
