import PySimpleGUI as sg

from .theme import THEME

sg.theme(THEME)


def stat_box(stat_name: str, size=(5, 1)):
    return sg.Text(
        "0",
        key=stat_name,
        relief=sg.RELIEF_SUNKEN,
        text_color="blue",
        size=size,
    )


stats_title = [
    [
        [
            sg.Text("Starting Money: "),
        ],
        [
            sg.Text("Current Money: "),
        ],
        [
            sg.Text("Fee Total: "),
        ],
        [
            sg.Text("Items Sold: "),
        ],
        [
            sg.Text("Roubles Made: "),
        ],
    ],
    [
        [
            sg.Text("Sale Attempts: "),
        ],
        [
            sg.Text("Offers Removed: "),
        ],
        [
            sg.Text("Success Rate: "),
        ],
        [
            sg.Text("Restarts: "),
        ],
    ],
]


stats_values = [
    [
        [
            stat_box("starting_money"),
        ],
        [
            stat_box("current_money"),
        ],
        [
            stat_box("fee_total"),
        ],
        [
            stat_box("item_sold"),
        ],
        [
            stat_box("roubles_made"),
        ],
    ],
    [
        [
            stat_box("sale_attempts"),
        ],
        [
            stat_box("offers_removed"),
        ],
        [
            stat_box("success_rate"),
        ],
        [
            stat_box("restarts"),
        ],
    ],
]

stats = [
    [
        sg.Column(stats_title[0], element_justification="right"),
        sg.Column(stats_values[0], element_justification="left"),
        sg.Column(stats_title[1], element_justification="right"),
        sg.Column(stats_values[1], element_justification="left"),
    ]
]
