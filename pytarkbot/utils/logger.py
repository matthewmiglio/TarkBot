import time
from functools import wraps
from queue import Queue
from pytarkbot.utils.file_logging import make_new_log_dir, add_line_to_log_file


class Logger:
    """Handles logging statistics"""

    def __init__(self, queue=None, timed=True):
        """Logger init"""

        # bot vars/stats
        self.queue: Queue[dict[str, str | int]] = Queue() if queue is None else queue
        self.start_time = time.time() if timed else None
        self.status = "Idle"
        self.restarts = 0
        self.autorestarts = 0
        self.errored = False
        self.log_file_path = make_new_log_dir()

        # flea sell mode stats
        self.roubles_made = 0
        self.sale_attempts = 0
        self.item_sold = 0
        self.offers_removed = 0

        # hideout mode stats
        self.workbench_starts = 0
        self.workbench_collects = 0
        self.bitcoin_collects = 0
        self.lavatory_starts = 0
        self.lavatory_collects = 0
        self.medstation_starts = 0
        self.medstation_collects = 0
        self.water_filters = 0
        self.water_collects = 0
        self.scav_case_starts = 0
        self.scav_case_collects = 0
        self.hideout_profit = 0
        self.stations_visited = 0

        # snipebot stats
        self.ruble_snipes = 0
        self.specific_snipes = 0

    def _update_queue(self):
        """updates the queue with a dictionary of mutable statistics"""
        if self.queue is None:
            return

        statistics: dict[str, str | int] = {
            # bot stats
            "restarts": self.restarts,
            "autorestarts": self.autorestarts,
            # flea mode stats
            "item_sold": self.item_sold,
            "roubles_made": self.format_money(self.roubles_made),
            "sale_attempts": self.sale_attempts,
            "success_rate": self.calc_success_rate(),
            "offers_removed": self.offers_removed,
            # hideout mode stats
            "workbench_starts": self.workbench_starts,
            "workbench_collects": self.workbench_collects,
            "bitcoin_collects": self.bitcoin_collects,
            "lavatory_starts": self.lavatory_starts,
            "lavatory_collects": self.lavatory_collects,
            "medstation_starts": self.medstation_starts,
            "medstation_collects": self.medstation_collects,
            "water_filters": self.water_filters,
            "water_collects": self.water_collects,
            "scav_case_starts": self.scav_case_starts,
            "scav_case_collects": self.scav_case_collects,
            "hideout_profit": self.hideout_profit,
            "station_time": self.calculate_station_time(),
            # snipebot stats
            "ruble_snipes": self.ruble_snipes,
            "specific_snipes": self.specific_snipes,
        }
        self.queue.put(statistics)

    @staticmethod
    def _updates_queue(func):
        """decorator to specify functions which update the queue with statistics"""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self._update_queue()  # pylint: disable=protected-access
            return result

        return wrapper

    @_updates_queue
    def error(self, message: str):
        """logs an error"""
        self.errored = True
        self.status = f"Error: {message}"
        print(f"Error: {message}")

    @_updates_queue
    def change_status(self, message):
        self.status = message
        add_line_to_log_file(self.log_file_path, message)
        print(message)

    @_updates_queue
    def add_profit(self, amount):
        self.hideout_profit += amount

    @_updates_queue
    def add_restart(self):
        self.restarts += 1

    @_updates_queue
    def add_roubles_made(self, amount):
        self.roubles_made = self.roubles_made + amount

    @_updates_queue
    def add_offer_removed(self):
        self.offers_removed += 1

    @_updates_queue
    def add_item_sold(self):
        self.item_sold = self.item_sold + 1

    @_updates_queue
    def add_flea_sale_attempt(self):
        self.sale_attempts = self.sale_attempts + 1

    @staticmethod
    def format_money(money: int | str) -> str:
        try:
            money = abs(int(money))
        except ValueError:
            return str(money)
        if money < 1000:
            return str(money)
        if money < 1000000:
            return f"{(money / 1000):.0f}k"
        return f"{(money / 1000000):.2f}m"

    def calc_success_rate(self) -> str:
        if self.sale_attempts == 0 or self.item_sold == 0:
            calculation = 0
        else:
            calculation = (self.item_sold / self.sale_attempts) * 100
        return f"{calculation:.1f}%"

    def calculate_station_time(self):
        stations_visited = self.stations_visited

        if stations_visited == 0 or self.start_time is None:
            return "0 s"

        time_taken = (time.time() - (self.start_time)) - 40

        time_per_station = time_taken / stations_visited

        return str(time_per_station)[:5]

    @_updates_queue
    def add_autorestart(self):
        self.autorestarts += 1

    @_updates_queue
    def set_job_count(self, amount):
        self.job_count += amount

    @_updates_queue
    def add_station_visited(self):
        self.stations_visited += 1

    @_updates_queue
    def add_workbench_start(self):
        self.workbench_starts += 1

    @_updates_queue
    def add_workbench_collect(self):
        self.workbench_collects += 1

    @_updates_queue
    def add_bitcoin_collect(self):
        self.bitcoin_collects += 1

    @_updates_queue
    def add_lavatory_start(self):
        self.lavatory_starts += 1

    @_updates_queue
    def add_lavatory_collect(self):
        self.lavatory_collects += 1

    @_updates_queue
    def add_medstation_start(self):
        self.medstation_starts += 1

    @_updates_queue
    def add_medstation_collect(self):
        self.medstation_collects += 1

    @_updates_queue
    def add_water_filter(self):
        self.water_filters += 1

    @_updates_queue
    def add_water_collect(self):
        self.water_collects += 1

    @_updates_queue
    def add_scav_case_start(self):
        self.scav_case_starts += 1

    @_updates_queue
    def add_scav_case_collect(self):
        self.scav_case_collects += 1

    @_updates_queue
    def add_ruble_snipe(self):
        self.ruble_snipes += 1

    @_updates_queue
    def add_specific_snipe(self):
        self.specific_snipes += 1
