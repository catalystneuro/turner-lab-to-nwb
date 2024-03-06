from typing import Optional

import numpy as np
from ndx_turner_metadata import TurnerLabMetaData
from neuroconv import ConverterPipe
from neuroconv.utils import DeepDict
from pynwb import NWBFile


class ASAPTdtNWBConverter(ConverterPipe):
    """
    Primary conversion class for handling multiple TDT data streams.
    """

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Explicitly set session_start_time to the start time from events interface (most accurate)
        events_interface = self.data_interface_objects["Events"]
        interface_metadata = events_interface.get_metadata()
        metadata["NWBFile"].update(session_start_time=interface_metadata["NWBFile"]["session_start_time"])

        return metadata

    def set_processed_recording_interface_properties(self, interface_name: str) -> None:
        """
        Set properties for a recording interface based on the raw recording interface.
        """
        recording_interface = self.data_interface_objects[interface_name]
        raw_recording_extractor_properties = self.data_interface_objects["Recording"].recording_extractor._properties

        extractor_num_channels = recording_interface.recording_extractor.get_num_channels()

        target_name = interface_name.replace("ProcessedRecording", "")
        indices = range(extractor_num_channels)
        if target_name:
            group_name = f"Group {target_name}"
            indices = np.where(raw_recording_extractor_properties["group_name"] == group_name)[0]
            if len(indices) == 0:
                return

        assert len(indices) == extractor_num_channels

        # Set new channel ids
        new_channel_ids = raw_recording_extractor_properties["channel_ids"][indices]
        recording_interface.recording_extractor._main_ids = new_channel_ids

        for property_name in raw_recording_extractor_properties:
            values = raw_recording_extractor_properties[property_name][indices]
            recording_interface.recording_extractor.set_property(key=property_name, ids=new_channel_ids, values=values)

        # Set aligned starting time with recording extractor
        starting_time = self.data_interface_objects["Recording"].get_timestamps()[0]
        recording_interface.set_aligned_starting_time(aligned_starting_time=starting_time)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)

        # Add LabMetaData
        lab_meta_data = TurnerLabMetaData(**metadata["LabMetaData"])
        nwbfile.add_lab_meta_data(lab_meta_data)

    def run_conversion(
        self,
        nwbfile_path: Optional[str] = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        conversion_options: Optional[dict] = None,
    ) -> None:

        # Set processed recording interface properties to match with raw recording interface
        procesed_recording_interface_names = [
            interface_name for interface_name in self.data_interface_objects if "ProcessedRecording" in interface_name
        ]
        for interface_name in procesed_recording_interface_names:
            self.set_processed_recording_interface_properties(interface_name=interface_name)

        plexon_sorting_interface_names = [
            interface_name for interface_name in self.data_interface_objects if "PlexonSorting" in interface_name
        ]
        num_plexon_sorting_interfaces = len(plexon_sorting_interface_names)

        if num_plexon_sorting_interfaces > 1:
            num_units = 0
            for interface_name in plexon_sorting_interface_names:
                sorting_interface = self.data_interface_objects[interface_name]
                sorting_extractor = sorting_interface.sorting_extractor
                extractor_unit_ids = sorting_extractor.get_unit_ids()
                # unit_ids are not unique across sorting interfaces, so we are offsetting them here
                sorting_extractor._main_ids = extractor_unit_ids + num_units
                num_units = len(extractor_unit_ids)

        # Add stimulation events metadata
        channel_metadata = self.data_interface_objects["Recording"]._electrode_metadata
        stimulation_site = channel_metadata["Stim. site"].replace(np.nan, None).unique()[0]
        if stimulation_site:
            stimulation_depth = channel_metadata["Stim. depth"].unique()[0]
            metadata["StimulationEvents"].update(stimulation_site=stimulation_site, stimulation_depth=stimulation_depth)

        super().run_conversion(
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            conversion_options=conversion_options,
        )
