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
# File: specgram.py
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

class Specgram(object):
    def __init__(self, sample_rate, file_length_sec, display_channel, scale, threshdb, threshdb_steps, markfreq, nfft, max_lines, color_pair):
        super(Specgram, self).__init__()
        self.sample_rate = sample_rate
        self.file_length_sec = file_length_sec
        self.display_channel = display_channel
        self.scale = scale
        self.threshdb = threshdb
        self.threshdb_steps = threshdb_steps
        self.markfreq = markfreq
        self.nfft = nfft
        self.max_lines = max_lines
        self.line_mod = 1
        self.lines_of_data = 0
        self.calc_line_mod=True
        self.data = []
        self.color_pair = color_pair

    def clear(self):
        self.data = []

    def parse_file(self, file):
        with open(str(file)) as f:
           for cnt, line in enumerate(f):
               voltages = line.split(',')
               self.data.append(float(voltages[self.display_channel-1]))

    def getFFTs(self):
        atend=False
        
        start=0
        strvec=[]
        indvec=[]
        while not atend:
            curvec=self.data[start:start+self.nfft]
            if len(curvec) == 0: 
                break

            #take fft
            fvec=numpy.fft.fft(curvec)
            fdb = list(20*math.log(abs(x)/pow(10,-6),10) for x in fvec[0:int(self.nfft/2)])
            line=''
            for f in fdb:
                if int(f)>=self.threshdb:
                    if int(f)-self.threshdb <= self.threshdb_steps:     # closest to thresh
                        line+=str(curses.COLOR_YELLOW)#gradient_chars[4]
                    elif int(f)-self.threshdb < self.threshdb_steps*2: # inbetween closest and max
                        line+=str(curses.COLOR_MAGENTA)#gradient_chars[3]
                    elif int(f)-self.threshdb >= self.threshdb_steps*2:   # loudest
                        line+=str(curses.COLOR_RED)#gradient_chars[3]
                else:
                    if self.threshdb-int(f) <= self.threshdb_steps:     # close to thresh
                        line+=str(curses.COLOR_GREEN)#gradient_chars[1]
                    elif self.threshdb-int(f) < self.threshdb_steps*2: # inbewtween 
                        line+=str(curses.COLOR_CYAN)#gradient_chars[1]
                    elif self.threshdb-int(f) >= self.threshdb_steps*2:   # quietest
                        line+=str(curses.COLOR_BLUE)#gradient_chars[1]

            strvec.append(line)
            indvec.append(start+self.nfft/2)
            start=start+self.nfft
            if start > (self.sample_rate*self.file_length_sec)-self.nfft:
                atend=True

        if self.calc_line_mod:
            self.lines_of_data = len(strvec)
            while self.lines_of_data/self.line_mod > self.max_lines:
                self.line_mod+=1

            self.calc_line_mod=False

        return (indvec, strvec)

    def add_intensity_bar(self, window, y,x):
        window.addstr(y,x,'    ', self.color_pair(curses.COLOR_BLUE))
        window.addstr('    ',     self.color_pair(curses.COLOR_CYAN))
        window.addstr('    ',     self.color_pair(curses.COLOR_GREEN))
        window.addstr('    ',     self.color_pair(curses.COLOR_YELLOW))
        window.addstr('    ',     self.color_pair(curses.COLOR_MAGENTA))
        window.addstr('    ',     self.color_pair(curses.COLOR_RED))
        window.addstr(y+1,x,'Quiet ------------- Loud')
        window.addstr(y+2,x,'%sdB  -----^------- %sdB'%(str(self.threshdb-self.threshdb_steps*2), str(self.threshdb+self.threshdb_steps*2)))
        window.addstr(y+3,x,'          %sdB          '%str(self.threshdb), curses.A_BOLD)
        return(y+3,x)

    def display(self, stdscr):
        if len(self.data) <= 0: # this is extra backup but is handled in the Ui
            stdscr.addstr('parse data from file first!')
            return
        # take fft of the channel data:
        (indvec, strout) = self.getFFTs()
        ii=0
        freqlist = numpy.fft.fftfreq(self.nfft)*self.sample_rate
        stdscr.addstr('df=' + str(freqlist[1]))
        stdscr.addstr(' maxfreq=' + str(freqlist[int(self.nfft/2-1)]) + '\n')
        markdind=0
        #get the index for markfreq
        ind = 0
        for f in freqlist:
            if f > self.markfreq-freqlist[1]/2 and f <= self.markfreq+freqlist[1]/2:
                self.markfreq = f
                markind=ind
            ind=ind+1
        
        strbord=''
        fbord=''
        gotf=False
        for s in range(0,int(self.nfft/2)):
            if s!=markind:
                if not gotf:
                    fbord=fbord+' '
                strbord=strbord+'-'
            else:
                fbord = fbord+str(round(self.markfreq, 3)) +'Hz'
                gotf=True
                strbord=strbord+'|'
        stdscr.addstr('time [s]')
        stdscr.addstr(fbord[1:] + '\n', curses.A_BOLD)
        stdscr.addstr('       ' +  strbord + '\n')
        ms_vec = list(int(float(x)/self.sample_rate*1000) for x in indvec)

        self.max_lines=len(strout)
        for i, stro in enumerate(strout):
            if i%self.line_mod==0:
                line = ('0.' + str(ms_vec[ii]).zfill(3) + '| ')
                stdscr.addstr(line.encode("utf-8"))
                for i, char in enumerate(stro):
                    if i!=markind:
                        stdscr.addstr(' ', self.color_pair(int(char)))
                    else:
                        stdscr.addstr('|', self.color_pair(int(char)))

                stdscr.addstr('\n')
            ii=ii+1

        stdscr.addstr('       ' +  strbord + '\n')
        stdscr.addstr('       ' +  fbord + '\n', curses.A_BOLD)