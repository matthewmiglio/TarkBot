"""
This module contains the main program for TarkBot, a bot for playing the game Escape from Tarkov.
It includes functionality for the flea market sell mode, hideout mode, and snipebot mode.
"""

import webbrowser
from queue import Queue

import PySimpleGUI as sg
from pytarkbot.flea_bot.state import flea_sell_mode_state_tree
from pytarkbot.hideout_bot.states import hideout_mode_state_tree
from pytarkbot.interface.layout import (
    CONTROLS_KEYS,
    DONATE_BUTTON_KEY,
    FLEA_SELL_CONTROL_KEYS,
    FLEA_SELL_REMOVE_OFFERS_TIMER_KEY,
    SELECT_FROM_SCAV_CASE_TOGGLE_KEY,
    FLEA_SELL_ROWS_INPUT_KEY,
    FLEA_SELL_START_KEY,
    FLEA_SELL_STOP_KEY,
    HIDEOUT_BITCOIN_TOGGLE_KEY,
    HIDEOUT_LAVATORY_TOGGLE_KEY,
    HIDEOUT_MED_STATION_TOGGLE_KEY,
    HIDEOUT_SCAV_CASE_TOGGLE_KEY,
    HIDEOUT_START_KEY,
    HIDEOUT_STOP_KEY,
    HIDEOUT_WATER_TOGGLE_KEY,
    HIDEOUT_WORKBENCH_TOGGLE_KEY,
    RUBLE_FARM_KEY,
    SCAV_CASE_TYPE_KEY,
    SNIPEBOT_ITEM_NAME_1_KEY,
    SNIPEBOT_ITEM_NAME_2_KEY,
    SNIPEBOT_ITEM_NAME_3_KEY,
    SNIPEBOT_ITEM_NAME_4_KEY,
    SNIPEBOT_ITEM_PRICE_1_KEY,
    SNIPEBOT_ITEM_PRICE_2_KEY,
    SNIPEBOT_ITEM_PRICE_3_KEY,
    SNIPEBOT_ITEM_PRICE_4_KEY,
    SNIPEBOT_START_KEY,
    SNIPEBOT_STOP_KEY,
    SPECIFIC_ITEM_KEY,
    START_KEYS,
    STOP_KEYS,
)
from pytarkbot.snipe_bot.state import snipebot_state_tree
from pytarkbot.utils.caching import (
    cache_user_settings,
    check_user_settings,
    read_user_settings,
)
from pytarkbot.utils.logger import Logger
from pytarkbot.utils.thread import StoppableThread, ThreadKilled

from pytarkbot.interface.layout import make_tarkbot_window

import pytarkbot.utils.medal


def save_current_settings(values) -> None:
    """
    Save the current user settings to cache.

    Args:
        values (dict): A dictionary containing the current user settings.

    Returns:
        None
    """
    # read the currently selected values for each key in user_config_keys
    user_settings = {key: values[key] for key in CONTROLS_KEYS if key in values}
    cache_user_settings(user_settings)
    print("Cached user settings")


def load_last_settings(window) -> None:
    """
    Load the last saved user settings and update the PySimpleGUI window accordingly.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object to update.

    Returns:
        None
    """
    if check_user_settings():
        window.read(timeout=10)  # read the window to edit the layout
        user_settings = read_user_settings()
        if user_settings is not None:
            for key in CONTROLS_KEYS:
                if key in user_settings:
                    window[key].update(user_settings[key])
        window.refresh()  # refresh the window to update the layout


