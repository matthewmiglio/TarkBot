import PySimpleGUI as sg

from .theme import THEME


def show_help_gui():
    out_text = (
        "Debugging Information\n\n"
        + "    2. If window resizing is your issue, try to start the tarkov client with a resolution smaller than 1280x960 (something like 1154x900).\n"
        + "\n\nFlea Mode Information:\n\n"
        + "     Bot will sell items from the top of your inventory down to as many rows specified in the GUI\n"
        + "     Non-FIR items in this section will obstruct the bot, but wont cause any real issues.\n"
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
