# Notes concerning the asap_tdt conversion

## Experiment notes

Based on the [manuscript](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3000829) provided by the lab, the experiment was performed as follows:

Extracellular spiking activity of neurons in globus pallidus-internus (GPi) and ventrolateral anterior nucleus (VLa) was recorded using multiple glass-insulated tungsten microelectrodes (0.5–1.5 MΩ, Alpha Omega)
or 16-contact linear probes (0.5–1.0 MΩ, V-probe, Plexon) in monkeys while performing a choice reaction time reaching task.
During a subset of data collection sessions, EMG activity was collected via either chronically implanted subcutaneous electrodes or electrodes inserted percutaneously immediately before the session.
All recordings were performed with at least one electrode positioned in each of GPi and VLa.
Some sessions also included stimulation of GPi using custom built stimulating electrodes implanted in the arm-related region of primary motor cortex and in the SCP at its decussation.
The stored neuronal data were high-pass filtered (Fpass: 300 Hz, Matlab FIRPM) and thresholded, and candidate action potentials were sorted into clusters in principal components space (Off-line Sorter, Plexon).

## DataList spreadsheet

The DataList spreadsheet contains information about the electrodes (e.g. the electrode number, the brain region, the depth, etc.)
and the sessions (the date, the task, whether stimulation was applied etc.).

## TDT session folder structure

Each TDT folder contains two sessions (e.g. `I_160615_1` and `I_160615_2`).
The continuous data for each session is stored in Tucker Davis format (with files of `.Tbk`, `.Tdx`, `.tev`, `.tnt`, `.tsq`). The raw data and the high-pass filtered data
is stored in `.ddt` and `.flt.mat` files. The `.plx` files contain the spike sorting data from Plexon Offline Sorter v3.

Example folder structure:

    I_160615/
    ├── Gaia_I_160615_1.Tbk
    ├── ...
    ├── Gaia_I_160615_2.Tbk
    ├── ...
    ├── I_160615_1.mat
    ├── I_160615_1_Chans_1_1.ddt
    ├── I_160615_1_Chans_1_1.flt.mat
    ├── I_160615_1_Chans_1_1.mat
    ├── I_160615_1_Chans_1_1.plx
    ├── I_160615_1_Chans_17_32.ddt
    ├── I_160615_1_Chans_17_32.flt.mat
    ├── I_160615_1_Chans_17_32.mat
    ├── I_160615_1_Chans_17_32.plx
    ├── ...
    └── I_160615_2.mat

## Events data

The events data is stored in `.mat` files (in a structure called `events`).

| Event Name   | Description   |
|--------------|---------------|
| trialnum     | The identifier of the trial |
| starttime    | The start time of the trial (sec) |
| endtime      | The end time of the trial (sec) |
| erroron      | The time of the error onset |
| target       | The identifier of the target (1:left or 3:right in this task) |
| rewardon     | The time of the reward onset |
| rewardoff    | The time of the reward off |
| mvt_onset    | The time of the hand sensor at the home-position off (= onset of the movement) |
| mvt_end      | The time of the hand sensor at the reach target on (= end of the movement) |
| return_onset | The time of the hand sensor at the reach target off (= onset of the return movement) |
| return_end   | The time of the hand sensor at the home-position on (= end of the return movement) |
| cue_onset    | The time of the target and go-cue instruction (reach target and go-cue were instructed simultaneously in this task) |

## Stimulation data

Some sessions may also include stimulation data which is stored in `.mat` files (in a structure called `dbs`).
This data contains the onset times of stimulation. The site of stimulation and depth is stored in the `DataList` spreadsheet ("Stim. depth", "Stim. site").

## TDT to NWB mapping

TODO: add UML diagram
