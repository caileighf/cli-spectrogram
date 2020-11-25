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

def run_cli(ui, specgram):
    # ui.run_async()
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

    ui = Ui(stdscr=stdscr, refresh_hz=args.file_length)
    specgram = Specgram(source=args.source,
                        register_keystroke_callable=ui.register_keystroke_callable,
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
                specgram=specgram)
    finally:
        specgram.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='cli-spectrogram')
    parser.add_argument('--sample-rate', help='', required=False, type=float)
    parser.add_argument('--device-name', help='', default=None, type=str)
    parser.add_argument('--file-length', help='in seconds', required=False, type=float)
    parser.add_argument('-d','--debug', action='store_true', help='Show debugging print messsages', required=False)
    parser.add_argument('--skip-empty', action='store_true', help='Skip empty data files -- do not show gaps', required=False)
    parser.add_argument('-r', '--right-hand-legend', action='store_true', 
                        help='Orient the legend to stick to the right side (default: left)', required=False)
    parser.add_argument('--stacked-mode', action='store_true', help='Start in stacked-mode', required=False)
    parser.add_argument('--source', help='Source directory with .txt files', required=False)
    parser.add_argument('--threshold-steps', help='How many dB above and below threshold', required=False, type=int)
    parser.add_argument('-c','--display-channel', help='', required=False, type=int, choices=range(0, 8))
    parser.add_argument('-t','--threshold-db', help='', required=False, type=int)
    parser.add_argument('-m','--markfreq-hz', help='', required=False, type=int)
    parser.add_argument('--nfft', help='', required=False, type=int)
    parser.add_argument('--use-config', help='Use config file', action='store_true')    
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