from typing import Optional

from neuroconv import NWBConverter
from neuroconv.datainterfaces import PlexonSortingInterface
from neuroconv.tools.nwb_helpers import get_default_backend_configuration, configure_backend
from neuroconv.utils import DeepDict
from pynwb import NWBFile

from turner_lab_to_nwb.asap_tdt.interfaces import ASAPTdtRecordingInterface, ASAPTdtEventsInterface
from turner_lab_to_nwb.asap_tdt.interfaces.asap_tdt_sortinginterface import ASAPTdtSortingInterface


class AsapTdtNWBConverter(NWBConverter):
    """Primary conversion class for Turner's extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPTdtRecordingInterface,
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

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata, conversion_options: Optional[dict] = None) -> None:
        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, conversion_options=conversion_options)

        backend_configuration = get_default_backend_configuration(nwbfile=nwbfile, backend="hdf5")
        configure_backend(nwbfile=nwbfile, backend_configuration=backend_configuration)

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
