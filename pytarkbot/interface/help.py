import PySimpleGUI as sg

from .theme import THEME


def show_help_gui():
    out_text = (
        "Debugging Information\n\n"
        + "    1. If youre getting '[WinError 5] Access is denied error', try running the program as administrator.\n"
        + "    2. If window resizing is your issue, try to start the tarkov client with a resolution smaller than 1280x960 (something like 1154x900).\n"
        + "\n\nFlea Mode Information:\n\n"
        + "     Bot will sell the items in the top ~40 rows of your inventory.\n"
        + "     Make sure this area is composed of items only for the flea.\n"
        + "     This bot does well to not flea the wrong items, or to waste your money- but it is not perfect.\n"
        + "     The bot chooses an item, looks for its price, and if the price recognition is any bit unsure itll move onto the next one, otherwise it will sell it according to an undercut function.\n\n"
        + "You can share any failures (or successes?) of the bot on the github @ github.com/matthewmiglio/py-tarkBot\n"
    )

    sg.theme(THEME)
    layout = [
        [sg.Text(out_text)],
    ]
    window = sg.Window("Py-TarkBot", layout)
    while True:
        read = window.read()
        event, _ = read or (None, None)
        if event in [sg.WIN_CLOSED, "Exit"]:
            break
    window.close()
