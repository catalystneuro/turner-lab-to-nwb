"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from turner_lab_to_nwb.asap_embargo.asap_embargo_intan_recordinginterface import ASAPEmbargoIntanRecordingInterface


class AsapEmbargoNWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPEmbargoIntanRecordingInterface,
    )
