import webbrowser
from queue import Queue

import PySimpleGUI as sg

from pytarkbot.bot import state_tree
from pytarkbot.interface import THEME, disable_keys, main_layout, show_help_gui
from pytarkbot.utils import Logger
from pytarkbot.utils.thread import StoppableThread

sg.theme(THEME)


def start_button_event(logger: Logger, window, values):
    logger.change_status("Starting")

    for key in disable_keys:
        window[key].update(disabled=True)

    # setup thread and start it
    args = values["rows_to_target"]
    thread = WorkerThread(logger, args)
    thread.start()

    # enable the stop button after the thread is started
    window["Stop"].update(disabled=False)

    return thread


def stop_button_event(logger: Logger, window, thread):
    logger.change_status("Stopping")
    window["Stop"].update(disabled=True)
    shutdown_thread(thread)  # send the shutdown flag to the thread


def shutdown_thread(thread, join=False):
    if thread is not None:
        thread.shutdown_flag.set()
        if join:
            # wait for the thread to close
            thread.join()  # this will block the gui


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

    thread: WorkerThread | None = None
    comm_queue: Queue[dict[str, str | int]] = Queue()
    logger = Logger(comm_queue, timed=False)  # dont time the inital logger

    # window layout
    window = sg.Window("Py-TarkBot", main_layout)

    # run the gui
    while True:
        # get gui vars
        read = window.read(timeout=100)
        event, values = read or (None, None)

        if event in [sg.WIN_CLOSED, "Exit"]:
            # shut down the thread if it is still running
            shutdown_thread(thread)
            break

        if event == "Start":
            # start the bot with new queue and logger
            comm_queue = Queue()
            logger = Logger(comm_queue)
            thread = start_button_event(logger, window, values)

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

        # handle when thread is finished
        if thread is not None and not thread.is_alive():
            # enable the start button and configuration after the thread is stopped
            for key in disable_keys:
                window[key].update(disabled=False)
            # reset the communication queue and logger
            comm_queue = Queue()
            logger = Logger(comm_queue, timed=False)
            thread = None

        update_layout(window, logger)

    shutdown_thread(thread, join=True)

    window.close()


class WorkerThread(StoppableThread):
    def __init__(self, logger: Logger, args, kwargs=None):
        super().__init__(args, kwargs)
        self.logger = logger

    def run(self):
        try:
            number_of_rows = self.args  # parse thread args
            state = "restart"
            # loop until shutdown flag is set
            while not self.shutdown_flag.is_set():
                # perform state transition
                # (state, ssid) = state_tree(jobs, self.logger, ssid_max, ssid, state)
                state = state_tree(self.logger, state, number_of_rows)
        except Exception as exc:  # pylint: disable=broad-except
            # catch exceptions and log to not crash the main thread
            self.logger.error(str(exc))


if __name__ == "__main__":
    main()
