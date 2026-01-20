"""
Extract MATLAB string arrays from __function_workspace__ binary blob.

MATLAB R2016b+ string arrays are stored as opaque objects that Python's scipy.io
and pymatreader cannot read. However, the string data is stored in the
__function_workspace__ binary blob in a predictable structure.

This module provides a function to extract these strings by reverse-engineering
the binary format. See matlab_string_extraction.md for detailed documentation.

Note: This approach is specific to the Turner Lab M1 MPTP dataset (MATLAB 5.0
MAT-files, Platform: PCWIN64). It may not work for other MATLAB versions or formats.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io as sio


def extract_stim_site_from_workspace(
    file_path: Path,
    n_trials: int,
) -> tuple[Optional[list[str]], Optional[str]]:
    """
    Extract stim_site string array from MATLAB __function_workspace__.

    Parameters
    ----------
    file_path : Path
        Path to the MATLAB .mat file
    n_trials : int
        Number of trials (length of the string array to extract)

    Returns
    -------
    tuple[Optional[list[str]], Optional[str]]
        Tuple of (strings, error_message)
        - strings: List of extracted strings if successful, None if failed
        - error_message: Error description if failed, None if successful

    Notes
    -----
    The binary structure in __function_workspace__ is:
    1. Find array size marker (n_trials as 8-byte little-endian int)
    2. Verify next 8 bytes = 1 (dimensions)
    3. Read n_trials x 8-byte length values (string lengths in characters)
    4. Read string data as UTF-16-LE (2 bytes per character)

    Empty strings have length 0 and no data in the string block.
    Multiple occurrences of n_trials may exist; we find the one followed by
    valid string array structure (dimension=1, reasonable length values).
    """
    mat_scipy = sio.loadmat(str(file_path), squeeze_me=True, struct_as_record=False)

    if "__function_workspace__" not in mat_scipy:
        return None, "No __function_workspace__ found in file"

    raw = mat_scipy["__function_workspace__"].tobytes()

    # Search for all occurrences of the array size marker (n_trials as 8-byte little-endian)
    size_bytes = n_trials.to_bytes(8, "little")
    size_positions = []
    pos = 0
    while True:
        pos = raw.find(size_bytes, pos)
        if pos == -1:
            break
        size_positions.append(pos)
        pos += 1

    if not size_positions:
        return None, f"Could not find array size marker ({n_trials}) in __function_workspace__"

    # Find the correct occurrence: followed by dimension=1 and valid length values
    size_pos = None
    for candidate_pos in size_positions:
        # Check if dimension=1 follows (at candidate_pos + 8)
        if candidate_pos + 16 > len(raw):
            continue
        dimension = int.from_bytes(raw[candidate_pos + 8 : candidate_pos + 16], "little")
        if dimension != 1:
            continue

        # Check if first length value is reasonable (0-100, typical string lengths)
        if candidate_pos + 24 > len(raw):
            continue
        first_length = int.from_bytes(raw[candidate_pos + 16 : candidate_pos + 24], "little")
        if first_length > 100:  # Unreasonable string length
            continue

        # This looks like a valid string array header
        size_pos = candidate_pos
        break

    if size_pos is None:
        return None, f"Could not find valid string array structure for {n_trials} trials"

    # Length array starts 16 bytes after size marker
    lengths_start = size_pos + 16

    # Extract string lengths (8 bytes each)
    lengths = []
    for i in range(n_trials):
        offset = lengths_start + i * 8
        if offset + 8 > len(raw):
            return None, f"Length array at offset {offset} extends beyond workspace (size {len(raw)})"
        length = int.from_bytes(raw[offset : offset + 8], "little")
        lengths.append(length)

    # String data starts immediately after the length array
    string_data_start = lengths_start + n_trials * 8

    # Extract strings (UTF-16-LE encoding: 2 bytes per character)
    strings = []
    current_pos = string_data_start

    for i, length in enumerate(lengths):
        if length == 0:
            strings.append("")
        else:
            byte_length = length * 2  # UTF-16-LE
            if current_pos + byte_length > len(raw):
                return None, f"String data for trial {i} extends beyond workspace"
            string_bytes = raw[current_pos : current_pos + byte_length]
            try:
                string_val = string_bytes.decode("utf-16-le")
                strings.append(string_val)
            except UnicodeDecodeError as e:
                return None, f"Unicode decode error for trial {i}: {e}"
            current_pos += byte_length

    return strings, None


def validate_stim_site_extraction(
    stim_site: list[str],
    stim_times: np.ndarray,
) -> tuple[bool, Optional[str]]:
    """
    Validate that extracted stim_site aligns with stim times.

    Parameters
    ----------
    stim_site : list[str]
        Extracted stimulation site strings
    stim_times : np.ndarray
        Stimulation times from Events['stim'] (NaN for no stimulation)

    Returns
    -------
    tuple[bool, Optional[str]]
        Tuple of (is_valid, error_message)

    Notes
    -----
    Validation rules:
    - Arrays must have same length
    - Where stim_times is NaN, stim_site should be empty string
    - Where stim_times has a value, stim_site should be non-empty
    """
    if len(stim_site) != len(stim_times):
        return False, f"Length mismatch: stim_site={len(stim_site)}, stim_times={len(stim_times)}"

    for i, (site, time) in enumerate(zip(stim_site, stim_times)):
        is_nan = np.isnan(time)
        is_empty = site == ""

        if is_nan and not is_empty:
            return False, f"Trial {i}: stim_times is NaN but stim_site='{site}' (expected empty)"
        if not is_nan and is_empty:
            return False, f"Trial {i}: stim_times={time} but stim_site is empty (expected non-empty)"

    return True, None
