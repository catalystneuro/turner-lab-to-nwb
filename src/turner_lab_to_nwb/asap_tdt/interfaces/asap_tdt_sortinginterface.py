from typing import Literal

from neuroconv.datainterfaces.ecephys.basesortingextractorinterface import BaseSortingExtractorInterface
from neuroconv.utils import FilePathType

from turner_lab_to_nwb.asap_tdt.extractors import ASAPTdtSortingExtractor


class ASAPTdtSortingInterface(BaseSortingExtractorInterface):
    Extractor = ASAPTdtSortingExtractor

    def __init__(self, file_path: FilePathType, location: Literal["GPi", "VL"] = None, verbose: bool = True):
        """
        Parameters
        ----------
        file_path: FilePathType
            Path to the MAT file containing the spiking data.
        location: Literal["GPi", "VL"], optional
            The location of the probe, when specified allows to filter the units by location. By default None.
        verbose: bool, default: True
            Allows verbosity.
        """
        super().__init__(file_path=file_path, location=location, verbose=verbose)
