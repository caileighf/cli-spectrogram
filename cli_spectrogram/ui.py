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
# File: ui.py
#
from common import min_width, min_height, ESC, unix_epoch_to_local, max_rows_specgram_no_menu, max_rows_specgram
import os
import numpy
import math
import argparse
import pathlib
import glob
import time
import curses

class Ui(object):
    def __init__(self, min_width, min_height, current_time, color_pair, mode='text'):
        super(Ui, self).__init__()
        self.min_width = min_width
        self.min_height = min_height
        self.current_time = current_time
        self.start = current_time
        self.nav_next_file = False
        self.nav_prev_file = False
        self.stop_at_file = False
        self.current_file = None
        self.hide_menu = False
        self.specgram_max_lines = max_rows_specgram
        self.specgram_max_lines_no_menu = max_rows_specgram_no_menu
        self.key_id=ESC
        self.mode=mode
        self.color_pair=color_pair

    def reset_nav(self):
        self.stop_at_file=False
        self.nav_prev_file=False
        self.nav_next_file=False

    def get_files(self, source):
        if self.mode=='binary':
            return(sorted(pathlib.Path(source).glob('1*.bin')))
        else:
            return(sorted(pathlib.Path(source).glob('1*.txt')))

    def get_file(self, window, source):
        files = self.get_files(source)
        if len(files) <= 2:
            files = self.handle_no_files(window, source)
        else:
            if self.stop_at_file and self.current_file is not None:
                # find position of current file in list
                pos=0
                try:
                    pos=files.index(self.current_file)
                except ValueError:
                    # reset attributes and resume streaming
                    self.reset_nav()

                # user wants to move to next file
                if self.nav_next_file:
                    self.nav_next_file=False
                    try:
                        self.current_file = files[pos+1]
                    except IndexError:
                        self.reset_nav()
                        
                # user wants previous file        
                if self.nav_prev_file:
                    self.nav_prev_file=False
                    try:
                        self.current_file = files[pos-1]
                    except IndexError:
                        self.reset_nav()


        if self.stop_at_file:
            # make sure user doesn't go to last file because it's empty
            if os.path.getsize(str(self.current_file)) <= 0:
                self.reset_nav()
                self.current_file=files[-2]
            return(self.current_file)
        else:
            self.current_file=files[-2]
            return(self.current_file)

    def handle_no_files(self, window, source):
        files = self.get_files(source)
        while len(files) <= 2:
            window.erase()
            window.nodelay(False)
            window.addstr('No files in the log directory!\n',curses.A_BOLD)
            window.addstr('----------------------------------------------\n')
            window.addstr('Current directory:  %s\n'%(str(source)))
            window.addstr('----------------------------------------------\n')
            window.addstr('Hit Ctrl + C to Exit or wait for log files\n', curses.A_BOLD)
            window.refresh()
            files = self.get_files(source)
        return(files)

    def handle_resize(self, window):
        h, w = window.getmaxyx()
        while h<self.min_height or w<self.min_width:
            window.erase()
            window.nodelay(False)
            window.addstr('The terminal window is too small!\n',curses.A_BOLD)
            window.addstr('----------------------------------------------\n')
            window.addstr('The minimum width is:  %i\tCurrent width:  %i\n'%(self.min_width, w))
            window.addstr('The minimum height is: %i\tCurrent height: %i\n'%(self.min_height, h))
            window.addstr('----------------------------------------------\n')
            window.addstr('Hit Ctrl + C to Exit or resize terminal\n', curses.A_BOLD)
            window.refresh()
            h, w = window.getmaxyx()

    def handle_key_strokes(self, window, specgram):
        self.current_time=time.time()
        while (self.current_time-self.start) <= specgram.file_length_sec:
            key = window.getch()
            if key == curses.KEY_UP:
                specgram.threshdb+=1
            elif key == curses.KEY_DOWN:
                specgram.threshdb-=1
            elif key == curses.KEY_RIGHT:
                specgram.markfreq+=200
            elif key == curses.KEY_LEFT:
                specgram.markfreq-=200
            elif key == curses.KEY_RESIZE:
                self.handle_resize(window)
            elif key == curses.KEY_PPAGE:
                self.nav_next_file=True
                self.stop_at_file=True
            elif key == curses.KEY_NPAGE:
                self.nav_prev_file=True
                self.stop_at_file=True
            elif key == ESC:
                self.reset_nav()
            elif key == ord('F') or key == ord('f'):
                if self.hide_menu:
                    specgram.max_lines=self.specgram_max_lines
                    self.hide_menu=False
                else:
                    specgram.max_lines=self.specgram_max_lines_no_menu
                    self.hide_menu=True
                # next display will recalc line mod    
                specgram.line_mod=1
                specgram.calc_line_mod=True
            elif key != -1:
                self.key_id=key

            self.current_time=time.time()
        self.start=self.current_time

    def spin(self, window, specgram):
        self.handle_resize(window)
        self.handle_key_strokes(window, specgram)

    def update(self, window, specgram, is_dup, count):
        if not self.hide_menu:
            self.display_legend(window, specgram, is_dup, count)

    def display_legend(self, window, specgram, is_dup, count):
        y_row1, x_col1 = window.getyx()   # | top right corner of col1 info
        x_col2 = x_col1+33 # y_row1, x_col2 | top right of col2 bar
        x_col3 = x_col2+27 # y_row1, x_col2 | top right of col3 nav

        window.addstr(' Threshold (dB):    %s'%(str(specgram.threshdb)))
        window.addstr('\n Sample Rate (Hz):  %s'%(str(specgram.sample_rate)))
        window.addstr('\n Viewing same file: ')
        if is_dup:
            window.addstr(str(is_dup), curses.A_BOLD)
        else:
            window.addstr(str(is_dup))
        window.addstr('\n file: ')
        window.addstr(str(self.current_file.stem+'.txt'), curses.A_BOLD)
        window.addstr('\n time: ')
        window.addstr(str(unix_epoch_to_local(float(self.current_file.stem)))) # time file was created or last modified
        window.addstr('\n -----------------------------')
        window.addstr('\n refresh count: %s'%(str(count)))
        # window.addstr('\n Key ID: ')
        # window.addstr(str(self.key_id))

        window.move(y_row1+1, x_col2) # move to top right corner of col2
        if self.stop_at_file:
            window.addstr('    Mode: Navigation    ', curses.A_BOLD | self.color_pair(7))
        else:
            window.addstr('    Mode: Streaming     ', self.color_pair(8))

        y, x = specgram.add_intensity_bar(window, y_row1+3,x_col2)

        window.move(y_row1, x_col3) # move to top right corner of col3
        window.addstr(y_row1,x_col3,  '[up   | down ] adjust the threshold (dB)')
        window.addstr(y_row1+1,x_col3,'[left | right] adjust the frequency marker (Hz)')
        window.addstr(y_row1+2,x_col3,'[pgup | pgdn ] view next file/view prev file')
        window.addstr(y_row1+3,x_col3,'-------------------------------------')
        window.addstr(y_row1+4,x_col3,'[ESC] Exit navigation mode and stream')
        window.addstr(y_row1+5,x_col3,'[F | f] toggle full screen')
        window.addstr(y_row1+6,x_col3,'-----------------------------')
        window.addstr(y_row1+7,x_col3,'Hit Ctrl + C to Exit', curses.A_BOLD)