import time
from os import environ
from os.path import dirname, join

import numpy
import pyautogui
import pygetwindow
import pytesseract
import win32com.client as win32
import win32gui
from PIL import Image
from screeninfo import get_monitors

from pytarkbot.detection import (
    coords_is_equal,
    find_references,
    get_first_location,
    pixel_is_equal,
)


def orientate_tarkov_client(logger):
    logger.change_status("Orientating tarkov client.")
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")[0]
    tark_window.moveTo(0, 0)
    tark_window.resizeTo(1299, 999)


def move_tarkov_client_to_topleft():
    for n in range(6):
        if (n % 2) == 0:
            print("Moving tark window")

        current_coord = find_eft_window()
        if current_coord is None:
            return
        current_coord = [current_coord[0] + 18, current_coord[1] - 2]
        pyautogui.moveTo(current_coord[0], current_coord[1], duration=0.33)
        time.sleep(0.33)
        pyautogui.dragTo(33, 6, duration=1)
    print("Done moving tark window.")


def move_window_to_top_left(window_name):
    window = pyautogui.getWindowsWithTitle(window_name)[0]  # type: ignore
    window.moveTo(0, 0)


def orientate_launcher():
    launcher_window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
    launcher_window.moveTo(0, 0)
    launcher_window.resizeTo(1122, 744)


def get_screen_resolution():
    monitor_1 = get_monitors()[0]
    w = monitor_1.width
    h = monitor_1.height
    return [w, h]


def orientate_terminal():
    try:
        terminal_window = pygetwindow.getWindowsWithTitle("Py-TarkBot")[0]
        terminal_window.moveTo(1292, 0)
    except:
        print("Couldnt orientate terminal.")


def combine_duplicate_coords(coords_list, tolerance=5):
    # method will take an array of coords ([x,y]) and combine duplicates
    # according to a certain tolerance.

    new_coords_list = []

    # loop vars
    total_coords_in_list = len(coords_list)
    # loop through every coord in coords_list
    for index in range(total_coords_in_list):
        # get current coord
        current_coord = coords_list[index]

        # if current_coord doesnt exist in new_coords_list make new coord in
        # new coords list
        if not (
            check_if_coord_in_coord_list(
                current_coord, new_coords_list, tolerance=tolerance
            )
        ):
            new_coords_list.append(current_coord)

    return new_coords_list


def check_if_coord_in_coord_list(coord, coord_list, tolerance=50):
    total_coords_in_coords_list = len(coord_list)

    for index in range(total_coords_in_coords_list):
        # get curent coord
        current_coord = coord_list[index]

        # compare current coord with coord in question
        if coords_is_equal(current_coord, coord, tol=tolerance):
            return True

    # if we make it out of the loop without ever returning True then that
    # means the coord is unique
    return False


def find_all_pixel_coords(region, color, image=None, tol=15):
    # searches entire region for pixel and returns a list of the coords of
    # every positive pixel.

    # make list of coords
    coords_list = []

    # make image-as-array
    iar = numpy.asarray(screenshot()) if image is None else numpy.asarray(image)
    x_coord = region[0]
    while x_coord < x_coord + region[2]:
        y_coord = region[1]
        while y_coord < y_coord + region[3]:
            # for each pixel in region
            iar_pix = iar[y_coord][x_coord]
            current_pix = [iar_pix[0], iar_pix[1], iar_pix[2]]
            current_coord = [x_coord, y_coord]

            # add all postiive pixels to return list
            if pixel_is_equal(color, current_pix, tol=tol):
                coords_list.append(current_coord)

            y_coord = y_coord + 1
        x_coord = x_coord + 1

    return coords_list


def find_all_pixel_colors(region, color, image=None):
    # searches entire region for pixel and returns a list of the coords of
    # every positive pixel.

    # make list of coords
    colors_list = []

    # make image-as-array
    iar = numpy.asarray(screenshot()) if image is None else numpy.asarray(image)
    x_coord = region[0]
    while x_coord < x_coord + region[2]:
        y_coord = region[1]
        while y_coord < y_coord + region[3]:
            # for each pixel in region
            iar_pix = iar[y_coord][x_coord]
            current_pix = [iar_pix[0], iar_pix[1], iar_pix[2]]
            # current_coord=[x_coord,y_coord]

            # add all postiive pixels to return list
            if pixel_is_equal(color, current_pix, tol=15):
                colors_list.append(current_pix)

            y_coord = y_coord + 1
        x_coord = x_coord + 1

    return colors_list


def screenshot(region=(0, 0, 1400, 1400)):
    if region is None:
        return pyautogui.screenshot()  # type: ignore
    return pyautogui.screenshot(region=region)  # type: ignore


def string_to_chars_only(string):
    out_string = ""
    for element in string:
        if element.isalpha():
            out_string = out_string + element
    return out_string


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


