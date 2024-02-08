import pandas as pd
from neuroconv.utils import FilePathType


def load_session_metadata(file_path: FilePathType, session_id: str, sheet_name: str = None):
    """Load the session metadata from the Excel file."""
    electrodes_metadata = pd.read_excel(file_path, sheet_name=sheet_name)
    # remove single quotes from the columns
    electrodes_metadata = electrodes_metadata.map(lambda x: x.replace("'", "") if isinstance(x, str) else x)
    # filter for this session
    electrode_metadata = electrodes_metadata[electrodes_metadata["Filename"] == session_id]
    electrode_metadata_without_duplicates = electrode_metadata.drop_duplicates(subset=["Chan#"])
    # map "GP" values to "GPi"
    electrode_metadata_without_duplicates.loc[:, "Target"] = electrode_metadata_without_duplicates["Target"].replace(
        "GP", "GPi"
    )
    # cast "Chan#" to int
    electrode_metadata_without_duplicates.loc[:, "Chan#"] = (
        electrode_metadata_without_duplicates["Chan#"].astype(int).astype(str)
    )
    return electrode_metadata_without_duplicates
