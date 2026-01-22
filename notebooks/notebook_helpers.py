"""
Helper functions for antidromic detection tutorial notebook.
"""
import numpy as np


def get_sweep_waveforms(sweep_row):
    """
    Extract neural response and stimulation waveforms from an antidromic sweep.

    Parameters
    ----------
    sweep_row : pd.Series
        A row from the AntidromicSweepsIntervals table

    Returns
    -------
    time_ms : np.ndarray
        Time axis in milliseconds (0 = stimulation onset)
    response_uv : np.ndarray
        Neural response in microvolts
    stim_ua : np.ndarray
        Stimulation current in microamperes
    """
    # Extract response data
    response_ref = sweep_row['response']
    index_start, count, response_series = response_ref
    response_uv = response_series.data[index_start:index_start + count].flatten() * response_series.conversion * 1e6

    # Extract stimulation data
    stim_ref = sweep_row['stimulation']
    index_start_s, count_s, stim_series = stim_ref
    stim_ua = stim_series.data[index_start_s:index_start_s + count_s].flatten() * stim_series.conversion * 1e6

    # Create time axis: sweeps are 50ms, centered on stimulation (t=0 at 25ms)
    sampling_rate = response_series.rate
    time_ms = (np.arange(count) / sampling_rate - 0.025) * 1000

    return time_ms, response_uv, stim_ua


def measure_response_latency(time_ms, response_uv, expected_latency, window_ms=2.0):
    """
    Measure actual response latency by finding the peak near expected latency.

    Parameters
    ----------
    time_ms : np.ndarray
        Time axis in milliseconds
    response_uv : np.ndarray
        Neural response in microvolts
    expected_latency : float
        Expected latency in ms
    window_ms : float
        Search window size (default 2.0 ms)

    Returns
    -------
    float
        Measured latency in ms, or NaN if no clear peak found
    """
    from scipy.signal import find_peaks

    mask = (time_ms >= expected_latency - window_ms) & (time_ms <= expected_latency + window_ms)
    if not mask.any():
        return np.nan

    window_response = np.abs(response_uv[mask])
    window_time = time_ms[mask]

    peaks, properties = find_peaks(window_response, height=np.percentile(window_response, 70))
    if len(peaks) == 0:
        return np.nan

    highest_peak_idx = peaks[np.argmax(properties['peak_heights'])]
    return window_time[highest_peak_idx]


def measure_response_amplitude(time_ms, response_uv, latency, window_ms=1.5):
    """
    Measure peak-to-peak amplitude near expected latency.

    Parameters
    ----------
    time_ms : np.ndarray
        Time axis in milliseconds
    response_uv : np.ndarray
        Neural response in microvolts
    latency : float
        Expected latency in ms
    window_ms : float
        Window size for amplitude measurement (default 1.5 ms)

    Returns
    -------
    float
        Peak-to-peak amplitude in microvolts
    """
    mask = (time_ms >= latency - window_ms) & (time_ms <= latency + window_ms)
    if mask.any():
        window = response_uv[mask]
        return np.max(window) - np.min(window)
    return 0
