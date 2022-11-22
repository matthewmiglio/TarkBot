import pyperclip
import PySimpleGUI as sg

from .theme import THEME


def show_donate_gui():
    sg.theme(THEME)
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
        read = window.read()
        event, _ = read or (None, None)
        if event in [sg.WIN_CLOSED, "Exit"]:
            break

        if event == "Copy link to clipboard":
            pyperclip.copy(
                "https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD"
            )

    window.close()
