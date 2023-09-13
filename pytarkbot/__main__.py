import time
import webbrowser
from os import path
from queue import Queue

import PySimpleGUI as sg
from pytarkbot.flea_sell_bot import flea_sell_mode_state_tree
from pytarkbot.flea_sell_bot.state import hideout_mode_state_tree
from pytarkbot.interface import (THEME, disable_keys, flea_mode_layout,
                                 hideout_disable_keys, hideout_mode_layout,
                                 show_help_gui, snipebot_mode_layout,
                                 user_config_keys)
from pytarkbot.utils import (Logger,  # pylint: disable=unused-import
                             admin_check)
from pytarkbot.utils.caching import (cache_user_settings, check_user_settings,
                                     read_user_settings)
from pytarkbot.utils.thread import StoppableThread, ThreadKilled

sg.theme(THEME)
ICON_PATH = "pixel-pytb-multi.ico"
if not path.isfile(ICON_PATH):
    ICON_PATH = path.join("docs\\assets", ICON_PATH)


def save_current_settings(values):
    # read the currently selected values for each key in user_config_keys
    user_settings = {key: values[key] for key in user_config_keys if key in values}
    # cache the user settings
    cache_user_settings(user_settings)


def load_last_settings(window):
    if check_user_settings():
        window.read(timeout=10)  # read the window to edit the layout
        user_settings = read_user_settings()
        if user_settings is not None:
            for key in user_config_keys:
                if key in user_settings:
                    window[key].update(user_settings[key])
        window.refresh()  # refresh the window to update the layout


def flea_mode_start_button_event(logger: Logger, window, values):
    logger.change_status("Starting")

    for key in disable_keys:
        window[key].update(disabled=True)

    # setup thread and start it
    args = (values["rows_to_target"], values["remove_offers_timer"])
    thread = FleaSellWorkerThread(logger, args)
    thread.start()

    # enable the stop button after the thread is started
    window["Stop"].update(disabled=False)

    return thread


def hideout_mode_start_button_event(logger: Logger, window, values):
    # check for invalid inputs
    logger.change_status("Starting hideout mode")

    for key in hideout_disable_keys:
        window[key].update(disabled=True)

    # unpack job list
    jobs = []
    if values["bitcoin_checkbox"]:
        jobs.append("Bitcoin")

    if values["lavatory_checkbox"]:
        jobs.append("Lavatory")

    if values["medstation_checkbox"]:
        jobs.append("medstation")

    if values["water_checkbox"]:
        jobs.append("water")

    if values["workbench_checkbox"]:
        jobs.append("Workbench")

    if values["scav_case_checkbox"]:
        jobs.append("scav_case")
        jobs.append(values["scav_case_type"])

    # setup thread and start it
    print("jobs: ", jobs)

    thread = HideoutModeWorkerThread(logger, jobs)
    thread.start()

    # enable the stop button after the thread is started
    window["Stop"].update(disabled=False)

    return thread


def stop_button_event(logger: Logger, window, thread):
    logger.change_status("Stopping")
    window["Stop"].update(disabled=True)
    shutdown_thread(thread, kill=True)  # send the shutdown flag to the thread


def shutdown_thread(thread: StoppableThread | None, kill=True):
    if thread is not None:
        thread.shutdown_flag.set()
        if kill:
            thread.kill()


def update_layout(window: sg.Window, logger: Logger):
    # comm_queue: Queue[dict[str, str | int]] = logger.queue
    window["time_since_start"].update(logger.calc_time_since_start())  # type: ignore
    # update the statistics in the gui
    if not logger.queue.empty():
        # read the statistics from the logger
        for stat, val in logger.queue.get().items():
            window[stat].update(val)  # type: ignore


def main():
    # orientate_terminal()

    thread: FleaSellWorkerThread | None = None
    comm_queue: Queue[dict[str, str | int]] = Queue()
    logger = Logger(comm_queue, timed=False)  # dont time the inital logger

    # window layout
    flea_sell_tab = sg.Tab("Flea Sell", flea_mode_layout)
    flea_snipe_tab = sg.Tab("Flea Snipe", snipebot_mode_layout)
    hideout_tab = sg.Tab("Hideout", hideout_mode_layout)
    tab_group = sg.TabGroup(
        [
            [
                flea_sell_tab,
                flea_snipe_tab,
                hideout_tab,
            ]
        ]
    )
    layout = [
        [tab_group],
    ]
    window = sg.Window("Py-TarkBot v1.0.0", layout, finalize=True)

    load_last_settings(window)

    # run the gui
    while True:
        event, values = window.read(timeout=100)

        try:
            if event != sg.TIMEOUT_KEY:
                print("event: ", event)
        except:
            pass

        # get gui vars

        if event in [sg.WIN_CLOSED, "Exit"]:
            # shut down the thread if it is still running
            shutdown_thread(thread)
            break

        if event == "hideout_mode_start":
            # start the bot with new queue and logger
            comm_queue = Queue()
            logger = Logger(comm_queue)
            thread = hideout_mode_start_button_event(logger, window, values)

        if event == "flea_mode_start":
            # start the bot with new queue and logger
            comm_queue = Queue()
            logger = Logger(comm_queue)
            thread = flea_mode_start_button_event(logger, window, values)

        if event == "snipebot_mode_start_button":
            print("snpiebot mode start button event")

        elif event == "Stop":
            stop_button_event(logger, window, thread)

        elif event == "Help":
            show_help_gui()

        elif event == "Donate":
            webbrowser.open(
                "https://www.paypal.com/donate/"
                + "?business=YE72ZEB3KWGVY"
                + "&no_recurring=0"
                + "&item_name=Support+my+projects%21"
                + "&currency_code=USD"
            )

        elif event == "issues-link":
            webbrowser.open(
                "https://github.com/matthewmiglio/py-tarkbot/issues/new/choose"
            )

        elif event in user_config_keys:
            save_current_settings(values)

        # handle when thread is finished
        if thread is not None and not thread.is_alive():
            # enable the start button and configuration after the thread is stopped
            for key in disable_keys:
                window[key].update(disabled=False)
            if thread.logger.errored:
                window["Stop"].update(disabled=True)
            else:
                # reset the communication queue and logger
                comm_queue = Queue()
                logger = Logger(comm_queue, timed=False)
                thread = None

        update_layout(window, logger)

    shutdown_thread(thread, kill=True)

    window.close()


class FleaSellWorkerThread(StoppableThread):
    def __init__(self, logger: Logger, args, kwargs=None):
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        try:
            number_of_rows, remove_offers_timer = self.args  # parse thread args

            state = "restart"

            loops = 0
            # loop until shutdown flag is set
            while not self.shutdown_flag.is_set():
                loops += 1

                state = flea_sell_mode_state_tree(
                    self.logger, state, number_of_rows, remove_offers_timer
                )

        except ThreadKilled:
            return

        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


class HideoutModeWorkerThread(StoppableThread):
    def __init__(self, logger: Logger, args, kwargs=None):
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        try:
            jobs = self.args  # parse thread args

            state = "start"

            loops = 0
            # loop until shutdown flag is set
            while not self.shutdown_flag.is_set():
                loops += 1

                state = hideout_mode_state_tree(state, self.logger, jobs)
                time.sleep(1)

        except ThreadKilled:
            return

        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


if __name__ == "__main__":
    main()
