import warnings
from datetime import datetime
from pathlib import Path

from natsort import natsorted
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.datainterfaces.ecephys.intan.intandatainterface import extract_electrode_metadata_with_pyintan
from neuroconv.utils import FolderPathType, get_schema_from_hdmf_class
from pynwb.ecephys import ElectricalSeries
from spikeinterface import ConcatenateSegmentRecording
from spikeinterface.extractors import IntanRecordingExtractor


class ASAPEmbargoIntanRecordingInterface(BaseRecordingExtractorInterface):
    Extractor = ConcatenateSegmentRecording

    def __init__(
        self,
        folder_path: FolderPathType,
        stream_id: str = "0",
        verbose: bool = True,
        es_key: str = "ElectricalSeries",
    ):
        """
        Load and prepare raw data and corresponding metadata from the Intan format (.rhs files).

        Parameters
        ----------
        folder_path : FolderPathType
            The path to the folder that contains the rhs files to be concatenated.
        stream_id : str, optional
            The stream of the data for spikeinterface, "0" by default.
        verbose : bool, default: True
            Verbose
        es_key : str, default: "ElectricalSeries"
        """
        self.folder_path = Path(folder_path)
        intan_files = natsorted(self.folder_path.glob("*.rhs"))
        assert intan_files, f"The .rhs files are missing from {folder_path}."

        recording_list = [
            IntanRecordingExtractor(file_path=str(file_path), stream_id=stream_id) for file_path in intan_files
        ]

        super().__init__(recording_list=recording_list, verbose=verbose, es_key=es_key)

        electrodes_metadata = extract_electrode_metadata_with_pyintan(file_path=str(intan_files[0]))

        self.chaninfo = self._load_chaninfo()

        group_names = electrodes_metadata["group_names"]
        group_electrode_numbers = electrodes_metadata["group_electrode_numbers"]
        unique_group_names = electrodes_metadata["unique_group_names"]
        custom_names = electrodes_metadata["custom_names"]

        channel_ids = self.recording_extractor.get_channel_ids()
        self.recording_extractor.set_property(key="group_name", ids=channel_ids, values=group_names)
        if len(unique_group_names) > 1:
            self.recording_extractor.set_property(
                key="group_electrode_number", ids=channel_ids, values=group_electrode_numbers
            )

        if any(custom_names):
            self.recording_extractor.set_property(key="custom_channel_name", ids=channel_ids, values=custom_names)

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"]["properties"].update(
            ElectricalSeriesRaw=get_schema_from_hdmf_class(ElectricalSeries)
        )
        return metadata_schema

    def _load_chaninfo(self):
        """
        Loads the mat file that contains the brain area for each electrode and other metadata as dictionary.
        Returns None when the mat file is missing from the folder.
        """
        from pymatreader import read_mat

        mat_files = list(self.folder_path.glob("*.mat"))
        if not mat_files:
            return

        mat = read_mat(str(self.folder_path / mat_files[0]))
        assert "chaninfo" in mat, f"'chaninfo' is missing from {mat_files[0]}"
        return mat["chaninfo"]

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        ecephys_metadata = metadata["Ecephys"]

        # Add device
        system_name = self.chaninfo.pop("system", None)
        device = dict(
            name="Intan",
            description=f"{system_name} recording",
            manufacturer="Intan",
        )
        device_list = [device]
        ecephys_metadata.update(Device=device_list)

        first_recording_file_name = Path(self.source_data["recording_list"][0].neo_reader.filename).stem
        try:
            date_from_fname = first_recording_file_name.split("_", maxsplit=1)[1]
            session_start_time = datetime.strptime(date_from_fname, "%y%m%d_%H%M%S")
            metadata["NWBFile"].update(session_start_time=session_start_time)
        except IndexError:
            warnings.warn(
                "Could not parse 'session_start_time' from the recording filename."
                "The 'session_start_time' should be set manually."
            )

        # Add electrode group
        unique_group_name = set(self.recording_extractor.get_property("group_name"))
        electrode_group_list = [
            dict(
                name=group_name,
                description=f"Group {group_name} electrodes.",
                device=device["name"],
                location="",
            )
            for group_name in unique_group_name
        ]

        if self.chaninfo is not None:
            for property_name, property_values in self.chaninfo.items():
                self.recording_extractor.set_property(
                    key=property_name,
                    values=property_values,
                )

            if "brain_area" in self.chaninfo:
                locations = set(self.chaninfo["brain_area"])
                for electrode_group, location in zip(electrode_group_list, locations):
                    electrode_group.update(location=location)

        ecephys_metadata.update(ElectrodeGroup=electrode_group_list)

        # Add electrodes and electrode groups
        ecephys_metadata.update(
            Electrodes=[
                dict(name="group_name", description="The name of the ElectrodeGroup this electrode is a part of.")
            ],
        )

        # Add group electrode number if available
        recording_extractor_properties = self.recording_extractor.get_property_keys()
        if "group_electrode_number" in recording_extractor_properties:
            ecephys_metadata["Electrodes"].append(
                dict(name="group_electrode_number", description="0-indexed channel within a group.")
            )
        if "custom_channel_name" in recording_extractor_properties:
            ecephys_metadata["Electrodes"].append(
                dict(name="custom_channel_name", description="Custom channel name assigned in Intan.")
            )

        return metadata
