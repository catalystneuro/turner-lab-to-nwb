from pathlib import Path
from typing import Optional

from pydantic import FilePath
from pynwb import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.utils import DeepDict


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

    def get_metadata(self) -> DeepDict:
        """Get metadata for the NWB file."""
        metadata = super().get_metadata()

        metadata["NWBFile"][
            "session_description"
        ] = f"Turner Lab MPTP electrode configuration from {self.base_file_path.stem}"
        metadata["NWBFile"]["session_id"] = self.base_file_path.stem

        return metadata

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

        # Create recording device
        recording_device = nwbfile.create_device(
            name="DeviceMicroelectrodeRecording",
            description="Glass-coated PtIr microelectrode mounted in hydraulic microdrive (MO-95, Narishige Intl., Tokyo). "
            "Signal amplified 10^4, bandpass filtered 0.3-10kHz. Sampling: 20kHz for unit discrimination.",
        )
        
        # Create stimulation device
        stimulation_device = nwbfile.create_device(
            name="DeviceStimulationElectrodes",
            description="Custom-built PtIr microwire electrodes for antidromic stimulation. "
            "Chronically implanted at projection sites for neuron classification.",
        )
        
        # Recording electrode group for M1 chamber (left hemisphere)
        recording_electrode_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupM1Recording",
            description="Left primary motor cortex recording within chamber-relative coordinate system. "
            "Chamber surgically positioned over left M1. Daily positions relative to chamber center. "
            "Functional verification via microstimulation (≤40μA, 10 pulses at 300Hz).",
            location="Primary motor cortex (M1), area 4, arm area",
            device=recording_device,
        )
        
        # Putamen stimulation electrode group (left hemisphere)
        putamen_stim_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupStimPutamen",
            description="Left posterolateral putamen stimulation electrodes for CSN antidromic identification. "
            "Three custom-built PtIr microwire electrodes. Histologically verified placement.",
            location="Putamen (posterolateral)",
            device=stimulation_device,
        )
        
        # Peduncle stimulation electrode group (left hemisphere)
        peduncle_stim_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupStimPeduncle",
            description="Left cerebral peduncle stimulation electrode for PTN antidromic identification. "
            "Single custom-built PtIr microwire electrode. Histologically verified placement.",
            location="Cerebral peduncle (pre-pontine)",
            device=stimulation_device,
        )
        
        # Thalamus stimulation electrode group (left hemisphere)
        thalamus_stim_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupStimThalamus",
            description="Left VL thalamus stimulation electrode for antidromic identification. "
            "Custom-built PtIr microwire electrode for thalamocortical projection testing.",
            location="Ventrolateral thalamus",
            device=stimulation_device,
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
        nwbfile.add_electrode_column(
            name="recording_site_index",
            description=(
                "Systematic cortical mapping site identifier: unique index for each chamber "
                "penetration location sampled during the experimental period. -1 for stimulation electrodes."
            ),
        )
        nwbfile.add_electrode_column(
            name="recording_session_index",
            description=(
                "Depth sampling session identifier: sequential recordings performed at different "
                "electrode insertion depths within the same cortical penetration site. -1 for stimulation electrodes."
            ),
        )
        
        # Add structured metadata columns
        nwbfile.add_electrode_column(
            name="is_stimulation",
            description="Boolean flag indicating whether electrode is used for stimulation (True) or recording (False).",
        )
        nwbfile.add_electrode_column(
            name="stim_notes",
            description="Additional notes for stimulation electrodes including stereotaxic details. Empty string for recording electrodes.",
        )

        # Extract recording system metadata from file naming convention
        base_name = self.base_file_path.stem.split(".")[0]  # e.g., "v5811" from "v5811.1.mat"
        
        # Parse file naming convention: v[Site][Session] where:
        # Characters 2-3: incremental count of recording chamber penetration sites
        # Characters 4-5: count of recording sessions at different penetration depths
        if len(base_name) >= 5 and base_name.startswith("v"):
            recording_site_index = int(base_name[1:3])  # Characters 2-3 (site index)
            recording_session_index = int(base_name[3:5])  # Characters 4-5 (session index)
        else:
            # Fallback for unexpected naming patterns
            recording_site_index = -1
            recording_session_index = -1

        # Add recording electrode with chamber grid coordinates and recording system metadata
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
            recording_site_index=recording_site_index,
            recording_session_index=recording_session_index,
            is_stimulation=False,
            stim_notes="",
        )
        
        # Add cerebral peduncle stimulation electrode for PTN identification
        nwbfile.add_electrode(
            x=float("nan"),
            y=float("nan"), 
            z=float("nan"),
            imp=float("nan"),
            location="Cerebral peduncle (pre-pontine)",
            filtering="Not applicable - stimulation electrode",
            group=peduncle_stim_group,
            chamber_grid_ap_mm=float("nan"),  # Not applicable for stimulation electrodes
            chamber_grid_ml_mm=float("nan"),
            chamber_insertion_depth_mm=float("nan"),
            recording_site_index=-1,  # Not applicable for stimulation electrodes
            recording_session_index=-1,
            is_stimulation=True,
            stim_notes="Ventral to substantia nigra, arm-responsive pre-pontine region",
        )
        
        # Add posterolateral putamen electrodes for CSN identification (3 electrodes)
        for i in range(3):
            nwbfile.add_electrode(
                x=float("nan"),
                y=float("nan"),
                z=float("nan"),
                imp=float("nan"),
                location="Putamen (posterolateral)",
                filtering="Not applicable - stimulation electrode",
                group=putamen_stim_group,
                chamber_grid_ap_mm=float("nan"),
                chamber_grid_ml_mm=float("nan"),
                chamber_insertion_depth_mm=float("nan"),
                recording_site_index=-1,
                recording_session_index=-1,
                is_stimulation=True,
                stim_notes=f"Electrode {i+1} of 3, posterolateral putamen for M1 CSN projections",
            )
        
        # Add VL thalamus electrode for antidromic identification
        nwbfile.add_electrode(
            x=float("nan"),
            y=float("nan"),
            z=float("nan"),
            imp=float("nan"),
            location="Ventrolateral thalamus",
            filtering="Not applicable - stimulation electrode",
            group=thalamus_stim_group,
            chamber_grid_ap_mm=float("nan"),
            chamber_grid_ml_mm=float("nan"),
            chamber_insertion_depth_mm=float("nan"),
            recording_site_index=-1,
            recording_session_index=-1,
            is_stimulation=True,
            stim_notes="VL thalamus for thalamocortical projection identification",
        )

        if self.verbose:
            print(f"Added electrode configuration: 1 recording electrode + 5 stimulation electrodes")
            print(f"Recording site index: {recording_site_index}, session index: {recording_session_index}")