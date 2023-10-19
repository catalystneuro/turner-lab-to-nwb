from datetime import datetime
from pathlib import Path
import pandas as pd
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.utils import FilePathType
from spikeinterface import ChannelSliceRecording


class ASAPTdtRecordingInterface(BaseRecordingExtractorInterface):

    Extractor = ChannelSliceRecording

    def __init__(
        self,
        file_path: FilePathType,
        electrode_metadata_file_path: FilePathType,
        stream_id: str = "3",
        verbose: bool = True,
        es_key: str = "ElectricalSeries",
    ):
        """
        Load and prepare raw data and corresponding metadata from the TDT format (.Tbk files).

        Parameters
        ----------
        file_path : FilePathType
            The path to the TDT recording file.
        stream_id : FilePathType
            The stream of the data for spikeinterface, "3" by default.
        verbose : bool, default: True
            Verbose
        es_key : str, default: "ElectricalSeries"
        """
        from spikeinterface.extractors import TdtRecordingExtractor

        self.file_path = Path(file_path)

        assert self.file_path.exists(), f"The file {file_path} does not exist."
        valid_suffices = [".Tbk", ".Tdx", ".tev", ".tnt", ".tsq"]
        assert self.file_path.suffix in valid_suffices, (
            f"The file {file_path} is not a valid TDT file." f"The file suffix must be one of {valid_suffices}."
        )

        self._electrode_metadata = self._load_electrode_metadata(file_path=electrode_metadata_file_path)
        parent_recording = TdtRecordingExtractor(
            folder_path=str(self.file_path), stream_id=stream_id, all_annotations=True
        )

        # Tungsten electrode on channel 1 (channels 2-15 were grounded)
        # 16ch V-probe (tip-first contact length: 500 µm, inter-contact-interval: 150 µm) on channels 17-32
        channel_ids = list(parent_recording.get_channel_ids())
        sliced_channel_ids = [channel_ids[0]] + channel_ids[-16:]
        super().__init__(
            parent_recording=parent_recording, channel_ids=sliced_channel_ids, verbose=verbose, es_key=es_key
        )

        # Set properties
        group_names = "Group " + self._electrode_metadata["Target"]
        self.recording_extractor.set_property(key="group_name", ids=sliced_channel_ids, values=group_names)
        custom_names = self._electrode_metadata.apply(lambda row: f"{row['Electrode']}-{row['Chan#']}", axis=1).tolist()
        self.recording_extractor.set_property(key="custom_channel_name", ids=sliced_channel_ids, values=custom_names)

        # Fix channel name format
        channel_names = self.recording_extractor.get_property("channel_name")
        channel_names = [name.replace("'", "")[1:] for name in channel_names]
        self.recording_extractor.set_property(key="channel_name", values=channel_names)

    def _load_electrode_metadata(self, file_path: FilePathType):
        """Load the electrode metadata from the Excel file."""
        electrodes_metadata = pd.read_excel(file_path)
        # filter for this session
        _, filename = self.file_path.stem.split("_", maxsplit=1)
        electrode_metadata = electrodes_metadata[electrodes_metadata["Filename"] == filename]
        # todo: how to handle duplicated channel numbers? (e.g. channel 21 is duplicated)
        electrode_metadata_without_duplicates = electrode_metadata.drop_duplicates(subset=["Chan#"])
        return electrode_metadata_without_duplicates

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        ecephys_metadata = metadata["Ecephys"]
        device_metadata = ecephys_metadata["Device"][0]
        device_metadata.update(
            description="TDT recording",
            manufacturer="Tucker-Davis Technologies (TDT)",
        )

        electrode_groups = []
        unique_electrodes_data = self._electrode_metadata.groupby("Area").first()
        for location, data in unique_electrodes_data.iterrows():
            electrode_groups.append(
                dict(
                    name=f'Group {data["Target"]}',
                    description=f"Group {data['Electrode']} electrodes.",
                    device=ecephys_metadata["Device"][0]["name"],
                    location=location,
                )
            )
        ecephys_metadata.update(ElectrodeGroup=electrode_groups)

        self.recording_extractor.set_property(
            # SpikeInterface refers to this as 'brain_area', NeuroConv remaps to 'location'
            key="brain_area",
            values=self._electrode_metadata["Area"].values.tolist(),
        )

        # Add electrodes and electrode groups
        ecephys_metadata.update(
            Electrodes=[
                dict(name="group_name", description="The name of the ElectrodeGroup this electrode is a part of."),
                dict(name="custom_channel_name", description="Custom channel name assigned in TDT."),
            ]
        )

        return metadata
