import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

import nibabel as nib
import numpy as np
from ndx_anatomical_localization import AnatomicalCoordinatesTable, Localization, Space
from pydantic import FilePath
from pynwb import NWBFile

from neuroconv.basedatainterface import BaseDataInterface

# D99 atlas data directory (relative to project root).
# Required files (download from https://afni.nimh.nih.gov/pub/dist/atlases/macaque/d99/D99_v2.0_dist.tgz):
#   - D99_atlas_v2.0.nii.gz  (813K, parcellation volume)
#   - D99_v2.0_labels_semicolon.txt  (20K, label names)
# Extract to: <project_root>/data/d99_atlas/D99_v2.0_dist/
_D99_ATLAS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "d99_atlas" / "D99_v2.0_dist"


@lru_cache(maxsize=1)
def _load_d99_atlas() -> tuple[np.ndarray, np.ndarray, dict]:
    """Load D99 atlas data (cached across sessions).

    Returns
    -------
    atlas_data : np.ndarray
        3D array of label IDs
    inv_affine : np.ndarray
        Inverse affine matrix (world RAS mm -> voxel indices)
    labels : dict
        Mapping from label_id to {"abbreviation": str, "full_name": str}
    """
    atlas_path = _D99_ATLAS_DIR / "D99_atlas_v2.0.nii.gz"
    labels_path = _D99_ATLAS_DIR / "D99_v2.0_labels_semicolon.txt"

    atlas = nib.load(str(atlas_path))
    atlas_data = np.asarray(atlas.dataobj)
    inv_affine = np.linalg.inv(atlas.affine)

    # Parse label file: id;abbreviation;full_name[;category;subcategory]
    labels = {}
    with open(labels_path) as f:
        for line in f:
            parts = line.strip().split(";")
            if len(parts) >= 3:
                label_id = int(parts[0])
                abbreviation = parts[1].strip()
                full_name = parts[2].strip().strip('"')
                labels[label_id] = {"abbreviation": abbreviation, "full_name": full_name}

    return atlas_data, inv_affine, labels



