import numpy as np
import pandas as pd


def load_units_dataframe(mat: dict) -> pd.DataFrame:
    """
    Load the units structure from the MAT file into a pandas DataFrame.

    Parameters
    ----------
    mat : dict
        The dictionary containing the MAT file data.
    """
    # Check if the units structure contains only a single unit
    units = mat["units"]
    if not isinstance(units["sort"], list):
        single_unit = dict()
        fields = ["uname", "sort", "chan", "brain_area", "ts", "sort_qual"]
        # single unit structure
        [single_unit.update({field: [units[field]]}) for field in fields if field in units]
        units_df = pd.DataFrame(single_unit)
    else:
        units_df = pd.DataFrame(units)

    # Some files have "Cont_Channel_Location" instead of "brain_area"
    if "brain_area" not in units_df and "Cont_Channel_Location" in mat:
        unique_channels = np.unique(units_df["chan"]).astype(int)
        unique_channel_indices = unique_channels - 1  # MATLAB indices start at 1
        brain_areas = (
            [mat["Cont_Channel_Location"]]
            if isinstance(mat["Cont_Channel_Location"], str)
            else mat["Cont_Channel_Location"]
        )
        brain_areas = np.array(brain_areas)
        if len(unique_channel_indices) != len(brain_areas):
            brain_areas = brain_areas[unique_channel_indices]
        channel_to_location_mapping = dict(zip(unique_channels, brain_areas))
        brain_area_per_unit = [channel_to_location_mapping[channel] for channel in units_df["chan"]]
        units_df["brain_area"] = brain_area_per_unit

    return units_df
