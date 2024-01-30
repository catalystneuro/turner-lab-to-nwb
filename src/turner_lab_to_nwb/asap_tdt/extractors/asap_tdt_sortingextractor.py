from typing import Optional, Literal
import numpy as np
import pandas as pd
from pymatreader import read_mat
from spikeinterface import BaseSorting, BaseSortingSegment

from neuroconv.utils import FilePathType


class ASAPTdtSortingExtractor(BaseSorting):
    extractor_name = "ASAPTdtSorting"
    installed = True
    mode = "file"
    installation_mesg = ""
    name = "tdtsorting"

    def __init__(self, file_path: FilePathType, location: Literal["GPi", "VL", None] = None):
        """
        Parameters
        ----------
        file_path : FilePathType
            The file path to the MAT file containing the clustered spike times.
        location: Literal["GPi", "VL", None], optional
            The location of the probe, when specified allows to filter the units by location. By default None.
        """

        mat = read_mat(file_path)
        assert "units" in mat, f"The 'units' structure is missing from '{file_path}'."
        units_df = pd.DataFrame(mat["units"])

        # filter out units based on location
        if location is not None:
            assert location in ["GPi", "VL"], f"Location must be one of ['GPi', 'VL'], not {location}."
            units_df = units_df[units_df["brain_area"].str.contains(location)]
            if units_df.empty:
                raise ValueError(f"No units found in '{file_path}' for location '{location}'.")

        unit_names = units_df["uname"].values.tolist()
        num_units = len(unit_names)
        unit_ids = np.arange(num_units)

        # Determine sampling frequency
        if "samplerate" in mat:
            sampling_frequency = float(mat["samplerate"])
        elif "ChanFS" in mat["Tanksummary"]:
            channel_names = mat["Tanksummary"]["ChanName"]
            channel_index = np.where(np.array(channel_names) == "Conx")[0]
            sampling_frequency = float(mat["Tanksummary"]["ChanFS"][channel_index])
        else:
            raise ValueError(f"Cannot determine sampling frequency from '{file_path}'.")
        BaseSorting.__init__(self, sampling_frequency=sampling_frequency, unit_ids=unit_ids)
        spike_times = units_df["ts"].values
        sorting_segment = ASAPTdtSortingSegment(
            sampling_frequency=sampling_frequency,
            spike_times=spike_times,
        )
        self.add_sorting_segment(sorting_segment)

        # Map unit quality values to more descriptive names
        quality_values_map = {
            "A": "excellent",
            "B": "good",
            "A -> B": "changed to good from excellent based on post-sorting quality",
            "B -> A": "changed to excellent from good based on post-sorting quality",
        }
        units_quality = units_df["sort_qual"].values.tolist()
        units_quality_renamed = [quality_values_map.get(quality, quality) for quality in units_quality]
        self.set_property(key="unit_quality_post_sorting", values=units_quality_renamed)

        units_df["chan"] = units_df["chan"].astype(int)

        # Rename non-unique unit names
        duplicates_mask = units_df["uname"].duplicated(keep=False)
        for i, row in units_df.iterrows():
            if duplicates_mask[i]:
                units_df.at[i, "uname"] = f'{row["uname"]}-{row["chan"]}'

        unit_properties_mapping = dict(
            uname="unit_name",
            sort="sort_label",
            brain_area="location",
            chan="channel_ids",
        )
        for property_name, renamed_property_name in unit_properties_mapping.items():
            self.set_property(
                key=renamed_property_name,
                values=units_df[property_name].values.tolist(),
            )


class ASAPTdtSortingSegment(BaseSortingSegment):
    def __init__(self, sampling_frequency: float, spike_times: np.ndarray):
        BaseSortingSegment.__init__(self)
        self._spike_times = spike_times
        self._sampling_frequency = sampling_frequency

    def get_unit_spike_train(
        self,
        unit_id: int,
        start_frame: Optional[int] = None,
        end_frame: Optional[int] = None,
    ) -> np.ndarray:
        times = self._spike_times[unit_id]
        frames = (times * self._sampling_frequency).astype(int)
        if start_frame is not None:
            frames = frames[frames >= start_frame]
        if end_frame is not None:
            frames = frames[frames < end_frame]
        return frames