def lookup_d99_region(ap_acx: float, ml_acx: float, depth_acx: float) -> tuple[str, str]:
    """Look up the D99 atlas region for a given ACx coordinate.

    Parameters
    ----------
    ap_acx : float
        Anterior-posterior coordinate (+anterior, mm)
    ml_acx : float
        Medial-lateral coordinate (+lateral left, mm)
    depth_acx : float
        Depth coordinate (+superior/dorsal, mm)

    Returns
    -------
    full_name : str
        Full region name from D99 labels
    abbreviation : str
        Region abbreviation from D99 labels
    """
    atlas_data, inv_affine, labels = _load_d99_atlas()

    # Convert ACx to D99 RAS world coordinates (AC is at origin 0,0,0)
    r = -ml_acx  # left hemisphere = negative R
    a = ap_acx
    s = depth_acx

    world_coord = np.array([r, a, s])
    voxel = nib.affines.apply_affine(inv_affine, world_coord)
    voxel_idx = tuple(np.round(voxel).astype(int))

    # Check bounds
    if all(0 <= voxel_idx[i] < atlas_data.shape[i] for i in range(3)):
        label_id = int(atlas_data[voxel_idx])
        if label_id > 0 and label_id in labels:
            return labels[label_id]["full_name"], labels[label_id]["abbreviation"]

    return "outside atlas", "outside"


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
                "A_P_acx": first_unit.get("A_P_acx", float("nan")),
                "M_L_acx": first_unit.get("M_L_acx", float("nan")),
                "Depth_acx": first_unit.get("Depth_acx", float("nan")),
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
                "Chamber grid position along the anterior-posterior axis, relative to chamber center "
                "(mm, positive = posterior). Recordings span -7 to 0 mm (all anterior to chamber center). "
                "NaN for stimulation electrodes."
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_grid_ml_mm",
            description=(
                "Chamber grid position along the medial-lateral axis, relative to chamber center "
                "(mm, positive = right). Recordings span -6 to -2 mm (all in left hemisphere). "
                "NaN for stimulation electrodes."
            ),
        )
        nwbfile.add_electrode_column(
            name="chamber_insertion_depth_mm",
            description=(
                "Electrode insertion depth from chamber reference point "
                "(mm, positive = deeper, range: 8.4-27.6mm). NaN for stimulation electrodes."
            ),
        )
        # Use D99 atlas ACx coordinates for standard x/y/z when available
        # ACx convention: A_P_acx (+anterior), M_L_acx (+lateral, left hemisphere), Depth_acx (+superior/dorsal)
        # NWB convention (PIR): x (+posterior), y (+inferior), z (+right), units in microns
        ap_acx = self.session_info["A_P_acx"]
        ml_acx = self.session_info["M_L_acx"]
        depth_acx = self.session_info["Depth_acx"]
        has_acx = not (math.isnan(ap_acx) or math.isnan(ml_acx) or math.isnan(depth_acx))

        if has_acx:
            x_pir = -ap_acx * 1000.0  # +anterior -> +posterior (flip sign), mm -> um
            y_pir = -depth_acx * 1000.0  # +superior -> +inferior (flip sign), mm -> um
            z_pir = -ml_acx * 1000.0  # +lateral(left) -> +right (flip sign), mm -> um
            d99_full_name, d99_abbreviation = lookup_d99_region(ap_acx, ml_acx, depth_acx)
            electrode_location = d99_full_name
        else:
            electrode_location = "Primary motor cortex (M1), area 4, arm area"

        # Add recording electrode with chamber grid coordinates
        nwbfile.add_electrode(
            x=x_pir if has_acx else float("nan"),
            y=y_pir if has_acx else float("nan"),
            z=z_pir if has_acx else float("nan"),
            imp=float("nan"),  # Electrode impedance not recorded
            location=electrode_location,
            filtering="0.3-10kHz bandpass for spikes, 1-100Hz for LFP when available",
            group=recording_electrode_group,
            chamber_grid_ap_mm=-self.session_info["A_P"],
            chamber_grid_ml_mm=self.session_info["M_L"],
            chamber_insertion_depth_mm=self.session_info["Depth"],
        )

        # Add D99 atlas coordinates via ndx-anatomical-localization if available
        if has_acx:
            d99_space = Space(
                name="D99",
                space_name="D99",
                origin="anterior commissure",
                units="mm",
                orientation="RAS",
            )

            coordinates_table = AnatomicalCoordinatesTable(
                name="D99AtlasCoordinates",
                target=nwbfile.electrodes,
                description=(
                    "Recording electrode coordinates in D99 macaque atlas space (RAS orientation, mm). "
                    "Origin: anterior commissure. "
                    "Coordinates computed by Dr. Robert Turner from chamber-relative positions using "
                    "the known chamber placement geometry (AP offset to AC and 35-degree coronal tilt). "
                    "See: https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/nonhuman/macaque_tempatl/atlas_d99v2.html"
                ),
                method=(
                    "Coordinates transformed from chamber-relative positions to D99 atlas space "
                    "by Dr. Robert Turner (data author) using a geometric transformation: "
                    "constant AP offset (-8.2 mm, chamber center to anterior commissure) "
                    "and 35-degree rotation in the coronal plane (coupling ML and Depth to atlas R and S axes). "
                    "No individual MRI registration was used."
                ),
                space=d99_space,
            )

            coordinates_table.add_column(
                name="brain_region_id",
                description="D99 atlas region abbreviation (e.g. F1_(4), F2_(6DR/6DC), 3a/b)",
            )

            # Convert ACx convention to D99 RAS:
            # R = -M_L (left hemisphere lateral is negative R)
            # A = A_P (source A_P is +anterior, same as RAS)
            # S = Depth (both +superior/dorsal)
            # Note: chamber_grid_ap_mm = -A_P (stored as +posterior), but RAS uses source A_P directly
            x_ras = -ml_acx
            y_ras = ap_acx
            z_ras = depth_acx

            coordinates_table.add_row(
                x=x_ras,
                y=y_ras,
                z=z_ras,
                localized_entity=0,  # Index into electrode table (single recording electrode)
                brain_region=d99_full_name,
                brain_region_id=d99_abbreviation,
            )

            localization = Localization()
            localization.add_spaces([d99_space])
            # Add localization to the NWBFile before adding the coordinates table,
            # so that both the DynamicTableRegion (localized_entity) and its target
            # (nwbfile.electrodes) share a common ancestor during validation.
            nwbfile.add_lab_meta_data(localization)
            localization.add_anatomical_coordinates_tables([coordinates_table])

        if self.verbose:
            print(f"Added electrode configuration: 1 recording electrode in electrodes table")
            if has_acx:
                print(f"Added D99 atlas coordinates (RAS mm): R={x_ras:.2f}, A={y_ras:.2f}, S={z_ras:.2f}")
                print(f"D99 region: {d99_full_name} ({d99_abbreviation})")