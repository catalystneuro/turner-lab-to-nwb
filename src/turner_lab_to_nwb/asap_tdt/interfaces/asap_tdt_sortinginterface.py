from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from neuroconv.utils import FilePathType

from turner_lab_to_nwb.asap_tdt.extractors import ASAPTdtSortingExtractor


class ASAPTdtSortingInterface(BaseSortingExtractorInterface):
    Extractor = ASAPTdtSortingExtractor

    def __init__(self, file_path: FilePathType, gpi_only: bool = True, verbose: bool = True):
        """
        Parameters
        ----------
        file_path: FilePathType
            Path to the MAT file containing the spiking data.
        gpi_only: bool, optional
            Determines whether to load only GPi units, by default True.
        verbose: bool, default: True
            Allows verbosity.
        """
        super().__init__(file_path=file_path, gpi_only=gpi_only, verbose=verbose)