class FleaSellWorkerThread(StoppableThread):
    """
    This class represents a worker thread for the flea market sell mode.
    It initializes the state and loops through the state tree
    until the shutdown flag is set. If an exception is caught, it logs the error.
    """

    def __init__(self, logger: Logger, args, kwargs=None):
        """
        Initializes a worker thread for the flea market sell mode.

        Args:
            logger (Logger): The logger object to use for logging.
            args (dict): A dictionary containing the arguments to pass to the worker thread.
            kwargs (dict, optional): A dictionary containing the keyword arguments to pass
            to the worker thread. Defaults to None.
        """
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        """
        Runs the worker thread for the flea market sell mode.
        """
        try:
            state = "restart"
            number_of_rows = self.args["rows"]
            select_from_scav_case_toggle = self.args["select_from_scav_case_toggle"]
            remove_offers_timer = self.args["remove_offers_timer"]

            while not self.shutdown_flag.is_set():
                state = flea_sell_mode_state_tree(
                    self.logger,
                    state,
                    number_of_rows,
                    remove_offers_timer,
                    select_from_scav_case_toggle,
                )

        except ThreadKilled:
            return

        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


class HideoutModeWorkerThread(StoppableThread):
    """
    This class represents a worker thread for the hideout mode.
    It initializes the state and loops through the state tree
    until the shutdown flag is set. If an exception is caught, it logs the error.
    """

    def __init__(self, logger: Logger, args, kwargs=None):
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        try:
            state = "start"
            # loop until shutdown flag is set
            while not self.shutdown_flag.is_set():
                state = hideout_mode_state_tree(state, self.logger, jobs=self.args)

        except ThreadKilled:
            return

        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


class SnipeModeWorkerThread(StoppableThread):
    """
    This class represents a worker thread for the snipe mode.
    It initializes the state, number of rows, and remove offers timer.
    It then loops through the state tree until the shutdown flag is set.
    If an exception is caught, it logs the error.
    """

    def __init__(self, logger: Logger, args, kwargs=None):
        """
        Initializes the SnipeModeWorkerThread class.

        Args:
        - logger (Logger): The logger object.
        - args (dict): The arguments to pass to the thread.
        - kwargs (dict): The keyword arguments to pass to the thread.
        """
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        """
        This method runs the snipe mode worker thread. It initializes the
        state, number of rows, and remove offers timer.
        It then loops through the state tree until the shutdown flag is set.
        If an exception is caught, it logs the error.
        """
        try:
            job_list = self.args["job_list"]
            snipe_data = self.args["snipe_data"]

            state = "restart"

            while not self.shutdown_flag.is_set():
                state = snipebot_state_tree(state, self.logger, job_list, snipe_data)
        except ThreadKilled:
            return

        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


def hideout_mode_start_button_event(
    logger: Logger, window, values
) -> HideoutModeWorkerThread:
    """
    This function is called when the "Start" button is clicked in hideout mode.
    It disables the start button keys and config keys for this mode, creates args for the thread,
    starts the thread, and enables the stop button.

    Args:
        logger (Logger): The logger object.
        window (sg.Window): The PySimpleGUI window object.
        values (dict): The dictionary of values from the PySimpleGUI window.

    Returns:
        HideoutModeWorkerThread: The thread object.
    """
    # check for invalid inputs
    logger.change_status("Starting hideout mode")

    # disable this mode's keys
    keys = [HIDEOUT_START_KEY, SNIPEBOT_START_KEY, FLEA_SELL_START_KEY] + CONTROLS_KEYS
    for key in keys:
        window[key].update(disabled=True)

    jobs = []

    # job checkboxes
    if values[HIDEOUT_BITCOIN_TOGGLE_KEY] is True:
        jobs.append("Bitcoin")
    if values[HIDEOUT_WORKBENCH_TOGGLE_KEY] is True:
        jobs.append("Workbench")
    if values[HIDEOUT_WATER_TOGGLE_KEY] is True:
        jobs.append("water")
    if values[HIDEOUT_SCAV_CASE_TOGGLE_KEY] is True:
        jobs.append("scav_case")
    if values[HIDEOUT_MED_STATION_TOGGLE_KEY] is True:
        jobs.append("medstation")
    if values[HIDEOUT_LAVATORY_TOGGLE_KEY] is True:
        jobs.append("Lavatory")

    # scav case type input
    for craft_type in [
        "15000",
        "95000",
        "Moonshine",
        "Intel",
    ]:
        if values[SCAV_CASE_TYPE_KEY] == craft_type:
            jobs.append(craft_type)

    print("\nJobs:")
    for job in jobs:
        print(job)
    print("\n")

    save_current_settings(values)

    # start thread
    thread = HideoutModeWorkerThread(logger, jobs)
    thread.start()

    # enable stop button
    window[HIDEOUT_STOP_KEY].update(disabled=False)

    # return the thread
    return thread


