#!/usr/bin/python

# UI modules
import curses
import threading

# Misc/essentials
import os
import csv
import sys
import traceback
import logging

# Modules for core functionality
import requests
import time
import sqlite3

# Configuration file
import config


class Ticker(object):
    def __init__(self, name):
        """
        Ticker class is used to store and handle
        all stock data.
        The initial values are set to 'N/A' until
        they are updated.

        See options variable in config.py for the list
        of data keys.
        """

        self.data = {}
        for option in options:
            self.data[option[0]] = 'N/A'
        self.data['Ticker'] = name

    def update(self, new_data):
        """
        Update data.

        new_data contains all the information
        for the Ticker, excluding the symbol
        """

        for option, value in zip(options[1:], new_data):
            self.data[option[0]] = value

    def direction(self, key):
        """
        Get the color pair value based on the direction
        of the stock price from open.

        All options are 3 (white) except the last price and
        the change, which are red (1) or green (2).

        key is the option key to be used
        """

        if key in (o[0] for o in options[1:4]):
            if self.data['Change'][0] == '+':
                return 2
            elif self.data['Change'][0] == '-':
                return 1
        return 3


class Portfolio(object):
    def __init__(self, db_path='db/monitor.db'):
        """
        Portfolio object to manage the portfolio continuously
        using an sqlite database. The database must contains the
        table named portfolio, which has all the stock names.

        db_path is the database name
        """

        self._conn = sqlite3.connect(database=db_path)
        self._curr = self._conn.cursor()
        self._conn.text_factory = str

    def get_table(self):
        self._curr.execute("SELECT * FROM portfolio;")
        return self._curr.fetchall()

    def get_item(self, item):
        self._curr.execute("SELECT * FROM portfolio WHERE symbol=?;", item)
        return self._curr.fetchone()

    def insert_item(self, item):
        try:
            self._curr.execute("INSERT INTO portfolio (symbol) VALUES (?);",
                               (item, ))
            self._conn.commit()
            return True

        # Handle error from existing symbol attribute because it is unique
        except sqlite3.IntegrityError:
            return False

    def remove_item(self, item):
        self._curr.execute("DELETE FROM portfolio WHERE symbol=?;", (item,))

    def close(self):
        self._conn.commit()
        self._curr.close()
        self._conn.close()


# Options obtained from config.py
options = config.options


