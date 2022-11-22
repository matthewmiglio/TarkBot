import PySimpleGUI as sg

from .theme import THEME


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

    sg.theme(THEME)
    layout = [
        [sg.Text(out_text)],
    ]
    window = sg.Window("PY-TarkBot", layout)
    while True:
        read = window.read()
        event, _ = read or (None, None)
        if event in [sg.WIN_CLOSED, "Exit"]:
            break
    window.close()
