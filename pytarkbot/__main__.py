import sys
import time

import pyautogui
import pyperclip
import PySimpleGUI as sg

from pytarkbot.client import intro_printout, orientate_terminal
from pytarkbot.configuration import load_user_settings
from pytarkbot.flee import (check_first_price, get_to_flee_tab,
                            get_to_flee_tab_from_my_offers_tab,
                            get_to_my_offers_tab, open_add_offer_tab,
                            post_item, remove_offers,
                            select_random_item_to_flee, set_flea_filters,
                            wait_till_can_add_another_offer)
from pytarkbot.hideout import manage_hideout
from pytarkbot.launcher import restart_tarkov
from pytarkbot.logger import Logger
from pytarkbot.tesseract_install import setup_tesseract

user_settings = load_user_settings()
launcher_path = user_settings["launcher_path"]

#tarkov_graphics_settings_path = user_settings["graphics_setting_path"]

#saved_user_settings_path = join(".\config","user_default_config","Graphics.ini")
#preset_graphics_for_bot_path = join(".\config","config_for_bot","Graphics.ini")


logger = Logger()
setup_tesseract()


def flea_items_main():

    state = "intro"

    while True:
        if state == "intro":
            state_intro()
            state = "flee_mode"

        if state == "restart":
            state_restart()
            state = "flee_mode"

        if state == "flee_mode":
            state = state_flee_mode()

        if state == "remove_flee_offers":
            state = state_remove_flee_offers()


def hideout_management_main(crafts_to_farm):
    # intro_printout(logger)
    state = "intro"
    while True:
        if state == "intro":
            state_intro()
            state = "manage_hideout_mode"

        if state == "manage_hideout_mode":
            state = state_hideout_management(crafts_to_farm)

        if state == "restart":
            state_restart()
            state = "manage_hideout_mode"


def state_user_help_printout():
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==user_help_printout")
    logger.log(blank_line)
    logger.log("")
    logger.log("lol good luck.")
    return "restart"


def state_intro():
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Intro")
    logger.log(blank_line)
    logger.log("")

    restart_tarkov(logger, launcher_path)


def state_remove_flee_offers():
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Remove flee offers")
    logger.log(blank_line)
    logger.log("")

    logger.log("STATE=remove_flee_offers")

    logger.log("Getting to the flea tab.")
    if get_to_flee_tab(logger) == "restart":
        return "restart"

    logger.log("Getting to my offers tab")
    if get_to_my_offers_tab(logger) == "restart":
        return "restart"

    logger.log("Starting remove offers alg.")
    remove_offers(logger)

    logger.log("Returning to browse page in the flea.")
    get_to_flee_tab_from_my_offers_tab(logger)

    return "flee_mode"


def state_flee_mode():
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==flee mode")
    logger.log(blank_line)
    logger.log("")

    logger.log("STATE=flee_mode")
    # open flea
    if get_to_flee_tab(logger) == "restart":
        return "restart"
    time.sleep(0.33)

    while True:
        pyautogui.press('n')

        # wait for add offer
        if wait_till_can_add_another_offer(logger) == "remove_flee_offers":
            return "remove_flee_offers"

        # click add offer button on top of screen
        open_add_offer_tab(logger)

        # fbi for random item
        if select_random_item_to_flee(logger) == "restart":
            logger.log("Issue selecting random item to flee.")
            return "restart"

        # set search
        set_flea_filters(logger)
        time.sleep(1)

        # if current price passes check, post this item up. else skip
        post_price = check_first_price(logger)
        if post_price is not False:
            logger.log("Post price passed all checks. Posting this item.")
            post_item(logger, post_price)


def state_restart():
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==Restart")
    logger.log(blank_line)
    logger.log("")

    # add to logegr
    logger.add_restart()

    # if tark open close it
    logger.log("STATE=RESTART")
    restart_tarkov(logger, launcher_path)

    return "flee_mode"


def state_hideout_management(crafts_to_farm):
    blank_line = "////////////////////////////////////////////////////"
    logger.log("")
    logger.log(blank_line)
    logger.log("State==hideout management")
    logger.log(blank_line)
    logger.log("")

    if manage_hideout(logger, crafts_to_farm) == "restart":
        return "restart"
    return "restart"


