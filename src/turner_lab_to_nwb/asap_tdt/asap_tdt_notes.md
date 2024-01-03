# Notes concerning the asap_tdt conversion

## TDT session folder structure

Each TDT folder contains two sessions (e.g. `I_160615` and `I_160615_2`).
The continuous data for each session is stored in Tucker Davis format (`.Tbk`). The unfiltered data is stored
in `.ddt` files and the filtered data is stored in `.flt.mat` files. The `.plx` files contain the spike sorting data from Plexon Offline Sorter v3.

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

## TDT to NWB mapping

TODO: add UML diagram
