import time
from functools import wraps
from queue import Queue


class Logger:
    """Handles logging statistics"""

    def __init__(self, queue=None):
        """Logger init"""

        self.queue: Queue[dict[str, str | int]] = Queue() if queue is None else queue

        self.start_time = time.time()
        self.status = "Idle"
        self.restarts = 0
        self.roubles_made = 0
        self.sale_attempts = 0
        self.item_sold = 0

    def _update_queue(self):
        """updates the queue with a dictionary of mutable statistics"""
        if self.queue is None:
            return

        statistics: dict[str, str | int] = {
            "current_status": self.status,
            "time_since_start": self.calc_time_since_start(),
            "restarts": self.restarts,
            "item_sold": self.item_sold,
            "roubles_made": self.format_roubles_made(),
            "sale_attempts": self.sale_attempts,
            "success_rate": self.calc_success_rate(),
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
    def change_status(self, message):
        self.status = message
        print(message)

    @_updates_queue
    def add_restart(self):
        self.restarts += 1

    @_updates_queue
    def add_roubles_made(self, amount):
        self.roubles_made = self.roubles_made + amount

    @_updates_queue
    def add_item_sold(self):
        self.item_sold = self.item_sold + 1

    @_updates_queue
    def add_flea_sale_attempt(self):
        self.sale_attempts = self.sale_attempts + 1

    def format_roubles_made(self) -> str:
        if self.roubles_made < 1000:
            return str(self.roubles_made)
        if self.roubles_made < 1000000:
            return f"{(self.roubles_made / 1000):.0f}k"
        return f"{(self.roubles_made / 1000000):.2f}m"

    def calc_success_rate(self):
        if self.sale_attempts == 0 or self.item_sold == 0:
            calculation = 0
        else:
            calculation = (self.item_sold / self.sale_attempts) * 100
        return f"{calculation:.1f}%"

    def calc_time_since_start(self) -> str:
        hours, remainder = divmod(time.time() - self.start_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
