import os


def get_graphics_config_file_path():
    dir = os.path.join(
        os.getenv("APPDATA"),
        "Battlestate Games",
        "Escape from Tarkov",
        "Settings",
        "Graphics.ini",
    )
    return dir


def change_fullscreenmode_line(mode: str):
    # get file path
    path = get_graphics_config_file_path()

    # parse the mode input
    newlines_dict = {
        "fullscreen": '    "FullScreenMode": 0,\n',
        "borderless": '    "FullScreenMode": 1,\n',
        "windowed": '    "FullScreenMode": 2,\n',
    }
    new_line = newlines_dict[mode]

    # read the lines, then replace the line in question
    with open(path, "r") as file:
        # Get all the lines
        lines = file.readlines()

        # Go through every line in the file, storing the good lines as we go
        good_lines = []
        for line in lines:
            # If at the line in question, replace line with new config
            if '"FullScreenMode":' in line:
                line = new_line

            # Add the current line to good lines
            good_lines.append(line)

    # Open the file again in write mode to update its contents
    with open(path, "w") as file:
        # Write the new lines to the file
        file.writelines(good_lines)


if __name__ == "__main__":
    change_fullscreenmode_line(
        input(f"\nSelect a mode:\nfullscreen\nborderless\nwindowed\n")
    )
