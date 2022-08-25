import subprocess
import sys
import time

import pygetwindow

from pytarkbot.client import check_quit_key_press, click, orientate_launcher, orientate_tarkov_client, screenshot
from pytarkbot.graphics_config import save_default_settings_to_file, set_tarkov_settings_to_bot_config, set_tarkov_settings_to_default_config
from pytarkbot.image_rec import check_for_location, find_references, pixel_is_equal
import pyautogui


def check_if_on_tark_main(logger):
    current_image = screenshot()
    reference_folder = "tark_main_menu"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
        "6.png",
        "7.png",
        "8.png",
        "9.png",
        "10.png",
        "11.png",
        
        
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )

    truth = check_for_location(locations)
    if truth:
        logger.log("On Tark main.")
    return truth


def wait_for_tark_main(logger):
    on_main = check_if_on_tark_main(logger)
    loops = 0
    while not (on_main):
        #top
        pyautogui.moveTo(250,250,duration=0.22)
        #left
        pyautogui.moveTo(125,330,duration=0.22)
        #bottom
        pyautogui.moveTo(250,500,duration=0.22)
        #right
        pyautogui.moveTo(330,330,duration=0.22)

        check_quit_key_press()
        logger.log(f"Waiting for tark main {loops}")
        loops = loops + 2

        on_main = check_if_on_tark_main(logger)
        if loops > 120:
            return "restart"
    logger.log("Made it to tarkov main.")


def close_tarkov_client(logger, tark_window):
    try:
        logger.log("Tark found open. Closing it.")
        tark_window = tark_window[0]
        tark_window.close()
    except BaseException:
        logger.log("error closing tarkov client.")


def close_launcher(logger, tark_launcher):
    logger.log("Tark launcher found open. Closing it.")
    tark_launcher = tark_launcher[0]
    tark_launcher.close()


def restart_tarkov(logger, launcher_path):
    # specify tark launcher path
    # launcher_path=r"B:\BsgLauncher\BsgLauncher.exe"

    # check if tarkov is open
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
    tark_launcher = pygetwindow.getWindowsWithTitle("BsgLauncher")

    # if tark open
    check_quit_key_press()
    if len(tark_window) != 0:
        close_tarkov_client(logger, tark_window)

    # if launcher open
    if len(tark_launcher) != 0:
        close_launcher(logger, tark_launcher)

    # open tark launcher
    check_quit_key_press()
    logger.log("Opening launcher.")
    try:
        subprocess.Popen(launcher_path)
    except FileNotFoundError:
        print(r"Launcher path not found, edit config file: %appdata%\py-TarkBot\config.json")
        sys.exit("Launcher path not found")
    time.sleep(10)

    # orientate launcher
    check_quit_key_press()
    logger.log("orientating launcher")
    orientate_launcher()

    #wait for launcher play button to appear
    if wait_for_play_button_in_launcher(logger)== "restart":
        restart_tarkov(logger,launcher_path)


    #click play
    check_quit_key_press()
    click(942,558)
    time.sleep(20)


    # wait for client opening
    check_quit_key_press()
    if wait_for_tarkov_to_open(logger) == "restart":
        restart_tarkov(logger, launcher_path)
    index = 0
    while index < 30:
        check_quit_key_press()
        logger.log(f"Giving tark time to load: {index}")
        time.sleep(2)
        index = index + 2

    # orientate tark client
    check_quit_key_press()
    orientate_tarkov_client("EscapeFromTarkov",logger)
    time.sleep(1)

    # wait for us to reach main menu
    check_quit_key_press()
    if wait_for_tark_main(logger)=="restart":
        restart_tarkov(logger,launcher_path)


def wait_for_tarkov_to_open(logger):
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
    loops = 0
    while len(tark_window) == 0:
        check_quit_key_press()
        logger.log(f"Waiting for tarkov to open {loops}")
        loops = loops + 2
        time.sleep(2)
        tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
        if loops > 50:
            return "restart"

    logger.log("Tarkov client detected. Done waiting")


def wait_for_tarkov_to_close(logger):
    loops = 0

    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
    while len(tark_window) != 0:
        close_tarkov_client(logger, tark_window)

        logger.log(f"Waiting for tarkov client to close {loops}")
        loops = loops + 2.33

        tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")

        time.sleep(2.33)

    time.sleep(1)

    logger.log("Done waiting for tarkov client to close.")


def check_if_play_button_exists_in_launcher():
    check_quit_key_press()
    current_image = screenshot()
    reference_folder = "check_if_play_button_exists_in_launcher2"
    references = [
        "1.png",
        "2.png",
        "3.png",
        "4.png",
        "5.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99
    )
    return check_for_location(locations)


def wait_for_play_button_in_launcher(logger):
    if len(pygetwindow.getWindowsWithTitle("BsgLauncher")) == 0:
        logger.log(
            "Launcher not detected while waiting for play button in launcher.")
        return "restart"
    loop = 0
    waiting = not (check_if_play_button_exists_in_launcher())
    while waiting:
        logger.log(f"Waiting for play button to appear in launcher {loop}")
        loop = loop + 2
        waiting = not (check_if_play_button_exists_in_launcher())
        waiting_animation(2)
        if loop > 50:
            logger.log(
                "Spent too long waiting for launcher's play button. Restarting.")
            return "restart"
