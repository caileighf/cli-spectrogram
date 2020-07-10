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
import numpy
import math
import curses

class Specgram(object):
    def __init__(self, sample_rate, file_length_sec, display_channel, scale, threshdb, threshdb_steps, markfreq, nfft, max_lines, color_pair, voltage_bar_width, v_min=-1, v_max=1):
        super(Specgram, self).__init__()
        self.sample_rate=sample_rate
        self.file_length_sec=file_length_sec
        self.display_channel=display_channel
        self.scale=scale
        self.threshdb=threshdb
        self.threshdb_steps=threshdb_steps
        self.markfreq=markfreq
        self.nfft=nfft
        self.max_lines=max_lines
        self.line_mod=1
        self.lines_of_data=0
        self.calc_line_mod=True
        self.data=[]
        self.color_pair=color_pair
        self.show_voltage=False
        self.voltage_bar_width=voltage_bar_width-2
        self.voltage_range=[v_min, v_max]
        self.raw_voltages=[]
        self.argmax_freq = 0.0

    def clear(self):
        self.data = []
        self.raw_voltages = []

    def pop_voltage_bar(self, voltages):
        self.voltage_range[0]=min(voltages)
        self.voltage_range[1]=max(voltages)
        step=abs(self.voltage_range[1]-self.voltage_range[0])/float(self.voltage_bar_width)
        mask= [[' ']*self.voltage_bar_width]*len(voltages)
        for row in range(0, len(voltages)):
            v=self.voltage_range[0]
            for col in range(0, self.voltage_bar_width):
                if voltages[row]<=v and ('.' not in mask[row]):
                    mask[row][col]='.'
                v+=step
        return(mask)

    def parse_file(self, file):
        with open(str(file)) as f:
            self.clear()
            for i, line in enumerate(f):
                voltages = line.split(',')
                try:
                    self.data.append(float(voltages[self.display_channel-1]))
                except ValueError:
                    continue
                else:
                    self.raw_voltages.append(self.data[-1])
            return True

    def getFFTs(self):
        atend=False
        
        start=0
        strvec=[]
        indvec=[]
        rms_voltages=[]
        self.argmax_freq=0.0
        while not atend:
            curvec=self.data[start:start+self.nfft]
            if len(curvec) == 0: 
                break

            #take fft
            fvec=numpy.fft.fft(curvec)
            try:
                fdb = list(20*math.log(abs(x)/pow(10,-6),10) for x in fvec[0:int(self.nfft/2)])
            except ValueError as e:
                print('Caught ValueError! Most likely bad data...\n{}'.format(e))
                # import ipdb; ipdb.set_trace() # BREAKPOINT
                return(None, None, None)

            self.argmax_freq=fdb.index(max(fdb))
            line=''
            for f in fdb:
                if int(f)>=self.threshdb:
                    if int(f)-self.threshdb <= self.threshdb_steps:     # closest to thresh
                        line+=str(curses.COLOR_YELLOW)
                    elif int(f)-self.threshdb < self.threshdb_steps*2: # inbetween closest and max
                        line+=str(curses.COLOR_MAGENTA)
                    elif int(f)-self.threshdb >= self.threshdb_steps*2:   # loudest
                        line+=str(curses.COLOR_RED)
                else:
                    if self.threshdb-int(f) <= self.threshdb_steps:     # close to thresh
                        line+=str(curses.COLOR_GREEN)
                    elif self.threshdb-int(f) < self.threshdb_steps*2: # inbewtween 
                        line+=str(curses.COLOR_CYAN)
                    elif self.threshdb-int(f) >= self.threshdb_steps*2:   # quietest
                        line+=str(curses.COLOR_BLUE)

            strvec.append(line)
            indvec.append(start+self.nfft/2)
            # calc RMS voltage for this line
            line_rms_voltage=0
            snapshot_rms=self.raw_voltages[start:start+self.nfft]
            # calc square
            for v in snapshot_rms:
                line_rms_voltage+=v**2
            # calc mean, then root
            rms_voltages.append(round(math.sqrt(line_rms_voltage/len(fdb)),6))

            start=start+self.nfft
            if start > (self.sample_rate*self.file_length_sec)-self.nfft:
                atend=True

        #self.argmax_freq=math.sqrt(self.argmax_freq/self.nfft)

        return (indvec, strvec, rms_voltages)

    def add_intensity_bar(self, window, y,x):
        window.addstr(y,x,'Quietest         Loudest')
        y+=1
        window.addstr(y,x,'    ', self.color_pair(curses.COLOR_BLUE))
        window.addstr('    ',     self.color_pair(curses.COLOR_CYAN))
        window.addstr('    ',     self.color_pair(curses.COLOR_GREEN))
        window.addstr('    ',     self.color_pair(curses.COLOR_YELLOW))
        window.addstr('    ',     self.color_pair(curses.COLOR_MAGENTA))
        window.addstr('    ',     self.color_pair(curses.COLOR_RED))
        window.addstr(y+1,x,'%sdB  -----^------  %sdB'%(str(self.threshdb-self.threshdb_steps*2), str(self.threshdb+self.threshdb_steps*2)))
        window.addstr(y+2,x,'          %sdB          '%str(self.threshdb), curses.A_BOLD)
        return(y+3,x)

    def display(self, stdscr, display_channel):
        if len(self.data) <= 0:
            stdscr.addstr('parse data from file first!')
            return
        # take fft of the channel data:
        (indvec, strout, rms_voltages) = self.getFFTs()
        if (indvec == None or strout == None):
            return
        ii=0
        freqlist = numpy.fft.fftfreq(self.nfft)*self.sample_rate
        maxfreq=freqlist[int(self.nfft/2-1)]
        minfreq=freqlist[1]
        stdscr.addstr('df=' + str(minfreq))
        stdscr.addstr(' maxfreq=' + str(maxfreq) + '\n')
        stdscr.addstr(' NFFT=' + str(self.nfft) + '\n')
        markdind=0
        #get the index for markfreq
        ind = 0
        # make sure we don't go off the end
        if self.markfreq > maxfreq:
            self.markfreq = maxfreq
        elif self.markfreq < minfreq:
            self.markfreq = minfreq

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

        stdscr.addstr('Channel [' + str(display_channel) + ']\n', curses.A_BOLD)
        stdscr.addstr('time [s]')
        stdscr.addstr(fbord[1:] + '\n', curses.A_BOLD)
        if self.show_voltage:
            stdscr.addstr('       ' +  strbord + ' - snapshot RMS voltage +\n')
        else:
            stdscr.addstr('       ' +  strbord + '\n')
        ms_vec = list(int(float(x)/self.sample_rate*1000) for x in indvec)

        #
        # if window was resized we need to recalculate the line mod
        #
        if self.calc_line_mod:
            self.lines_of_data=len(strout)
            self.line_mod=1
            while self.lines_of_data/self.line_mod > self.max_lines:
                self.line_mod+=1
            self.calc_line_mod=False
        #
        # Display colors
        #
        if self.show_voltage:
            mask=self.pop_voltage_bar(rms_voltages)

        for row, stro in enumerate(strout):
            if row%self.line_mod==0:
                line = ('0.' + str(ms_vec[ii]).zfill(3) + '| ')
                stdscr.addstr(line.encode("utf-8"))
                for col, char in enumerate(stro):
                    if col!=markind:
                        stdscr.addstr(' ', self.color_pair(int(char)))
                    else:
                        stdscr.addstr('|', self.color_pair(int(char)))

                if self.show_voltage:
                    stdscr.addstr('  ')
                    col=0
                    for col in range(1, self.voltage_bar_width):
                        if mask[row][col]=='.':
                            stdscr.addstr('.', self.color_pair(10) | curses.A_BOLD)
                        elif col==self.voltage_bar_width/2:
                            stdscr.addstr('|', self.color_pair(9))
                        else:
                            stdscr.addstr(' ', self.color_pair(9))

                stdscr.addstr('\n')
            ii=ii+1

        stdscr.addstr('       ' +  strbord + '\n')
        stdscr.addstr('       ' +  fbord + '\n', curses.A_BOLD)