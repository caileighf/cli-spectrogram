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
from collections import OrderedDict
from cached_ui_elements import (handle_ui_element_cache, invalidate_ui_element_cache, invalidate_cache)
from common import (KeystrokeCallable, WindowDimensions, FileNavManager, CursesPixel, is_python_2_7)
from common import (default_emphasis, ESC, Q_MARK, SHIFT_UP, SHIFT_DOWN, SHIFT_LEFT, SHIFT_RIGHT)
from common import (
        BACKGROUND_COLOR,
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
from common import (
        full_color,
        grayscale_color,
        full_color_standout,
        grayscale_color_standout,
        full_color_accent,
        grayscale_color_accent
    )
import sys, time
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
                    A_BLINK,
                    A_REVERSE,
                    A_STANDOUT,
                    A_VERTICAL,
                    A_PROTECT,
                    KEY_MOUSE,
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
                       ui,
                       device_name,
                       legend_side=RIGHT,
                       display_channel=0, 
                       threshold_db=90, 
                       markfreq_hz=5000, 
                       threshold_steps=1, 
                       nfft=240,
                       sample_rate=19200,
                       file_length=1.0,
                       use_full_color=True,
                       skip_empty=False):
        super(Specgram, self).__init__()
        self.ui = ui # ui instance for creating plot window and legend windows
        self.window = ui.new_full_size_window(name='specgram_plot')
        self.first_draw = True
        self.force_redraw = True
        self.window.add_callback(self.redraw_specgram)
        self.window.fill_screen = True
        self.window.on_state_change.append(self.handle_plot_state_change)
        self.window.set_background_color(BACKGROUND_COLOR)

        self.max_rows = self.window.rows
        self.max_columns = self.window.columns
        self.vertical_axis_width = 8    # 8 characters for the vertical axis
        self.horizontal_axis_height = 6 # 6 characters for the horizontal axis 

        self.source = source
        self.display_channel = display_channel
        self.available_channels = display_channel + 1 # zero indexed channels
                                                      # we will update once we get a look at the data files
        self.threshold_db = threshold_db
        self.markfreq_hz = markfreq_hz
        self.markfreq_char = '|'
        self.threshold_steps = threshold_steps
        self.nfft = nfft
        self.nfft_step = 10
        self.sample_rate = sample_rate
        self.file_length_sec = file_length
        self.argmax_freq = 0

        self.skip_empty = skip_empty
        self.file_manager = FileNavManager(data_dir=self.source, skip_empty=skip_empty)
        self.current_file = self.file_manager.next_file()
        self.device_name = device_name
        self.data = []
        self.current_rows = []
        self.current_axis = []
        self.is_scroll_active = False
        self.scroll_up_step = -15
        self.scroll_dn_step = 15
        self.scroll_top_min = 9
        self.scroll_line_index = {'top': 0, 'bottom': 0}
        self.mini_legend_mode = False
        self.cached_legend_elements = {}

        self.full_screen_mode = False
        self._init_color(use_full_color)

        self._init_keymap()
        self._init_cmd_map()
        self._init_legend(legend_side)
        self._init_ui_help()
        self.handle_plot_state_change(event='INITIAL_RESIZE')

    def _init_legend(self, legend_side):
        rows, _ = self.window.term_size
        self.legend = self.ui.new_legend(name='specgram_legend', 
                                         num_panels=1, 
                                         get_legend_dict=self.legend_data, 
                                         type_=SINGLE_V, 
                                         shared_dimension=50, 
                                         side=legend_side)
        self.legend.default_key = 'UPPER'
        self.legend.footer = 'Show ALL keyboard shortcuts with ? or space'
        self.legend.set_x_label('Frequency (Hz)')
        self.legend.set_y_label('Time (relative to file start)')

    def _init_color(self, use_full_color):
        self.use_full_color = use_full_color
        self.color = full_color if self.use_full_color else grayscale_color
        self.standout_color = full_color_standout if self.use_full_color else grayscale_color_standout
        self.accent_color = full_color_accent if self.use_full_color else grayscale_color_accent

    @invalidate_cache(cache='cached_legend_elements')
    def toggle_grayscale(self, *args):
        self._init_color(use_full_color=not self.use_full_color)

    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__scroll_mode_bar__')
    def toggle_scroll_mode(self, *args):
        self.is_scroll_active ^= True
        self.scroll_line_index['top'] = 0
        self.scroll_line_index['bottom'] = self.window.rows

    def handle_mouse_event(self, *args):
        lines_to_scroll = 0
        _id, x, y, z, mouse_state = args
        dir_switch = False
        if mouse_state == 134217728:
            lines_to_scroll = self.scroll_up_step
            self.log('Scroll UP')
        elif mouse_state == 524288:
            lines_to_scroll = self.scroll_dn_step
            self.log('Scroll DOWN')
        elif mouse_state == 128:
            # switching scrolling direction!
            self.scroll_dn_step *= -1
            self.scroll_up_step *= -1
            self.log('Switching directions!')
            dir_switch = True

        if not self.is_scroll_active and lines_to_scroll != 0:
            self.toggle_scroll_mode()

        if not dir_switch:
            self.scroll(lines_to_scroll)
            self.log('scroll_line_index: top: {} bottom: {}'.format(self.scroll_line_index['top'], self.scroll_line_index['bottom']))
        else:
            self.ui.flash_message(output=['Switching scroll directions!'], 
                                  duration_sec=1.5,
                                  flash_screen=False)

    def scroll(self, lines):
        if lines > 0:
            # this ensures empty files show full error
            if self.scroll_line_index['top'] > self.scroll_top_min:
                self.scroll_line_index['top'] -= lines
                self.scroll_line_index['bottom'] -= lines
            else:
                self.ui.beep() # lets user know they hit boundary
        else:
            lines *= -1
            if self.scroll_line_index['bottom'] < len(self.current_rows):
                self.scroll_line_index['top'] += lines
                self.scroll_line_index['bottom'] += lines
            else:
                self.ui.beep() # lets user know they hit boundary

    @invalidate_cache(cache='cached_legend_elements')
    def reverse_color_map(self, *args):
        self.color.reverse()

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
            KeystrokeCallable(key_id=ord('G'),
                              key_name='G',
                              call=[self.toggle_grayscale],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('H'),
                              key_name='H',
                              call=[self.toggle_legend],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('M'),
                              key_name='M',
                              call=[self.toggle_minimal_mode],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('R'),
                              key_name='R',
                              call=[self.reverse_color_map],
                              case_sensitive=False),
            KeystrokeCallable(key_id=ord('S'),
                              key_name='S',
                              call=[self.toggle_scroll_mode],
                              case_sensitive=False),
            KeystrokeCallable(key_id=KEY_UP,
                              key_name='Up',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=KEY_DOWN,
                              key_name='Down',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=KEY_LEFT,
                              key_name='Left',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=KEY_RIGHT,
                              key_name='Right',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=SHIFT_LEFT,
                              key_name='Shift + Left',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=SHIFT_RIGHT,
                              key_name='Shift + Right',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=SHIFT_UP,
                              key_name='Shift + Up',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=SHIFT_DOWN,
                              key_name='Shift + Down',
                              call=[self.handle_plot_change]),
            KeystrokeCallable(key_id=KEY_PPAGE,
                              key_name='Previous Page',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_NPAGE,
                              key_name='Next Page',
                              call=[self.handle_navigation]),
            KeystrokeCallable(key_id=ESC,
                              key_name='Escape',
                              call=[]),#self.handle_navigation]),
            KeystrokeCallable(key_id=KEY_MOUSE,
                              key_name='Mouse Event',
                              call=[self.handle_mouse_event],
                              case_sensitive=False),
        ]
        for key in self.keymap:
            self.ui.register_keystroke_callable(keystroke_callable=key, update=True)

    def log(self, output, end='\n'):
        with open('keystrokes.log', 'a+') as f:
            f.write('[{}]: {}{}'.format(int(time.time()), output, end))

    def close(self):
        self.file_manager.close()

    def legend_data(self):
        legend_dict = {
            'UPPER': {
                'File Information': {
                    'File': self.file_manager.current_file.name,
                    'Data Loc': str(self.get_formatted_data_dir()),
                    'Time': str(self.get_formatted_dt()),
                    'Device Name': self.device_name,
                    '__dataset_position_marker__':
                        self.create_dataset_position_bar()
                },
                'Spectrogram Information': {
                    'Threshold (dB)': self.threshold_db,
                    'Sample Rate (Hz)': self.sample_rate,
                    'Max Freq': self.argmax_freq,
                    'NFFT': self.nfft,
                    'Vertical Axis': self.legend.y_label,
                    'Horizontal Axis': self.legend.x_label,
                    '__channel_bar__':
                        self.create_channel_bar(),
                    '__scroll_mode_bar__':
                        self.create_scroll_mode_bar(),
                    '__nav_mode_bar__': 
                        self.create_nav_mode_bar(),
                    '__plot_mode_bar__':
                        self.create_plot_mode_bar(),
                    '__intensity_bar__': 
                        self.create_intensity_bar(),
                },
            },
            'LOWER': {
                'Keyboard Shortcuts': {
                    'Up / Down': 'Adjust color threshold by +/-{}dB'.format(self.threshold_steps),
                    'Shift + (Up / Down)': 'Adjust NFFT by +/-{}'.format(self.nfft_step),
                    'Left / Right': 'Move mark frequency by +/-100Hz',
                    'C / c': 'Cycle through channels',
                    'Pg Up / Pg Down': 'Previous file / Next file',
                    'A / a': 'Move backwards 60 seconds / 10 seconds',
                    'D / d': 'Move forwards 60 seconds / 10 seconds',
                    'B / b': 'Jump to beginning of dataset',
                    'E / e': 'Jump to end of dataset',
                    'Escape': 'Resume streaming',
                    '__hline01__': self.legend.hline(ch=' '),
                    'Shift + Left': 'Move legend left',
                    'Shift + Right': 'Move legend right',
                    'H / h': 'Toggle keyboard shortcuts on / off',
                    'F / f': 'Toggle full screen on / off',
                    'G / g': 'Toggle grayscale / full color',
                    'R / r': 'Reverse color map',
                    '__hline02__': self.legend.hline(ch=' '),
                    'S / s': 'Toggle scroll to scroll through file',
                    'Scroll Up / Down': 'Explore full data file',
                    'Scroll wheel button': 'Reverse scroll direction',
                },
            },
            '__minimal__': {
                'Spectrogram Information': {
                    'Time': str(self.get_formatted_dt()),
                    'Threshold (dB)': self.threshold_db,
                    'Sample Rate (Hz)': self.sample_rate,
                    'Max Freq': self.argmax_freq,
                    'NFFT': self.nfft,
                    '__dataset_position_marker__':
                        self.create_dataset_position_bar(),
                    '__channel_bar__':
                        self.create_channel_bar(),
                    '__scroll_mode_bar__':
                        self.create_scroll_mode_bar(),
                    '__nav_mode_bar__': 
                        self.create_nav_mode_bar(),
                    '__intensity_bar__': 
                        self.create_intensity_bar(),
                },
            },
        }

        if is_python_2_7:
            if self.mini_legend_mode:
                legend_dict['__minimal__']['Spectrogram Information']\
                 = OrderedDict(sorted(legend_dict['__minimal__']['Spectrogram Information'].items()))
            else:
                legend_dict['UPPER'] = OrderedDict(sorted(legend_dict['UPPER'].items()))
                legend_dict['UPPER']['File Information']\
                 = OrderedDict(sorted(legend_dict['UPPER']['File Information'].items()))
                legend_dict['UPPER']['Spectrogram Information']\
                 = OrderedDict(sorted(legend_dict['UPPER']['Spectrogram Information'].items()))
                legend_dict['LOWER']['Keyboard Shortcuts']\
                 = OrderedDict(sorted(legend_dict['LOWER']['Keyboard Shortcuts'].items()))

        return(legend_dict)

    def _init_ui_help(self):
        try:
            help_ = self.get_formatted_kb_shortcuts()
        except KeyError:
            help_ = {'Problem loading shortcuts':'Check legend keys'}

        rc = self.ui.set_help_info(info=help_, title='Spectrogram Keyboard Shortcuts')
        return(rc)

    def get_formatted_kb_shortcuts(self):
        try:
            return(self.legend_data()['LOWER']['Keyboard Shortcuts'])
        except KeyError:
            raise KeyError('Unable to get formatted keyboard shortcuts! Check legend keys')

    @invalidate_cache(cache='cached_legend_elements')
    def handle_minimal_mode(self, *args):
        if hasattr(self, 'mini_legend'):
            if self.mini_legend_mode:
                self.mini_legend.show_all()
                self.legend.hide_all()
            else:
                self.mini_legend.hide_all()
                self.legend.show_all()
        else:
            self.legend.hide_all()
            self.mini_legend = self.ui.new_legend(name='specgram_mini_legend', 
                                                  num_panels=1, 
                                                  get_legend_dict=self.legend_data, 
                                                  type_=SINGLE_H, 
                                                  shared_dimension=50, 
                                                  side=TOP_RIGHT)
            self.mini_legend.minimal_mode = True
            self.mini_legend.footer = 'Show ALL keyboard shortcuts with ? or space'
            self.ui.add_legend_manager(name='specgram_mini_legend', manager=self.mini_legend)

        if self.ui.get_panel_mode() == 'Best Fit':
            self.ui.toggle_overlap_mode()

    def toggle_minimal_mode(self, *args):
        self.mini_legend_mode ^= True
        self.handle_minimal_mode()
        if self.mini_legend_mode:
            self.ui.flash_message(output=['Minimal Legend Mode Active'], 
                                  duration_sec=1.0,
                                  flash_screen=False)

    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__dataset_position_marker__')
    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__nav_mode_bar__')
    def handle_position_cache(self):
        pass

    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__intensity_bar__')
    def handle_plot_attrs_cache(self):
        pass

    def handle_plot_change(self, key):
        start = time.time()
        if key.key_id == KEY_LEFT or key.key_id == KEY_RIGHT:
            if key.key_id == KEY_RIGHT:
                self.markfreq_hz += 100
            else:
                self.markfreq_hz -= 100
            self.markfreq_hz = self.markfreq_hz if self.markfreq_hz >= 1 else 1
            self.markfreq_hz = self.markfreq_hz if self.markfreq_hz <= 10000 else 10000
        elif key.key_id == KEY_UP or key.key_id == KEY_DOWN:
            self.handle_plot_attrs_cache()
            if key.key_id == KEY_UP:
                self.threshold_db += self.threshold_steps
            else:
                self.threshold_db -= self.threshold_steps
            self.threshold_db = self.threshold_db if self.threshold_db >= 1 else 1
            self.threshold_db = self.threshold_db if self.threshold_db <= 150 else 150
        elif key.key_id == SHIFT_UP or key.key_id == SHIFT_DOWN:
            self.handle_plot_attrs_cache()
            if key.key_id == SHIFT_UP:
                self.nfft += self.nfft_step
            else:
                self.nfft -= self.nfft_step
        elif key.key_id == SHIFT_LEFT or key.key_id == SHIFT_RIGHT:
            self.handle_move_legend(key)
        stop = time.time()
        self.log('specgram::handle_plot_change() Timer: %.3f seconds' % (stop - start))

    def _init_cmd_map(self):
        self.cmd_map = {}
        self.ui.register_general_cmd_callback(callback=[self.handle_cmd])

    def goto(self, *args):
        h = m = s = 0
        if len(args) > 3 or len(args) < 1:
            return
        if len(args) == 3:
            h, m, s = args
        elif len(args) == 2:
            h, m = args
        elif len(args) == 1:
            h = args

        rel_time = float(self.file_manager.current_file.stem)
        rel_time = datetime.datetime.fromtimestamp(rel_time)

        target_time = datetime.datetime.combine(date=rel_time.date(),
                                                time=datetime.time(hour=int(h),
                                                                   minute=int(m),
                                                                   second=int(s)))

        # raise ValueError('{}:{}:{}\n\ntotal delta sec: {}\nrel_t: {}\ntarg_t: {}\n'.format(h, m, s, 
        #      (rel_time - target_time).total_seconds(), rel_time, target_time))
        if rel_time > target_time:
            return int((rel_time - target_time).total_seconds())
        elif rel_time < target_time:
            return int(-(rel_time - target_time).total_seconds())
        # raise ValueError('{}:{}:{}\n\ntotal delta sec: {}\n\n{}'.format(h, m, s, total_delta_sec, rel_time))

    def handle_cmd(self, **kwargs):
        if kwargs and 'key' in kwargs:
            key = kwargs['key']
            if 'val' in kwargs:
                val = kwargs['val']
            else:
                val = None
        else:
            self.ui.beep()
            return

        if key in self.__dict__:
            _type = type(self.__dict__[key])
            self.__dict__[key] = _type(val)
        elif key == 'print' and val in self.__dict__:
            self.ui.flash_message('{}: {}'.format(val, self.__dict__[val]),
                                  flash_screen=False,
                                  duration_sec=1.5)
        elif 'begin' in key and val == None:
            self.handle_position_cache()
            cursor_pos = self.file_manager.move_to_beginning()
        elif 'end' == key or 'stream' == key and val == None:
            self.handle_position_cache()
            cursor_pos = self.file_manager.move_to_end()
        elif 'goto' == key and val != None:
            self.handle_position_cache()
            _time = val.split(':')
            total_delta_sec = self.goto(*_time)
            self.file_manager.move_cursor(delta=-int(total_delta_sec / self.file_length_sec))

    def handle_navigation(self, key):
        start = time.time()
        if not key.case_sensitive:
            if key.key_name.upper() == 'B':
                self.handle_position_cache()
                cursor_pos = self.file_manager.move_to_beginning()
            elif key.key_name.upper() == 'E':
                self.handle_position_cache()
                cursor_pos = self.file_manager.move_to_end()
            elif key.key_name.upper() == 'A':
                self.handle_position_cache()
                if key.key_name.isupper():
                    cursor_pos = self.file_manager.move_cursor(delta=-int(600 / self.file_length_sec)) # 10 mins
                else:
                    cursor_pos = self.file_manager.move_cursor(delta=-int(60 / self.file_length_sec))  # 1 min
            elif key.key_name.upper() == 'D':
                self.handle_position_cache()
                if key.key_name.isupper():
                    cursor_pos = self.file_manager.move_cursor(delta=+int(600 / self.file_length_sec)) # 10 mins
                else:
                    cursor_pos = self.file_manager.move_cursor(delta=+int(60 / self.file_length_sec))  # 1 min

        else:
            if key.key_id == KEY_PPAGE:
                self.handle_position_cache()
                cursor_pos = self.file_manager.move_cursor(delta=-1)
            elif key.key_id == KEY_NPAGE:
                self.handle_position_cache()
                cursor_pos = self.file_manager.move_cursor(delta=1)
            elif key.key_id == ESC:
                self.handle_position_cache()
                cursor_pos = self.file_manager.move_to_end()
                if self.mini_legend_mode:
                    self.toggle_minimal_mode()

        stop = time.time()
        self.log('specgram::handle_navigation() Timer: %.3f seconds' % (stop - start))

    def handle_move_legend(self, key):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        if key.key_id == SHIFT_LEFT:
            legend.move_left()
        elif key.key_id == SHIFT_RIGHT:
            legend.move_right()

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__dataset_position_marker__')  
    def create_dataset_position_bar(self):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        if self.file_manager.is_streaming():
            return([CursesPixel(text='', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])

        top_bar = [CursesPixel(text='  ', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)]
        bottom_bar = [CursesPixel(text='  ', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)]
        for i in range(int(self.file_manager.total_files * ((legend.columns - 4) / self.file_manager.total_files))):
            ioi = i == int(self.file_manager.current_position * ((legend.columns - 4) / self.file_manager.total_files))
            top_bar.append(
                    CursesPixel(text='|' if ioi else '_', 
                                fg=-1, 
                                bg=self.standout_color[1] if ioi else COLOR_BLACK,
                                attr=A_BOLD if ioi else A_NORMAL)
                )
            bottom_bar.append(
                    CursesPixel(text='^' if ioi else ' ', 
                                fg=-1, 
                                bg=self.standout_color[1] if ioi else COLOR_BLACK, 
                                attr=A_BOLD if ioi else A_NORMAL)
                )
        dataset_pos_bar = []
        dataset_pos_bar.extend(top_bar)
        dataset_pos_bar.extend([CursesPixel(text='\n', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])
        dataset_pos_bar.extend(bottom_bar)
        return(dataset_pos_bar)

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__channel_bar__')  
    def create_channel_bar(self):
        self.validate_channel_count()
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        top_bar = []
        bottom_bar = []
        chan_str = ' Channel: '
        available_width = self.legend.columns - len(chan_str)
        top_bar.append(CursesPixel(text='\n{}'.format(chan_str), fg=-1, attr=A_BOLD, bg=self.standout_color[0]))
        bottom_bar.append(CursesPixel(text=' ' * len(chan_str), fg=-1, attr=A_BOLD, bg=COLOR_BLACK))
        for i in range(self.available_channels):
            top_bar.append(
                    CursesPixel(text='{}'.format(i).center(int(available_width / self.available_channels)), 
                        fg=-1, attr=A_BOLD,
                        bg=COLOR_BLACK if self.display_channel != i else self.standout_color[0]),
                )
            bottom_bar.append(
                    CursesPixel(text='{}'.format(' ' if self.display_channel != i else '^').center(int(available_width / self.available_channels)), 
                        fg=-1, attr=A_BOLD,
                        bg=COLOR_BLACK if self.display_channel != i else self.standout_color[1]),
                )

        channel_bar = []
        channel_bar.extend(top_bar)
        channel_bar.extend(bottom_bar)
        return(channel_bar)

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__scroll_mode_bar__')
    def create_scroll_mode_bar(self):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        mode_bar = []
        if self.is_scroll_active:
            color = self.accent_color[1]
            scroll_mode_text = 'ON (full Spectrogram)'
        else:
            color = self.accent_color[0]
            scroll_mode_text = 'OFF (shrunk-to-fit Spectrogram)'

        mode_bar.extend([
                CursesPixel(text='Scroll Mode: {}'.format(scroll_mode_text).center(legend.columns), 
                    fg=-1, bg=color, attr=A_BOLD),
            ])
        return(mode_bar)

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__plot_mode_bar__')
    def create_plot_mode_bar(self):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        mode_bar = []
        if self.ui.get_panel_mode() == 'Stacked':
            color = self.accent_color[1]
        elif self.ui.get_panel_mode() == 'Best Fit':
            color = self.accent_color[0]
        else:
            color = self.accent_color[2]

        mode_bar.extend([
                CursesPixel(text='Window Mode: {}'.format(self.ui.get_panel_mode()).center(legend.columns), 
                    fg=-1, bg=color, attr=A_BOLD),
            ])
        return(mode_bar)

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__nav_mode_bar__')
    def create_nav_mode_bar(self):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        mode_bar = []
        if self.file_manager.state == 'Streaming':
            color = self.accent_color[0]
        elif self.file_manager.state == 'Navigation':
            color = self.accent_color[1]
        else:
            color = self.accent_color[2]
        mode_bar.extend([
                CursesPixel(text='Nav Mode: {}'.format(self.file_manager.state).center(legend.columns), 
                    fg=-1, bg=color, attr=A_BOLD),
            ])
        return(mode_bar)

    @handle_ui_element_cache(cache='cached_legend_elements', target_element='__intensity_bar__')
    def create_intensity_bar(self):
        if self.mini_legend_mode:
            legend = self.mini_legend
        else:
            legend = self.legend

        intensity_bar = []
        intensity_bar.extend([
                CursesPixel(text='  Quietest'.ljust(int(legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text='Loudest  '.rjust(int(legend.columns / 2)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
            ])
        intensity_bar.extend([
                CursesPixel(text=' ' * int(self.legend.columns / 5), fg=-1, bg=self.color[0], attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=self.color[1], attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=self.color[2], attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=self.color[3], attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=self.color[4], attr=A_BOLD),
                CursesPixel(text=' ' * int(self.legend.columns / 6), fg=-1, bg=self.color[5], attr=A_BOLD),
                CursesPixel(text=' ',                                fg=-1, bg=self.color[5], attr=A_BOLD),
            ])
        lower_bound = ' {}dB'.format(self.threshold_db - self.threshold_steps * 2)
        current_dB = '{}dB'.format(self.threshold_db)
        upper_bound = '{}dB '.format(self.threshold_db + self.threshold_steps * 2)
        intensity_bar.extend([
                CursesPixel(text=lower_bound.ljust(int(legend.columns / 3)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text=current_dB.center(int(legend.columns / 3)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
                CursesPixel(text=upper_bound.rjust(int(legend.columns / 3)), fg=-1, bg=COLOR_BLACK, attr=A_BOLD),
            ])
        intensity_bar.extend([CursesPixel(text='', fg=-1, bg=COLOR_BLACK, attr=A_BOLD)])
        return(intensity_bar)

    def get_formatted_dt(self):
        try:
            dt = datetime.datetime.fromtimestamp(float(self.file_manager.current_file.stem))
        except:
            dt = None
        return(dt)

    def get_formatted_data_dir(self):
        dir_str = str(self.file_manager.current_file.parent)
        max_width = self.mini_legend.columns - 20\
         if self.mini_legend_mode\
          else self.legend.columns - 20

        formatted_dir = dir_str[-(max_width):] + '/'
        return('<<' + formatted_dir[formatted_dir.find('/') + 1:])

    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__channel_bar__')
    def cycle_channels(self, key):
        self.display_channel += 1

    @invalidate_ui_element_cache(cache='cached_legend_elements', target_element='__plot_mode_bar__')
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

        # Toggle correct legend for mode
        if self.mini_legend_mode:
            self.mini_legend.hide_all()\
             if self.full_screen_mode\
              else self.mini_legend.show_all()
        else:
            self.legend.hide_all()\
             if self.full_screen_mode\
              else self.legend.show_all()

        # Expand plot if in best fit mode
        if self.full_screen_mode:
            if self.ui.get_panel_mode() == 'Best Fit':
                self.ui.toggle_overlap_mode()

        self.window.refresh()

    def toggle_legend(self, args):
        self.legend.toggle_bottom()
        self.window.refresh()

    def redraw_specgram(self, *args):
        if self.file_manager.next_file() == self.current_file:
            if self.first_draw:
                self.first_draw = False
            elif not self.force_redraw:
                return

        formatted_data = self.format_data(self.get_plot_dimensions(), shrink_to_fit=not self.is_scroll_active)
        self.window.clear_buffer()

        if self.is_scroll_active and len(formatted_data) >= 20:
            for row in formatted_data[self.scroll_line_index['top']: self.scroll_line_index['bottom']]:
                self.window.buffer.append(row)
        else:
            for row in formatted_data:
                self.window.buffer.append(row)

    def validate_channel_count(self):
        with open(str(self.file_manager.next_file()), 'r') as f:
            line = f.readline()
            self.available_channels = len(line.strip().split(','))
            
        self.file_manager.move_to_end()

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

        if self.nfft <= 0:
            self.nfft = 0
            if not self.full_screen_mode:
                self.ui.flash_message(['Hiding legend(s)-',
                                       '-to fit Spectrogram!'], 
                                       flash_screen=False)
                self.full_screen(None)
                self.handle_nfft(expand=True)

    def format_x_axis_pixels(self, line, attr):
        formatted_row = []
        for i in range(len(line)):
            formatted_row.append(CursesPixel(text=line[i], fg=COLOR_BLACK, bg=COLOR_BLACK, attr=attr))
        return(formatted_row)

    def format_data(self, term_size, shrink_to_fit=True):
        # make sure nfft will work for current term size
        self.handle_nfft()
        
        # output data
        formatted_data = [] # list of lists 2D
        formatted_info_line = []  # 1D row of CursesPixels
        formatted_border_line = []  # 1D row of CursesPixels

        # create matrix with color for dB intensity that fits in alloted rows
        try:
            axis, rows = self.create_specgram()
            self.current_axis = axis
            self.current_rows = rows
            if len(rows) <= 0:
                # TODO: handle this better...
                raise ZeroDivisionError('Empty data file')

            if shrink_to_fit:
                axis, rows = self.fit_data(axis, rows)

        except ValueError:
            # TODO handle values too low error with popup error
            self.ui.flash_message(output=['NFFT set TOO LOW!',
                                          'nfft: {}'.format(self.nfft)], 
                                  duration_sec=1.5,
                                  flash_screen=False)
            return([])
        except ZeroDivisionError:
            self.log('Found empty data file!')
            error_text = [
                'THIS DATA FILE IS EMPTY!'.center(self.window.columns),
                'You are seeing this messages because the default behavior-'.center(self.window.columns),
                '-is to show these gaps. To skip empty files, pass --skip-empty'.center(self.window.columns),
                ]
            formatted_data.append(self.window.hline(ch=' '))
            formatted_data.append([CursesPixel(text=error_text[0], fg=COLOR_BLACK, bg=COLOR_BLACK, attr=A_BOLD | A_BLINK)])
            for line in error_text[1:]:
                formatted_data.append([CursesPixel(text=line, fg=COLOR_BLACK, bg=COLOR_BLACK, attr=A_BOLD)])
            return(formatted_data)

        freqlist = numpy.fft.fftfreq(abs(self.nfft)) * self.sample_rate
        maxfreq = freqlist[int(self.nfft / 2 - 1)]
        minfreq = freqlist[1]

        freq_marker_column = self.get_markfreq_data(minfreq=minfreq, maxfreq=maxfreq, freqlist=freqlist)
        x_axis = self.format_x_axis(freq_marker_column)
        y_axis = self.get_time_data(axis=axis)
        info_line = ''.join([str(val) for val in x_axis['info_row']])
        border_line = ''.join([str(val) for val in x_axis['border_row']])

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
                    formatted_row.append(CursesPixel(text=self.markfreq_char, fg=COLOR_BLACK, bg=color, attr=A_BOLD))
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
                        line.append(self.color[3])
                    elif int(f) - self.threshold_db < self.threshold_steps * 2:  # in between closest and max
                        line.append(self.color[4])
                    elif int(f) - self.threshold_db >= self.threshold_steps * 2: # loudest
                        line.append(self.color[5])
                else:
                    if self.threshold_db - int(f) <= self.threshold_steps:      # close to thresh
                        line.append(self.color[2])
                    elif self.threshold_db - int(f) < self.threshold_steps * 2: # in between 
                        line.append(self.color[1])
                    elif self.threshold_db - int(f) >= self.threshold_steps * 2:  # quietest
                        line.append(self.color[0])

            rows.append(line)
            time_vector.append(start + self.nfft / 2)
            start += self.nfft
            if start > (self.sample_rate * self.file_length_sec) - self.nfft:
                done = True
        return(time_vector, rows)