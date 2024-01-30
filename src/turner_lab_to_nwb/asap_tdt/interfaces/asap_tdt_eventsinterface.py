from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from neuroconv import BaseDataInterface
from neuroconv.utils import FilePathType, DeepDict
from pymatreader import read_mat
from pynwb import NWBFile


class ASAPTdtEventsInterface(BaseDataInterface):
    """Events interface for asap_tdt conversion"""

    keywords = ["behavior"]

    def __init__(self, file_path: FilePathType, verbose: bool = False):
        """
        Parameters
        ----------
        file_path : FilePathType
            The path that points to the .mat file containing the events, units data and optionally include the stimulation data.
        """
        file_path = Path(file_path)
        assert file_path.exists(), f"File {file_path} does not exist."
        self.file_path = file_path
        self.verbose = verbose
        self._events_data = read_mat(filename=str(self.file_path))

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        # Convert “TankSummary.CollectDate” as the days from Jan/1/1900 to datetime timestamp
        start_date = datetime(1900, 1, 1)
        assert (
            "Tanksummary" in self._events_data
        ), "The 'Tanksummary' structure is not in the file. The start time of the session cannot be determined."
        assert (
            "CollectDate" in self._events_data["Tanksummary"]
        ), "The 'CollectDate' field is not in the 'Tanksummary' structure. The start time of the session cannot be determined."
        days_from_start_date = self._events_data["Tanksummary"]["CollectDate"]
        days_timedelta = timedelta(days=days_from_start_date)
        session_start_time = start_date + days_timedelta
        metadata["NWBFile"].update(session_start_time=session_start_time)

        metadata["StimulationEvents"] = dict(
            name="StimulationEvents",
            description="The container for stimulation events.",
        )

        return metadata

    def add_trials(self, nwbfile: NWBFile, target_name_mapping: Optional[dict] = None):
        """
        Add trials to the nwbfile

        Parameters
        ----------
        nwbfile : NWBFile
            The nwbfile to add the trials to.
        target_name_mapping : Optional[dict], optional
            A dictionary mapping the target identifiers to more descriptive names, e.g. 1: "Left", 3: "Right".
        """

        event_structure_name = "events"

        if event_structure_name not in self._events_data:
            return

        events = self._events_data[event_structure_name]

        for trial_start_time, trial_stop_time in zip(events["starttime"], events["endtime"]):
            nwbfile.add_trial(
                start_time=trial_start_time,
                stop_time=trial_stop_time,
            )

        # Use more descriptive names for the event types
        event_names_mapping = dict(
            erroron="error_onset_time",
            rewardon="reward_start_time",
            rewardoff="reward_stop_time",
            mvt_onset="movement_start_time",
            mvt_end="movement_stop_time",
            return_onset="return_start_time",
            return_end="return_stop_time",
            cue_onset="cue_onset_time",
        )
        events_description_mapping = dict(
            erroron="The times of the error onset.",
            rewardon="The times of the reward onset.",
            rewardoff="The times of the reward offset.",
            mvt_onset="The times of the hand sensor at the home-position off (= onset of the movement).",
            mvt_end="The times of the hand sensor at the reach target on (= end of the movement).",
            return_onset="The times of the hand sensor at the reach target off (= onset of the return movement)",
            return_end="The times of the hand sensor at the home-position on (= end of the return movement)",
            cue_onset="The times of the target and go-cue instruction (reach target and go-cue were instructed simulatneously in this task).",
        )

        for event_name, mapped_event_name in event_names_mapping.items():
            # if event is missing or event type contains only NaNs, skip it
            if event_name not in events or np.isnan(events[event_name]).all():
                continue
            nwbfile.add_trial_column(
                name=mapped_event_name,
                description=events_description_mapping[event_name],
                data=events[event_name],
            )

        target_data = events["target"].astype(int)
        if target_name_mapping is not None:
            target_data = [target_name_mapping[t] for t in target_data]
        nwbfile.add_trial_column(
            name="target",
            description="Defines whether the target was on the left or right side.",
            data=target_data,
        )

    def add_stimulation_events(self, nwbfile: NWBFile, metadata: dict):
        """
        Add stimulation events to the nwbfile

        Parameters
        ----------
        nwbfile : NWBFile
            The nwbfile to add the stimulation events to.
        """
        from ndx_events import AnnotatedEventsTable

        stimulation_metadata = metadata["StimulationEvents"]
        assert (
            stimulation_metadata["name"] not in nwbfile.acquisition
        ), f"The {stimulation_metadata['name']} is already in nwbfile. "
        events = AnnotatedEventsTable(
            name=stimulation_metadata["name"],
            description=stimulation_metadata["description"],
        )
        event_type_kwargs = dict(
            label="stimulation_onset",
            event_description="The stimulation onset times.",
            event_times=self._events_data["dbs"],
        )
        if "stimulation_depth" in stimulation_metadata:
            events.add_column(
                name="stimulation_depth",
                description="The depth of stimulation in micrometers.",
                index=True,
            )
            event_type_kwargs.update(stimulation_depth=[stimulation_metadata["stimulation_depth"]])
        if "stimulation_site" in stimulation_metadata:
            events.add_column(
                name="stimulation_site",
                description="The site of stimulation.",
                index=True,
            )
            event_type_kwargs.update(stimulation_site=[stimulation_metadata["stimulation_site"]])

        # add an event type (row) to the AnnotatedEventsTable instance
        events.add_event_type(**event_type_kwargs)

        nwbfile.add_acquisition(events)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, target_name_mapping: Optional[dict] = None):
        self.add_trials(nwbfile=nwbfile, target_name_mapping=target_name_mapping)

        # 'dbs' is the structure containing the stimulation onset times
        stimulation_structure_name = "dbs"
        if stimulation_structure_name in self._events_data:
            self.add_stimulation_events(nwbfile=nwbfile, metadata=metadata)
