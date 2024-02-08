from typing import Optional

import numpy as np
from neuroconv import NWBConverter
from neuroconv.utils import DeepDict
from pynwb import NWBFile

from turner_lab_to_nwb.asap_tdt.asap_tdt_gaia import ASAPTdtGaiaPlexonSortingInterface
from turner_lab_to_nwb.asap_tdt.interfaces import (
    ASAPTdtEventsInterface,
    ASAPTdtFilteredRecordingInterface,
    ASAPTdtRecordingInterface,
    ASAPTdtSortingInterface,
)


class AsapTdtGaiaNWBConverter(NWBConverter):
    """Primary conversion class for Turner's extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPTdtRecordingInterface,
        ProcessedRecording=ASAPTdtFilteredRecordingInterface,
        PlexonSorting=ASAPTdtGaiaPlexonSortingInterface,
        CuratedSorting=ASAPTdtSortingInterface,
        Events=ASAPTdtEventsInterface,
    )

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Explicitly set session_start_time to the start time from events interface (most accurate)
        events_interface = self.data_interface_objects["Events"]
        interface_metadata = events_interface.get_metadata()
        metadata["NWBFile"].update(session_start_time=interface_metadata["NWBFile"]["session_start_time"])

        return metadata

    # def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
    #     super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)
    #
    #     backend_configuration = get_default_backend_configuration(nwbfile=nwbfile, backend="hdf5")
    #     configure_backend(nwbfile=nwbfile, backend_configuration=backend_configuration)

    def set_processed_recording_interface_properties(self, interface_name: str) -> None:
        """
        Set properties for a recording interface based on the raw recording interface.
        """
        recording_interface = self.data_interface_objects[interface_name]
        raw_recording_extractor_properties = self.data_interface_objects["Recording"].recording_extractor._properties

        extractor_num_channels = recording_interface.recording_extractor.get_num_channels()
        raw_recording_num_channels = self.data_interface_objects["Recording"].recording_extractor.get_num_channels()
        assert extractor_num_channels == raw_recording_num_channels, (
            f"The number of channels in the processed recording extractor ({extractor_num_channels}) "
            f"does not match the number of channels in the raw recording extractor ({raw_recording_num_channels})."
        )

        # Set new channel ids
        new_channel_ids = raw_recording_extractor_properties["channel_ids"]
        recording_interface.recording_extractor._main_ids = new_channel_ids

        for property_name in raw_recording_extractor_properties:
            values = raw_recording_extractor_properties[property_name]
            recording_interface.recording_extractor.set_property(key=property_name, ids=new_channel_ids, values=values)

        # Set aligned starting time with recording extractor
        starting_time = self.data_interface_objects["Recording"].get_timestamps()[0]
        recording_interface.set_aligned_starting_time(aligned_starting_time=starting_time)

    def run_conversion(
        self,
        nwbfile_path: Optional[str] = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        conversion_options: Optional[dict] = None,
    ) -> None:

        if "ProcessedRecording" in self.data_interface_objects:
            self.set_processed_recording_interface_properties(interface_name="ProcessedRecording")

        # Add stimulation events metadata
        session_metadata = self.data_interface_objects["Recording"]._electrode_metadata
        stimulation_site = session_metadata["Stim. site"].replace(np.nan, None).unique()[0]
        if stimulation_site:
            stimulation_depth = session_metadata["Stim. depth"].unique()[0]
            metadata["StimulationEvents"].update(stimulation_site=stimulation_site, stimulation_depth=stimulation_depth)

        super().run_conversion(
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            conversion_options=conversion_options,
        )
