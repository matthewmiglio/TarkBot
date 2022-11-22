from pytarkbot.utils import setup_tesseract

setup_tesseract()

# pylint: disable=C0413
from .client import (
    calculate_avg_pixel,
    click,
    find_all_pixel_coords,
    find_all_pixels,
    img_to_txt,
    img_to_txt_numbers_only,
    orientate_launcher,
    orientate_tarkov_client,
    orientate_terminal,
    screenshot,
)
from .launcher import restart_tarkov

__all__ = [
    "orientate_terminal",
    "calculate_avg_pixel",
    "click",
    "find_all_pixel_coords",
    "find_all_pixels",
    "img_to_txt",
    "img_to_txt_numbers_only",
    "screenshot",
    "orientate_launcher",
    "orientate_tarkov_client",
    "restart_tarkov",
]
