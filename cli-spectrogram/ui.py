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
# Date:   1-/17/2020
#
# File: ui.py
#
from __future__ import print_function
from collections import deque
import time, os
import curses, curses.panel
import traceback
import copy
import threading

from common import (
        KeystrokeCallable, 
        WindowDimensions, 
        Cursor, 
        get_term_size, 
        get_fitted_window,
        init_color_pairs,
        init_mouse,
        ESC,
        Q_MARK
    )
from panel_manager import (LegendManager, PanelManager)
from common import (
        TOP_LEFT,
        TOP_RIGHT,
        BOTTOM_LEFT,
        BOTTOM_RIGHT,
        TOP,
        BOTTOM,
        LEFT,
        RIGHT,
        SPLIT_V_STACK,
        SPLIT_H_STACK,
        SINGLE_V,
        SINGLE_H
    )
    
class Ui(object):
    """docstring for Ui

    The Ui class manages all things related to curses and what is displayed
    """
    def __init__(self, stdscr, refresh_hz=0):
        super(Ui, self).__init__()
        init_color_pairs()
        init_mouse()
        self.running_async = False
        self.key_buffer = deque()
        self.base_window = stdscr
        self.refresh_rate = refresh_hz
        # holds all panels (other classes can add panels)
        self.panels = {
            'main': self._init_panel(),
        }
        self.saved_windows = {}
        self.legend_managers = {}
        # key map callables (on key do x)
        self._init_keymap()
        self._init_help()
        # self._init_message_bar()
        self._overlap_mode = True # panels overlap and are not "fitted" together
        self._original_panel_mode = self.get_panel_mode()
        # set base window to nodelay so getch will be non-blocking
        self.base_window.nodelay(True)
        curses.curs_set(False)
        # create flash message window
        self.new_center_window(rows=10, columns=50, name='flash_message')
        self.panels['flash_message'].border()
        self.panels['flash_message'].set_basic_buffer()
        self.panels['flash_message'].hide()

    @property
    def main_window(self):
        return(self.panels['main'])

    def _init_keymap(self):
        self.keymap = {}
        self.register_keystroke_callable(KeystrokeCallable(key_id=ord('X'),
                                                           key_name='X',
                                                           call=[self.log_keystroke, self.toggle_overlap_mode],
                                                           case_sensitive=False))
        self.register_keystroke_callable(KeystrokeCallable(key_id=curses.KEY_DC,
                                                           key_name='DELETE',
                                                           call=[self.log_keystroke, self.stop, self._kill],
                                                           case_sensitive=True))
        self.register_keystroke_callable(KeystrokeCallable(key_id=curses.KEY_RESIZE,
                                                           key_name='RESIZE',
                                                           call=[self.log_keystroke, self.handle_refit, self.handle_resize],
                                                           case_sensitive=True))
        self.register_keystroke_callable(KeystrokeCallable(key_id=ESC,
                                                           key_name='Escape',
                                                           call=[self.revert_to_original_mode],
                                                           case_sensitive=True))
        self.register_keystroke_callable(KeystrokeCallable(key_id=ord(' '),
                                                           key_name='Space',
                                                           call=[self.toggle_help],
                                                           case_sensitive=True))
        self.register_keystroke_callable(KeystrokeCallable(key_id=Q_MARK,
                                                           key_name='?',
                                                           call=[self.toggle_help],
                                                           case_sensitive=True))

    def _init_help(self):
        self.help_info = {
            'UI Keyboard Shortcuts': {
                'X / x': 'Toggle window mode Stacked / Best Fit',
                'Delete': 'Exit',
                'Escape': 'Revert to original layout'
            }
        }
        height, _ = get_term_size()
        help_panel = self.new_center_window(rows=(height - 8), columns=50, name='ui_help')
        self.add_legend_manager(name='ui_help_legend', 
                                manager=LegendManager(panels=[help_panel],
                                                      get_legend_dict=self.get_help_info))
        self.legend_managers['ui_help_legend'].footer = 'Show/Hide this window with ? or space bar'
        self.legend_managers['ui_help_legend'].hide_all()
        self.is_help_shown = False

    def _init_message_bar(self):
        self.message_bar = self.new_corner_window(corner=BOTTOM, rows=3, columns=None, name='ui_message_bar')
        self.message_bar.set_basic_buffer()
        self.message_bar.border(True)
        self.message_bar.print('  Hit the space bar or ? to toggle the help window | Ctrl + c to quit ', post_clean=False)
        
        curses.panel.update_panels()
        curses.doupdate()

    def set_help_info(self, info, title, overwrite=False):
        if not overwrite:
            if title in self.help_info:
                return(False)

        self.help_info[title] = info
        return(True)

    def get_help_info(self):
        return(self.help_info)

    def toggle_help(self, *args):
        self.is_help_shown ^= True
        self.legend_managers['ui_help_legend'].toggle_all()

    def revert_to_original_mode(self, *args):
        if self._original_panel_mode != self.get_panel_mode():
            self.toggle_overlap_mode()
        # all_legends_hidden = [manager.is_hidden() for name, manager in self.legend_managers.items()]
        # if False not in all_legends_hidden:
        #     if self._original_panel_mode != self.get_panel_mode():
        #         self.toggle_overlap_mode()
            
    def stacked_mode(self):
        self._original_panel_mode = 'Stacked'
        if not self._overlap_mode:
            self.toggle_overlap_mode()

    def best_fit_mode(self):
        self._original_panel_mode = 'Best Fit'
        if self._overlap_mode:
            self.toggle_overlap_mode()

    def get_panel_mode(self):
        if self._overlap_mode:
            mode = 'Stacked'
        else:
            mode = 'Best Fit'
        return(mode)

    def add_legend_manager(self, name, manager):
        self.legend_managers[name] = manager

    def toggle_overlap_mode(self, *args):
        self._overlap_mode ^= True
        self.handle_refit(state_just_changed=True)

    def handle_refit(self, *args, state_just_changed=False):
        plot_name, plot = [(k, p) for k, p in self.panels.items() if 'plot' in k][0]
    
        if state_just_changed:
            plot.fill_screen = self._overlap_mode
            if self._overlap_mode:
                # refit plot to window by recalling last saved plot
                plot.replace(self.get_saved_window(plot_name))
            else:
                self.save_window(plot_name)

        if not self._overlap_mode:
            self.fit_plot_panels()

    def handle_resize(self, args):
        {panel.handle_resize() for panel_id, panel in self.panels.items() if panel_id != 'main'}

    def save_window(self, name):
        self.saved_windows[name] = '.__{}__'.format(name)
        with open(self.saved_windows[name], 'w+b') as f:
            self.panels[name].window.putwin(f)

    def get_saved_window(self, name):
        with open(self.saved_windows.pop(name), 'r+b') as f:
            return(curses.getwin(f))

    def fit_plot_panels(self):
        # for now just do this for first plot
        plot_name, plot = [(k, p) for k, p in self.panels.items() if 'plot' in k][0]
        # log all panels Ui is tracking
        self.log(output=', '.join([str(k) for k, p in self.panels.items()]))
        # force legend panels to snap back to their sides if they have been moved
        for legend in self.legend_managers.values():
            legend.snap_back()

        new_win = get_fitted_window(self.legend_managers)
        self.log(new_win.data)
        self.log('plot panel: {}'.format(plot.window_dimensions.data))
        if plot.window_dimensions != new_win:
            plot.resize(new_win)

    def new_corner_window(self, corner, rows, columns, name, 
                          output=None, set_focus=True, 
                          overwrite=False, callback=[]):
        height, width = get_term_size()
        if corner == TOP_RIGHT or corner == TOP_LEFT or\
           corner == TOP or corner == LEFT or corner == RIGHT:
            y = 0
        else:
            y = height - rows

        if corner == BOTTOM_LEFT or corner == TOP_LEFT or\
           corner == TOP or corner == LEFT or corner == BOTTOM:
            x = 0
        else:
            x = width - columns

        if corner == TOP or corner == BOTTOM:
            columns = width
        elif corner == LEFT or corner == RIGHT:
            rows = height

        return(self.new_window(x=x, 
                               y=y, 
                               rows=rows, 
                               columns=columns, 
                               name=name,
                               corner=corner,
                               output=output,
                               set_focus=set_focus,
                               overwrite=overwrite,
                               callback=callback))

    def new_legend(self, name, num_panels, get_legend_dict, type_, shared_dimension, side):
        mini_options = [TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]
        full_options = [TOP, BOTTOM, LEFT, RIGHT]
        panels = []
        max_rows, max_columns = get_term_size()
        for i in range(num_panels):
            for opt in mini_options:
                if side == opt:
                    panels.append(self.new_corner_window(corner=side, 
                                                         rows=25, 
                                                         columns=50, 
                                                         name='{}_section_{}'.format(name, i)))
            for opt in full_options:
                if side == opt:
                    if side == LEFT or side == RIGHT:
                        columns = shared_dimension
                        rows = max_rows / num_panels
                        y = 0 + (i * rows)
                        x = 0 if side == LEFT else max_columns - columns
                    elif side == TOP or side == BOTTOM:
                        columns = max_columns / num_panels
                        rows = shared_dimension
                        x = 0 + (i * columns)
                        y = 0 if side == TOP else max_rows - rows

                    panels.append(self.new_window(x=x, 
                                                  y=y, 
                                                  rows=rows, 
                                                  columns=columns, 
                                                  name='{}_section_{}'.format(name, i),
                                                  corner=side))

        if len(panels) <= 0:
            raise ValueError(name, num_panels, get_legend_dict, type_, shared_dimension, side, mini_options, full_options)

        self.legend_managers[name] = LegendManager(panels, get_legend_dict, type_)
        return(self.legend_managers[name])

    def flash_message(self, output, duration_sec=1.0, flash_screen=True):
        if flash_screen:
            curses.flash()

        self.panels['flash_message'].show()
        self.panels['flash_message'].set_focus()

        if not isinstance(output, list): output = [output]
        for i, line in enumerate(output):
            self.panels['flash_message'].print_line(line, 2, i+1, end='', center=True)

        curses.panel.update_panels()
        curses.doupdate()
        time.sleep(duration_sec)
        
        self.panels['flash_message'].hide()

    def new_center_window(self, rows, columns, name, 
                                output=None, set_focus=True, 
                                overwrite=False, callback=[]):
        if name == 'main': raise AttributeError('Cannot overwrite the main panel')

        height, width = get_term_size()
        if name in self.panels:
            if not overwrite:
                return(None)
            else:
                win = self._init_panel(WindowDimensions(x=(width / 2) - (columns / 2), 
                                                        y=(height - rows) / 2, 
                                                        rows=rows, columns=columns))
                self.panels[name].replace(window=win.window)
        else:
            self.panels[name] = self._init_panel(WindowDimensions(x=(width / 2) - (columns / 2), 
                                                                  y=(height - rows) / 2, 
                                                                  rows=rows, columns=columns))

        if output != None:
            self.panels[name].print(output)
        self.panels[name].set_focus() if set_focus else self.panels[name].hide()
        return(self.panels[name])

    def new_window(self, x, y, rows, columns, name, 
                         output=None, set_focus=True, 
                         overwrite=False, callback=[], corner=None):
        if name == 'main': raise AttributeError('Cannot overwrite the main panel')

        if name in self.panels:
            if not overwrite:
                return(None)
            else:
                win = self._init_panel(WindowDimensions(x=x, y=y, rows=rows, columns=columns), corner=corner)
                self.panels[name].replace(window=win.window)
        else:
            self.panels[name] = self._init_panel(WindowDimensions(x=x, y=y, rows=rows, columns=columns), corner=corner)

        if output != None:
            self.panels[name].print(output)
        self.panels[name].set_focus() if set_focus else self.panels[name].hide()
        return(self.panels[name])

    def new_full_size_window(self, name, output=None, set_focus=True, overwrite=True, callback=[]):
        rows, columns = get_term_size()
        return(self.new_window(x=0, y=0, rows=rows, columns=columns, 
                                         name=name, output=output, set_focus=set_focus, 
                                         overwrite=overwrite, callback=callback))

    def print(self, output, y=None, x=0, end='\n'):
        try:
            self.main_window.print(output=output, x=x, y=y, end=end)
        except curses.error:
            self.log(traceback.format_exc())
            self.log('Current cursor position: y: {}, x: {}'.format(*self.main_window.window.getyx()))

    def register_keystroke_callable(self, keystroke_callable, update=False):
        if keystroke_callable.key_id in self.keymap:
            if not update:
                return(False)

            old_reg = self.keymap[keystroke_callable.key_id]
            keystroke_callable.call.extend(old_reg.call)

        self.keymap[keystroke_callable.key_id] = keystroke_callable
        if not keystroke_callable.case_sensitive:
            self.keymap[keystroke_callable.switch_case_id()] = keystroke_callable.switch_case()

        return(True)

    def register_key(self, key_id, key_name, calls, case_sensitive=True, update=False):
        new_reg = KeystrokeCallable(key_id=key_id,
                                    key_name=key_name,
                                    call=[calls],
                                    case_sensitive=case_sensitive)
        return(self.register_keystroke_callable(keystroke_callable=new_reg))

    def stop(self, *args):
        self.shutdown = True

    def run_async(self):
        self.running_async = True
        self.shutdown = False
        self._stop_display = False
        # handle 
        threading.excepthook = self._kill
        # the rendering of the display happens in a separate loop
        self._async_display_thread = threading.Thread(target=self.run)
        self._async_display_thread.start()
        
        try:
            while not self.shutdown:
                # all input related handlers should go here
                self._handle_keystokes()
        finally:
            self._stop_display = True
            self._async_display_thread.join()

    def run(self):
        while not self._stop_display:
            self.spin()

    def spin(self):
        # handle message bar
        # if not self.message_bar.is_focus():
        #     self.message_bar.set_focus()

        start = time.time()
        for panel_id, panel in self.panels.items():
            if panel_id != 'main':
                panel.redraw_warning()

        # self.message_bar.print(' Hit the space bar or ? to toggle the help window | Ctrl + c or Delete to quit ', post_clean=False)
        curses.panel.update_panels()
        curses.doupdate()
        stop = time.time()
        if not self.running_async:
            self._handle_keystokes(remaining_time=abs(self.refresh_rate - (stop - start)))

        # self.log_keystroke(KeystrokeCallable(key_id=-1,
        #                                      key_name='spin() Timer: --> {} seconds'.format('%.3f' % (stop - start)),
        #                                      call=[],
        #                                      case_sensitive=True))

    def log(self, output, end='\n'):
        with open('debug.log', 'a+') as f:
            f.write('[{}]: {}{}'.format(int(time.time()), output, end))

    def log_keystroke(self, key):
        with open('keystokes.log', 'a+') as f:
            f.write('[{}]: {}\n'.format(int(time.time()), key.key_name))

    @classmethod
    def get_replacement_window(cls, window_dimensions):
        window = curses.newwin(window_dimensions.rows,
                               window_dimensions.columns,
                               window_dimensions.y,
                               window_dimensions.x)
        return(window)

    def _init_panel(self, window_dimensions=None, callback=[], corner=None):
        if window_dimensions == None:
            rows, columns = get_term_size()
            window_dimensions = WindowDimensions(x=0, y=0, rows=rows, columns=columns)

        window = curses.newwin(window_dimensions.rows,
                               window_dimensions.columns,
                               window_dimensions.y,
                               window_dimensions.x)
        panel = curses.panel.new_panel(window)

        return(PanelManager(panel=panel,
                            window_dimensions=window_dimensions,
                            callback=callback,
                            corner=corner))

    def _handle_keystokes(self, remaining_time=None):
        if remaining_time == None:
            remaining_time = self.refresh_rate

        start = time.time()
        while time.time() - start <= remaining_time:
            key = self.base_window.getch()
            if key != -1:
                if key in self.keymap:
                    start_key_timer = time.time()
                    if key == curses.KEY_MOUSE:
                        args = curses.getmouse()
                        [func(*args) for func in self.keymap[key].call]
                    else:
                        [func(self.keymap[key]) for func in self.keymap[key].call]
                    stop_key_timer = time.time()

                else:
                    # curses.flash()
                    self.log_keystroke(KeystrokeCallable(key_id=-1,
                                                         key_name='ERROR Unregistered key: {}'.format(curses.keyname(key)),
                                                         call=[],
                                                         case_sensitive=True))
        stop = time.time()

    def _kill(self, *arg):
        raise KeyboardInterrupt

