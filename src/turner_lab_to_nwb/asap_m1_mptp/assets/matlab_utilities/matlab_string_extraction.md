# MATLAB String Type Extraction Problem

## The Problem

MATLAB R2016b introduced a new `string` data type distinct from traditional `char` arrays. When MATLAB saves files containing string arrays (e.g., `stim_site` in the Events structure), these are stored as opaque objects that Python MATLAB readers cannot interpret:

```matlab
% MATLAB code
Events.stim_site = ["", "", ..., "Str", "Str", ...];  % string array
```

When loading in Python:
```python
from pymatreader import read_mat
mat = read_mat("v5604b.2.mat")
print(mat['Events']['stim_site'])  # Returns: None
```

The `pymatreader` library explicitly warns:
> "pymatreader cannot import Matlab string variables. Please convert these variables to char arrays in Matlab."

## MATLAB Storage Order: Column-Major (Fortran Order)

MATLAB uses column-major (Fortran-style) memory layout for arrays. This is relevant for reverse engineering because:

- Elements in the same column are stored contiguously in memory
- For a 1D array (column vector), elements are stored sequentially
- MATLAB inherited this from Fortran, the language it was originally written in

Sources:
- [MATLAB Row- and Column-Major Array Layouts](https://www.mathworks.com/help/coder/ug/what-are-column-major-and-row-major-representation-1.html)
- [Wikipedia: Row- and column-major order](https://en.wikipedia.org/wiki/Row-_and_column-major_order)

## Reverse Engineering Attempt: Detailed Example

### Test File: `v5604b.2.mat`

**Known facts from other Events fields:**
- Total trials: 40
- `stim` field values: indices 0-10 are NaN, indices 11-39 have values (~244-245 ms)
- Therefore: 11 trials without stimulation, 29 trials with stimulation

**Known facts from MATLAB export (user verification):**
- `stim_site` is a 40x1 string array
- Indices 0-10: empty strings (`""`) - 11 trials without stimulation
- Indices 11-39: `"Str"` - 29 trials with stimulation

The `stim` and `stim_site` arrays are perfectly aligned: wherever `stim` is NaN, `stim_site` is empty; wherever `stim` has a value, `stim_site` is "Str".

### Discovery: UTF-16-LE Strings in `__function_workspace__`

MATLAB string values are stored as UTF-16-LE encoded text within the `__function_workspace__` binary blob:

```python
import scipy.io as sio

mat = sio.loadmat("v5604b.2.mat")
raw = mat['__function_workspace__'].tobytes()

# Search for 'Str' in UTF-16-LE encoding
str_utf16 = 'Str'.encode('utf-16-le')  # = b'S\x00t\x00r\x00'
count = raw.count(str_utf16)
print(count)  # Returns: 29
```

### Validation Results

| Metric | Expected | Found | Match |
|--------|----------|-------|-------|
| Total "Str" occurrences | 29 | 29 | Yes |
| Trials with stimulation (non-NaN stim) | 29 | 29 | Yes |

The count exactly matches the number of trials with stimulation.

### Successful Extraction: Binary Structure Decoding

Through detailed analysis, we discovered the complete binary structure:

**Binary Layout in `__function_workspace__`:**

| Offset | Size | Content | Example Value |
|--------|------|---------|---------------|
| 504 | 8 bytes | Array size (n_trials) | 40 |
| 512 | 8 bytes | Dimensions (always 1) | 1 |
| 520 | n_trials * 8 bytes | String lengths array | [0,0,...,3,3,...] |
| 520 + n_trials*8 | variable | UTF-16-LE string data | "Str", "Str", ... |

**Decoded String Lengths (v5604b.2.mat):**

```
Offset 520: Trial  0 length = 0 (empty)
Offset 528: Trial  1 length = 0 (empty)
...
Offset 600: Trial 10 length = 0 (empty)
Offset 608: Trial 11 length = 3 ("Str")
Offset 616: Trial 12 length = 3 ("Str")
...
Offset 832: Trial 39 length = 3 ("Str")
```

**String Data Block (starts at offset 840):**
- 29 consecutive "Str" strings in UTF-16-LE (6 bytes each)
- Empty strings (length=0) have no data in this block
- Total: 29 * 6 = 174 bytes of string data

### Working Extraction Code

```python
import scipy.io as sio

def extract_stim_site_from_workspace(file_path, n_trials):
    """Extract stim_site string array from __function_workspace__."""
    mat = sio.loadmat(str(file_path))
    raw = mat['__function_workspace__'].tobytes()

    # Find array size marker
    size_bytes = n_trials.to_bytes(8, 'little')
    size_pos = raw.find(size_bytes)

    # Length array starts 16 bytes after size marker
    lengths_start = size_pos + 16

    # Extract string lengths
    lengths = []
    for i in range(n_trials):
        offset = lengths_start + i * 8
        lengths.append(int.from_bytes(raw[offset:offset+8], 'little'))

    # Extract strings (UTF-16-LE)
    strings = []
    string_pos = lengths_start + n_trials * 8
    for length in lengths:
        if length == 0:
            strings.append("")
        else:
            byte_length = length * 2
            strings.append(raw[string_pos:string_pos+byte_length].decode('utf-16-le'))
            string_pos += byte_length

    return strings
```

### Validation Across All 171 Files

**Full dataset validation: 171/171 files passed**

| Site | Files | Description |
|------|-------|-------------|
| Thal | 117 | Thalamus stimulation |
| Str | 51 | Striatum stimulation |
| Ped | 3 | Peduncle stimulation |

Sample files tested:

| File | Trials | Non-empty | Unique Values | Status |
|------|--------|-----------|---------------|--------|
| v5604b.2.mat | 40 | 29 | {"", "Str"} | OK |
| v4301.1.mat | 20 | 19 | {"", "Thal"} | OK |
| v4509.1.mat | 17 | 15 | {"", "Thal"} | OK |

### Ground Truth Verification: v4509.1.mat

MATLAB export confirmed (1-indexed):
- Indices 1-2: empty strings (`""`)
- Indices 3-17: `"Thal"` (15 elements)

Python extraction (0-indexed):
- Indices 0-1: empty strings
- Indices 2-16: "Thal"

Matches perfectly with the `stim` field:
- `stim[0:2]` = NaN (no stimulation)
- `stim[2:17]` = ~244 ms (stimulation delivered)

## Remaining Considerations

### 1. MATLAB Version Consistency (Confirmed)

All files in this dataset use the same MATLAB format:
- Header: `MATLAB 5.0 MAT-file, Platform: PCWIN64`
- Created: July 2025 (December 2025 update batch)

This means version variability is **not a concern** for this specific dataset.

### 2. Validation Against `stim` Field

The extraction can be validated by checking alignment with the `stim` numeric field:
- Where `stim` is NaN, `stim_site` should be empty
- Where `stim` has a value, `stim_site` should be non-empty

### 3. Multiple String Fields

If future MATLAB files contain multiple string variables, their data may be interleaved in `__function_workspace__`. The current implementation assumes `stim_site` is the only string field.

## Implementation

The extraction function is implemented in:
- `extract_matlab_strings.py` - Main extraction function
- `__init__.py` - Module exports

Usage:
```python
from turner_lab_to_nwb.asap_m1_mptp.assets.matlab_utilities import (
    extract_stim_site_from_workspace,
    validate_stim_site_extraction,
)

stim_site, error = extract_stim_site_from_workspace(file_path, n_trials=40)
if error:
    print(f"Extraction failed: {error}")
else:
    is_valid, validation_error = validate_stim_site_extraction(stim_site, stim_times)
```

## Current Implementation Status

- `stim` field (stimulation times): Successfully extracted via `pymatreader`
- `stim_site` field (stimulation locations): **Successfully extracted** via reverse-engineered binary decoding

## References

- pymatreader issue: MATLAB string type not supported
- pymatreader MR #42: Adds support for v7.3 MAT files with strings (not applicable - our files are v5 format)
- scipy.io documentation: `__function_workspace__` is an internal MATLAB structure
