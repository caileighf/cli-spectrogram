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
# Date:   10/17/2020
#
# File: common.py
#
from __future__ import print_function
from collections import namedtuple
import os, sys, time
import threading
import pathlib
import curses
import traceback

default_fg = curses.COLOR_BLACK
default_bg = curses.COLOR_WHITE
default_emphasis = curses.A_NORMAL
ESC = 27
SHIFT_UP = 337
SHIFT_DOWN = 336
SHIFT_LEFT = 393
SHIFT_RIGHT = 402
Q_MARK = 63

STANDOUT_GREEN = 50
STANDOUT_RED = 51

def init_color_pairs():
    curses.use_default_colors()
    # default values for specgram plot
    curses.init_pair(curses.COLOR_BLUE,    curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(curses.COLOR_CYAN,    curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(curses.COLOR_GREEN,   curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(curses.COLOR_YELLOW,  curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(curses.COLOR_MAGENTA, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(curses.COLOR_RED,     curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(50, curses.COLOR_GREEN, -1)
    curses.init_pair(51, curses.COLOR_RED, -1)

TOP    = 0
BOTTOM = 1
LEFT   = 2
RIGHT  = 3

TOP_LEFT  = 4
TOP_RIGHT = 5

BOTTOM_LEFT  = 6
BOTTOM_RIGHT = 7

SPLIT_V_STACK = 0
SPLIT_H_STACK = 1
SINGLE_V = 2
SINGLE_H = 3

POTENTIAL_POSITIONS = [TOP, BOTTOM, LEFT, RIGHT, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]

CursesPixel = namedtuple('CursesPixel', ['text', 'fg', 'bg', 'attr'])
Line = namedtuple('Line', ['data', 'attr_mask'])

def accumulate(x, l=[0]): l[0] += x; return l[0];

def get_fitted_window(legend_managers):
    minus_top, minus_bottom = (0, 0)
    minus_left, minus_right = (0, 0)
    for legend in legend_managers.values():
        # find delta from each side
        minus_right  += legend.get_total_width(side=RIGHT)
        minus_left   += legend.get_total_width(side=LEFT)
        minus_top    += legend.get_total_height(side=TOP)
        minus_bottom += legend.get_total_height(side=BOTTOM)

    # find (x, y) for new plot win
    x = minus_left
    y = minus_top

    max_rows, max_columns = get_term_size()
    max_rows -= minus_top + minus_bottom
    max_columns -= minus_left + minus_right
    
    return(WindowDimensions(x=x, y=y, 
                            rows=max_rows,
                            columns=max_columns))

def get_term_size():
    rows, columns = os.popen('stty size', 'r').read().split()
    return(int(rows), int(columns))

class WindowDimensions(object):
    """docstring for WindowDimensions"""
    def __init__(self, rows, columns, x=0, y=0):
        super(WindowDimensions, self).__init__()
        self.x = int(x)
        self.y = int(y)
        self.rows = int(rows)
        self.columns = int(columns)

    @property
    def data(self):
        return('x = {}, y = {}, rows = {}, columns = {}'.format(self.x, self.y, self.rows, self.columns))
        
    def __eq__(self, compare):
        if compare != None and\
           self.x == compare.x and\
           self.y == compare.y and\
           self.rows == compare.rows and\
           self.columns == compare.columns:
            return(True)
        return(False)

class KeystrokeCallable(object):
    """docstring for KeystrokeCallable"""
    def __init__(self, key_id, key_name, call=[], case_sensitive=True):
        super(KeystrokeCallable, self).__init__()
        self.key_id = key_id
        self.key_name = key_name
        self.call = call if isinstance(call, list) else [call]
        self.case_sensitive = case_sensitive

        # ONLY alpha characters can be case-in-sensitive
        if not self.key_name.isalpha() and not case_sensitive:
            self.case_sensitive = True

    def switch_case_id(self):
        if self.case_sensitive:
            return(None)

        if self.key_name.islower():
            return(ord(self.key_name.upper()))
        return(ord(self.key_name.lower()))

    def switch_case(self):
        if self.case_sensitive:
            return(None)

        if self.key_name.islower():
            return(KeystrokeCallable(key_id=ord(self.key_name.upper()),
                                     key_name=self.key_name.upper(),
                                     call=self.call,
                                     case_sensitive=self.case_sensitive))
        return(KeystrokeCallable(key_id=ord(self.key_name.lower()),
                                 key_name=self.key_name.lower(),
                                 call=self.call,
                                 case_sensitive=self.case_sensitive))

    def __str__(self):
        return(str(
            'id: {}, name: {}, call(s): {}, case-sensitive: {}'.format(self.key_id,
                                                                       self.key_name,
                                                                       self.call,
                                                                       self.case_sensitive)
            ))

class FileNavManager(object):
    """docstring for FileNavManager

    Handles list of files and holds "position" of cursor in list of files
    """
    def __init__(self, data_dir, file_name_pattern='1*.txt'):
        super(FileNavManager, self).__init__()
        self.data_dir = data_dir
        self.shutdown = False
        self._state = 'Streaming'
        self.file_pattern = file_name_pattern
        self.cursor_pos = self._update_files()
        self._thread = threading.Thread(target=self.run)
        self._thread.start()
        self._current_file = None

    @property
    def current_file(self):
        if self._current_file == None:
            self._current_file = pathlib.Path('NO-DATA-FILES-FOUND')
        return(self._current_file)
    
    @property
    def state(self):
        return(self._state)

    @property
    def total_files(self):
        return(self._update_files())

    @property
    def current_position(self):
        return(self.cursor_pos)
    
    
    def validate_cursor(self):
        if self.cursor_pos >= len(self._files):
            self.move_to_end()
        elif self.cursor_pos <= 0:
            self.move_to_beginning()

    def move_cursor(self, delta):
        self._state = 'Navigation'
        self.cursor_pos += delta
        return(self.cursor_pos)

    def move_to_beginning(self):
        self._state = 'Beginning'
        self.cursor_pos = 1
        return(self.cursor_pos)

    def move_to_end(self):
        self._state = 'Streaming'
        self.cursor_pos = len(self._files)
        return(self.cursor_pos)
    
    def next_file(self):
        self.validate_cursor()
        if len(self._files) <= 0:
            next_file = None
        else:
            next_file = self._files[self.cursor_pos - 1]
        # if streaming advance cursor 1 file
        if self.is_streaming(): 
            self.cursor_pos += 1

        self._current_file = next_file
        return(self.current_file)

    def is_streaming(self):
        return(self._state == 'Streaming')

    def run(self):
        while not self.shutdown:
            self._update_files()
            time.sleep(0.01)

    def close(self):
        self.shutdown = True

    def _kill(self):
        sys.exit()

    def _update_files(self):
        self._files = sorted(pathlib.Path(self.data_dir).glob(self.file_pattern))[:-1]
        return(len(self._files))

class Cursor(object):
    """docstring for Cursor"""
    def __init__(self, max_rows, min_rows=0, step=1):
        super(Cursor, self).__init__()
        self.max_rows = max_rows
        self.min_rows = min_rows
        self.step = step
        self.iter_y = iter(range(self.min_rows, self.max_rows - 1, self.step))

    @property
    def y(self):
        try:
            return(next(self.iter_y))
        except StopIteration:
            self.iter_y = iter(range(self.min_rows, self.max_rows - 1, self.step))
            return(next(self.iter_y))
        