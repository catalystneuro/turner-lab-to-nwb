from pathlib import Path
from typing import Optional

import numpy as np
from neuroconv.utils import FilePathType
from pymatreader import read_mat
from spikeinterface import BaseRecording, BaseRecordingSegment


class ASAPTdtFilteredRecordingExtractor(BaseRecording):
    extractor_name = "ASAPTdtFilteredRecording"
    mode = "file"
    name = "tdtfiltered"

    def __init__(self, file_path: FilePathType):
        """
        Parameters
        ----------
        file_path : FilePathType
            The file path to the MAT file containing the high-pass filtered data.
        """

        file_path = Path(file_path)
        assert file_path.exists(), f"The file {file_path} does not exist."

        fft_data = read_mat(file_path)
        assert "samplerate" in fft_data, f"The file {file_path} does not contain a 'samplerate' key."
        assert "hp_cont" in fft_data, f"The file {file_path} does not contain a 'hp_cont' key."

        data = fft_data["hp_cont"]
        channel_ids = list(range(data.shape[1])) if len(data.shape) > 1 else [0]
        sampling_frequency = fft_data["samplerate"]
        dtype = data.dtype

        super().__init__(sampling_frequency, channel_ids, dtype)

        rec_segment = ASAPTdtFilteredRecordingSegment(sampling_frequency=sampling_frequency, data=data)
        self.add_recording_segment(rec_segment)


class ASAPTdtFilteredRecordingSegment(BaseRecordingSegment):
    def __init__(self, sampling_frequency: float, t_start: Optional[float] = None, data=None):
        super().__init__(sampling_frequency=sampling_frequency, t_start=t_start)

        self._data = data
        self.num_channels = self._data.shape[1] if len(self._data.shape) > 1 else 1
        self.num_samples = self._data.shape[0]

    def get_traces(self, start_frame=None, end_frame=None, channel_indices=None):
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = self._data.shape[0]
        if channel_indices is None:
            channel_indices = slice(None)

        if self.num_channels == 1:
            traces = self._data[start_frame:end_frame]
            return traces[:, np.newaxis]

        return self._data[start_frame:end_frame, channel_indices]

    def get_num_samples(self) -> int:
        return self.num_samples
