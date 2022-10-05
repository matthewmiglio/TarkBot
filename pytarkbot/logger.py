import time


class Logger:
    """Handles creating and reading logs
    """

    def __init__(self):
        """Logger init
        """
        self.start_time = time.time()
        self.restarts = 0
        self.roubles_made = 0
        self.sale_attempts = 0
        self.item_sold = 0
        self.crafts_completed = 0
        self.hideout_rotations = 0
        self.snipes = 0


    def make_timestamp(self):
        """creates a time stamp for log output

        Returns:
            str: log time stamp
        """
        output_time = time.time() - self.start_time
        output_time = int(output_time)

        time_str = str(self.convert_int_to_time(output_time))

        output_string = time_str

        return output_string

    def make_output_string(self):
        """creates scoreboard for log output

        Returns:
            str: log scoreboard
        """

        restart_str = str(self.restarts) + " restarts"
        roubles_made_str = str(self.roubles_made) + " profit"
        items_sold_str = str(self.item_sold) + " items sold"
        crafts_completed_str = str(self.crafts_completed) + " crafts completed"
        hideout_rotations_str = str(
            self.hideout_rotations) + " hideout rotations"
        flea_success_str = str(self.make_flea_success_rate()) + "%" + " success rate fleaing items"
        snipes_str=str(self.snipes)+" snipes"

        gap_str = "|"
        return gap_str + restart_str + gap_str + roubles_made_str + gap_str + items_sold_str + gap_str + flea_success_str + gap_str + snipes_str + gap_str

    def convert_int_to_time(self, seconds):
        """convert epoch to time

        Args:
            seconds (int): epoch time in int

        Returns:
            str: human readable time
        """
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def log(self, message):
        """add message to log

        Args:
            message (str): message to add
        """
        print(f"{self.make_timestamp()} - {self.make_output_string()} : {message}")

    def add_restart(self):
        """add restart to log
        """
        self.restarts += 1

    def add_roubles_made(self, amount):
        self.roubles_made = self.roubles_made + amount

    def add_item_sold(self):
        self.item_sold = self.item_sold + 1

    def add_craft_completed(self):
        self.crafts_completed = self.crafts_completed + 1

    def add_hideout_rotation(self):
        self.hideout_rotations = self.hideout_rotations + 1

    def make_flea_success_rate(self):
        if (self.sale_attempts==0): return 0
        if (self.item_sold == 0): return 0
        calculation= (self.item_sold / self.sale_attempts) * 100
        return int(calculation)
    
    def add_flea_sale_attempt(self):
        self.sale_attempts = self.sale_attempts + 1
        
    def add_snipe(self):
        self.snipes = self.snipes + 1