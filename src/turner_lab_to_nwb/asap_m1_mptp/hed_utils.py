"""
HED (Hierarchical Event Descriptors) annotation utilities for Turner Lab ASAP M1 MPTP dataset.

This module provides HED annotations following the HED schema version 8.4.0 for
standardized, machine-actionable event descriptions in NWB files.

References:
- HED Specification: https://www.hedtags.org/hed-specification/
- HED in NWB: https://www.hedtags.org/hed-resources/HedAnnotationInNWB.html
- HED Schema 8.4.0: https://www.hedtags.org/display_hed.html
"""

# HED Schema Version
HED_VERSION = "8.4.0"

# HED Definitions for reusable event patterns
# Note: Definitions disabled for now - using inline tags only until validation issues resolved
# The HED validator is being very strict about definition syntax
HED_DEFINITIONS = {}


def get_center_hold_hed() -> str:
    """
    Get HED annotation for center hold phase.

    Returns
    -------
    str
        HED string for center target appearance and hold initiation
    """
    return "(Sensory-event, Visual-presentation, Computer-screen), (Agent-action, Stay-still)"


def get_movement_cue_hed(movement_type: str) -> str:
    """
    Get HED annotation for movement cue (lateral target appearance).

    Parameters
    ----------
    movement_type : str
        Movement type: "flexion" or "extension"

    Returns
    -------
    str
        HED string for lateral target appearance with movement type
    """
    return f"(Sensory-event, Visual-presentation, Computer-screen), (Condition-variable/MovementType, {movement_type.capitalize()})"


def get_movement_execution_hed(movement_type: str) -> str:
    """
    Get HED annotation for movement execution.

    Parameters
    ----------
    movement_type : str
        Movement type: "flexion" or "extension"

    Returns
    -------
    str
        HED string for movement execution
    """
    if movement_type.lower() == "flexion":
        return "(Agent-action, Move-upper-extremity, Bend)"
    else:  # extension
        return "(Agent-action, Move-upper-extremity, Stretch)"


def get_perturbation_hed(perturbation_type: str) -> str:
    """
    Get HED annotation for torque perturbation.

    Parameters
    ----------
    perturbation_type : str
        Perturbation type: "flexion", "extension", or "none"

    Returns
    -------
    str
        HED string for perturbation
    """
    if perturbation_type.lower() == "none":
        return "(Condition-variable/PerturbationType, None)"
    else:
        return f"(Sensory-event, Sense-by-touch), (Condition-variable/PerturbationType, {perturbation_type.capitalize()})"


def get_trial_context_hed(mptp_condition: str, neuron_types: list = None) -> str:
    """
    Get HED annotation for trial context (MPTP state and neuron types).

    Parameters
    ----------
    mptp_condition : str
        MPTP treatment state: "Pre" or "Post"
    neuron_types : list, optional
        List of neuron types recorded in this session: "PTN", "CSN", "UNSURE"

    Returns
    -------
    str
        HED string for trial context
    """
    # Map MPTP condition
    if mptp_condition == "Pre":
        mptp_hed = "(Condition-variable/TreatmentState, Control)"
    elif mptp_condition == "Post":
        mptp_hed = "(Condition-variable/TreatmentState, MPTP-treated)"
    else:
        mptp_hed = f"(Condition-variable/TreatmentState, {mptp_condition})"

    # Map neuron types
    if neuron_types:
        neuron_tags = []
        unique_types = set(neuron_types)
        for ntype in unique_types:
            if ntype == "PTN":
                neuron_tags.append("(Condition-variable/NeuronType, Pyramidal-tract-neuron)")
            elif ntype == "CSN":
                neuron_tags.append("(Condition-variable/NeuronType, Corticostriatal-neuron)")
            elif ntype == "UNSURE":
                neuron_tags.append("(Condition-variable/NeuronType, Unidentified)")

        if len(neuron_tags) > 1:
            neuron_hed = f"({', '.join(neuron_tags)})"
        elif len(neuron_tags) == 1:
            neuron_hed = neuron_tags[0]
        else:
            neuron_hed = ""

        if neuron_hed:
            return f"{mptp_hed}, (Measurement-event, {neuron_hed})"

    return mptp_hed


def get_reward_hed() -> str:
    """
    Get HED annotation for reward delivery.

    Returns
    -------
    str
        HED string for reward
    """
    return "Experiment-control"


# HED column descriptions for NWB trials table
HED_COLUMN_DESCRIPTIONS = {
    "center_hold_HED": "HED annotation for center hold phase: visual cue presentation and hold initiation",
    "movement_cue_HED": "HED annotation for movement cue: lateral target appearance specifying movement direction (flexion/extension)",
    "movement_execution_HED": "HED annotation for movement execution: voluntary upper extremity movement (flexion or extension)",
    "perturbation_HED": "HED annotation for torque perturbation: proprioceptive stimulus (0.1 Nm, 50ms) if present",
    "trial_context_HED": "HED annotation for trial context: MPTP treatment state (Control/MPTP-treated) and neuron types recorded",
    "reward_HED": "HED annotation for reward delivery: juice or food reward for successful trial completion",
}
