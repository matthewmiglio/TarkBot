import PySimpleGUI as sg

out_text = "" + "-Python Tarkov bot - Matthew Miglio ~Aug 2022\n\n"
out_text += (
    "-You MUST manually set tarkov to windowed and 4:3 BEFORE running the bot.\n"
)
# defining various things that r gonna be in the gui.
main_layout = [
    [sg.Text(out_text)],
    # buttons
    [sg.Button("Start"), sg.Button("Stop"), sg.Button("Help"), sg.Button("Donate")]
    # https://www.paypal.com/donate/?business=YE72ZEB3KWGVY&no_recurring=0&item_name=Support+my+projects%21&currency_code=USD
]
