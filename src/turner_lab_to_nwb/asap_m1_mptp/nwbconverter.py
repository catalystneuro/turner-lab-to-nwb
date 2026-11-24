"""The NWB converter of one session of the Turner lab M1 MPTP dataset."""

from neuroconv import ConverterPipe

from turner_lab_to_nwb.asap_m1_mptp.interfaces import (
    M1MPTPAntidromicStimulationInterface,
    M1MPTPElectrodesInterface,
    M1MPTPEMGInterface,
    M1MPTPLFPInterface,
    M1MPTPManipulandumInterface,
    M1MPTPSpikeTimesInterface,
    M1MPTPTrialsInterface,
)

# The source gives the antidromic sweeps no clock time, so they are placed this many seconds after the last trial
ANTIDROMIC_GAP_AFTER_TRIALS = 10.0


class M1MPTPNWBConverter(ConverterPipe):
    """
    One session: the trials, units, analog streams and antidromic sweeps of the files in its session plan.

    The trials, units and analog streams share one timeline, built from the trial durations with a fixed gap between
    trials (the source files are trialized and hold no time between trials). The antidromic sweeps are placed after
    the last trial when the converter aligns its interfaces.
    """

    def __init__(
        self,
        session_plan: dict,
        joint: str,
        muscle_names: list[str] | None = None,
        inter_trial_time_interval: float = 3.0,
        verbose: bool = False,
    ):
        """
        Parameters
        ----------
        session_plan : dict
            One session from session_plan.plan_sessions: its trials as (MATLAB file, trial index) pairs, the files
            they come from, its units and its electrode locations
        joint : {"elbow", "wrist"}
            Joint moved in the task: elbow for monkey V, wrist for monkey L
        muscle_names : list of str, optional
            The muscle of each EMG channel, as the lab's metadata table names it
        inter_trial_time_interval : float, default: 3.0
            Seconds between consecutive trials on the session timeline
        verbose : bool, default: False
        """
        trial_sources = session_plan["trial_sources"]
        data_interfaces = {
            # The electrodes interface sets up the electrodes table that the units refer to
            "electrodes": M1MPTPElectrodesInterface(
                electrode_locations=session_plan["electrode_locations"], verbose=verbose
            ),
            "spike": M1MPTPSpikeTimesInterface(
                units=session_plan["units"],
                trial_sources=trial_sources,
                inter_trial_time_interval=inter_trial_time_interval,
                verbose=verbose,
            ),
            "manipulandum": M1MPTPManipulandumInterface(
                trial_sources=trial_sources, inter_trial_time_interval=inter_trial_time_interval, verbose=verbose
            ),
            "lfp": M1MPTPLFPInterface(
                trial_sources=trial_sources, inter_trial_time_interval=inter_trial_time_interval, verbose=verbose
            ),
            "emg": M1MPTPEMGInterface(
                trial_sources=trial_sources,
                inter_trial_time_interval=inter_trial_time_interval,
                muscle_names=muscle_names,
                verbose=verbose,
            ),
            "trials": M1MPTPTrialsInterface(
                trial_sources=trial_sources,
                trial_files=session_plan["trial_files"],
                joint=joint,
                inter_trial_time_interval=inter_trial_time_interval,
                verbose=verbose,
            ),
            "antidromic": M1MPTPAntidromicStimulationInterface(units=session_plan["units"], verbose=verbose),
        }
        super().__init__(data_interfaces=data_interfaces, verbose=verbose)

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        """Place the antidromic sweeps ANTIDROMIC_GAP_AFTER_TRIALS seconds after the end of the last trial."""
        antidromic_alignment = self.temporal_alignment["antidromic"]
        if not antidromic_alignment.keys():
            return
        trial_start_times, trial_durations = self.data_interface_objects["trials"].get_trial_timeline()
        antidromic_alignment.shift_times(trial_start_times[-1] + trial_durations[-1] + ANTIDROMIC_GAP_AFTER_TRIALS)
