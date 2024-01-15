from typing import Optional

import numpy as np
import pandas as pd
from neuroconv import NWBConverter
from neuroconv.datainterfaces import PlexonSortingInterface
from neuroconv.tools.nwb_helpers import get_default_backend_configuration, configure_backend
from neuroconv.utils import DeepDict
from pynwb import NWBFile

from turner_lab_to_nwb.asap_tdt.interfaces import (
    ASAPTdtEventsInterface,
    ASAPTdtFilteredRecordingInterface,
    ASAPTdtRecordingInterface,
    ASAPTdtSortingInterface,
)


class AsapTdtNWBConverter(NWBConverter):
    """Primary conversion class for Turner's extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPTdtRecordingInterface,
        ProcessedRecordingVL=ASAPTdtFilteredRecordingInterface,
        ProcessedRecordingGPi=ASAPTdtFilteredRecordingInterface,
        PlexonSortingVL=PlexonSortingInterface,
        PlexonSortingGPi=PlexonSortingInterface,
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
        group_name = f"Group {recording_interface.location}"
        raw_recording_extractor_properties = self.data_interface_objects["Recording"].recording_extractor._properties

        indices = np.where(raw_recording_extractor_properties["group_name"] == group_name)[0]
        if len(indices) == 0:
            return

        extractor_num_channels = recording_interface.recording_extractor.get_num_channels()
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

    def run_conversion(
        self,
        nwbfile_path: Optional[str] = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        conversion_options: Optional[dict] = None,
    ) -> None:
        # Add unit properties
        electrode_metadata = self.data_interface_objects["Recording"]._electrode_metadata
        # self.data_interface_objects["Recording"].recording_extractor.set_channel_gains(1.0)

        # Set processed recording interface properties to match with raw recording interface
        vl_interface_name = "ProcessedRecordingVL"
        self.set_processed_recording_interface_properties(
            recording_interface_name=vl_interface_name, electrode_metadata=electrode_metadata
        )

        gpi_interface_name = "ProcessedRecordingGPi"
        if gpi_interface_name in self.data_interface_objects:
            self.set_processed_recording_interface_properties(
                recording_interface_name=gpi_interface_name, electrode_metadata=electrode_metadata
            )

        num_units = 0
        plexon_sorting_interfaces = [
            interface_name for interface_name in self.data_interface_objects if "PlexonSorting" in interface_name
        ]
        for interface_name in plexon_sorting_interfaces:
            target_name = interface_name.replace("PlexonSorting", "")
            sorting_metadata = electrode_metadata[electrode_metadata["Target"] == target_name]

            sorting_interface = self.data_interface_objects[interface_name]
            sorting_extractor = sorting_interface.sorting_extractor

            # set unit properties
            area_value = sorting_metadata["Area"].values[0]
            sorting_extractor.set_property(
                key="location",
                values=[area_value] * sorting_extractor.get_num_units(),
            )
            extractor_unit_ids = sorting_extractor.get_unit_ids()
            # unit_ids are not unique across sorting interfaces, so we are offsetting them here
            sorting_extractor._main_ids = extractor_unit_ids + num_units
            num_units = len(extractor_unit_ids)

        # Add stimulation events metadata
        stimulation_site = electrode_metadata["Stim. site"].unique()[0]
        if stimulation_site:
            stimulation_depth = electrode_metadata["Stim. depth"].unique()[0]
            metadata["StimulationEvents"].update(stimulation_site=stimulation_site, stimulation_depth=stimulation_depth)

        super().run_conversion(
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            conversion_options=conversion_options,
        )
