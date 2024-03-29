"""
This module contains functions for detecting and locating images within a screenshot.
"""

import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from os.path import dirname, join
from typing import Union

import cv2
import numpy as np
from joblib import Parallel, delayed
from PIL import Image


def coords_is_equal(coords_a, coords_b, tol=30):
    """
    Check if two sets of coordinates are equal within a certain tolerance.

    Args:
        coords_a (list[int]): First set of coordinates.
        coords_b (list[int]): Second set of coordinates.
        tol (int, optional): Tolerance for equality. Defaults to 30.

    Returns:
        bool: True if the coordinates are equal within the tolerance, False otherwise.
        None: If either set of coordinates is None.
    """
    if (coords_a is None) or (coords_b is None):
        return None
    coords_1_diff = abs(coords_a[0] - coords_b[0])
    coords_2_diff = abs(coords_a[1] - coords_b[1])
    return coords_1_diff < tol and coords_2_diff < tol


def get_first_location(locations: list[Union[list[int], None]], flip=False):
    """get the first location from a list of locations

    Args:
        locations (list[list[int]]): list of locations
        flip (bool, optional): flip coordinates. Defaults to False.

    Returns:
        list[int]: location
    """
    return next(
        (
            [location[1], location[0]] if flip else location
            for location in locations
            if location is not None
        ),
        None,
    )


def check_for_location(locations: list[Union[list[int], None]]):
    """check for a location

    Args:
        locations (list[list[int]]): _description_

    Returns:
        bool: if location is found or not
    """
    return any(location is not None for location in locations)


def find_references(
    screenshot: Union[np.ndarray, Image.Image],
    folder: str,
    names: list[str],
    tolerance=0.97,
) -> list[Union[list[int], None]]:
    """find reference images in a screenshot

    Args:
        screenshot (Union[np.ndarray, Image.Image]): find references in screenshot
        folder (str): folder to find references (from within reference_images)
        names (list[str]): names of references
        tolerance (float, optional): tolerance. Defaults to 0.97.

    Returns:
        list[Union[list[int], None]: coordinate locations
    """
    num_cores = multiprocessing.cpu_count()
    with ThreadPoolExecutor(num_cores) as ex:
        futures = [
            ex.submit(find_reference, screenshot, folder, name, tolerance)
            for name in names
        ]
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                return [result]
    return [None]


def find_all_references(
    screenshot: Union[np.ndarray, Image.Image],
    folder: str,
    names: list[str],
    tolerance=0.97,
):
    """find all reference images in a screenshot

    Args:
        screenshot (Union[np.ndarray, Image.Image]): find references in screenshot
        folder (str): folder to find references (from within reference_images)
        names (list[str]): names of references
        tolerance (float, optional): tolerance. Defaults to 0.97.

    Returns:
        list[Union[list[int],None]]: coordinate locations
    """
    num_cores = multiprocessing.cpu_count()

    return Parallel(n_jobs=num_cores, prefer="threads")(
        delayed(find_reference)(screenshot, folder, name, tolerance) for name in names
    )


def find_reference(
    screenshot: Union[np.ndarray, Image.Image], folder: str, name: str, tolerance=0.97
):
    """find a reference image in a screenshot

    Args:
        screenshot (Union[np.ndarray, Image.Image]): find reference in screenshot
        folder (str): folder to find reference (from within reference_images)
        name (str): name of reference
        tolerance (float, optional): tolerance. Defaults to 0.97.

    Returns:
        Union[list[int], None]: coordinate location
    """
    top_level = dirname(__file__)
    reference_folder = join(top_level, "reference_images")

    return compare_images(
        screenshot, Image.open(join(reference_folder, folder, name)), tolerance
    )


def pixel_is_equal(pix1, pix2, tol):
    """check pixel equality

    Args:
        pix1 (list[int]): [R,G,B] pixel
        pix2 (list[int]): [R,G,B] pixel
        tol (float): tolerance

    Returns:
        bool: are pixels equal
    """
    diff_r = abs(pix1[0] - pix2[0])
    diff_g = abs(pix1[1] - pix2[1])
    diff_b = abs(pix1[2] - pix2[2])
    return (diff_r < tol) and (diff_g < tol) and (diff_b < tol)


def compare_images(
    image: Union[np.ndarray, Image.Image],
    template: Union[np.ndarray, Image.Image],
    threshold=0.8,
):
    """detects pixel location of a template in an image
    Args:
        image (Union[np.ndarray, Image.Image]): image to find template within
        template (Union[np.ndarray, Image.Image]): template image to match to
        threshold (float, optional): matching threshold. defaults to 0.8
    Returns:
        Union[list[int], None]: a list of pixel location (x,y)
    """

    # show template
    # template.show()

    # Convert image to np.array

    image = np.array(image)
    template = np.array(template)

    # Convert image colors
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)  # pylint: disable=no-member
    template_gray = cv2.cvtColor(
        template, cv2.COLOR_RGB2GRAY
    )  # pylint: disable=no-member

    # Perform match operations.
    res = cv2.matchTemplate(
        img_gray, template_gray, cv2.TM_CCOEFF_NORMED
    )  # pylint: disable=no-member

    # Store the coordinates of matched area in a numpy array
    loc = np.where(res >= threshold)  # type: ignore

    return None if len(loc[0]) != 1 else [int(loc[0][0]), int(loc[1][0])]


def make_reference_image_list(file_name):
    """Creates a list of reference images for a given file name

    Args:
        file_name (str): Name of the file to create reference images for

    Returns:
        list[str]: List of reference image names
    """
    reference_image_list = []

    size = get_file_count(file_name)

    for i in range(size):
        i = i + 1
        image_name = f"{i}.png"
        reference_image_list.append(image_name)

    return reference_image_list


def get_file_count(folder):
    """Method to return the amount of a files in a given directory

    Args:
        directory (str): Directory to count files in

    Returns:
        int: Amount of files in the given directory
    """
    directory = dirname(__file__)
    directory = join(directory, "reference_images", folder)

    return sum(len(files) for root_dir, cur_dir, files in os.walk(directory))
