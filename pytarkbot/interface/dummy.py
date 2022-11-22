"""a dummy test function to simulate the interface"""

import time
import webbrowser
from typing import Any

import PySimpleGUI as sg

from pytarkbot.interface.help import show_help_gui
from pytarkbot.interface.layout import disable_keys, main_layout
from pytarkbot.interface.theme import THEME

sg.theme(THEME)

if __name__ == "__main__":
    # some sample statistics
    statistics: dict[str, Any] = {
        "current_status": "Idle",
        "time_since_start": "00:00:00",
        "restarts": 1,
        "item_sold": 2,
        "roubles_made": 3,
        "sale_attempts": 4,
        "success_rate": 5,
    }

    window = sg.Window("Py-TarkBot", main_layout)

    running = False

    while True:
        event, values = window.read(timeout=100)  # type: ignore
        if event == sg.WIN_CLOSED:
            break
        if event == "Start":
            window["current_status"].update("Starting")  # type: ignore
            for key in disable_keys:
                window[key].update(disabled=True)
            running = True
            window["Stop"].update(disabled=False)

        elif event == "Stop":
            window["current_status"].update("Stopping")  # type: ignore
            running = False
            for key in disable_keys:
                window[key].update(disabled=False)
            window["Stop"].update(disabled=True)

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

        if running:
            # change some of the statistics
            statistics["current_status"] = "Running"
            statistics["time_since_start"] = "00:00:01"
            statistics["restarts"] += 1
            statistics["item_sold"] += 1
            statistics["roubles_made"] += 1
            statistics["sale_attempts"] += 1
            statistics["success_rate"] += 1

        # update the statistics
        window["current_status"].update(statistics["current_status"])  # type: ignore
        window["time_since_start"].update(statistics["time_since_start"])  # type: ignore
        window["restarts"].update(statistics["restarts"])  # type: ignore
        window["item_sold"].update(statistics["item_sold"])  # type: ignore
        window["roubles_made"].update(statistics["roubles_made"])  # type: ignore
        window["sale_attempts"].update(statistics["sale_attempts"])  # type: ignore
        window["success_rate"].update(statistics["success_rate"])  # type: ignore

        time.sleep(1)

    window.close()
