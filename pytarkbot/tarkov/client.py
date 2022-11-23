import time

import numpy
import pyautogui
import pygetwindow

from pytarkbot.detection import pixel_is_equal

pyautogui.FAILSAFE = False


def orientate_tarkov_client(logger):
    logger.change_status("Orientating tarkov client.")
    tark_window = pygetwindow.getWindowsWithTitle("EscapeFromTarkov")[0]
    tark_window.moveTo(0, 0)
    tark_window.resizeTo(1299, 999)


def orientate_launcher():
    launcher_window = pygetwindow.getWindowsWithTitle("BsgLauncher")[0]
    launcher_window.moveTo(0, 0)
    launcher_window.resizeTo(1122, 744)


def orientate_terminal():
    try:
        terminal_window = pygetwindow.getWindowsWithTitle("Py-TarkBot")[0]
        terminal_window.moveTo(1292, 0)
    except:
        print("Couldnt orientate terminal.")


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
