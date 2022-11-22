import sys

import pyautogui
import PySimpleGUI as sg

from pytarkbot.bot import flea_items_main
from pytarkbot.interface import THEME, main_layout, show_donate_gui, show_help_gui
from pytarkbot.tarkov import intro_printout, orientate_terminal
from pytarkbot.utils import Logger, get_bsg_launcher_path, setup_tesseract

pyautogui.FAILSAFE = False

# setup dependency paths
bsg_launcher_path = get_bsg_launcher_path()
setup_tesseract()


logger = Logger()


def main():
    orientate_terminal()
    intro_printout(logger)

    sg.theme(THEME)

    # window layout
    window = sg.Window("PY-TarkBot", main_layout)
    # run the gui
    while True:
        # get gui vars
        read = window.read()
        event, _ = read or (None, None)
        # if gui sees close then close
        if event in [sg.WIN_CLOSED, "Exit"]:
            break
        # if gui sees start press then start bot
        if event == "Start":
            # if Flea mode checkbox is checked, run the Flea mode main
            window.close()
            logger.log("\n\nStarting flea snipe mode.\n")
            flea_items_main(logger, bsg_launcher_path)

        if event == "Help":
            show_help_gui()

        if event == "Donate":
            show_donate_gui()

    window.close()


def end_loop():
    print("Press ctrl-c to close the program.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        end_loop()
