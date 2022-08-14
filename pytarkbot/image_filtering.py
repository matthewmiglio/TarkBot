from image_rec import find_references, get_first_location


def look_for_ruble_symbol(ss):
    current_image = ss
    reference_folder = "ruble_symbol"
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
        tolerance=0.97
    )
    coords = get_first_location(locations)
    if coords is None:
        return None
    return [coords[1], coords[0]]