def flea_sell_mode_start_button_event(
    logger: Logger, window, values
) -> FleaSellWorkerThread:
    """
    Event handler for the flea sell mode start button.

    Args:
        logger (Logger): The logger instance.
        window (sg.Window): The PySimpleGUI window instance.
        values (dict): The dictionary of values from the PySimpleGUI window.

    Returns:
        FleaSellWorkerThread: The thread instance that was started.
    """
    # check for invalid inputs
    logger.change_status("Starting flea sell mode mode")

    # disable all the start button keys
    for key in START_KEYS:
        window[key].update(disabled=True)

    # disable the config keys for this mode
    for key in FLEA_SELL_CONTROL_KEYS:
        window[key].update(disabled=True)

    # create args for thread
    args = {
        "rows": values[FLEA_SELL_ROWS_INPUT_KEY],
        "remove_offers_timer": values[FLEA_SELL_REMOVE_OFFERS_TIMER_KEY],
        "select_from_scav_case_toggle": values[SELECT_FROM_SCAV_CASE_TOGGLE_KEY],
    }

    save_current_settings(values)

    # start thread
    thread = FleaSellWorkerThread(logger, args)
    thread.start()

    # enable stop button
    window[FLEA_SELL_STOP_KEY].update(disabled=False)

    # return the thread
    return thread


def snipe_mode_start_button_event(
    logger: Logger, window, values
) -> SnipeModeWorkerThread:
    """
    This function is called when the user clicks the "Start" button for the snipe mode.
    It checks for invalid inputs, creates a job list based on user's selection, creates
    snipe_data based on user input, creates args for the thread, starts the thread,
    enables the stop button, and returns the thread.

    Args:
        logger (Logger): The logger object.
        window (sg.Window): The PySimpleGUI window object.
        values (dict): The dictionary of values from the PySimpleGUI window.

    Returns:
        SnipeModeWorkerThread: The thread object.
    """
    # check for invalid inputs
    logger.change_status("Starting snipe mode")

    # disable this mode's keys
    # for key in hideout_disable_keys:
    #     window[key].update(disabled=True)

    # Define the keys for PySimpleGUI inputs
    name_keys = [
        SNIPEBOT_ITEM_NAME_1_KEY,
        SNIPEBOT_ITEM_NAME_2_KEY,
        SNIPEBOT_ITEM_NAME_3_KEY,
        SNIPEBOT_ITEM_NAME_4_KEY,
    ]

    price_keys = [
        SNIPEBOT_ITEM_PRICE_1_KEY,
        SNIPEBOT_ITEM_PRICE_2_KEY,
        SNIPEBOT_ITEM_PRICE_3_KEY,
        SNIPEBOT_ITEM_PRICE_4_KEY,
    ]

    save_current_settings(values)

    # Create job_list based on user's selection
    job_list = ["ruble_sniping"] if values[RUBLE_FARM_KEY] else []
    if values[SPECIFIC_ITEM_KEY]:
        job_list.append("item_sniping")

    # Create snipe_data based on user input
    snipe_data = []

    for name_key, price_key in zip(name_keys, price_keys):
        item_name = values[name_key]
        item_price = values[price_key]
        item_price = item_price.replace(",", "")

        if not item_name:
            continue
        if not item_price:
            continue
        if not check_if_int(item_price):
            continue

        snipe_data.append((item_name, item_price))

    # Create args for the thread
    args = {
        "job_list": job_list,
        "snipe_data": snipe_data,
    }

    # Start the thread
    thread = SnipeModeWorkerThread(logger, args)
    thread.start()

    # enable stop button
    window[SNIPEBOT_STOP_KEY].update(disabled=False)

    # return the thread
    return thread


