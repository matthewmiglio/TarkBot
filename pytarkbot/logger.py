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
        self.item_sold=0

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
        roubles_made_str=str(self.roubles_made)+" profit"
        items_sold_str=str(self.item_sold)+ " items sold"
        
        gap_str = "|"
        return gap_str + restart_str + gap_str + roubles_made_str + gap_str + items_sold_str + gap_str

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

    def add_roubles_made(self,amount):
        self.roubles_made = self.roubles_made + amount
        
    def add_item_sold(self):
        self.item_sold = self.item_sold + 1
        
        
    