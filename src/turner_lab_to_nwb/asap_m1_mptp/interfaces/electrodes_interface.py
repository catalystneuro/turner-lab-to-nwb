from pathlib import Path
from typing import Optional

from pydantic import FilePath
from pynwb import NWBFile

from neuroconv.basedatainterface import BaseDataInterface


class M1MPTPElectrodesInterface(BaseDataInterface):
    """Data interface for Turner Lab M1 MPTP electrode setup (recording and stimulation electrodes)."""

    keywords = ("electrodes", "recording electrodes", "stimulation electrodes", "antidromic identification")
    associated_suffixes = (".mat",)
    info = "Interface for Turner Lab M1 MPTP electrode configuration including recording and stimulation electrodes"

    def __init__(
        self,
        file_path: FilePath,
        session_metadata: dict,
        verbose: bool = False,
    ):
        """
        Initialize the M1MPTPElectrodesInterface.

        Parameters
        ----------
        file_path : FilePath
            Path to the first Turner Lab .mat file (used for session metadata extraction)
        session_metadata : dict
            Metadata for all units in this session (each unit contains session-level info)
        verbose : bool, optional
            Whether to print verbose output, by default False
        """
        super().__init__(verbose=verbose)
        self.base_file_path = Path(file_path)
        self.session_metadata = session_metadata
        
        # Extract session-level info from first unit (all units have same session info)
        if self.session_metadata:
            first_unit = self.session_metadata[0]
            self.session_info = {
                "Animal": first_unit["Animal"],
                "MPTP": first_unit["MPTP"],
                "DateCollected": first_unit["DateCollected"],
                "A_P": first_unit["A_P"],
                "M_L": first_unit["M_L"],
                "Depth": first_unit["Depth"],
            }

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: Optional[dict] = None) -> None:
        """
        Add electrode configuration to the NWB file.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add electrode configuration to
        metadata : dict, optional
            Metadata dictionary
        """
        if metadata is None:
            metadata = self.get_metadata()

        # Create device for M1 recording electrode
        recording_device = nwbfile.create_device(
            name="DeviceMicroelectrodeRecording",
            description="Glass-coated PtIr microelectrode mounted in hydraulic microdrive (MO-95, Narishige Intl., Tokyo). "
            "Signal amplified 10^4, bandpass filtered 0.3-10kHz. Sampling: 20kHz for unit discrimination.",
        )

        # Create devices for chronically implanted stimulation electrodes
        # These are documented as devices even though they're not in the electrodes table
        # (stimulation electrode metadata is in StimulationElectrodesTable in the antidromic_identification module)
        nwbfile.create_device(
            name="DeviceMicrowirePeduncleStimulation",
            description="Custom-built PtIr microwire electrode for antidromic stimulation in cerebral peduncle. "
            "Chronically implanted for PTN identification.",
        )
        nwbfile.create_device(
            name="DeviceMicrowirePutamenStimulation1",
            description="Custom-built PtIr microwire electrode 1 of 3 for antidromic stimulation in posterolateral putamen. "
            "Chronically implanted for CSN identification.",
        )
        nwbfile.create_device(
            name="DeviceMicrowirePutamenStimulation2",
            description="Custom-built PtIr microwire electrode 2 of 3 for antidromic stimulation in posterolateral putamen. "
            "Chronically implanted for CSN identification.",
        )
        nwbfile.create_device(
            name="DeviceMicrowirePutamenStimulation3",
            description="Custom-built PtIr microwire electrode 3 of 3 for antidromic stimulation in posterolateral putamen. "
            "Chronically implanted for CSN identification.",
        )
        nwbfile.create_device(
            name="DeviceMicrowireThalamicStimulation",
            description="Custom-built PtIr microwire electrode for antidromic stimulation in VL thalamus. "
            "Chronically implanted for thalamocortical projection identification.",
        )

        # Recording electrode group for M1 chamber (left hemisphere)
        recording_electrode_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupMicroelectrodeRecording",
            description="Left primary motor cortex recording within chamber-relative coordinate system. "
            "Chamber surgically positioned over left M1. Daily positions relative to chamber center. "
            "Functional verification via microstimulation (≤40μA, 10 pulses at 300Hz).",
            location="Primary motor cortex (M1), area 4, arm area",
            device=recording_device,
        )

        # Add custom columns for chamber grid coordinates and recording system metadata
        nwbfile.add_electrode_column(
            name="chamber_grid_ap_mm",
            description=(
                "Chamber grid position: Anterior-Posterior coordinate relative to chamber center "
                "(mm, positive = anterior, range: -7 to +6mm). NaN for stimulation electrodes."
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_grid_ml_mm",
            description=(
                "Chamber grid position: Medial-Lateral coordinate relative to chamber center "
                "(mm, positive = lateral, range: -6 to +2mm). NaN for stimulation electrodes."
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_insertion_depth_mm",
            description=(
                "Electrode insertion depth from chamber reference point "
                "(mm, positive = deeper, range: 8.4-27.6mm). NaN for stimulation electrodes."
            ),
        )
        # Add recording electrode with chamber grid coordinates
        nwbfile.add_electrode(
            x=float("nan"),  # Unknown global coordinates
            y=float("nan"),
            z=float("nan"),
            imp=float("nan"),  # Electrode impedance not recorded
            location="Primary motor cortex (M1), area 4, arm area",
            filtering="0.3-10kHz bandpass for spikes, 1-100Hz for LFP when available",
            group=recording_electrode_group,
            chamber_grid_ap_mm=self.session_info["A_P"],
            chamber_grid_ml_mm=self.session_info["M_L"],
            chamber_insertion_depth_mm=self.session_info["Depth"],
        )

        if self.verbose:
            print(f"Added electrode configuration: 1 recording electrode in electrodes table")