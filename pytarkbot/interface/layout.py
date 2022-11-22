import PySimpleGUI as sg

from .stats import stat_box, stats

out_text = """Tarkov settings must match the following:
    - windowed mode
    - 4:3 aspect ratio
    - smaller than 1280x960 resolution
Program must be run as administrator.

The top 40 rows will be sold on the flea."""

# defining various things that r gonna be in the gui.
main_layout = [
    [
        sg.Frame(
            layout=[[sg.Text(out_text, size=(35, 7))]],
            title="Info",
            relief=sg.RELIEF_SUNKEN,
        ),
        sg.Frame(layout=stats, title="Stats", relief=sg.RELIEF_SUNKEN),
    ],
    [
        stat_box("time_since_start", size=(9, 1)),
        sg.InputText(
            "Idle",
            key="current_status",
            use_readonly_for_disable=True,
            disabled=True,
            text_color="blue",
            size=(60, 1),
        ),
    ],
    # buttons
    [
        sg.Button("Start"),
        sg.Button("Stop", disabled=True),
        sg.Button("Help"),
        sg.Button("Issues?", key="issues-link"),
        sg.Button("Donate"),
        sg.Text("Matthew Miglio, Martin Miglio - Nov 2022"),
    ],
    # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
]

# a list of all the keys that contain user configuration
user_config_keys = []

# list of button and checkbox keys to disable when the bot is running
disable_keys = user_config_keys + ["Start"]
