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
        sg.Text("Items Sold: "),
    ],
    [
        sg.Text("Roubles Made: "),
    ],
    [
        sg.Text("Sale Attempts: "),
    ],
    [
        sg.Text("Success Rate: "),
    ],
    [
        sg.Text("Restarts: "),
    ],
]

stats_values = [
    [
        stat_box("item_sold"),
    ],
    [
        stat_box("roubles_made"),
    ],
    [
        stat_box("sale_attempts"),
    ],
    [
        stat_box("success_rate"),
    ],
    [
        stat_box("restarts"),
    ],
]

stats = [
    [
        sg.Column(stats_title, element_justification="right"),
        sg.Column(stats_values, element_justification="left"),
    ]
]
