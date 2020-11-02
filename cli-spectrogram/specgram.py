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
# File: specgram.py
#
from __future__ import print_function
from common import (KeystrokeCallable, WindowDimensions, FileNavManager, CursesPixel)
from common import (default_emphasis, ESC, Q_MARK, SHIFT_UP, SHIFT_DOWN, SHIFT_LEFT, SHIFT_RIGHT)
from common import (
        TOP_LEFT,
        TOP_RIGHT,
        BOTTOM_LEFT,
        BOTTOM_RIGHT,
        TOP,
        BOTTOM,
        LEFT,
        RIGHT,
        STANDOUT_GREEN,
        STANDOUT_RED,
        SPLIT_V_STACK,
        SPLIT_H_STACK,
        SINGLE_V,
        SINGLE_H
    )
import sys
import numpy
import math
import datetime
import traceback
from curses import (COLOR_YELLOW,
                    COLOR_MAGENTA,
                    COLOR_RED,
                    COLOR_GREEN,
                    COLOR_CYAN,
                    COLOR_BLUE,
                    COLOR_BLACK,
                    A_BOLD,
                    A_UNDERLINE,
                    A_NORMAL,
                    KEY_PPAGE,
                    KEY_NPAGE,
                    KEY_UP,
                    KEY_DOWN,
                    KEY_LEFT,
                    KEY_RIGHT)

