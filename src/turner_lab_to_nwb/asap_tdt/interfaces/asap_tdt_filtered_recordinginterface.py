from pathlib import Path
from typing import Literal, Optional, List

import pandas as pd
from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.utils import FilePathType

from turner_lab_to_nwb.asap_tdt.extractors import ASAPTdtFilteredRecordingExtractor


class ASAPTdtFilteredRecordingInterface(BaseRecordingExtractorInterface):
    Extractor = ASAPTdtFilteredRecordingExtractor

    def __init__(
        self,
        file_path: FilePathType,
        channel_metadata: dict,
        es_key: str = "ElectricalSeriesProcessed",
        verbose: bool = True,
    ):
        """
        The interface to convert the high-pass filtered data from the ASAP TDT dataset.

        Parameters
        ----------
        file_path : FilePathType
            The path to the MAT file containing the high-pass filtered data.
        channel_metadata : dict
            The dictionary containing the metadata for the channels.
        es_key : str, optional
            The key to use for the ElectricalSeries, by default "ElectricalSeriesProcessed".
        verbose : bool, optional
            Allows for verbose output, by default True.
        """

        # Determine which channels to load for files with multiple channels (that do not have "Chans" in the name)
        # should be zero-indexed
        channel_ids = [int(chan) - 1 for chan in channel_metadata["Chan#"]]
        super().__init__(es_key=es_key, verbose=verbose, file_path=file_path, channel_ids=channel_ids)

        # Set properties
        self._electrode_metadata = pd.DataFrame(channel_metadata)
        group_names = "Group " + self._electrode_metadata["Target"]
        extractor_channel_ids = self.recording_extractor.get_channel_ids()
        self.recording_extractor.set_property(key="group_name", ids=extractor_channel_ids, values=group_names)
        custom_names = self._electrode_metadata.apply(lambda row: f"{row['Electrode']}-{row['Chan#']}", axis=1).tolist()
        self.recording_extractor.set_property(key="custom_channel_name", ids=extractor_channel_ids, values=custom_names)

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        ecephys_metadata = metadata["Ecephys"]
        brain_areas = self._electrode_metadata["Target"].unique()
        ecephys_metadata.update(ElectrodeGroup=[dict(name=f"Group {location}") for location in brain_areas])

        # Add electrodes and electrode groups
        ecephys_metadata.update(
            Electrodes=[
                dict(name="group_name", description="The name of the ElectrodeGroup this electrode is a part of."),
                dict(name="custom_channel_name", description="Custom channel name assigned in TDT."),
            ]
        )

        brain_areas_description = ", ".join(brain_areas) if len(brain_areas) > 1 else brain_areas[0]
        metadata["Ecephys"][self.es_key].update(
            description=f"High-pass filtered traces (200 Hz) from {brain_areas_description} region."
        )
        return metadata
