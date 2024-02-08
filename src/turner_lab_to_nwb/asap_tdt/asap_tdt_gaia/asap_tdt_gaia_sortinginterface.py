from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from neuroconv.utils import FilePathType
from spikeinterface import UnitsSelectionSorting
from spikeinterface.extractors import PlexonSortingExtractor


class ASAPTdtGaiaPlexonSortingInterface(BaseSortingExtractorInterface):
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
        channel_ids = channel_metadata["Chan#"]

        plexon_header = parent_sorting.neo_reader.header
        channel_names = [chan[0] for chan in plexon_header["signal_channels"] if chan[1] in channel_ids]
        channel_name_brain_area_mapping = dict(zip(channel_names, channel_metadata["Area"]))
        brain_area_units = [
            channel_name_brain_area_mapping[chan[0]]
            for chan in plexon_header["spike_channels"]
            if chan[0] in channel_names
        ]
        unit_ids_to_keep = [
            chan_ind for chan_ind, chan in enumerate(plexon_header["spike_channels"]) if chan[0] in channel_names
        ]
        super().__init__(parent_sorting=parent_sorting, unit_ids=unit_ids_to_keep, renamed_unit_ids=None)

        self.sorting_extractor.set_property(
            # SpikeInterface refers to this as 'brain_area', NeuroConv remaps to 'location'
            key="brain_area",
            values=brain_area_units,
        )
