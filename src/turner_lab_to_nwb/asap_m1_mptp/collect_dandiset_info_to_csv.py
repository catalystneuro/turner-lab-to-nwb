#!/usr/bin/env python
"""
Collect metadata from Turner Lab NWB files on DANDI to create a master CSV.

This script streams NWB files from DANDI dandiset 001636 and extracts metadata
for researchers to filter and select sessions based on experimental conditions.

See documentation/experiment_hypothesis_variables.md for details on how these
variables map to the paper hypotheses.

Usage:
    uv run python collect_dandiset_info_to_csv.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import remfile
import h5py
from pynwb import NWBHDF5IO
from tqdm import tqdm
from dandi.dandiapi import DandiAPIClient


# =============================================================================
# CONFIGURATION - Edit these variables to change settings
# =============================================================================

DANDISET_ID = "001636"
DANDISET_VERSION = "draft"
OUTPUT_PATH = Path(__file__).parent / "dandiset_session_metadata.csv"
MAX_FILES = None  # Set to integer for testing (e.g., 3), None for all files


# =============================================================================
# CONNECT TO DANDI
# =============================================================================

print(f"Connecting to DANDI:{DANDISET_ID} ({DANDISET_VERSION})...")
client = DandiAPIClient()
dandiset = client.get_dandiset(DANDISET_ID, DANDISET_VERSION)
assets = list(dandiset.get_assets())
nwb_assets = [a for a in assets if a.path.endswith(".nwb")]
print(f"Found {len(nwb_assets)} NWB files")

if MAX_FILES:
    nwb_assets = nwb_assets[:MAX_FILES]
    print(f"Limited to {MAX_FILES} files for testing")


# =============================================================================
# COLLECT METADATA
# =============================================================================

row_list = []

# Write CSV header
columns = [
    "asset_path", "asset_url", "session_id", "subject_id", "session_date", "session_time",
    "mptp_status", "related_publications", "chamber_grid_ap_mm", "chamber_grid_ml_mm",
    "chamber_insertion_depth_mm", "total_units", "ptn_count", "csn_count", "other_neuron_count",
    "neuron_projection_types", "min_antidromic_latency_ms", "max_antidromic_latency_ms",
    "mean_antidromic_latency_ms", "receptive_field_locations", "total_trials", "flexion_trials",
    "extension_trials", "has_perturbation_trials", "perturbation_trial_count", "mean_peak_velocity",
    "mean_movement_amplitude", "mean_reaction_time", "has_emg", "has_lfp", "has_isolation_monitoring_stim",
]
with open(OUTPUT_PATH, "w") as f:
    f.write(",".join(columns) + "\n")

for asset in tqdm(nwb_assets, desc="Collecting metadata"):
    # Open NWB file for streaming
    s3_url = asset.get_content_url(follow_redirects=1, strip_query=False)
    file_system = remfile.File(s3_url)
    h5_file = h5py.File(file_system, mode="r")
    io = NWBHDF5IO(file=h5_file)
    nwbfile = io.read()

    # -------------------------------------------------------------------------
    # Asset Information
    # -------------------------------------------------------------------------
    asset_path = asset.path
    asset_url = s3_url

    # -------------------------------------------------------------------------
    # Session-Level Metadata
    # -------------------------------------------------------------------------
    session_id = nwbfile.session_id
    subject_id = nwbfile.subject.subject_id

    session_start = nwbfile.session_start_time
    session_date = session_start.strftime("%Y-%m-%d")
    session_time = session_start.strftime("%H:%M:%S")

    # Extract MPTP status from session_id
    if "PreMPTP" in session_id:
        mptp_status = "Pre-MPTP"
    elif "PostMPTP" in session_id:
        mptp_status = "Post-MPTP"
    else:
        mptp_status = "Unknown"

    # Related publications
    related_publications = "; ".join(list(nwbfile.related_publications))

    # -------------------------------------------------------------------------
    # Electrode/Recording Location
    # -------------------------------------------------------------------------
    electrodes_df = nwbfile.electrodes.to_dataframe()
    recording_electrodes = electrodes_df[electrodes_df["chamber_grid_ap_mm"].notna()]
    rec_electrode = recording_electrodes.iloc[0]
    chamber_grid_ap_mm = float(rec_electrode["chamber_grid_ap_mm"])
    chamber_grid_ml_mm = float(rec_electrode["chamber_grid_ml_mm"])
    chamber_insertion_depth_mm = float(rec_electrode["chamber_insertion_depth_mm"])

    # -------------------------------------------------------------------------
    # Unit Summary Statistics
    # -------------------------------------------------------------------------
    units_df = nwbfile.units.to_dataframe()
    total_units = len(units_df)

    # Count neuron types
    projection_types = units_df["neuron_projection_type"].tolist()
    ptn_count = sum(1 for pt in projection_types if pt == "pyramidal_tract_neuron")
    csn_count = sum(1 for pt in projection_types if pt == "corticostriatal_neuron")
    other_neuron_count = total_units - ptn_count - csn_count
    unique_types = sorted(set(projection_types))
    neuron_projection_types = "; ".join(unique_types)

    # Antidromic latency statistics
    if "antidromic_latency_ms" in units_df.columns:
        latencies = units_df["antidromic_latency_ms"].dropna()
        if len(latencies) > 0:
            min_antidromic_latency_ms = float(latencies.min())
            max_antidromic_latency_ms = float(latencies.max())
            mean_antidromic_latency_ms = float(latencies.mean())
        else:
            min_antidromic_latency_ms = None
            max_antidromic_latency_ms = None
            mean_antidromic_latency_ms = None
    else:
        min_antidromic_latency_ms = None
        max_antidromic_latency_ms = None
        mean_antidromic_latency_ms = None

    # Receptive field locations
    if "receptive_field_location" in units_df.columns:
        rf_locations = units_df["receptive_field_location"].dropna()
        unique_rf = sorted(
            set(
                loc
                for loc in rf_locations
                if loc and loc not in ["not_tested", "no_response"]
            )
        )
        receptive_field_locations = "; ".join(unique_rf)
    else:
        receptive_field_locations = ""

    # -------------------------------------------------------------------------
    # Trial/Behavioral Information
    # -------------------------------------------------------------------------
    trials_df = nwbfile.trials.to_dataframe()
    total_trials = len(trials_df)

    # Movement type counts
    movement_types = trials_df["movement_type"]
    flexion_trials = int((movement_types == "flexion").sum())
    extension_trials = int((movement_types == "extension").sum())

    # Perturbation information
    perturbation_types = trials_df["torque_perturbation_type"]
    perturbation_mask = perturbation_types != "none"
    has_perturbation_trials = bool(perturbation_mask.any())
    perturbation_trial_count = int(perturbation_mask.sum())

    # Kinematic summary
    velocities = trials_df["derived_peak_velocity"].dropna()
    mean_peak_velocity = float(velocities.mean()) if len(velocities) > 0 else None

    amplitudes = trials_df["derived_movement_amplitude"].dropna()
    mean_movement_amplitude = float(amplitudes.mean()) if len(amplitudes) > 0 else None

    # Reaction time: cursor_departure_time - lateral_target_appearance_time
    reaction_times = (
        trials_df["cursor_departure_time"] - trials_df["lateral_target_appearance_time"]
    )
    valid_rt = reaction_times.dropna()
    mean_reaction_time = float(valid_rt.mean()) if len(valid_rt) > 0 else None

    # -------------------------------------------------------------------------
    # Data Availability Flags
    # -------------------------------------------------------------------------
    has_emg = any(name.startswith("EMG") for name in nwbfile.acquisition.keys())
    has_lfp = any(
        name == "LFP" or "LFP" in name for name in nwbfile.acquisition.keys()
    )

    # Isolation monitoring stimulation
    has_isolation_monitoring_stim = trials_df["isolation_monitoring_stim_time"].notna().any()

    # -------------------------------------------------------------------------
    # Build row dictionary
    # -------------------------------------------------------------------------
    row_dict = {
        # Asset Information
        "asset_path": asset_path,
        "asset_url": asset_url,
        # Session-Level Metadata
        "session_id": session_id,
        "subject_id": subject_id,
        "session_date": session_date,
        "session_time": session_time,
        "mptp_status": mptp_status,
        "related_publications": related_publications,
        # Electrode/Recording Location
        "chamber_grid_ap_mm": chamber_grid_ap_mm,
        "chamber_grid_ml_mm": chamber_grid_ml_mm,
        "chamber_insertion_depth_mm": chamber_insertion_depth_mm,
        # Unit Summary Statistics
        "total_units": total_units,
        "ptn_count": ptn_count,
        "csn_count": csn_count,
        "other_neuron_count": other_neuron_count,
        "neuron_projection_types": neuron_projection_types,
        # Unit-Level Aggregates
        "min_antidromic_latency_ms": min_antidromic_latency_ms,
        "max_antidromic_latency_ms": max_antidromic_latency_ms,
        "mean_antidromic_latency_ms": mean_antidromic_latency_ms,
        "receptive_field_locations": receptive_field_locations,
        # Trial/Behavioral Information
        "total_trials": total_trials,
        "flexion_trials": flexion_trials,
        "extension_trials": extension_trials,
        "has_perturbation_trials": has_perturbation_trials,
        "perturbation_trial_count": perturbation_trial_count,
        # Kinematic Summary
        "mean_peak_velocity": mean_peak_velocity,
        "mean_movement_amplitude": mean_movement_amplitude,
        "mean_reaction_time": mean_reaction_time,
        # Data Availability Flags
        "has_emg": has_emg,
        "has_lfp": has_lfp,
        "has_isolation_monitoring_stim": has_isolation_monitoring_stim,
    }

    row_list.append(row_dict)

    # Stream row to CSV immediately
    row_df = pd.DataFrame([row_dict])
    row_df.to_csv(OUTPUT_PATH, mode="a", header=False, index=False)

    # Cleanup resources
    io.close()
    h5_file.close()


# =============================================================================
# DONE
# =============================================================================

print(f"\nSaved {len(row_list)} rows to {OUTPUT_PATH}")
