from datetime import datetime
from pathlib import Path
from typing import Literal

from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.utils import FilePathType
from spikeinterface import ChannelSliceRecording

from turner_lab_to_nwb.asap_tdt.utils import load_session_metadata


class ASAPTdtRecordingInterface(BaseRecordingExtractorInterface):
    Extractor = ChannelSliceRecording

    def __init__(
        self,
        file_path: FilePathType,
        data_list_file_path: FilePathType,
        gain: float,
        stream_name: str = None,
        location: Literal["GPi", "VL", None] = None,
        verbose: bool = True,
        es_key: str = "ElectricalSeries",
    ):
        """
        Load and prepare raw data and corresponding metadata from the TDT format (.Tbk files).

        Parameters
        ----------
        file_path : FilePathType
            The path to the TDT recording file.
        data_list_file_path : FilePathType
            The path that points to the electrode metadata file (.xlsx).
        gain : float
            The conversion factor from int16 to microvolts.
        stream_name : str, optional
            The name of the stream for spikeinterface, when not specified defaults to "Conx" (extracellular signal).
        location : Literal["GPi", "VL", None], optional
            The location of the probe, when specified allows to filter the channels by location. By default None.
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

        # Determine stream_id (can differ from session to session which stream_id corresponds to the extracellular signal)
        stream_name = stream_name or "Conx"
        stream_id = self._determine_stream_id(stream_name=stream_name)

        _, filename = self.file_path.stem.split("_", maxsplit=1)
        electrode_metadata = load_session_metadata(file_path=data_list_file_path, session_id=filename)

        # Filter by location
        if location is not None:
            assert location in ["GPi", "VL"], f"Location must be one of ['GPi', 'VL'], not {location}."
            electrode_metadata = electrode_metadata[electrode_metadata["Target"].isin([location])]

        self._electrode_metadata = electrode_metadata.drop_duplicates(subset=["Chan#"])
        parent_recording = TdtRecordingExtractor(
            folder_path=str(self.file_path), stream_id=stream_id, all_annotations=True
        )
        # Set "gain_to_uV" extractor property
        parent_recording.set_channel_gains(gain)

        # Tungsten electrode on channel 1 (channels 2-15 were grounded)
        # 16ch V-probe (tip-first contact length: 500 µm, inter-contact-interval: 150 µm) on channels 17-32
        # Note the channel map can be different from session to session
        sliced_channel_ids = electrode_metadata["Chan#"].astype(str).values.tolist()
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
        # Remove duplicate channel_names property
        self.recording_extractor.delete_property(key="channel_names")

    def _determine_stream_id(self, stream_name: str) -> str:
        """Determine the stream_id for the specified stream_name."""
        from spikeinterface.extractors import TdtRecordingExtractor

        stream_names, stream_ids = TdtRecordingExtractor.get_streams(folder_path=str(self.file_path))
        stream_index = [stream_index for stream_index, stream in enumerate(stream_names) if stream_name in stream]
        assert len(stream_index) == 1, f"Found {len(stream_index)} streams with name {stream_name}."
        return stream_ids[stream_index[0]]

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        metadata["NWBFile"].update(
            session_start_time=datetime.strptime(str(self._electrode_metadata["Date"].values[0]), "%y%m%d"),
        )

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
        self.recording_extractor.set_property(
            key="location",
            values=self._electrode_metadata[["ML", "AP", "Z"]].values,
        )

        # Add electrodes and electrode groups
        ecephys_metadata.update(
            Electrodes=[
                dict(name="group_name", description="The name of the ElectrodeGroup this electrode is a part of."),
                dict(name="custom_channel_name", description="Custom channel name assigned in TDT."),
            ]
        )

        return metadata
