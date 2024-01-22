from typing import Literal

from neuroconv.datainterfaces.ecephys.baserecordingextractorinterface import BaseRecordingExtractorInterface
from neuroconv.utils import FilePathType

from turner_lab_to_nwb.asap_tdt.extractors import ASAPTdtFilteredRecordingExtractor


class ASAPTdtFilteredRecordingInterface(BaseRecordingExtractorInterface):
    Extractor = ASAPTdtFilteredRecordingExtractor

    def __init__(
        self,
        file_path: FilePathType,
        location: Literal["GPi", "VL"] = "GPi",
        es_key: str = "ElectricalSeriesProcessed",
        verbose: bool = True,
    ):
        """
        The interface to convert the high-pass filtered data from the ASAP TDT dataset.

        Parameters
        ----------
        file_path : FilePathType
            The path to the MAT file containing the high-pass filtered data.
        location : Literal["GPi", "VL"], optional
            The location of the probe, by default "GPi".
        es_key : str, optional
            The key to use for the ElectricalSeries, by default "ElectricalSeriesProcessed".
        verbose : bool, optional
            Allows for verbose output, by default True.
        """

        es_key_with_location = es_key + location
        self.location = location
        super().__init__(es_key=es_key_with_location, verbose=verbose, file_path=file_path)

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Ecephys"]["ElectrodeGroup"][0].update(name=f"Group {self.location}")
        metadata["Ecephys"][self.es_key].update(
            description=f"High-pass filtered traces (200 Hz) from {self.location} region."
        )
        return metadata
