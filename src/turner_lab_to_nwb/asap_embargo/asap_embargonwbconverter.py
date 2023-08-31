"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    SpikeGLXRecordingInterface,
    SpikeGLXLFPInterface,
    PhySortingInterface,
)

from turner_lab_to_nwb.asap_embargo import AsapEmbargoBehaviorInterface


class AsapEmbargoNWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=SpikeGLXRecordingInterface,
        LFP=SpikeGLXLFPInterface,
        Sorting=PhySortingInterface,
        Behavior=AsapEmbargoBehaviorInterface,
    )
