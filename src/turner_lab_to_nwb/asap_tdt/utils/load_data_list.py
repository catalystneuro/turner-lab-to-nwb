import pandas as pd
from neuroconv.utils import FilePathType


def load_session_metadata(file_path: FilePathType, session_id: str):
    """Load the session metadata from the Excel file."""
    electrodes_metadata = pd.read_excel(file_path)
    # filter for this session
    electrode_metadata = electrodes_metadata[electrodes_metadata["Filename"] == session_id]
    electrode_metadata_without_duplicates = electrode_metadata.drop_duplicates(subset=["Chan#"])
    return electrode_metadata_without_duplicates