def show_donate_gui():
    sg.theme('Material2')
    layout = [
        [sg.Text('Paypal donate link: \n\nhttps://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD'),
         sg.Text(size=(15, 1), key='-OUTPUT-')],

        [sg.Button('Exit'), sg.Button('Copy link to clipboard')]
        # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
    ]
    window = sg.Window('PY-TarkBot', layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == "Copy link to clipboard":
            pyperclip.copy(
                'https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD')

    window.close()


def show_help_gui():
    sg.theme('Material2')
    layout = [[sg.Text('Hideout Information:\n  Workbench: Have M18 smokes and M67 nades for green gunpowder craft \n  Medstation: Have AI-2s, bandages(blue and white ones), and augmentin \n  Water collector: have extra water filters \n  Scav case: Have intelligence folders \n  Booze generator: Have sugar and super water (bot will use water collector super water btw)\n\nFlea Mode Information:\n  Bot will sell the items in the top ~40 rows of your inventory.\n  Make sure this area is composed of items only for the flea.\n  This bot does well to not flea the wrong items, or to waste your money- but it is not perfect.'), sg.Text(
        size=(15, 1), key='-OUTPUT-')], [sg.Button('Exit')]]
    window = sg.Window('PY-TarkBot', layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
    window.close()


def main():
    orientate_terminal()
    intro_printout(logger)
    sg.theme('Material2')
    # defining various things that r gonna be in the gui.
    layout = [
        # text output var
        [sg.Text('Python Tarkov bot - Matthew Miglio ~Aug 2022\n\nREMINDER: Set tarkov graphics settings BEFORE starting the bot\n(windowed/1280x960/4:3)\n'),
         sg.Text(size=(15, 1), key='-OUTPUT-')],
        # text input var
        # [sg.Input(key='-IN-')],
        # bot config checkboxes
        [sg.Text('Select ONLY ONE of the following modes:'),
         sg.Text(size=(15, 1), key='-OUTPUT-')],
        [sg.Checkbox('Manage Hideout', default=True,
                     key="-hideout_management_in-")],
        [sg.Checkbox('Flea items', default=False, key="-flea_items_in-")],
        [sg.Text('Select which stations to farm:'),
         sg.Text(size=(15, 1), key='-OUTPUT-')],
        [sg.Checkbox('Workbench crafts', default=True, key="-workbench_crafts_in-"),
         sg.Checkbox(
            'Medstation crafts',
            default=True,
            key="-medstation_crafts_in-"),
            sg.Checkbox(
            'Water collector crafts',
            default=True,
            key="-water_collector_crafts_in-"),
            sg.Checkbox(
            'Scav case crafts',
            default=True,
            key="-scav_case_crafts_in-"),
            sg.Checkbox('Booze generator crafts', default=True, key="-booze_generator_crafts_in-")],

        # buttons
        [sg.Button('Start'), sg.Button('Help'), sg.Button('Donate')]
        # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
    ]
    # window layout
    window = sg.Window('PY-TarkBot', layout)
    # run the gui
    while True:
        # get gui vars
        event, values = window.read()
        # if gui sees close then close
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        # if gui sees start press then start bot
        if event == 'Start':
            print("starting")
            # if both are checked blow the program up
            if (values["-hideout_management_in-"]
                    ) and (values["-flea_items_in-"]):
                logger.log("Select ONLY ONE of the mode checkboxes")
                break

            # if hideout management checkbox is checked, run the hideout
            # management main
            if values["-hideout_management_in-"]:
                window.close()

                crafts_to_farm = []
                if values["-workbench_crafts_in-"]:
                    crafts_to_farm.append("workbench")
                if values["-scav_case_crafts_in-"]:
                    crafts_to_farm.append("scav_case")
                if values["-medstation_crafts_in-"]:
                    crafts_to_farm.append("medstation")
                if values["-water_collector_crafts_in-"]:
                    crafts_to_farm.append("water_collector")
                if values["-booze_generator_crafts_in-"]:
                    crafts_to_farm.append("booze_generator")

                print(crafts_to_farm)

                hideout_management_main(crafts_to_farm)

            # if flea items checkbox is checked, run the flea items main
            if values["-flea_items_in-"]:
                window.close()
                flea_items_main()

        if event == 'Help':
            show_help_gui()

        if event == 'Donate':
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
    main()
