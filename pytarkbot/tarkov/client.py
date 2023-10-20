"""
This module contains functions for interacting with the Tarkov game client.

"""
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
    """
    Finds the filters window in hideout mode.

    Returns:
    - A list containing the x and y coordinates of the top-left corner of the filters window.
    - None if the filters window cannot be found.
    """
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
    """
    Checks if the filters window in hideout mode is oriented correctly.

    Returns:
    - True if the filters window is oriented correctly.
    - False otherwise.
    """
    coords = hideout_mode_find_filters_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 24)
    value2 = abs(coords[1] - 35)
    return value1 <= 3 and value2 <= 3


def open_filters_window(logger):
    """
    Opens the filters window in hideout mode.

    Args:
    - logger: A logger object.

    Returns:
    - True if the filters window was successfully opened.
    - False otherwise.
    """
    start_time = time.time()
    click(328, 87, clicks=3, interval=0.5)
    time.sleep(0.33)
    if (
        hideout_mode_orientate_filters_window(logger, start_time=start_time)
        == "restart"
    ):
        return False
    return True


def hideout_mode_orientate_filters_window(logger, start_time=time.time()) -> bool:
    """
    Orients the filters window in hideout mode.

    Args:
    - logger: A logger object.
    - start_time: The time at which the function was called.

    Returns:
    - True if the filters window was successfully oriented.
    - False otherwise.
    """
    is_orientated = hideout_mode_check_filters_window_orientation()
    loops = 0
    while not is_orientated:
        time_taken = time.time() - start_time
        if time_taken > 23:
            return False
        loops += 1
        if loops > 10:
            open_filters_window(logger)
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

    return True


def set_hideout_mode_flea_filters(logger):
    """
    Sets the flea filters for price undercut recognition in hideout mode.

    Args:
    - logger: A logger object.

    Returns:
    - "restart" if the filters window could not be opened.
    - None otherwise.
    """
    operation_delay = 0.25

    logger.change_status("Setting the flea filters for price undercut recognition")

    # open filter window
    logger.change_status("Opening the filters window")
    if not open_filters_window(logger):
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
    """
    Gets the size of the BsgLauncher window.

    Returns:
    - A tuple containing the width and height of the window, in pixels.
    - False if the window cannot be found.
    """
    try:
        window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
        size = window.size
        return size
    except IndexError:
        return False


def cycle_hideout_tab():
    """
    Cycles to the next tab in the hideout menu.

    Returns:
    - None
    """
    click(40, 932)
    time.sleep(1)


def orientate_tarkov_client():
    """
    Resizes and moves the Tarkov client window to a specific size and position.

    Returns:
    - None
    """
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")[0]
    tark_window.moveTo(0, 0)
    tark_window.resizeTo(1299, 999)


def orientate_launcher():
    """
    Resizes and moves the BsgLauncher window to a specific size and position.

    Returns:
    - None
    """
    launcher_window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
    launcher_window.moveTo(0, 0)
    launcher_window.resizeTo(100, 100)


def get_terminal_res():
    """
    Gets the size of the terminal window.

    Returns:
    - A tuple containing the width and height of the window, in pixels.
    - False if the window cannot be found.
    """
    try:
        window = pygetwindow.getWindowsWithTitle(TERMINAL_NAME)[0]
        size = window.size
        return size
    except IndexError:
        return False


def buy_this_offer(logger):
    """
    Buys an item if an offer exists.

    Args:
    - logger: A logger object.

    Returns:
    - True if an item was bought.
    - False otherwise.
    """
    if check_if_offer_exists():
        # click purchase
        click(1186, 152)
        time.sleep(0.33)

        # click all
        click(773, 475)
        time.sleep(0.33)

        # press y to buy it
        pyautogui.press("y")

        logger.change_status("Bought an item")

        # sleep to avoid captcha
        time.sleep(7)
        return True
    return False


