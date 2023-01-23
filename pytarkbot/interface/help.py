import PySimpleGUI as sg

from .theme import THEME


def show_help_gui():
    out_text = (
        "Controls Information\n"
        + "    1. Rows to target: Bot will sell items from the top of your inventory down to as many rows as you choose\n"
        + "    2. Remove offers timer: How long the bot will wait for another flee slot before removing existing offers\n"
        + "    3. Auto-start: Automatically begin the bot 1m after opening the program\n\n"
        + "*Non-FIR items in this section will obstruct the bot, but wont cause any real issues.*\n\n"
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
