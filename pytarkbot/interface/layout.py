import PySimpleGUI as sg

from .stats import stat_box, stats

out_text = """Tarkov settings must match the following:
    - windowed mode
    - 4:3 aspect ratio
    - smaller than 1280x960 resolution
Program must be run as administrator.

Matthew Miglio, Martin Miglio - Nov 2022"""

# defining various things that r gonna be in the gui.
main_layout = [
    [
        sg.Frame(
            layout=[[sg.Text(out_text, size=(35, 7))]],
            title="Info",
            relief=sg.RELIEF_SUNKEN,
            expand_y=True,
        ),
        sg.Frame(layout=stats, title="Stats", relief=sg.RELIEF_SUNKEN),
    ],
    # buttons
    [
        sg.Frame(
            layout=[
                [
                    sg.Text("Number of rows to target in your stash:"),
                    sg.Slider(
                        range=(1, 11),
                        default_value=11,
                        key="rows_to_target",
                        orientation="horizontal",
                        size=(26, None),
                        relief=sg.RELIEF_FLAT,
                        enable_events=True,
                    ),
                ],
                [
                    sg.Text("Remove Offers Timer:"),
                    sg.Combo(
                        ["1m", "2m", "5m", "10m"],
                        key="remove_offers_timer",
                        default_value="5m",
                        enable_events=True,
                    ),
                ],
                [
                    sg.Column(
                        [
                            [
                                sg.Button("Start"),
                                sg.Button("Stop", disabled=True),
                                sg.Checkbox(
                                    text="Auto-start",
                                    key="autostart",
                                    default=False,
                                    enable_events=True,
                                ),
                            ]
                        ],
                        element_justification="left",
                        expand_x=True,
                    ),
                    sg.Column(
                        [
                            [
                                sg.Button("Help"),
                                sg.Button("Issues?", key="issues-link"),
                                sg.Button("Donate"),
                            ]
                        ],
                        element_justification="right",
                        expand_x=True,
                    ),
                ],
            ],
            title="Controls",
            relief=sg.RELIEF_SUNKEN,
            expand_x=True,
        ),
    ],
    [
        stat_box("time_since_start", size=(7, 1)),
        sg.InputText(
            "Idle",
            key="current_status",
            use_readonly_for_disable=True,
            disabled=True,
            text_color="blue",
            expand_x=True,
        ),
    ],
    # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
]

# a list of all the keys that contain user configuration
# user_config_keys = ["rows_to_target", "remove_offers_timer", "autostart"]
user_config_keys = [
    "rows_to_target",
    "remove_offers_timer",
]

# list of button and checkbox keys to disable when the bot is running
disable_keys = user_config_keys + ["Start"]
