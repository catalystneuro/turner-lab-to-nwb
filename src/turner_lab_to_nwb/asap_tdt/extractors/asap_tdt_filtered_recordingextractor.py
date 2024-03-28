from pathlib import Path
from typing import Optional, List

import numpy as np
from neuroconv.utils import FilePathType
from pymatreader import read_mat
from spikeinterface import BaseRecording, BaseRecordingSegment


class ASAPTdtFilteredRecordingExtractor(BaseRecording):
    extractor_name = "ASAPTdtFilteredRecording"
    mode = "file"
    name = "tdtfiltered"

    def __init__(self, file_path: FilePathType, channel_ids: Optional[List[int]] = None):
        """
        Parameters
        ----------
        file_path : FilePathType
            The file path to the MAT file containing the high-pass filtered data.
        channel_ids: Optional[List[int]], optional
            The indices of the channels to load (should be zero-indexed), by default None.
            When not specified, all channels are loaded.
        """

        file_path = Path(file_path)
        assert file_path.exists(), f"The file {file_path} does not exist."

        fft_data = read_mat(file_path)
        assert "samplerate" in fft_data, f"The file {file_path} does not contain a 'samplerate' key."
        assert "hp_cont" in fft_data, f"The file {file_path} does not contain a 'hp_cont' key."

        data = fft_data["hp_cont"]

        num_channels_in_file = data.shape[1] if len(data.shape) > 1 else 1
        if len(channel_ids) == num_channels_in_file:
            channel_ids = list(range(data.shape[1])) if len(data.shape) > 1 else [0]
        elif len(channel_ids) < num_channels_in_file:
            if "Chans" not in file_path.name:
                data = data[:, channel_ids]
            else:
                first_channel = channel_ids[0]
                # offset channel_ids to zero
                offset_channel_ids = [chan - first_channel for chan in channel_ids]
                data = data[:, offset_channel_ids]
        else:
            raise ValueError(f"channel_ids {channel_ids} has more channels than the file {file_path}")
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

        if self.num_channels == 1 and len(self._data.shape) == 1:
            traces = self._data[start_frame:end_frame]
            return traces[:, np.newaxis]

        return self._data[start_frame:end_frame, channel_indices]

    def get_num_samples(self) -> int:
        return self.num_samples


class ASAPTdtMultiFileFilteredRecordingExtractor(BaseRecording):
    def __init__(self, file_paths: list):
        """
        Parameters
        ----------
        file_paths : list
            The list of file paths to the MAT files containing the high-pass filtered data.
        """
        import h5py

        channel_ids = [int(Path(file_path).stem.replace(".flt", "").split("_")[-1]) for file_path in file_paths]

        with h5py.File(str(file_paths[0]), "r") as f:
            sampling_frequency = f["samplerate"][:][0][0]
            num_samples = f["hp_cont"].shape[1]
            dtype = f["hp_cont"][0, 0].dtype

        super().__init__(sampling_frequency, channel_ids, dtype)

        rec_segment = ASAPTdtMultiFileFilteredRecordingSegment(
            sampling_frequency=sampling_frequency, file_paths=file_paths, num_samples=num_samples
        )
        self.add_recording_segment(rec_segment)


class ASAPTdtMultiFileFilteredRecordingSegment(BaseRecordingSegment):
    def __init__(self, sampling_frequency: float, file_paths: list, num_samples: int, t_start: Optional[float] = None):
        super().__init__(sampling_frequency=sampling_frequency, t_start=t_start)

        self.file_paths = file_paths
        self.num_channels = len(file_paths)
        self.num_samples = num_samples

    def _concatenate_over_channels(self, start_frame=None, end_frame=None):
        import h5py

        data = []
        for file_path in self.file_paths:
            with h5py.File(str(file_path), "r") as f:
                data.append(f["hp_cont"][:, start_frame:end_frame])
        return np.concatenate(data, axis=0)

    def get_traces(self, start_frame=None, end_frame=None, channel_indices=None):
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = self.num_samples
        if channel_indices is None:
            channel_indices = slice(None)

        data = np.transpose(self._concatenate_over_channels(start_frame, end_frame), (1, 0))
        return data[:, channel_indices]

    def get_num_samples(self) -> int:
        return self.num_samples
