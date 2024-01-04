from typing import Optional

from neuroconv import NWBConverter
from neuroconv.datainterfaces import PlexonSortingInterface
from pynwb import NWBFile

from turner_lab_to_nwb.asap_tdt.interfaces import ASAPTdtRecordingInterface


class AsapTdtNWBConverter(NWBConverter):
    """Primary conversion class for Turner's extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPTdtRecordingInterface,
        SortingVL=PlexonSortingInterface,
        SortingGPi=PlexonSortingInterface,
    )

    def run_conversion(
        self,
        nwbfile_path: Optional[str] = None,
        nwbfile: Optional[NWBFile] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = False,
        conversion_options: Optional[dict] = None,
    ) -> None:

        # Rename unit properties to have descriptive names
        unit_properties_mapping = {
            "Area": "brain_area",
            "Quality": "unit_quality",
            "Quality (post-sorting)": "unit_quality_post_sorting",
            "GoodPeriod": "good_period",
        }

        # Map unit quality values to more descriptive names
        quality_values_map = dict(
            A="excellent",
            B="good",
            C="not good enough to call single-unit",
        )
        electrode_metadata = self.data_interface_objects["Recording"]._electrode_metadata
        electrode_metadata["Quality"] = electrode_metadata["Quality"].replace(quality_values_map)
        electrode_metadata["Quality (post-sorting)"] = electrode_metadata["Quality (post-sorting)"].replace(
            quality_values_map
        )

        num_units = 0
        sorting_interfaces = [
            interface_name for interface_name in self.data_interface_objects if "Sorting" in interface_name
        ]
        for interface_name in sorting_interfaces:
            target_name = interface_name.replace("Sorting", "")
            sorting_metadata = electrode_metadata[electrode_metadata["Target"] == target_name]

            sorting_interface = self.data_interface_objects[interface_name]
            sorting_extractor = sorting_interface.sorting_extractor

            if len(sorting_metadata) != sorting_extractor.get_num_units():
                # TODO: how to deal with the fact that the Vla data has 2 units but only one of them in the metadata
                area_value = sorting_metadata["Area"].values[0]
                sorting_extractor.set_property(
                    key="brain_area",
                    values=[area_value] * sorting_extractor.get_num_units(),
                )
                continue
            for property_name, renamed_property_name in unit_properties_mapping.items():
                sorting_extractor.set_property(
                    key=renamed_property_name,
                    values=sorting_metadata[property_name].values.tolist(),
                )
            extractor_unit_ids = sorting_extractor.get_unit_ids()
            # unit_ids are not unique across sorting interfaces, so we are offsetting them here
            sorting_extractor._main_ids = extractor_unit_ids + num_units
            num_units = len(extractor_unit_ids)

        super().run_conversion(
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            conversion_options=conversion_options,
        )
