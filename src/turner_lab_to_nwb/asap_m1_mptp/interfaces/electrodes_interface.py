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
        device = nwbfile.create_device(
            name="DeviceMicroelectrodeSystem",
            description="Turner Lab microelectrode recording system: Glass-coated PtIr microelectrode "
            "mounted in hydraulic microdrive (MO-95, Narishige Intl., Tokyo) within "
            "cylindrical stainless steel recording chamber (35° coronal angle). "
            "Signal amplified 10^4, bandpass filtered 0.3-10kHz. "
            "Sampling: 20kHz for unit discrimination, 1kHz for analog/behavioral signals. "
            "Chamber-relative coordinate system with sub-millimeter precision.",
        )
        
        # Recording electrode group for M1 chamber
        recording_electrode_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupM1Recording",
            description="Primary motor cortex (M1) recording electrode group within chamber-relative coordinate system. "
            "Layer 5 pyramidal neurons targeted in arm representation area. "
            "Chamber surgically positioned over left M1 using stereotactic atlas coordinates. "
            "Daily electrode positions defined relative to chamber center/reference point. "
            "Chamber grid system: A_P: -7 to +6mm (anterior-posterior), M_L: -6 to +2mm (medial-lateral), "
            "Depth: 8.4-27.6mm (insertion depth from chamber reference). "
            "Functional verification via microstimulation (≤40μA, 10 pulses at 300Hz). "
            "Glass-coated PtIr microelectrode in hydraulic microdrive for single-unit isolation.",
            location="Primary motor cortex (M1), arm area, Layer 5 - chamber coordinates",
            device=device,
        )
        
        # Stimulation electrode group for antidromic identification
        stimulation_electrode_group = nwbfile.create_electrode_group(
            name="ElectrodeGroupAntidromicStimulation",
            description="Stimulation electrodes for antidromic identification of cortical neuron projection targets. "
            "Custom-built PtIr microwire electrodes chronically implanted at projection sites to classify "
            "recorded M1 neurons as pyramidal tract neurons (PTNs) or corticostriatal neurons (CSNs). "
            "Electrodes positioned using standard electrophysiological mapping techniques. "
            "Histological reconstruction confirmed optimal placement for M1 projection targeting.",
            location="Multiple subcortical projection targets - see individual electrode locations",
            device=device,
        )

        # Add custom columns for chamber grid coordinates and recording system metadata
        nwbfile.add_electrode_column(
            name="chamber_grid_ap_mm",
            description=(
                "Chamber grid position: Anterior-Posterior coordinate relative to chamber center "
                "(mm, positive = anterior, range: -7 to +6mm)"
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_grid_ml_mm",
            description=(
                "Chamber grid position: Medial-Lateral coordinate relative to chamber center "
                "(mm, positive = lateral, range: -6 to +2mm)"
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_insertion_depth_mm",
            description=(
                "Electrode insertion depth from chamber reference point "
                "(mm, positive = deeper, range: 8.4-27.6mm)"
            ),
        )
        nwbfile.add_electrode_column(
            name="recording_site_index",
            description=(
                "Systematic cortical mapping site identifier: unique index for each chamber "
                "penetration location sampled during the experimental period"
            ),
        )
        nwbfile.add_electrode_column(
            name="recording_session_index",
            description=(
                "Depth sampling session identifier: sequential recordings performed at different "
                "electrode insertion depths within the same cortical penetration site"
            ),
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
            x=0.0,  # Use neutral coordinates for standard x,y,z
            y=0.0,
            z=0.0,
            imp=float("nan"),  # Electrode impedance not recorded
            location="Primary motor cortex (M1), arm area, Layer 5",
            filtering="0.3-10kHz bandpass for spikes, 1-100Hz for LFP when available",
            group=recording_electrode_group,
            chamber_grid_ap_mm=self.session_info["A_P"],
            chamber_grid_ml_mm=self.session_info["M_L"],
            chamber_insertion_depth_mm=self.session_info["Depth"],
            recording_site_index=recording_site_index,
            recording_session_index=recording_session_index,
        )
        
        # Add stimulation electrodes for antidromic identification
        # Cerebral peduncle electrode for PTN identification
        nwbfile.add_electrode(
            x=0.0,
            y=0.0, 
            z=0.0,
            imp=float("nan"),
            location="Cerebral peduncle, arm-responsive pre-pontine region",
            filtering="Not applicable - stimulation electrode",
            group=stimulation_electrode_group,
            chamber_grid_ap_mm=float("nan"),  # Not applicable for stimulation electrodes
            chamber_grid_ml_mm=float("nan"),
            chamber_insertion_depth_mm=float("nan"),
            recording_site_index=-1,  # Not applicable for stimulation electrodes
            recording_session_index=-1,
        )
        
        # Posterolateral striatum electrodes for CSN identification (3 electrodes)
        for i in range(3):
            nwbfile.add_electrode(
                x=0.0,
                y=0.0,
                z=0.0,
                imp=float("nan"),
                location=f"Posterolateral striatum (putamen), electrode {i+1} of 3",
                filtering="Not applicable - stimulation electrode",
                group=stimulation_electrode_group,
                chamber_grid_ap_mm=float("nan"),
                chamber_grid_ml_mm=float("nan"),
                chamber_insertion_depth_mm=float("nan"),
                recording_site_index=-1,
                recording_session_index=-1,
            )
        
        # Thalamus stimulation electrode
        nwbfile.add_electrode(
            x=0.0,
            y=0.0,
            z=0.0,
            imp=float("nan"),
            location="Thalamus, motor-responsive region",
            filtering="Not applicable - stimulation electrode",
            group=stimulation_electrode_group,
            chamber_grid_ap_mm=float("nan"),
            chamber_grid_ml_mm=float("nan"),
            chamber_insertion_depth_mm=float("nan"),
            recording_site_index=-1,
            recording_session_index=-1,
        )
        
        # Subthalamic nucleus stimulation electrode
        nwbfile.add_electrode(
            x=0.0,
            y=0.0,
            z=0.0,
            imp=float("nan"),
            location="Subthalamic nucleus (STN)",
            filtering="Not applicable - stimulation electrode",
            group=stimulation_electrode_group,
            chamber_grid_ap_mm=float("nan"),
            chamber_grid_ml_mm=float("nan"),
            chamber_insertion_depth_mm=float("nan"),
            recording_site_index=-1,
            recording_session_index=-1,
        )

        if self.verbose:
            print(f"Added electrode configuration: 1 recording electrode + 6 stimulation electrodes")
            print(f"Recording site index: {recording_site_index}, session index: {recording_session_index}")