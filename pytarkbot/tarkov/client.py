import time

import numpy
import pyautogui
import pygetwindow

from pytarkbot.detection import pixel_is_equal
from pytarkbot.detection.image_rec import (
    check_for_location,
    find_references,
    get_first_location,
    make_reference_image_list,
)

pyautogui.FAILSAFE = False

TERMINAL_NAME = "Py-TarkBot v1"


def hideout_mode_find_filters_window():
    current_image = screenshot()
    reference_folder = "find_filters_tab"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    coords = get_first_location(locations)
    return None if coords is None else [coords[1] + 3, coords[0] + 3]


def hideout_mode_check_filters_window_orientation():
    coords = hideout_mode_find_filters_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 24)
    value2 = abs(coords[1] - 35)
    return value1 <= 3 and value2 <= 3


def hideout_mode_open_filters_window(logger):
    start_time = time.time()
    click(328, 87, clicks=3, interval=0.5)
    time.sleep(0.33)
    if (
        hideout_mode_orientate_filters_window(logger, start_time=start_time)
        == "restart"
    ):
        return "restart"


def hideout_mode_orientate_filters_window(logger, start_time=time.time()):
    is_orientated = hideout_mode_check_filters_window_orientation()
    loops = 0
    while not is_orientated:
        time_taken = time.time() - start_time
        print(f"time taken orientating filters {time_taken}")
        if time_taken > 23:
            print("failed orientate filters window timeout")
            return "restart"
        loops += 1
        if loops > 10:
            hideout_mode_open_filters_window(logger)
        logger.change_status("Orientating filters window.")
        coords = hideout_mode_find_filters_window()
        if coords is not None:
            origin = pyautogui.position()
            pyautogui.moveTo(coords[0], coords[1], duration=0.1)
            time.sleep(0.33)
            pyautogui.dragTo(3, 3, duration=0.33)
            pyautogui.moveTo(origin[0], origin[1])
            time.sleep(0.33)
        is_orientated = hideout_mode_check_filters_window_orientation()
    logger.change_status("Orientated filters window.")


def set_hideout_mode_flea_filters(logger):
    operation_delay = 0.25

    logger.change_status("Setting the flea filters for price undercut recognition")

    # open filter window
    logger.change_status("Opening the filters window")
    if hideout_mode_open_filters_window(logger) == "restart":
        return "restart"
    time.sleep(operation_delay)

    # click 'display offers from' dropdown
    logger.change_status("Filtering by trader sales only.")
    click(171, 188)
    time.sleep(operation_delay)

    # click players from dropdown
    click(179, 228)
    time.sleep(operation_delay)

    # click OK
    logger.change_status("Clicking OK in filters tab.")
    click(83, 272)
    time.sleep(operation_delay)


def get_launcher_res():
    try:
        window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
        s = window.size
        return s
    except:
        return False


def cycle_hideout_tab():
    click(40, 932)
    time.sleep(1)


def orientate_tarkov_client():
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")[0]
    tark_window.moveTo(0, 0)
    tark_window.resizeTo(1299, 999)


def orientate_launcher():
    launcher_window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
    launcher_window.moveTo(0, 0)
    launcher_window.resizeTo(100, 100)


def get_terminal_res():
    try:
        window = pygetwindow.getWindowsWithTitle(TERMINAL_NAME)[0]
        s = window.size
        return s
    except:
        return False


def orientate_terminal():
    try:
        terminal_res = get_terminal_res()
        w, h = terminal_res
        terminal_window = pygetwindow.getWindowsWithTitle(TERMINAL_NAME)[0]
        terminal_window.moveTo(pyautogui.size()[0] - w, 0)
    except:
        print("Couldnt orientate terminal...")


def get_to_hideout():
    print("Getting to hideout")

    orientate_tarkov_client()
    start_time = time.time()

    while not check_if_in_hideout():
        if time.time() - start_time > 60:
            return "restart"

        click(x=150, y=977)
        time.sleep(5)
    print("at hideout")


def check_if_in_hideout():
    iar = numpy.asarray(screenshot())
    hideout_pixel = iar[979][183]
    if pixel_is_equal(hideout_pixel, [159, 157, 144], tol=30):
        return True
    return False


def check_if_in_hideout_cycle_mode():
    current_image = screenshot(region=[0, 890, 80, 90])
    reference_folder = "in_hideout_cycle_mode_icon"
    references = make_reference_image_list(reference_folder)

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )

    return check_for_location(locations)


def screenshot(region=(0, 0, 1400, 1400)):
    if region is None:
        return pyautogui.screenshot()  # type: ignore
    return pyautogui.screenshot(region=region)  # type: ignore


def click(x, y, clicks=1, interval=0.0, duration=0.1, button="left"):
    # get current moust position
    origin = pyautogui.position()

    # move the mouse to the spot
    pyautogui.moveTo(x, y, duration=duration)

    # click it as many times as ur suppsoed to
    loops = 0
    while loops < clicks:
        pyautogui.click(x=x, y=y, button=button)
        loops += 1
        time.sleep(interval)

    # move mouse back to original position
    pyautogui.moveTo(origin[0], origin[1])


if __name__ == "__main__":
    # orientate_launcher()
    # print(get_launcher_res())
    # orientate_tarkov_client()
    orientate_launcher()
