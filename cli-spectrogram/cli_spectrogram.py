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
# File: cli_spectrogram.py
#
from __future__ import print_function
import argparse
import os, sys, time
import curses

# internal
from ui import Ui
from specgram import Specgram
from common import (
        TOP_LEFT,
        TOP_RIGHT,
        BOTTOM_LEFT,
        BOTTOM_RIGHT,
        TOP,
        BOTTOM,
        LEFT,
        RIGHT
    )

def run_cli(ui, specgram, do_run_async=False):
    if do_run_async:
        ui.run_async()
    else:
        while True: 
            ui.spin()

def handle_config(args):
    import json
    config_file = os.getenv('DAQ_CONFIG')
    if config_file != None:
        with open(config_file, 'r') as f:
            data = json.load(f)

        args.source = data['data_directory']
        args.file_length = data['file_length_sec']
        args.sample_rate = data['sample_rate']
        args.mode = data['file_mode']

    return(args)

def main(stdscr, args):
    if args.use_config:
        args = handle_config(args)

    ui = Ui(stdscr=stdscr, refresh_hz=0)#args.file_length)
    specgram = Specgram(source=args.source,
                        ui=ui,
                        display_channel=args.display_channel,
                        device_name=args.device_name,
                        legend_side=LEFT if not args.right_hand_legend else RIGHT,
                        threshold_db=args.threshold_db, 
                        markfreq_hz=args.markfreq_hz, 
                        threshold_steps=args.threshold_steps, 
                        nfft=args.nfft,
                        sample_rate=args.sample_rate,
                        file_length=args.file_length,
                        skip_empty=args.skip_empty)
    if not args.stacked_mode:
        ui.best_fit_mode()

    try:
        run_cli(ui=ui,
                specgram=specgram,
                do_run_async=True)
    finally:
        specgram.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''cli-spectrogram -- This tool was
                                                    created to facilitate viewing voltage data
                                                    (in the original use-case, voltage data was
                                                    collected from a hydrophone) 
                                                    as a spectrogram in the command line.''')
    parser.add_argument('--sample-rate', 
                        help='''Sample rate the data files were sampled at (in Hz)
                                (Default: 19200.0Hz)
                                * this cannot be changed during operation.''', 
                        required=False, 
                        type=float)
    parser.add_argument('--device-name', 
                        help='''Helpful for when you have multiple instances of the
                                cli-spectrogram running. (Default: None)
                                * this cannot be changed during operation.''',    
                        default=None, 
                        type=str)
    parser.add_argument('--file-length', 
                        help='''Describes the file length in seconds.
                                If you have a sample-rate of 100.0Hz and a file-length of 1.0 seconds,
                                you *should have 100 rows of data PER file! (Default: 1.0 sec)
                                * this cannot be changed during operation.''', 
                        required=False, 
                        type=float)
    parser.add_argument('--source', 
                        help='''Source directory with .txt files. 
                                Compatible files will format voltage values in comma separated columns
                                where each column represents a channel and each row represents a discrete
                                moment in time.
                                (Default: current working directory)
                                * this cannot be changed during operation.''', 
                        required=False)
    parser.add_argument('-d','--debug',
                        help='Show debugging print messages', 
                        action='store_true', 
                        required=False)
    parser.add_argument('--nfft', 
                        help='''Starting NFFT.
                                (Default: 240)''', 
                        required=False, 
                        type=int)
    parser.add_argument('-c','--display-channel', 
                        help='''Select the channel you want to start with.
                                The current limit is 8 channels. The channels are zero indexed!
                                If you would like to look at the second channel you would pass \"-c 1\".
                                (Default: 0)''', 
                        required=False, 
                        type=int, 
                        choices=range(0, 8))
    parser.add_argument('--threshold-steps', 
                        help='''Starting threshold-steps will define the color intensity.
                                (Default: 5dB)''', 
                        required=False, 
                        type=int)
    parser.add_argument('-t','--threshold-db', 
                        help='''Starting threshold. (Default: 85dB)''', 
                        required=False, 
                        type=int)
    parser.add_argument('-m','--markfreq-hz', 
                        help='''Starting frequency to \"mark\" with a vertical line.
                                (Default: 5,000Hz)''', 
                        required=False, 
                        type=int)
    parser.add_argument('--use-config', 
                        help='''Use JSON config file. This flag is for use with 
                                the MCC_DAQ driver found here: https://github.com/caileighf/MCC_DAQ''', 
                        action='store_true')
    parser.add_argument('--skip-empty', 
                        help='''Skip empty data files -- do not show gaps (Default: False)
                                * this cannot be changed during operation.''', 
                        action='store_true', 
                        required=False)
    parser.add_argument('-r', '--right-hand-legend',
                        help='''Start with the legend of the Right side of the console. This can be
                                moved during operation and will \"stick\" to the opposite side if it
                                travels all the way there.
                                (Default: Left)''', 
                        action='store_true', 
                        required=False)
    parser.add_argument('--stacked-mode', 
                        help='''Start in stacked-mode. Stacked mode will display an overlapping legend
                                rather than a \"Best-fit\" mode where nothing is covered and the plot is 
                                shrunk to fit the available space. (Default: Best-fit)''', 
                        action='store_true', 
                        required=False)

    parser.set_defaults(source=os.getcwd(), 
                        display_channel=0, 
                        threshold_db=85, 
                        markfreq_hz=5000, 
                        threshold_steps=5, 
                        nfft=240,
                        sample_rate=19200,
                        file_length=1.0)
    args = parser.parse_args()

    try:
        curses.wrapper(main, args)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n\tExiting...\n')

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
    # *In watts per square meter.