def check_if_offer_exists():
    """
    Checks if there is an offer available in the flea market.

    Returns:
    - True if an offer exists.
    - False otherwise.
    """
    iar = numpy.asarray(screenshot())
    for x_coord in range(1148, 1236):
        this_pixel = iar[152][x_coord]
        if pixel_is_equal(this_pixel, [151, 149, 137], tol=20):
            return True
    return False


def set_specific_snipe_flea_filters(logger, price, print_mode):
    """
    Sets the flea market filters for price undercut recognition.

    Args:
    - logger: A logger object.
    - price: The price to set the filter to.
    - print_mode: A boolean indicating whether to print status messages.

    Returns:
    - None.
    """
    operation_delay = 0.15

    if print_mode:
        logger.change_status("Setting the flea filters for price undercut recognition")

    # open filter window
    if print_mode:
        logger.change_status("Opening the filters window")
    open_filters_window(logger)
    time.sleep(operation_delay)

    # click currency dropdown
    if print_mode:
        logger.change_status("Filtering by roubles.")
    click(113, 62)
    time.sleep(operation_delay)

    # click RUB from dropdown
    click(124, 100)
    time.sleep(operation_delay)

    # click 'display offers from' dropdown
    if print_mode:
        logger.change_status("Filtering by player sales only.")
    click(171, 188)
    time.sleep(operation_delay)

    # click players from dropdown
    click(179, 250)
    time.sleep(operation_delay)

    # click 'condition from:' text input box
    click(131, 123)
    time.sleep(operation_delay)

    # write 100 in 'condition from:' text box
    pyautogui.typewrite("100")
    time.sleep(operation_delay)

    # click price input
    click(226, 84)
    time.sleep(operation_delay)

    # type price
    pyautogui.typewrite(str(price))
    time.sleep(operation_delay)

    # click OK
    if print_mode:
        logger.change_status("Clicking OK in filters tab.")
    click(83, 272)
    time.sleep(operation_delay)


def search_for_item(name):
    """
    Searches for an item in the flea market.

    Args:
    - name: The name of the item to search for.

    Returns:
    - "no results" if no search results were found.
    - None otherwise.
    """
    # click search bar in flea tab
    click(x=157, y=113)
    time.sleep(0.1)

    # write item name
    pyautogui.typewrite(name)
    time.sleep(4)

    # check if any search results appeared
    if not check_for_search_results():
        return "no results"

    # click item in search results page
    click(134, 142)

    # wait
    time.sleep(1)


def check_for_search_results() -> bool:
    """
    Check if there are any search results in the flea market.
    """
    iar = numpy.asarray(screenshot())
    for i in range(60, 110):
        this_pixel = iar[138][i]
        if pixel_is_equal([211, 210, 199], this_pixel, tol=20):
            return True

    for i in range(60, 130):
        this_pixel = iar[142][i]
        if pixel_is_equal([197, 195, 178], this_pixel, tol=20):
            return True

    return False


def orientate_terminal() -> bool:
    """
    Orientate the terminal window.
    """
    try:
        terminal_res = get_terminal_res()
        width, _ = terminal_res
        terminal_window = pygetwindow.getWindowsWithTitle(TERMINAL_NAME)[0]
        terminal_window.moveTo(pyautogui.size()[0] - width, 0)
    except:
        pass


def get_to_hideout() -> bool:
    """
    Navigate to the hideout.
    """
    print("Getting to hideout")

    orientate_tarkov_client()
    start_time = time.time()

    while not check_if_in_hideout():
        if time.time() - start_time > 60:
            return False

        click(x=150, y=977)
        time.sleep(5)
    print("At hideout")

    return True


def check_if_in_hideout() -> bool:
    """
    Check if the player is currently in the hideout.
    """
    iar = numpy.asarray(screenshot())
    hideout_pixel = iar[979][183]
    if pixel_is_equal(hideout_pixel, [159, 157, 144], tol=30):
        return True
    return False


