from pathlib import Path

import pynwb
from hdmf.backends.hdf5 import H5DataIO
from neuroconv import BaseDataInterface
from neuroconv.tools import get_module
from neuroconv.utils import FilePathType
from pymatreader import read_mat
from pynwb import NWBFile


class ASAPTdtFilteredRecordingInterface(BaseDataInterface):
    def __init__(
        self,
        file_path: FilePathType,
        es_key: str = "ElectricalSeriesProcessed",
        brain_area: str = "GPi",
    ):
        """
        Load processed ephys data from .mat file.
        The data was high-pass filtered (Fpass: 300 Hz, Matlab FIRPM) and thresholded.

        Parameters
        ----------
        file_path : FilePathType
            The path to the .mat file containing the filtered electrical series data.
        verbose : bool, default: True
            Verbose
        es_key : str, default: "ElectricalSeriesProcessed"
        """
        file_path = Path(file_path)
        assert file_path.exists(), f"The file {file_path} does not exist."

        fft_data = read_mat(file_path)
        assert "samplerate" in fft_data, f"The file {file_path} does not contain a 'samplerate' key."
        assert "hp_cont" in fft_data, f"The file {file_path} does not contain a 'hp_cont' key."

        self.es_key = es_key + brain_area
        self.brain_area = brain_area
        self._data = fft_data["hp_cont"]
        self._sampling_frequency = fft_data["samplerate"]

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Ecephys"]["ElectrodeGroup"] = [dict(name=f"Group {self.brain_area}")]
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        # get electrode group
        electrode_group_name = metadata["Ecephys"]["ElectrodeGroup"][0]["name"]
        assert (
            electrode_group_name in nwbfile.electrode_groups
        ), f"The electrode group {electrode_group_name} is not in the NWBFile."

        electrodes = nwbfile.electrodes.to_dataframe()
        region = electrodes[electrodes["group_name"] == electrode_group_name].index.values
        electrode_table_region = nwbfile.create_electrode_table_region(
            region=list(region),
            description=f"The electrodes of {self.brain_area}.",
        )
        ecephys_mod = get_module(
            nwbfile=nwbfile,
            name="ecephys",
            description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
        )
        if "Processed" not in ecephys_mod.data_interfaces:
            ecephys_mod.add(pynwb.ecephys.FilteredEphys(name="Processed"))

        raw_electrical_series = nwbfile.electrical_series["ElectricalSeries"]
        ecephys_mod["Processed"].create_electrical_series(
            name=self.es_key,
            description=f"The high-pass filtered (Fpass: 300 Hz, Matlab FIRPM) data from {self.brain_area}.",
            data=H5DataIO(data=self._data, compression=True),
            electrodes=electrode_table_region,
            rate=self._sampling_frequency,
            starting_time=raw_electrical_series.starting_time,
            conversion=raw_electrical_series.conversion,
        )
