import subprocess
import sys
import time
import tkinter.messagebox
from typing import TYPE_CHECKING

import numpy
import pygetwindow

from pytarkbot.detection import check_for_location, find_references, pixel_is_equal
from pytarkbot.tarkov import (
    click,
    orientate_launcher,
    orientate_tarkov_client,
    screenshot,
)
from pytarkbot.tarkov.client import orientate_terminal
from pytarkbot.utils.dependency import get_bsg_launcher_path

if TYPE_CHECKING:
    from pytarkbot.utils.logger import Logger


def check_if_on_tark_main(logger):
    logger.change_status("Checking if on tark main")
    iar = numpy.asarray(screenshot())
    pix_list = [
        iar[613][762],
        iar[616][926],
        iar[611][294],
        iar[618][769],
        iar[651][427],
        iar[615][1010],
        iar[648][290],
    ]

    return all(pixel_is_equal(pix, [175, 90, 50], tol=100) for pix in pix_list)


def wait_for_tark_main(logger):
    on_main = check_if_on_tark_main(logger)
    loops = 0
    while not on_main:
        orientate_terminal()
        logger.change_status(f"Waiting for tark main {loops}")
        loops = loops + 2
        time.sleep(2)
        on_main = check_if_on_tark_main(logger)
        if loops > 120:
            return "restart"
    logger.change_status("Made it to tarkov main.")


def close_tarkov_client(logger, tark_window):
    try:
        logger.change_status("Tark found open. Closing it.")
        tark_window = tark_window[0]
        tark_window.close()
    except BaseException:
        logger.change_status("error closing tarkov client.")


def close_launcher(logger, tark_launcher):
    logger.change_status("Tark launcher found open. Closing it.")
    tark_launcher = tark_launcher[0]
    tark_launcher.close()


def restart_tarkov(logger: Logger):
    # sourcery skip: extract-duplicate-method, extract-method
    orientate_terminal()

    # check if tarkov is open
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
    tark_launcher = pygetwindow.getWindowsWithTitle("BsgLauncher")

    # if tark open
    if len(tark_window) != 0:
        logger.change_status("Tarkov client detected. Closing it.")
        orientate_terminal()
        close_tarkov_client(logger, tark_window)
        time.sleep(5)

    # if launcher open
    if len(tark_launcher) != 0:
        logger.change_status("Tarkov launcher detected. Closing it.")
        orientate_terminal()
        close_launcher(logger, tark_launcher)
        time.sleep(5)

    # open tark launcher
    logger.change_status("Opening launcher.")
    try:
        subprocess.Popen(get_bsg_launcher_path())  # pylint: disable=consider-using-with
    except FileNotFoundError:
        tkinter.messagebox.showinfo(
            "CRITICAL ERROR",
            "Could not start launcher. Open a bug report on github and share your BSGlauncher install path.",
        )
        sys.exit("Launcher path not found")

    # Wait for launcher to open and load up
    logger.change_status("Waiting for launcher to open.")
    index = 0
    has_window = False
    while not has_window:
        orientate_terminal()
        time.sleep(1)
        index += 1
        if len(pygetwindow.getWindowsWithTitle("BsgLauncher")) > 0:
            has_window = True
        if index > 25:
            logger.change_status("Launcher failed to open.")
            restart_tarkov(logger)
    time.sleep(5)

    # orientate launcher
    logger.change_status("orientating launcher")
    orientate_launcher()
    orientate_terminal()
    time.sleep(3)

    # wait for launcher play button to appear
    logger.change_status("Waiting for launcher's play button")
    if wait_for_play_button_in_launcher(logger) == "restart":
        restart_tarkov(logger)

    # click play
    logger.change_status("Clicking play.")
    click(942, 558)
    time.sleep(20)

    # wait for client opening
    logger.change_status("Waiting for tarkov client to open.")
    if wait_for_tarkov_to_open(logger) == "restart":
        restart_tarkov(logger)
    for index in range(0, 30, 2):
        orientate_terminal()
        logger.change_status(f"Manually giving tark time to load: {index}")
        time.sleep(2)

    # orientate tark client
    orientate_tarkov_client()
    orientate_terminal()
    time.sleep(1)

    # wait for us to reach main menu
    logger.change_status("Waiting for tarkov client to reach main menu.")
    if wait_for_tark_main(logger) == "restart":
        restart_tarkov(logger)


def wait_for_tarkov_to_open(logger):
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
    loops = 0
    while len(tark_window) == 0:
        orientate_terminal()
        logger.change_status(f"Waiting for tarkov to open {loops}")
        loops = loops + 2
        time.sleep(2)
        tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")
        if loops > 50:
            return "restart"

    logger.change_status("Tarkov client detected. Done waiting")


def check_if_play_button_exists_in_launcher():

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
        tolerance=0.99,
    )
    return check_for_location(locations)


def wait_for_play_button_in_launcher(logger):
    loops = 0
    logger.change_status("Waiting for play button to appear.")
    while not check_if_play_button_exists_in_launcher():
        loops += 1
        if loops > 20:
            return "restart"
        time.sleep(1)

    logger.change_status("Done waiting for play button to appear.")
