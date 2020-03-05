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
# File: cli_spectrogram.py
#
from common import min_width, min_height, ESC, unix_epoch_to_local, config_curses
from specgram import Specgram
from ui import Ui
import os
import numpy
import math
import argparse
import pathlib
import glob
import time
import curses

def main(source, sample_rate, file_length_sec, debug, display_channel, threshold_db, markfreq_hz, threshold_steps, nfft):
    log_dir = source
    if not os.path.isdir(log_dir):
        print('Must provide valid log directory! source=%s'%str(log_dir))
        exit(2)

    stdscr, curses = config_curses()   
    # create Ui object
    ui = Ui(min_width, min_height, time.time(), curses.color_pair)
    # create specgram object 
    specgram = Specgram(sample_rate, file_length_sec, display_channel, scale='dB', threshdb=threshold_db, threshdb_steps=threshold_steps, markfreq=markfreq_hz, nfft=nfft, max_lines=ui.specgram_max_lines, color_pair=curses.color_pair)
    # now dow stuff
    try:
        count=0
        latest_file = ui.get_file(stdscr, source)
        previous_file = latest_file
        is_dup = True 
        while True:
            ui.spin(stdscr, specgram) # needs to happen every iteration (handles key strokes and window resize)
            latest_file = ui.get_file(stdscr, source)
            # 
            # if DAQ isn't running, new files aren't being added to the log dir
            # - Let user know they are looking at the specgram of the same file over and over
            # - Let's user know when they are looking at new streaming data
            #
            if latest_file == previous_file: 
                is_dup = True
            else:
                is_dup = False
            previous_file = latest_file

            # clear out data list
            specgram.clear()
            # take the file and parse into specgram object
            specgram.parse_file(latest_file)
            # clear curses window
            stdscr.erase()
            # display the specgram
            specgram.display(stdscr)
            # display Ui elements (legend and intensity bar)
            ui.update(stdscr, specgram, is_dup, count)
            # draw everything in the buffer 
            stdscr.refresh()
            count+=1

    except KeyboardInterrupt:
        print('\n\tExiting...\n\n')
        exit(1)
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--sample-rate', help='', required=True, type=float)
    parser.add_argument('--file-length', help='in seconds', required=True, type=int)
    parser.add_argument('-d','--debug', action='store_true', help='Show debugging print messsages', required=False)
    parser.add_argument('--source', help='Source directory with .txt files', required=False)
    parser.add_argument('--threshold-steps', help='How many dB above and below threshold', required=False, type=int)
    parser.add_argument('-c','--display-channel', help='', required=False, type=int, choices=range(1, 9))
    parser.add_argument('-t','--threshold-db', help='', required=False, type=int)
    parser.add_argument('-m','--markfreq-hz', help='', required=False, type=int)
    parser.add_argument('--nfft', help='', required=False, type=int)
    parser.set_defaults(source=os.getcwd(), display_channel=1, threshold_db=60, markfreq_hz=5000, threshold_steps=5, nfft=200)
    args = parser.parse_args()

    curses.wrapper(main(args.source, args.sample_rate, args.file_length, args.debug, args.display_channel, args.threshold_db, args.markfreq_hz, args.threshold_steps, args.nfft))

    # Sound levels for nonlinear (decibel) and linear (intensity) scales decibels     
    # ---------------------------------------------------------------------
    # dB   intensity*  type of sound
    # ---------------------------------------------------------------------
    # 130     10      artillery fire at close proximity (threshold of pain)
    # 120     1       amplified rock music; near jet engine
    # 110     10^1    loud orchestral music, in audience
    # 100     10^2    electric saw
    # 90      10^3    bus or truck interior
    # 80      10^4    automobile interior
    # 70      10^5    average street noise; loud telephone bell
    # 60      10^6    normal conversation; business office
    # 50      10^7    restaurant; private office
    # 40      10^8    quiet room in home
    # 30      10^9    quiet lecture hall; bedroom
    # 20      10^10   radio, television, or recording studio
    # 10      10^11   soundproof room
    # 0       10^12   absolute silence (threshold of hearing)
    # ---------------------------------------------------------------------
    # *In watts per square metre.