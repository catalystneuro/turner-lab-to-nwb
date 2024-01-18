from typing import Optional
import numpy as np
from pymatreader import read_mat
from spikeinterface import BaseSorting, BaseSortingSegment

from neuroconv.utils import FilePathType


class ASAPTdtSortingExtractor(BaseSorting):
    extractor_name = "ASAPTdtSorting"
    installed = True
    mode = "file"
    installation_mesg = ""
    name = "tdtsorting"

    def __init__(self, file_path: FilePathType):
        """
        Parameters
        ----------
        file_path : FilePathType
            The file path to the MAT file containing the clustered spike times.
        """

        mat = read_mat(file_path)
        assert "units" in mat, f"The 'units' structure is missing from '{file_path}'."
        self._units_data = mat["units"]
        spike_times = self._units_data["ts"]
        num_units = len(self._units_data["uname"])
        unit_ids = np.arange(num_units)

        sampling_frequency = float(mat["Tanksummary"]["ChanFS"][-1])

        BaseSorting.__init__(self, sampling_frequency=sampling_frequency, unit_ids=unit_ids)
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
        units_quality = [quality_values_map.get(quality, quality) for quality in self._units_data["sort_qual"]]
        self.set_property(key="unit_quality_post_sorting", values=units_quality)

        unit_properties_mapping = dict(
            uname="unit_name",
            sort="sort_label",
            brain_area="location",
            chan="channel_ids",
        )
        for property_name, renamed_property_name in unit_properties_mapping.items():
            self.set_property(
                key=renamed_property_name,
                values=self._units_data[property_name],
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