def check_if_int(var: str) -> bool:
    """
    Check if a given variable can be converted to an integer.

    Args:
        var (str): The variable to check.

    Returns:
        bool: True if the variable can be converted to an integer, False otherwise.
    """
    try:
        int(var)
        return True
    except ValueError:
        return False


def shutdown_thread(thread: StoppableThread | None, kill=True) -> None:
    """
    Sends a shutdown flag to a given thread and kills it if specified.

    Args:
        thread (StoppableThread | None): The thread to shutdown.
        kill (bool): Whether to kill the thread or not. Defaults to True.

    Returns:
        None
    """
    if thread is not None:
        thread.shutdown_flag.set()
        if kill:
            thread.kill()


def update_layout(window: sg.Window, logger: Logger) -> None:
    """
    Updates the statistics in the GUI window with the values from the logger queue.

    Args:
        window (sg.Window): The PySimpleGUI window object.
        logger (Logger): The logger object.

    Returns:
        None
    """
    if not logger.queue.empty():
        # read the statistics from the logger
        for stat, val in logger.queue.get().items():
            window[stat].update(val)  # type: ignore


def stop_button_event(logger: Logger, window, thread) -> None:
    """
    Event handler for the stop button. Sends a shutdown flag to the given thread and kills it.

    Args:
        logger (Logger): The logger object.
        window (sg.Window): The PySimpleGUI window object.
        thread (StoppableThread | None): The thread to shutdown.

    Returns:
        None
    """
    logger.change_status("Stopping")

    # disable stop keys
    for key in STOP_KEYS:
        window[key].update(disabled=True)

    # enable input keys
    for key in CONTROLS_KEYS:
        window[key].update(disabled=False)

    shutdown_thread(thread, kill=True)  # send the shutdown flag to the thread


def main():
    """
    The main function of the Py-TarkBot program.
    Initializes the GUI window and handles user input events.

    Returns:
        None
    """

    thread: FleaSellWorkerThread | None = None
    comm_queue: Queue[dict[str, str | int]] = Queue()
    logger = Logger(comm_queue, timed=False)  # dont time the inital logger

    window = make_tarkbot_window()

    load_last_settings(window)

    while True:
        event, values = window.read(timeout=100)

        if event in [sg.WIN_CLOSED, "Exit"]:
            # shut down the thread if it is still running
            shutdown_thread(thread)
            break

        # start buttons:
        if event == FLEA_SELL_START_KEY:
            logger = Logger(comm_queue)
            thread = flea_sell_mode_start_button_event(logger, window, values)

        if event == HIDEOUT_START_KEY:
            logger = Logger(comm_queue)
            thread = hideout_mode_start_button_event(logger, window, values)

        if event == SNIPEBOT_START_KEY:
            logger = Logger(comm_queue)
            thread = snipe_mode_start_button_event(logger, window, values)

        if event in STOP_KEYS:
            stop_button_event(logger, window, thread)

        if event not in {"__TIMEOUT__", DONATE_BUTTON_KEY}:
            save_current_settings(values)

        if event == DONATE_BUTTON_KEY:
            webbrowser.open(
                "https://www.paypal.com/donate/"
                + "?business=YE72ZEB3KWGVY"
                + "&no_recurring=0"
                + "&item_name=Support+my+projects%21"
                + "&currency_code=USD"
            )

        # handle when thread is finished
        if thread is not None and not thread.is_alive():
            # enable the start button and configuration after the thread is stopped
            for key in START_KEYS:
                window[key].update(disabled=False)

            if thread.logger.errored:
                for key in STOP_KEYS:
                    window[key].update(disabled=True)
            else:
                # reset the communication queue and logger
                comm_queue = Queue()
                logger = Logger(comm_queue, timed=False)
                thread = None
        update_layout(window, logger)
    shutdown_thread(thread, kill=True)
    window.close()


if __name__ == "__main__":
    main()
