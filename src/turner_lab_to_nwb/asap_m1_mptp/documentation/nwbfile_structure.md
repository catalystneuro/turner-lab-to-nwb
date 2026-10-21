# NWBFile Structure for Turner Lab ASAP M1 MPTP

Overview of how the conversion writes the Turner Lab M1 MPTP sessions into an NWBFile. Each NWB file represents one recording session (one or two simultaneously isolated units) from the visuomotor step-tracking task described across the Turner lab publications (2011 Cerebral Cortex, 2013 Frontiers in Systems Neuroscience, 2016 Brain; summarized in `assets/papers_summary_and_notes/`).

## Session scope and identifiers
- Session ID format: `{Animal}++{FName}++{Pre|Post}MPTP++Depth{depth_um}um++{YYYYMMDD}` (see `conversion_script.py`).
- `session_start_time` set to the recording date at 00:00 Pittsburgh time; intra-day ordering encoded via file sequence if multiple sessions per date.
- `nwbfile.notes` documents the synthetic 3 s gaps between trials; use trial/series timestamps for timing analyses, not the absolute session clock.

## NWBFile metadata and subject
- `NWBFile` fields populated from `metadata.yaml` and session metadata (`session_description`, `experiment_description`, `keywords`, `related_publications`, `pharmacology` with session-specific Pre/Post MPTP note).
- Subject filled from metadata table (`Subject.subject_id`, species, sex, weight, description).
- Lab/institution/experimenter set to Turner Lab (Emory); surgery text describes chamber and implanted stimulating electrodes.

## Devices
- `DeviceMicroelectrodeRecording`: glass-coated PtIr microelectrode and amplifier chain for spikes/LFP.
- `DeviceMicrowirePeduncleStimulation`, `DeviceMicrowirePutamenStimulation1-3`, `DeviceMicrowireThalamicStimulation`: chronic stimulation electrodes used for antidromic identification.
- `TorqueMotor`: manipulandum torque motor used for task control and perturbations.

## Electrodes table
- One recording electrode row per distinct recording location of the session's source files, created in `electrodes_interface.py` under `ElectrodeGroupMicroelectrodeRecording` (location: left M1). Almost every session has one; `v3204`, merged from files recorded at 19.5 and 19.4 mm, has two.
- Custom columns: `chamber_grid_ap_mm`, `chamber_grid_ml_mm`, `chamber_insertion_depth_mm`, `icms_effect`, `icms_threshold_uA`.
- Recording coordinates/depth derived from session metadata (`A_P`, `M_L`, `Depth`). Note: `A_P` is negated during conversion so `chamber_grid_ap_mm` uses +posterior convention; `M_L` is stored as-is (+right). Each unit's `electrodes` column lists the electrodes of the files it was recorded in.

## Trials table and HED annotations
- Built in `trials_interface.py` using MATLAB `Events` and `Mvt` structures; start/stop times from `Events['end']` with 3 s inter-trial spacing.
- Columns with HED tagging via `assets/trials_hed_sidecar.json`: `center_target_appearance_time`, `lateral_target_appearance_time`, `cursor_departure_time`, `reward_time`, `torque_perturbation_onset_time`, `derived_movement_onset_time`, `derived_movement_end_time`, `derived_peak_velocity`, `derived_peak_velocity_time`, `derived_movement_amplitude`, `derived_end_position`.
- Additional categorical columns: `movement_type` (flexion/extension), `torque_perturbation_type` (flexion/extension/none; not_available in every monkey L trial), `isolation_monitoring_stim_time`/`isolation_monitoring_stim_site`, `source_file` (the source file of each trial, which differs within sessions merged from several files).
- `HedLabMetaData` stored in `lab_meta_data` for schema versioning; trials table validated with HedNWBValidator.

## Units table (spike times and cell ID metadata)
- Added in `spike_times_interface.py`; spike times concatenated across trials with trial offsets (ms → s) and linked to the electrode of each file the unit was recorded in.
- Key columns: `neuron_projection_type` (PTN/CSN/variants), `antidromic_stimulation_sites`, `antidromic_latency_ms`, `antidromic_threshold`, optional secondary latency/threshold, `receptive_field_location`, `receptive_field_stimulus`, `unit_name` (source file and unit, e.g. `v0502.1`, or `v2701.1+v2702.2` for a neuron recorded across two files), `is_post_mptp`.
- Cell-type metadata derived from antidromic tests and receptive field notes in the metadata table, aligning with the paper summaries in `assets/papers_summary_and_notes/`.

## Behavioral and electrophysiology acquisitions
- Manipulandum signals (`manipulandum_interface.py`), named for the joint moved: `Elbow*` in monkey V files, `Wrist*` in monkey L files:
  - `ElbowAngle` (`SpatialSeries`, acquisition) – joint angle (deg), positive = flexion.
  - `ElbowTorque` (`TimeSeries`, acquisition) – torque command (a.u.).
  - `ElbowVelocity` (`TimeSeries`, behavior processing module) – joint velocity (deg/s).
- EMG (`emg_interface.py`):
  - One acquisition `TimeSeries` per muscle channel, named `EMG{Muscle}` (e.g., `EMGTricepsLongus`, duplicates get numeric suffixes); unit `a.u.`, descriptions include muscle function and preprocessing.
- LFP (`lfp_interface.py`):
  - `LFP` acquisition; volts, bandpass 1–100 Hz, concatenated across trials. See [lfp.md](lfp.md) for details.

## Antidromic identification processing
- Processing module `antidromic_identification` from `antidromic_stimulation_interface.py` stores per-sweep antidromic tests used for neuron classification.
- `StimulationElectrodesTable` (DynamicTable) documents the chronically implanted multi-contact stimulation electrodes (peduncle, two posterior putamen, VL thalamus, plus STN for monkey Leu only). Per-electrode contact counts are stored in the `n_contacts` column and the per-monkey complement was confirmed by R. Turner (2026-05-04). Venus has 4 rows; Leu has 5 rows.
- `AntidromicSweepsIntervals` (TimeIntervals) rows reference:
  - `AntidromicStimulation_{file}_{Location}` (`TimeSeries`, amperes, estimated conversion), e.g. `AntidromicStimulation_v2701.1_Peduncle`: one series per source unit file and stimulation site, holding its sweeps back to back
  - `AntidromicResponse_{file}_{Location}` (`ElectricalSeries`, volts, estimated conversion, electrode region pointing to the recording electrode of that file)
  - Columns: stimulation_onset_time, unit_name, unit (link to the units table row), location, stimulation_protocol (Collision/FrequencyFollowing/Orthodromic, or unspecified where the source label names only the site), source_label (the sweep's label in the source), sweep_number, stimulation/response references, stimulation_electrode index.
- Antidromic sweeps are placed after behavioral trials (buffer + per-site spacing); sampling rate derived from sweep timebase.

## Alignment and timing
- Analog sampling rate pulled from MATLAB `file_info['analog_fs']`; each trial's samples start at that trial's `start_time` (the same trial start times the trials table and spikes use, from `interfaces/trial_sources.py`), spaced by 1/`analog_fs`.
- Trial start/stop times from `Events['end']` ensure acquisitions and unit timestamps share the same absolute timeline.
- Session-level note warns that inter-trial intervals are synthetic; within-trial timestamps and relative event times remain faithful to source data.

## Related sources
- Experimental context and neuron definitions follow the three Turner lab papers (Cerebral Cortex 2011, Frontiers 2013, Brain 2016) summarized in `assets/papers_summary_and_notes/`.
- Task design, timing, and column semantics match `documentation/trial_structure.md` and `documentation/experiment_hypothesis_variables.md`.
