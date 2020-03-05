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

min_width=110
min_height=53
max_rows_specgram=43
max_rows_specgram_no_menu=52
ESC=27
ZOOM_IN=43  # +
ZOOM_OUT=45 # -

def unix_epoch_to_local(epoch):
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
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.clearok(True)
    stdscr.scrollok(True)
    stdscr.nodelay(True)
    return(stdscr, curses)