def test(stdscr):
    import random

    ui = Ui(stdscr=stdscr, refresh_hz=0.1)
    i = 0
    step = 1
    ui.flash_message(output=['Flash!'])
    while True:
        start = time.time()
        rows, columns = get_term_size()
        win_name = 'Test_{}'.format(i)
        if i >= 5:
            pan = curses.panel.bottom_panel()
            if pan != None:
                pan.hide()
                ui.spin()
        if i != 0 and i % 15 == 0:
            ui.flash_message(output=[
                    'Flash!',
                    'Flash!',
                    'Flash!',
                    'Flash!',
                    'Flash!',
                ])
            i = random.randint(0, 30)
            if i % 2 == 0:
                step = 1
            else:
                step = -1

        try:
            ui.new_window(4+i, 3+i, 20, 50, win_name, overwrite=True)
        except curses.error:
            i = rows / 2
            step = 1
        else:
            i += step
            ui.panels[win_name].border()
            ui.panels[win_name].set_basic_buffer()
            stop = time.time()
            ui.panels[win_name].print('This is a test! i = {}'.format(i), post_clean=False)
            ui.panels[win_name].print('Duration: {} seconds'.format(stop - start), post_clean=False)
        ui.spin()

if __name__ == '__main__':
    try:
        curses.wrapper(test)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n\tExiting...\n')