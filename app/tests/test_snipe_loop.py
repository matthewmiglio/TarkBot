"""The snipe loop's decisions against a stand-in screen. No game needed.

Run:  python tests/test_snipe_loop.py

interact/snipe.py is replaced with a fake, so what is under test is the loop: does a cheap
offer get bought, does a dear one get left, does an unreadable price stop the pass rather than
being guessed at, does a Stop land part way through a sweep, and does a sweep whose filters
would not go on refuse to read the board at all.

Exits non-zero on the first thing that is wrong, because every one of these is a path that ends
in money leaving the stash.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import snipe_bot  # noqa: E402
from sell_bot import Stopped  # noqa: E402


class FakeBoard:
    """Stands in for interact/snipe.py. Every call is recorded, nothing touches a screen."""

    def __init__(self, price, buttons=1, filters=True, search=True, locked=False,
                 buy_lands=True, item_filter=False):
        self.price = price  # what read_price answers, or None for unreadable
        self.buttons = buttons  # how many offer rows the board is showing
        self.filters = filters
        self.search = search  # whether the search box can be found at all
        self.locked = locked  # whether the suggestion list shows a padlock
        self.buy_lands = buy_lands  # whether the balance actually moved after the confirm
        self.item_filter = item_filter  # whether a filter-by-item chip survived the filters
        self.did = []  # the board-level steps, in the order they happened
        self.searched = []
        self.bought = []
        self.looked = 0  # how many items got as far as looking for the search box
        self.BOARD_DELAY = 0  # the test does not wait three seconds per item

    BOARD_DELAY = 0  # the test does not wait three seconds for a board to reload either

    def apply_flea_filters(self, region=None):
        self.did.append('filters')
        return self.filters

    def remove_filter_by_item_filter(self, region=None):
        self.did.append('clear item filter')
        return self.item_filter

    def find_search_box(self, region=None, cached=None):
        self.looked += 1
        if not self.search:
            raise LookupError('flea_enter_item_name_input not on screen')
        return 'box'

    def search_for(self, name, box, region=None):
        self.searched.append(name)
        return None if self.locked else (100, 200)

    def purchase_buttons(self, region=None):
        return [f'button{n}' for n in range(self.buttons)]

    def read_price(self, button):
        return self.price

    def buy(self, button, region=None):
        self.bought.append(button)
        return self.buy_lands


def sniper(board, margin=500, watchlist=None):
    """A FleaSniper with no window behind it and `board` in place of the screen."""
    bot = snipe_bot.FleaSniper.__new__(snipe_bot.FleaSniper)
    bot.region = (0, 0, 1920, 1080)
    bot.margin = margin
    bot.watchlist = watchlist or [('RAM stick', 'Therapist', 19890)]
    bot.stats = {key: 0 for key, _ in snipe_bot.STAT_LABELS}
    bot._stop = threading.Event()
    bot._search_box = None
    snipe_bot.snipe = board  # module level, which is what check_one reaches through
    return bot


def check(condition, message):
    if not condition:
        sys.exit(f'FAILED: {message}')
    print(f'  ok  {message}')


if __name__ == '__main__':
    real = snipe_bot.snipe
    try:
        print('a top offer under the margin gets bought')
        board = FakeBoard(price=19_000)  # 890 under the 19,890 Therapist pays
        bot = sniper(board)
        check(bot.sweep_once() == 1, 'the sweep reports one buy')
        check(board.searched == ['RAM stick'], 'it searched the watchlist name')
        check(len(board.bought) == 1, 'it clicked purchase once')
        check(bot.stats['bought'] == 1 and bot.stats['spent'] == 19_000, 'spent is counted')
        check(bot.stats['trader_value'] == 19_890, 'what the traders will pay is counted')
        check(bot.stats['profit'] == 890, 'and profit is the difference between the two')
        check(bot.stats['profit'] == bot.stats['trader_value'] - bot.stats['spent'],
              'the three rows agree with each other')

        print('a top offer inside the margin is left alone')
        board = FakeBoard(price=19_500)  # only 390 under, against a 500 margin
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.bought == [], 'purchase was never clicked')
        check(bot.stats['checked'] == 1, 'but it still counts as checked')

        print('an unreadable price is never acted on')
        board = FakeBoard(price=None)
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.bought == [], 'purchase was never clicked')
        check(bot.stats['price_missing'] == 1, 'and it is counted as unreadable')

        print('a price too far under trader value reads as a misread, not a bargain')
        board = FakeBoard(price=890)  # what 19,890 looks like with its leading digits cut off
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.bought == [], 'purchase was never clicked')

        print('a filter-by-item that survived the filter window is cleared before searching')
        board = FakeBoard(price=19_500, item_filter=True)
        bot = sniper(board)
        bot.sweep_once()
        check(board.did == ['filters', 'clear item filter'],
              'the filters go on, then the item filter comes off')
        check(board.searched == ['RAM stick'], 'and only then does it search')

        print('filters that will not go on stop the sweep before it clears anything')
        board = FakeBoard(price=19_500, filters=False)
        bot = sniper(board)
        bot.sweep_once()
        check(board.did == ['filters'], 'it gave up at the filters and never touched the board')

        print('a purchase whose balance never moved is not counted')
        # The 2026-08-17 bug, in one case. Two items were bought on paper and not in the game,
        # because the confirmation dialog never took the keypress and nothing checked. Every
        # rouble stat downstream inherited it, so the run reported 47,650 profit against a real
        # 34,204.
        board = FakeBoard(price=19_000, buy_lands=False)
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'the sweep does not report a buy')
        check(len(board.bought) == 1, 'it did try to buy')
        check(bot.stats['bought'] == 0, 'but nothing is counted as bought')
        check(bot.stats['spent'] == 0, 'no roubles counted as spent')
        check(bot.stats['trader_value'] == 0 and bot.stats['profit'] == 0, 'and no profit')
        check(bot.stats['buy_failed'] == 1, 'it is counted as a buy that missed')
        check(bot.stats['hits'] == 1, 'the offer was still worth buying, it just did not land')

        print('a locked item is skipped before the board is ever read')
        board = FakeBoard(price=1, locked=True)  # a price that would buy instantly if read
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.bought == [], 'purchase was never clicked')
        check(bot.stats['locked'] == 1, 'and it is counted as locked')
        check(bot.stats['price_missing'] == 0, 'the price was never even looked at')

        print('an empty board is not a crash')
        board = FakeBoard(price=19_000, buttons=0)
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.bought == [], 'purchase was never clicked')

        print('a search box that has never been found ends the run')
        board = FakeBoard(price=19_000, search=False)
        bot = sniper(board, watchlist=[('RAM stick', 'Therapist', 19890),
                                       ('Cat figurine', 'Therapist', 31777)])
        try:
            bot.sweep_once()
            check(False, 'the sweep raised')
        except LookupError:
            check(True, 'the sweep raised')
        check(board.searched == [], 'nothing was typed anywhere')
        # The point of the raise: the second item is never reached, because it would fail the
        # same way and the run cannot buy anything until somebody empties the field.
        check(board.looked == 1, 'and it stopped on the first item rather than trying all 77')

        print('filters that will not go on stop the sweep before it reads anything')
        board = FakeBoard(price=19_000, filters=False)
        bot = sniper(board)
        check(bot.sweep_once() == 0, 'nothing bought')
        check(board.searched == [], 'it never searched, so it never read a board')

        print('a shuffled sweep still covers every item exactly once')
        board = FakeBoard(price=19_500)
        watchlist = [(f'item {n}', 'Therapist', 10_000) for n in range(30)]
        bot = sniper(board, watchlist=watchlist)
        bot.sweep_once()
        check(sorted(board.searched) == sorted(n for n, _, _ in watchlist),
              'every name searched, none twice')
        # Two sweeps in a row must not walk the same order, or the shuffle is not doing anything.
        # 30 items, so two sweeps agreeing by chance is not a thing that happens.
        first = list(board.searched)
        board.searched.clear()
        bot.sweep_once()
        check(board.searched != first, 'the second sweep runs in a different order')

        print('Stop lands part way through a sweep')
        board = FakeBoard(price=19_500)
        watchlist = [(f'item {n}', 'Therapist', 10_000) for n in range(20)]
        bot = sniper(board, watchlist=watchlist)
        bot._stop.set()
        try:
            bot.sweep_once()
            sys.exit('FAILED: a sweep with stop already set ran to the end')
        except Stopped:
            pass
        check(board.searched == [], 'it stopped before the first item')
    finally:
        snipe_bot.snipe = real

    print('ok')
