import sys

import pyautogui
import pyperclip
import PySimpleGUI as sg

from pytarkbot.bot import flea_items_main
from pytarkbot.tarkov import intro_printout, orientate_terminal
from pytarkbot.utils import Logger, get_bsg_launcher_path, setup_tesseract

pyautogui.FAILSAFE = False

# setup dependency paths
bsg_launcher_path = get_bsg_launcher_path()
setup_tesseract()


logger = Logger()


def show_donate_gui():
    sg.theme("Material2")
    layout = [
        [
            sg.Text(
                "Paypal donate link: \n\nhttps://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD"
            ),
            sg.Text(size=(15, 1), key="-OUTPUT-"),
        ],
        [sg.Button("Exit"), sg.Button("Copy link to clipboard")]
        # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
    ]
    window = sg.Window("PY-TarkBot", layout)
    while True:
        event, values = window.read()
        if event in [sg.WIN_CLOSED, "Exit"]:
            break

        if event == "Copy link to clipboard":
            pyperclip.copy(
                "https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD"
            )

    window.close()


def show_help_gui():
    out_text = (
        "Debugging Information\n\n"
        + "    1. If the bot is instantly closing after pressing the start button, it is likely due to an incorrectly specified launcher path @ appdata/roaming/py-tarkBot/config.json\n"
        + "        In this config file make sure to use double slashes as shown in the default launcher path.\n"
        + "    2. If youre getting '[WinError 5] Access is denied error', try running the program as administrator.\n"
        + "    3. If window resizing is your issue, try to start the tarkov client with a resolution smaller than 1280x960 (something like 1154x900).\n"
        + "    4. Hideout mode is WIP so dont even expect that mode to do anything right and keep this in mind when reporting glaring bugs with the hideout mode.\n"
        + "\n\nHideout Information:\n\n"
        + "     Workbench: Have M18 smokes and M67 nades for green gunpowder craft\n"
        + "     Medstation: Have AI-2s, bandages(blue and white ones), and augmentin\n"
        + "     Water collector: have extra water filters \n"
        + "     Scav case: Have intelligence folders \n"
        + "\n\nFlea Mode Information:\n\n"
        + "     Bot will sell the items in the top ~40 rows of your inventory.\n"
        + "     Make sure this area is composed of items only for the flea.\n"
        + "     This bot does well to not flea the wrong items, or to waste your money- but it is not perfect.\n"
        + "     The bot chooses an item, looks for its price, and if the price recognition is any bit unsure itll move onto the next one, otherwise it will sell it according to an undercut function.\n\n"
        + "You can share any failures (or successes?) of the bot on the github @ github.com/matthewmiglio/py-tarkBot\n"
    )

    sg.theme("Material2")
    layout = [
        [sg.Text(out_text)],
    ]
    window = sg.Window("PY-TarkBot", layout)
    while True:
        event, values = window.read()
        if event in [sg.WIN_CLOSED, "Exit"]:
            break
    window.close()


def main():
    orientate_terminal()
    intro_printout(logger)

    out_text = "" + "-Python Tarkov bot - Matthew Miglio ~Aug 2022\n\n"
    out_text += (
        "-You MUST manually set tarkov to windowed and 4:3 BEFORE running the bot.\n"
    )

    sg.theme("Material2")
    # defining various things that r gonna be in the gui.
    layout = [
        [sg.Text(out_text)],
        # buttons
        [sg.Button("Start"), sg.Button("Stop"), sg.Button("Help"), sg.Button("Donate")]
        # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
    ]
    # window layout
    window = sg.Window("PY-TarkBot", layout)
    # run the gui
    while True:
        # get gui vars
        event, values = window.read()
        # if gui sees close then close
        if event in [sg.WIN_CLOSED, "Exit"]:
            break
        # if gui sees start press then start bot
        if event == "Start":
            # if Flea mode checkbox is checked, run the Flea mode main
            window.close()
            logger.log("\n\nStarting flea snipe mode.\n")
            flea_items_main()

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
