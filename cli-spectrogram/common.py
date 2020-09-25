# GNU LESSER GENERAL PUBLIC LICENSE
#    Version 2.1, February 1999
#
# See LICENSE
#
# Copyright (c) 2020 Caileigh F
#
# Woods Hole Oceanographic Institution
# Author: Caileigh Fitzgerald
# Email:  cfitzgerald@whoi.edu
# Date:   03/04/2020
#
# File: common.py
#
import time
import curses

voltage_bar_width=0   # 22 for values and buffer of 1 on each side
extra_column_buffer=10 # need buffer of 10 columns for axis labels
menu_row_buffer=13     # menu takes up 13 rows
menu_column_buffer=115 # menu takes up about 110 columns
default_console_height=53 # resonable to expect 53 char height for console
ESC=27
ZOOM_IN=43  # +
ZOOM_OUT=45 # -
SHIFT_UP=337
SHIFT_DOWN=336

class ConfigError(Exception):
    def __init__(self, key, value):
        self.key = key
        self.value = value

def unix_epoch_to_local(epoch, no_date=False):
    if no_date:
        return(str(time.strftime('%Hhour%Mmin%Ssecond', time.localtime(epoch))))
    return(str(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))))

def config_curses():
    # start curses
    stdscr = curses.initscr()
    curses.start_color()
    # 0:black, 1:red, 2:green, 3:yellow, 4:blue, 5:magenta, 6:cyan, and 7:white.
    curses.init_pair(curses.COLOR_BLUE, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(curses.COLOR_CYAN, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(curses.COLOR_GREEN, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(curses.COLOR_YELLOW, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(curses.COLOR_MAGENTA, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(curses.COLOR_RED, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(10, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.clearok(True)
    stdscr.scrollok(True)
    stdscr.nodelay(True)
    return(stdscr, curses)