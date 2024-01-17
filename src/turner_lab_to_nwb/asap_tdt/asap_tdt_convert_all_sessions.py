import os
from pathlib import Path

import numpy as np
from neuroconv.tools import LocalPathExpander

from turner_lab_to_nwb.asap_tdt.asap_tdt_convert_session import session_to_nwb
from turner_lab_to_nwb.asap_tdt.utils import load_session_metadata


# The root folder containing the sessions
folder_path = Path("/Volumes/t7-ssd/Turner/Previous_PD_Project_sample")
# The output folder for the NWB files
output_dir_path = folder_path / "nwbfiles"
os.makedirs(output_dir_path, exist_ok=True)

# The path to the electrode metadata file (.xlsx)
data_list_file_path = folder_path / "Isis_DataList_temp.xlsx"
stub_test = False  # Set to False to convert the full session, otherwise only a stub will be converted for testing
verbose = True

# Specify source data (note this assumes the files are arranged in the same way as in the example data)
source_data_spec = {
    "recording": {
        "base_directory": folder_path,
        "file_path": "I_{date_string}/{subject_id}_{session_id}.Tbk",
    }
}

# Instantiate LocalPathExpander
path_expander = LocalPathExpander()

# Expand paths and extract metadata
metadata_list = path_expander.expand_paths(source_data_spec)

for index, metadata in enumerate(metadata_list):
    date_string = metadata["metadata"]["extras"]["date_string"]
    subject_id = metadata["metadata"]["Subject"]["subject_id"]
    session_id = metadata["metadata"]["NWBFile"]["session_id"]
    print(f"Converting session {session_id} of subject {subject_id} ...")

    nwbfile_name = f"{subject_id}_{session_id}.nwb"
    if stub_test:
        nwbfile_name = f"stub_{subject_id}_{session_id}.nwb"

    session_metadata = load_session_metadata(file_path=data_list_file_path, session_id=session_id)
    plexon_data = session_metadata.groupby("Area")["Chan#"].first().reset_index()

    stim_site = session_metadata["Stim. site"].replace(np.nan, None).unique().tolist()[0]

    vl_plexon_first_channel = plexon_data.loc[plexon_data["Area"] == "VLa", "Chan#"].values[0]
    vl_plexon_file_path = list(
        folder_path.rglob(f"I_{date_string}/{session_id}_Chans_{vl_plexon_first_channel}_*.plx")
    )[0]

    if stim_site is None:
        gpi_plexon_first_channel = plexon_data.loc[plexon_data["Area"] == "GPi", "Chan#"].values[0]
        gpi_plexon_file_path = list(
            folder_path.rglob(f"I_{date_string}/{session_id}_Chans_{gpi_plexon_first_channel}_*.plx")
        )[0]
    else:
        # If stimulation site is GPi, we only have spike sorting date from VL region, the plexon file for GPi is empty
        gpi_plexon_file_path = None

    events_file_path = folder_path / f"I_{date_string}" / f"{session_id}.mat"
    # The mapping of the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right"
    target_name_mapping = {1: "Left", 3: "Right"}

    session_to_nwb(
        tdt_tank_file_path=metadata["source_data"]["recording"]["file_path"],
        nwbfile_path=output_dir_path / nwbfile_name,
        data_list_file_path=data_list_file_path,
        vl_plexon_file_path=vl_plexon_file_path,
        gpi_plexon_file_path=gpi_plexon_file_path,
        session_id=session_id,
        events_file_path=events_file_path,
        target_name_mapping=target_name_mapping,
        stub_test=stub_test,
    )