class Monitor:
    def __init__(self):
        """
        Monitor is the main class which handles the TUI, fetches
        the quote data, and manages the portfolio.
        """

        logging.basicConfig(filename='log/monitor.log',
                            format='%(asctime)s %(levelname)s: %(message)s',
                            level=logging.DEBUG)

        self.portfolio = Portfolio()
        self.stocks = {}
        for stock in self.portfolio.get_table():
            self.stocks[stock[1]] = Ticker(stock[1])

        self.loop = True

        try:
            # Init Screen
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.nodelay(1)
            self.maxy, self.maxx = self.stdscr.getmaxyx()
            self.time_window = self.create_window(2, self.maxx, 0, 0)
            self.title_window = self.create_window(3, self.maxx, 2, 0)
            self.quote_window = self.create_window(self.maxy-4,
                                                   self.maxx, 5, 0)
            self.quote_window.scrollok(1)
            # Init color pairs
            curses.curs_set(0)
            curses.start_color()
            curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
            self.update_title()

        except:
            self.end_session()
            traceback.print_exc()
            sys.exit(1)

        # Time window is threaded to avoid delay
        self.time_thread = threading.Thread(target=self.update_time)
        self.time_thread.daemon = True
        self.time_thread.start()

    def create_window(self, sizey, sizex, posy, posx):
        temp_window = curses.newwin(sizey, sizex, posy, posx)
        temp_window.nodelay(1)
        temp_window.keypad(1)
        return temp_window

    # Format url to get quote from Yahoo! finance
    # Default options are to recieve the symbol and price
    def format_url(self):
        """
        format_url formats the url for yahoo! quotes.

        """

        base_url = "http://finance.yahoo.com/d/quotes.csv"
        url = "{0}?s=".format(base_url)

        # Add stock symbols to URL
        for symbol in self.portfolio.get_table():
            url = url + "{0}+".format(symbol[1])

        # Add options to URL (and remove extra '+'
        url = "{0}&f={1}".format(url[:-1],
                                 ''.join([o[1] for o in options]))

        return url

    # Return True/False if market is open/closed
    def is_open(self):
        now = time.localtime(time.time())
        return(now[6] < 5 and
               (9 <= now[3] < 15 or
               (now[3] == 8 and now[4] >= 30)))

    def handle_resize(self):
        self.maxy, self.maxx = self.stdscr.getmaxyx()
        curses.resize_term(self.maxy, self.maxx)
        self.update_title()

    # Functions to update curses windows

    def update_time(self):
        while self.loop:
            self.time_window.clear()
            self.time_window.addstr("Time: " +
                                    time.strftime('%X', time.localtime(
                                                       time.time())) + " CST ")
            if not self.is_open():
                self.time_window.addstr(" (Market closed)")

            self.time_window.refresh()
            time.sleep(0.1)

    def update_title(self):
        self.title_window.clear()
        for option in options:
            self.title_window.addstr(option[0] +
                                     " "*(self.maxx//len(options) -
                                          len(option[0])))

        self.title_window.addstr("\n")

        self.title_window.addstr("_"*(self.maxx))
        self.title_window.refresh()

    def update_quotes(self):
        self.quote_window.clear()

        # Variable to properly space the data
        data_size = len(options)

        for item in self.stocks.values():
            for key in options:
                # Add data to window
                self.quote_window.addstr(item.data[key[0]] +
                                         " "*(self.maxx//data_size -
                                              len(item.data[key[0]])),
                                         curses.color_pair(
                                             item.direction(key[0])))
            self.quote_window.addstr("\n")
        self.quote_window.refresh()

    # Retrieve quote from Yahoo! finance and display
    def get_data(self, url):
        response = requests.get(url, timeout=5)
        results = response.text

        for line in csv.reader(results.splitlines(), delimiter=','):
            self.stocks[line[0]].update(line[1:])

    # Get stock ticker from input
    # Called from run when + or - key is pressed
    def get_ticker(self):
        self.quote_window.clear()
        self.quote_window.addstr("Input ticker: ")
        self.quote_window.refresh()
        self.quote_window.nodelay(0)

        curses.echo()
        ticker = self.quote_window.getstr()
        # Check for proper symbol
        curses.noecho()
        self.quote_window.nodelay(1)
        return ticker.upper()

    # Main function
    def run(self):
        # Get url
        url = self.format_url()

        # Infinite loop
        while True:
            # Get input from quote window
            ch = self.quote_window.getch()

            # Quit on 'q' pressed
            if ch == ord('q'):
                self.end_session()
                break

            # Add stock ticker
            elif ch == ord('+'):
                ticker = self.get_ticker()

                # Check for valid input
                if ticker != '':
                    if self.portfolio.insert_item(ticker):
                        url = self.format_url()
                        # Add new ticker to stocks
                        self.stocks[ticker] = Ticker(ticker)

            # Remove ticker
            elif ch == ord('-'):
                ticker = self.get_ticker()
                self.portfolio.remove_item(ticker)
                url = self.format_url()
                # Delete Ticker from stocks
                del self.stocks[ticker]

            # Handle terminal resize event
            elif ch == 410 or ch == curses.KEY_RESIZE:
                self.handle_resize()

            # Get quote data
            try:
                self.get_data(url)
            except requests.exceptions.Timeout, e:
                logging.warning(str(e))
                continue

            self.update_quotes()

            # Sleep before getting new data
            # Reduces CPU usage
            time.sleep(0.25)

    # Properly end session
    def end_session(self):
        self.loop = False
        self.time_thread.join()
        self.stdscr.keypad(0)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        self.portfolio.close()

if __name__ == "__main__":
    # Init monitor
    monitor = Monitor()

    # Monitor until script is stopped
    try:
        monitor.run()
    except KeyboardInterrupt, SystemExit:
        monitor.end_session()
        sys.exit(0)
    except:
        monitor.end_session()
        traceback.print_exc()
        sys.exit(1)