class Specgram(object):
    """docstring for Specgram

    """
    def __init__(self, source,
                       register_keystroke_callable,
                       ui,
                       device_name,
                       display_channel=0, 
                       threshold_db=90, 
                       markfreq_hz=5000, 
                       threshold_steps=5, 
                       nfft=240,
                       sample_rate=19200,
                       file_length=1.0):
        super(Specgram, self).__init__()
        self.ui = ui # ui instance for creating plot window and legend windows
        self.window = ui.new_full_size_window(name='specgram_plot')
        self.first_draw = False
        self.force_redraw = True
        self.window.add_callback(self.redraw_specgram)
        self.window.fill_screen = True
        self.window.on_state_change.append(self.handle_plot_state_change)

        self.max_rows = self.window.rows
        self.max_columns = self.window.columns
        self.register_keystroke_callable = register_keystroke_callable
        self.vertical_axis_width = 8    # 8 characters for the vertical axis
        self.horizontal_axis_height = 6 # 6 characters for the horizontal axis 

        self.source = source
        self.display_channel = display_channel
        self.available_channels = display_channel + 1 # zero indexed channels
                                                      # we will update once we get a look at the data files
        self.threshold_db = threshold_db
        self.markfreq_hz = markfreq_hz
        self.threshold_steps = threshold_steps
        self.nfft = nfft
        self.nfft_step = 10
        self.sample_rate = sample_rate
        self.file_length_sec = file_length
        self.argmax_freq = 0

        self.full_screen_mode = False
        self.file_manager = FileNavManager(data_dir=self.source)
        self.current_file = self.file_manager.next_file()
        self.device_name = device_name
        self.data = []
        self._init_keymap()
        self.handle_plot_state_change(event='INITIAL_RESIZE')

        self.legend = ui.new_legend(name='specgram_legend', 
                                    num_panels=2, 
                                    get_legend_dict=self.legend_data, 
                                    type_=SPLIT_V_STACK, 
                                    shared_dimension=50, 
                                    side=RIGHT)

        with open('_debug.log', 'a+') as f:
            output = '<<<<<<<'
            for i, p in enumerate(self.legend.panels):
                output += '\n[{}]: Corner type: {}'.format(i, p.corner)
                output += '\n      columns: {}'.format(p.columns)
                output += '\n      __dict__.panel: {}'.format(p.__dict__)
            output += '\n>>>>>>>\n'
            f.write(output)

    def _init_keymap(self):
        self.keymap = [
            KeystrokeCallable(key_id=ord('A'),
                              key_name='A',
                              call=[self.handle_navigation],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('B'),
                              key_name='B',
                              call=[self.handle_navigation],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('C'),
                              key_name='C',
                              call=[self.cycle_channels],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('D'),
                              key_name='D',
                              call=[self.handle_navigation],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('E'),
                              key_name='E',
                              call=[self.handle_navigation],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('F'),
                              key_name='F',
                              call=[self.full_screen],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('H'),
                              key_name='H',
                              call=[self.toggle_legend],
                              case_sensitive=False),
            KeystrokeCallable(key_id=Q_MARK,
                              key_name='?',
                              call=[self.handle_config]),
            KeystrokeCallable(key_id=KEY_UP,
                              key_name='Up',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_DOWN,
                              key_name='Down',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_LEFT,
                              key_name='Left',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_RIGHT,
                              key_name='Right',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=SHIFT_LEFT,
                              key_name='Shift + Left',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=SHIFT_RIGHT,
                              key_name='Shift + Right',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=SHIFT_UP,
                              key_name='Shift + Up',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=SHIFT_DOWN,
                              key_name='Shift + Down',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_PPAGE,
                              key_name='Previous Page',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_NPAGE,
                              key_name='Next Page',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=ESC,
                              key_name='Escape',
                              call=[self.handle_navigation]),
        ]
        for key in self.keymap:
            self.register_keystroke_callable(keystroke_callable=key, update=True)

    def close(self):
        self.file_manager.close()

    def legend_data(self):
        return({
                'UPPER': {
                    'File Information': {
                        'File': self.file_manager.current_file.name,
                        'Time': self.get_formatted_dt(),
                        'Device Name': self.device_name,
                        '__dataset_position_marker__':
                            self.create_dataset_position_bar(),
                    },
                    'Spectrogram Information': {
                        'Threshold (dB)': self.threshold_db,
                        'Sample Rate (Hz)': self.sample_rate,
                        'Max Freq': self.argmax_freq,
                        'NFFT': self.nfft,
                    },
                    '__channel_bar__':
                        self.create_channel_bar(),
                    '__nav_mode_bar__': 
                        self.create_nav_mode_bar(),
                    '__plot_mode_bar__':
                        self.create_plot_mode_bar(),
                    '__intensity_bar__': 
                        self.create_intensity_bar(),
                },
                'LOWER': {
                    'Keyboard Shortcuts': {
                        'Up / Down': 'Adjust color threshold by +/-{}dB'.format(self.threshold_steps),
                        'Shift + (Up / Down)': 'Adjust NFFT by +/-{}'.format(self.nfft_step),
                        'Left / Right': 'Move mark frequency by +/-100Hz',
                        '__hline00__': self.legend.hline(ch=' '),
                        'C / c': 'Cycle through channels',
                        '__hline01__': self.legend.hline(ch=' '),
                        'Pg Up / Pg Down': 'Previous file / Next file',
                        'A / a': 'Move backwards 60 seconds / 10 seconds',
                        'D / d': 'Move forwards 60 seconds / 10 seconds',
                        'B / b': 'Jump to beginning of dataset',
                        'E / e': 'Jump to end of dataset',
                        'Escape': 'Resume streaming',
                        '__hline02__': self.legend.hline(ch=' '),
                        'Shift + Left': 'Move legend left',
                        'Shift + Right': 'Move legend right',
                        'H / h': 'Toggle keyboard shortcuts on / off',
                        'F / f': 'Toggle full screen on / off',
                        'X / x': 'Toggle Stacked / Best Fit panels',
                    },
                }
        })

    def handle_config(self, key):
        pass

    def handle_navigation(self, key):
        if not key.case_sensitive:
            if key.key_name.upper() == 'B':
                cursor_pos = self.file_manager.move_to_beginning()
            elif key.key_name.upper() == 'E':
                cursor_pos = self.file_manager.move_to_end()
            elif key.key_name.upper() == 'A':
                if key.key_name.isupper():
                    cursor_pos = self.file_manager.move_cursor(delta=-int(60 / self.file_length_sec)) # 10 mins
                else:
                    cursor_pos = self.file_manager.move_cursor(delta=-int(10 / self.file_length_sec))  # 1 min
            elif key.key_name.upper() == 'D':
                if key.key_name.isupper():
                    cursor_pos = self.file_manager.move_cursor(delta=+int(60 / self.file_length_sec)) # 10 mins
                else:
                    cursor_pos = self.file_manager.move_cursor(delta=+int(10 / self.file_length_sec))  # 1 min

        else:
            if key.key_id == KEY_PPAGE:
                cursor_pos = self.file_manager.move_cursor(delta=-1)
            elif key.key_id == KEY_NPAGE:
                cursor_pos = self.file_manager.move_cursor(delta=1)
            elif key.key_id == ESC:
                cursor_pos = self.file_manager.move_to_end()
            elif key.key_id == KEY_LEFT or key.key_id == KEY_RIGHT:
                if key.key_id == KEY_RIGHT:
                    self.markfreq_hz += 100
                else:
                    self.markfreq_hz -= 100
                self.markfreq_hz = self.markfreq_hz if self.markfreq_hz >= 1 else 1
                self.markfreq_hz = self.markfreq_hz if self.markfreq_hz <= 10000 else 10000
            elif key.key_id == KEY_UP or key.key_id == KEY_DOWN:
                if key.key_id == KEY_UP:
                    self.threshold_db += self.threshold_steps
                else:
                    self.threshold_db -= self.threshold_steps
                self.threshold_db = self.threshold_db if self.threshold_db >= 1 else 1
                self.threshold_db = self.threshold_db if self.threshold_db <= 150 else 150
            elif key.key_id == SHIFT_UP or key.key_id == SHIFT_DOWN:
                if key.key_id == SHIFT_UP:
                    self.nfft += self.nfft_step
                else:
                    self.nfft -= self.nfft_step
            elif key.key_id == SHIFT_LEFT or key.key_id == SHIFT_RIGHT:
                self.handle_move_legend(key)

    def handle_move_legend(self, key):
        if key.key_id == SHIFT_LEFT:
            self.legend.move_left()
        else:
            self.legend.move_right()

    def create_dataset_position_bar(self):
        if self.file_manager.is_streaming():
            return([CursesPixel(text='', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])

        top_bar = [CursesPixel(text='  ', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)]
        bottom_bar = [CursesPixel(text='  ', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)]
        for i in range(int(self.file_manager.total_files * ((self.legend.columns - 4) / self.file_manager.total_files))):
            ioi = i == int(self.file_manager.current_position * ((self.legend.columns - 4) / self.file_manager.total_files))
            top_bar.append(
                    CursesPixel(text='|' if ioi else '_', 
                                fg=-1, 
                                bg=STANDOUT_RED if ioi else COLOR_BLACK, 
                                attr=A_BOLD if ioi else A_NORMAL)
                )
            bottom_bar.append(
                    CursesPixel(text='^' if ioi else ' ', 
                                fg=-1, 
                                bg=STANDOUT_RED if ioi else COLOR_BLACK, 
                                attr=A_BOLD if ioi else A_NORMAL)
                )
        dataset_pos_bar = []
        dataset_pos_bar.extend(top_bar)
        dataset_pos_bar.extend([CursesPixel(text='\n', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])
        dataset_pos_bar.extend(bottom_bar)
        return(dataset_pos_bar)

    def create_channel_bar(self):
        top_bar = []
        bottom_bar = []
        chan_str = ' Channel: '
        available_width = self.legend.columns - len(chan_str)
        top_bar.append(CursesPixel(text='{}'.format(chan_str), fg=-1, attr=A_BOLD, bg=STANDOUT_GREEN))
        bottom_bar.append(CursesPixel(text=' ' * len(chan_str), fg=-1, attr=A_BOLD, bg=COLOR_BLACK))
        for i in range(self.available_channels):
            top_bar.append(
                    CursesPixel(text='{}'.format(i).center(int(available_width / self.available_channels)), 
                        fg=-1, attr=A_BOLD,
                        bg=COLOR_BLACK if self.display_channel != i else STANDOUT_GREEN),
                )
            bottom_bar.append(
                    CursesPixel(text='{}'.format(' ' if self.display_channel != i else '^').center(int(available_width / self.available_channels)), 
                        fg=-1, attr=A_BOLD,
                        bg=COLOR_BLACK if self.display_channel != i else STANDOUT_RED),
                )

        channel_bar = []
        channel_bar.extend(top_bar)
        channel_bar.extend(bottom_bar)
        return(channel_bar)

    def create_plot_mode_bar(self):
        mode_bar = []
        if self.ui.get_panel_mode() == 'Stacked':
            color = COLOR_YELLOW
        elif self.ui.get_panel_mode() == 'Best Fit':
            color = COLOR_GREEN
        else:
            color = COLOR_RED
        mode_bar.extend([
                CursesPixel(text='Window Mode: {}'.format(self.ui.get_panel_mode()).center(self.legend.columns), 
                    fg=-1, bg=color, attr=A_BOLD),
            ])
        return(mode_bar)

    def create_nav_mode_bar(self):
        mode_bar = []
        if self.file_manager.state == 'Streaming':
            color = COLOR_GREEN
        elif self.file_manager.state == 'Navigation':
            color = COLOR_YELLOW
        else:
            color = COLOR_RED
        mode_bar.extend([
                CursesPixel(text='Nav Mode: {}'.format(self.file_manager.state).center(self.legend.columns), 
                    fg=-1, bg=color, attr=A_BOLD),
            ])
        return(mode_bar)

    def create_intensity_bar(self):
        intensity_bar = []
        intensity_bar.extend([
                CursesPixel(text='  Quietest'.ljust(int(self.legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text='Loudest  '.rjust(int(self.legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
            ])
        intensity_bar.extend([
                CursesPixel(text=' ' * int(self.legend.columns / 5), fg=-1, bg=COLOR_CYAN, attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=COLOR_BLUE, attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=COLOR_GREEN, attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=COLOR_YELLOW, attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=COLOR_MAGENTA, attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=COLOR_RED, attr=A_BOLD),
                CursesPixel(text=' ', fg=-1, bg=COLOR_RED, attr=A_BOLD),
            ])
        lower_bound = '  {}dB'.format(self.threshold_db - self.threshold_steps * 2)
        upper_bound = '{}dB    '.format(self.threshold_db + self.threshold_steps * 2)
        intensity_bar.extend([
                CursesPixel(text=lower_bound.ljust(int(self.legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text='{}dB'.format(self.threshold_db), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text=upper_bound.rjust(int(self.legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
            ])
        intensity_bar.extend([CursesPixel(text='', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])
        return(intensity_bar)

    def get_formatted_dt(self):
        try:
            dt = datetime.datetime.fromtimestamp(float(self.file_manager.current_file.stem))
        except:
            dt = None
        return(str(dt))

    def cycle_channels(self, key):
        self.display_channel += 1

    def handle_plot_state_change(self, event):
        if 'RESIZE' in event:
            # see if we can expand the plot to fit the window
            self.handle_nfft(expand=True)

    def get_plot_dimensions(self):
        if not self.window.fill_screen:
            return(self.window.rows, self.window.columns)
        return(self.window.term_size)

    def full_screen(self, args):
        self.full_screen_mode ^= True # toggle
        if self.full_screen_mode:
            self.legend.hide_all()
        else:
            self.legend.show_all()
        self.window.refresh()

    def toggle_legend(self, args):
        self.legend.toggle_bottom()
        self.window.refresh()

    def redraw_specgram(self, *args):
        if self.file_manager.next_file() == self.current_file:
            if not self.first_draw:
                self.first_draw = True
            elif not self.force_redraw:
                return

        formatted_data = self.format_data(self.get_plot_dimensions())
        self.window.clear_buffer()
        for row in formatted_data:
            self.window.buffer.append(row)

    def get_data(self):
        self.current_file = self.file_manager.next_file()
        data = []
        with open(str(self.current_file), 'r') as f:
            for line in f.readlines():
                channel_data = line.strip().split(',')
                self.available_channels = len(channel_data)
                if self.available_channels <= 0:
                    raise ValueError('Data file is empty!')
                elif self.available_channels <= self.display_channel:
                    self.display_channel = 0
                data.append(float(channel_data[self.display_channel]))
        return(data)

    def validate_mark_freq(self, minfreq, maxfreq):
        if self.markfreq_hz > maxfreq:
            self.markfreq_hz = maxfreq
        elif self.markfreq_hz < minfreq:
            self.markfreq_hz = minfreq

    def get_markfreq_data(self, minfreq, maxfreq, freqlist):
        self.validate_mark_freq(minfreq=minfreq, maxfreq=maxfreq)
        i = 0
        for f in freqlist:
            if f > self.markfreq_hz-freqlist[1] / 2 and f <= self.markfreq_hz + freqlist[1] / 2:
                self.markfreq_hz = f
                return(i)
            i += 1
        return(0)

    def get_time_data(self, axis):
        time_vector = []
        for t in axis:
            time_vector.append(int(float(t) / self.sample_rate * 1000))
        return(time_vector)

    def format_x_axis(self, freq_marker_column):
        x_axis = {
            'info_row': [' ' * (self.vertical_axis_width - 1)],
            'border_row': [' ' * (self.vertical_axis_width - 1)]
        }
        for column in range(int(self.nfft / 2)):
            if column != freq_marker_column:
                x_axis['info_row'].append(' ')
                x_axis['border_row'].append('-')
            else:
                x_axis['info_row'].append('{}Hz'.format(int(self.markfreq_hz)))
                x_axis['border_row'].append('|')

        # truncate extra spaces in info_row so both x_axis lists are the same length
        x_axis['info_row'], x_axis['border_row'] = zip(*zip(x_axis['info_row'], x_axis['border_row']))
        return(x_axis)

    def handle_nfft(self, expand=False):
        old_nfft = self.nfft
        if self.window.columns < ((self.nfft / 2) + self.vertical_axis_width):
            # we need to make nfft smaller
            while self.window.columns < ((self.nfft / 2) + self.vertical_axis_width):
                self.nfft -= self.nfft_step

        elif expand:
            # we can make it bigger!
            while self.window.columns > ((self.nfft / 2) + self.vertical_axis_width):
                self.nfft += self.nfft_step
                if self.window.columns < ((self.nfft / 2) + self.vertical_axis_width):
                    self.nfft -= self.nfft_step
                    break

        with open('_debug.log', 'a+') as f:
            output = '!!!!!!!!!!!!!!!!'
            output += '\n nfft (new/old): {}/{}'.format(self.nfft, old_nfft)
            output += '\n first condition: {}'.format(self.window.columns < ((self.nfft / 2) + self.vertical_axis_width))
            output += '\n second condition: {}'.format(expand)
            output += '\n ---> rows, columns: ({}, {})'.format(self.window.rows, self.window.columns)
            output += '\n!!!!!!!!!!!!!!!\n'
            f.write(output)

    def format_x_axis_pixels(self, line, attr):
        formatted_row = []
        for i in range(len(line)):
            formatted_row.append(CursesPixel(text=line[i], fg=COLOR_BLACK, bg=COLOR_BLACK, attr=attr))
        return(formatted_row)

    def format_data(self, term_size):
        # make sure nfft will work for current term size
        self.handle_nfft()
        # create matrix with color for dB intensity that fits in alloted rows
        try:
            axis, rows = self.fit_data(*self.create_specgram())
        except ValueError:
            # TODO handle values too low error with popup error
            return([])

        freqlist = numpy.fft.fftfreq(self.nfft) * self.sample_rate
        maxfreq = freqlist[int(self.nfft / 2 - 1)]
        minfreq = freqlist[1]

        freq_marker_column = self.get_markfreq_data(minfreq=minfreq, maxfreq=maxfreq, freqlist=freqlist)
        x_axis = self.format_x_axis(freq_marker_column)
        y_axis = self.get_time_data(axis=axis)
        info_line = ''.join([str(val) for val in x_axis['info_row']])
        border_line = ''.join([str(val) for val in x_axis['border_row']])

        # output data
        formatted_data = [] # list of lists 2D
        formatted_info_line = []  # 1D row of CursesPixels
        formatted_border_line = []  # 1D row of CursesPixels

        formatted_info_line = self.format_x_axis_pixels(info_line, A_BOLD)
        formatted_border_line = self.format_x_axis_pixels(border_line, A_NORMAL)
        formatted_data.append(formatted_info_line)
        formatted_data.append(formatted_border_line)

        # append y-axis AND each row data to output buffer
        for row, row_data in enumerate(rows):
            line = '0.{}| '.format(str(y_axis[row]).zfill(3))
            formatted_row = [CursesPixel(text=ch, fg=COLOR_BLACK, bg=COLOR_BLACK, attr=A_NORMAL) for ch in line]
            for col, color in enumerate(row_data):
                if col != freq_marker_column:
                    formatted_row.append(CursesPixel(text=' ', fg=COLOR_BLACK, bg=color, attr=A_NORMAL))
                else:
                    formatted_row.append(CursesPixel(text='|', fg=COLOR_BLACK, bg=color, attr=A_BOLD))
            formatted_data.append(formatted_row)

        # append x-axis data to output buffer in reverse order
        formatted_data.append(formatted_border_line)
        formatted_data.append(formatted_info_line)

        return(formatted_data)

    # found here:
    # https://stackoverflow.com/questions/3012721/downsampling-the-number-of-entries-in-a-list-without-interpolation
    def downsample_to_max(self, rows, max_rows):
        return(self.downsample_to_proportion(rows, max_rows / float(len(rows))))

    # see stackoverflow link
    def downsample_to_proportion(self, rows, proportion):
        counter = 0.0
        last_counter = None
        results = []

        for row in rows:
            counter += proportion

            if int(counter) != last_counter:
                results.append(row)
                last_counter = int(counter)

        return(results)

    def fit_data(self, axis, rows):
        return(self.downsample_to_max(axis, self.window.columns), 
               self.downsample_to_max(rows, self.window.columns))

    def create_specgram(self):
        done = False
        start = 0
        try:
            data = self.get_data()
        except IOError:
            data = [0.0]

        rows = []
        time_vector = []
        while not done:
            frequency_db_vector = []
            try:
                frequency_vector = numpy.fft.fft(data[start:start + self.nfft])
                for x in frequency_vector[0:int(self.nfft / 2)]:
                    frequency_db_vector.append(20 * math.log(abs(x) / pow(10, -6), 10))
            except ValueError:
                if len(data[start:start + self.nfft]) <= 0:
                    break
                else:
                    raise ValueError('Values too low for threshold \n{}'.format(traceback.format_exc()))
           
            self.argmax_freq = frequency_db_vector.index(max(frequency_db_vector))
            line=[]
            for f in frequency_db_vector:
                if int(f) >= self.threshold_db:
                    if int(f) - self.threshold_db <= self.threshold_steps:       # closest to thresh
                        line.append(COLOR_YELLOW)
                    elif int(f) - self.threshold_db < self.threshold_steps * 2:  # in between closest and max
                        line.append(COLOR_MAGENTA)
                    elif int(f) - self.threshold_db >= self.threshold_steps * 2: # loudest
                        line.append(COLOR_RED)
                else:
                    if self.threshold_db - int(f) <= self.threshold_steps:      # close to thresh
                        line.append(COLOR_GREEN)
                    elif self.threshold_db - int(f) < self.threshold_steps * 2: # in between 
                        line.append(COLOR_CYAN)
                    elif self.threshold_db - int(f) >= self.threshold_steps * 2:  # quietest
                        line.append(COLOR_BLUE)

            rows.append(line)
            time_vector.append(start + self.nfft / 2)
            start += self.nfft
            if start > (self.sample_rate * self.file_length_sec) - self.nfft:
                done = True
        return(time_vector, rows)