def get_image(folder, name):
    top_level = dirname(__file__)
    reference_folder = join(top_level, "reference_images")
    return Image.open(join(reference_folder, folder, name))


def find_all_pixels_not_equal_to(region, color, image=None, tol=15):
    # make iar
    if image is None:
        iar = numpy.asarray(screenshot(region))
    else:
        iar = numpy.asarray(image)

    # make return list
    coords_list = []

    # loop through iar
    sentinel = [color[0], color[1], color[2]]
    width = iar.shape[1]
    height = iar.shape[0]
    x_coord = 0
    while x_coord < width:
        y_coord = 0
        while y_coord < height:
            current_pixel = iar[y_coord][x_coord]
            if not pixel_is_equal(current_pixel, sentinel, tol=tol):
                current_coord = [x_coord, y_coord]
                coords_list.append(current_coord)

            y_coord += 1
        x_coord += 1

    return coords_list


def find_all_pixels(region):
    # make iar
    iar = numpy.asarray(screenshot(region))

    # return var
    pix_list = []

    # loop vars
    x_coord = 0
    while x_coord < region[2]:
        y_coord = 0
        while y_coord < region[3]:
            current_pix = iar[y_coord][x_coord]
            current_pix = [current_pix[0], current_pix[1], current_pix[2]]
            pix_list.append(current_pix)

            y_coord += 1
        x_coord += 1

    return pix_list


def calculate_avg_pixel(pix_list):
    # collect as we loop
    r_total = 0
    g_total = 0
    b_total = 0
    total_pixels = len(pix_list)

    for index in range(total_pixels):
        current_pix = pix_list[index]
        r_total = r_total + current_pix[0]
        g_total = g_total + current_pix[1]
        b_total = b_total + current_pix[2]

    # make return pixel
    r_avg = int(r_total / total_pixels)
    g_avg = int(g_total / total_pixels)
    b_avg = int(b_total / total_pixels)
    return [r_avg, g_avg, b_avg]


def windowEnumerationHandler(hwnd, top_windows):
    top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))


def get_window_size(window_name):
    title = window_name  # find first window with this title
    top_windows = []  # all open windows
    win32gui.EnumWindows(windowEnumerationHandler, top_windows)

    winlst = [i for i in top_windows if i[1] == title]
    hwnd = winlst[0][0]  # first window with title, get hwnd id
    shell = win32.Dispatch("WScript.Shell")  # set focus on desktop
    shell.SendKeys("%")  # Alt key,  send key
    # rect = win32gui.GetWindowRect(hwnd)
    x0, y0, x1, y1 = win32gui.GetWindowRect(hwnd)
    w = x1 - x0
    h = y1 - y0

    return [w, h]


def resize_window(window_name, resize):
    # windown name gotta be a string
    # resize gotta be a 1x2 ar like [width,height]
    title = window_name  # find first window with this title
    top_windows = []  # all open windows
    win32gui.EnumWindows(windowEnumerationHandler, top_windows)

    winlst = [i for i in top_windows if i[1] == title]
    hwnd = winlst[0][0]  # first window with title, get hwnd id
    shell = win32.Dispatch("WScript.Shell")  # set focus on desktop
    shell.SendKeys("%")  # Alt key,  send key
    # rect = win32gui.GetWindowRect(hwnd)
    x0, y0, _, _ = win32gui.GetWindowRect(hwnd)
    # w = x1 - x0
    # h = y1 - y0

    win32gui.MoveWindow(hwnd, x0, y0, resize[0], resize[1], True)


def move_window(window_name, coord):
    window = pygetwindow.getWindowsWithTitle(window_name)[0]
    window.moveTo(coord[0], coord[1])


def find_eft_window():

    current_image = screenshot()
    reference_folder = "find_eft_window"
    references = [
        "5.png",
    ]

    locations = find_references(
        screenshot=current_image,
        folder=reference_folder,
        names=references,
        tolerance=0.99,
    )
    coord = get_first_location(locations)
    return None if coord is None else [coord[1], coord[0]]


def img_to_txt(image):
    pytesseract.pytesseract.tesseract_cmd = environ["TESSERACT_PATH"]
    config = "-l eng --oem 3 --psm 9"
    return pytesseract.image_to_string(image, config=config)


def img_to_txt_numbers_only(image):
    pytesseract.pytesseract.tesseract_cmd = environ["TESSERACT_PATH"]
    # config = ('--oem 3 --psm 10 tessedict_char_whitelist=0123456789P')
    return pytesseract.image_to_string(image, config="digits --psm 7")


def img_to_txt_single_char(image):
    pytesseract.pytesseract.tesseract_cmd = environ["TESSERACT_PATH"]
    # config = ('--oem 3 --psm 10 tessedict_char_whitelist=0123456789P')
    return pytesseract.image_to_string(image, config="--psm 10")
