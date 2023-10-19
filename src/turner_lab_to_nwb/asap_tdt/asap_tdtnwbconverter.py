from neuroconv import NWBConverter

from turner_lab_to_nwb.asap_tdt.interfaces import ASAPTdtRecordingInterface


class AsapTdtNWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Recording=ASAPTdtRecordingInterface,
    )
