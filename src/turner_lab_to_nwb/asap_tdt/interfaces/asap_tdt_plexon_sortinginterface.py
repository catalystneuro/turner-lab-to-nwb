from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from neuroconv.utils import FilePathType
from spikeinterface import UnitsSelectionSorting
from spikeinterface.extractors import PlexonSortingExtractor


class ASAPTdtPlexonSortingInterface(BaseSortingExtractorInterface):
    Extractor = UnitsSelectionSorting

    def __init__(self, file_path: FilePathType, channel_metadata: dict):
        """
        Parameters
        ----------
        file_path: FilePathType
            Path to the MAT file containing the spiking data.
        channel_metadata: dict
            The channel metadata.
        """

        parent_sorting = PlexonSortingExtractor(file_path=file_path)
        if parent_sorting.get_num_units() == 0:
            raise ValueError(f"No units found in '{file_path}'.")

        plexon_header = parent_sorting.neo_reader.header
        plexon_channel_ids = [str(int(chan)) for chan in channel_metadata["plx Chan#"]]
        plexon_channel_names = [f"Channel{num.zfill(2)}" for num in plexon_channel_ids]
        channel_names = [
            chan[0]
            for chan in plexon_header["spike_channels"]
            for channel_name in plexon_channel_names
            if channel_name == chan[0]
        ]

        brain_area = channel_metadata["Area"]
        if len(plexon_channel_names) != brain_area:
            if len(set(brain_area)) == 1:
                brain_area = [brain_area[0]] * len(plexon_channel_names)
        else:
            raise ValueError(
                f"Length of channel names ({len(plexon_channel_names)}) does not match length of brain area ({len(channel_metadata['Area'])})."
            )

        channel_name_brain_area_mapping = dict(zip(plexon_channel_names, brain_area))
        brain_area_units = [
            channel_name_brain_area_mapping[chan[0]]
            for chan in plexon_header["spike_channels"]
            if chan[0] in channel_names
        ]
        unit_ids_to_keep = [
            chan_ind for chan_ind, chan in enumerate(plexon_header["spike_channels"]) if chan[0] in channel_names
        ]
        assert len(unit_ids_to_keep), f"No units found in '{file_path}' for channels '{plexon_channel_ids}'."
        super().__init__(parent_sorting=parent_sorting, unit_ids=unit_ids_to_keep, renamed_unit_ids=None)

        self.sorting_extractor.set_property(
            # SpikeInterface refers to this as 'brain_area', NeuroConv remaps to 'location'
            key="location",
            values=brain_area_units,
        )