def check_if_in_hideout_cycle_mode() -> bool:
    """
    Check if the player is currently in hideout cycle mode.
    """
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
    """
    Take a screenshot of the specified region.
    """
    if region is None:
        return pyautogui.screenshot()  # type: ignore
    return pyautogui.screenshot(region=region)  # type: ignore


def set_cordura_flea_filters(logger):
    """
    Set the flea filters for price undercut recognition.
    """
    operation_delay = 0.25

    logger.change_status("Setting the flea filters for price undercut recognition")

    # open filter window
    logger.change_status("Opening the filters window")
    if not open_filters_window(logger):
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


def reset_filters(logger):
    """
    Reset the flea filters.
    """
    open_filters_window(logger)

    # reset filters
    click(182, 273)
    time.sleep(0.33)

    # click OK
    click(85, 274)
    time.sleep(0.33)


# flea filters window
def find_filters_window() -> list:
    """
    Find the flea filters window.
    """
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
    return [] if coords is None else [coords[1] + 3, coords[0] + 3]


def check_filters_window_orientation() -> bool:
    """
    Check the orientation of the flea filters window.
    """
    coords = find_filters_window()
    if coords is None:
        return False
    value1 = abs(coords[0] - 24)
    value2 = abs(coords[1] - 35)
    return value1 <= 3 and value2 <= 3


def orientate_filters_window(logger):
    """
    Orientate the flea filters window.
    """
    is_orientated = check_filters_window_orientation()
    loops = 0
    while not is_orientated:
        loops += 1
        if loops > 10:
            open_filters_window(logger)
        logger.change_status("Orientating filters window.")
        coords = find_filters_window()
        if coords is not None:
            origin = pyautogui.position()
            pyautogui.moveTo(coords[0], coords[1], duration=0.1)
            time.sleep(0.33)
            pyautogui.dragTo(3, 3, duration=0.33)
            pyautogui.moveTo(origin[0], origin[1])
            time.sleep(0.33)
        is_orientated = check_filters_window_orientation()
    logger.change_status("Orientated filters window.")


def click(x, y, clicks=1, interval=0.0, duration=0.1, button="left") -> None:
    """
    Click the specified coordinates.
    """
    # get current mouse position
    origin = pyautogui.position()

    # move the mouse to the spot
    pyautogui.moveTo(x, y, duration=duration)

    # click it as many times as you're supposed to
    loops = 0
    while loops < clicks:
        pyautogui.click(x=x, y=y, button=button)
        loops += 1
        time.sleep(interval)

    # move mouse back to original position
    pyautogui.moveTo(origin[0], origin[1])


def check_if_on_flea_page() -> bool:
    """
    Check if the player is currently on the flea market page.
    """
    iar = numpy.asarray(screenshot())

    pix1 = iar[984][813]
    pix2 = iar[972][810]
    pix3 = iar[976][883]
    pix4 = iar[984][883]

    color_tan = [159, 157, 144]

    if not pixel_is_equal(pix1, color_tan, tol=25):
        return False
    if not pixel_is_equal(pix2, color_tan, tol=25):
        return False
    if not pixel_is_equal(pix3, color_tan, tol=25):
        return False
    if not pixel_is_equal(pix4, color_tan, tol=25):
        return False
    return True


def get_to_flea_tab(logger, print_mode=True):
    """
    Navigate to the flea market tab.
    """
    GET_TO_FLEA_PAGE_TIMEOUT = 60  # s
    get_to_flea_start_time = time.time()

    if print_mode:
        logger.change_status("Getting to flea tab")

    #close scav case coord
    click(1280,386)
    time.sleep(0.22)

    while time.time() - get_to_flea_start_time < GET_TO_FLEA_PAGE_TIMEOUT:
        if check_if_on_flea_page():
            if print_mode:
                logger.change_status("At flea tab")
            return True

        click(829, 977)
        time.sleep(5)

    logger.change_status("Failure getting to flea tab")
    return "restart"
