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
import time, os
import curses, curses.panel
import traceback
import copy

from common import (KeystrokeCallable, WindowDimensions, Cursor, get_term_size, get_fitted_window)
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
        self.base_window = stdscr
        self.refresh_rate = refresh_hz
        # holds all panels (other classes can add panels)
        self.panels = {
            'main': self._init_panel(),
        }
        self._init_keymap()
        self.saved_windows = {}
        self.legend_managers = {}
        # key map callables (on key do x)
        self._overlap_mode = True # panels overlap and are not "fitted" together
        # set base window to nodelay so getch will be non-blocking
        self.base_window.nodelay(True)
        curses.curs_set(False)

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
                                                           call=[self.log_keystroke, self._kill],
                                                           case_sensitive=True))
        self.register_keystroke_callable(KeystrokeCallable(key_id=curses.KEY_RESIZE,
                                                           key_name='RESIZE',
                                                           call=[self.log_keystroke, self.handle_refit, self.handle_resize],
                                                           case_sensitive=True))
            
    def get_panel_mode(self):
        if self._overlap_mode:
            mode = 'Stacked'
        else:
            mode = 'Best Fit'
        return(mode)

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
           corner == TOP or corner == LEFT:
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
        panels = []
        max_rows, max_columns = get_term_size()
        for i in range(num_panels):
            if side == LEFT or side == RIGHT:
                columns = shared_dimension
                rows = max_rows / num_panels
                y = 0 + (i * rows)
                x = 0 if side == LEFT else max_columns - columns
            else:
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

        self.legend_managers[name] = LegendManager(panels, get_legend_dict, type_)
        return(self.legend_managers[name])

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

            old_reg = self.keymap[key_id]
            keystroke_callable.calls.extend(old_reg.calls)

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

    def spin(self):
        {panel.redraw_warning() for panel_id, panel in self.panels.items() if panel_id != 'main'}
        curses.panel.update_panels()
        self.base_window.refresh()
        self._handle_keystokes()

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

    def _handle_keystokes(self):
        start = time.time()
        while time.time() - start <= self.refresh_rate:
            key = self.base_window.getch()
            if key != -1:
                if key in self.keymap:
                    start = time.time()
                    [func(self.keymap[key]) for func in self.keymap[key].call]
                    stop = time.time()
                    self.log_keystroke(KeystrokeCallable(key_id=self.keymap[key].key_id,
                                                         key_name='Timer for: {} --> {} seconds'.format(self.keymap[key].key_name,
                                                                                                        '%.3f' % (stop - start)),
                                                         call=[],
                                                         case_sensitive=True))

                if key not in self.keymap:
                    self.log_keystroke(KeystrokeCallable(key_id=-1,
                                                         key_name='ERROR Unregistered key: {}'.format(key),
                                                         call=[],
                                                         case_sensitive=True))

    def _kill(self, *arg):
        raise KeyboardInterrupt





def test(stdscr):
    import random

    ui = Ui(stdscr=stdscr)
    i = 0
    step = 1
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
            stop = time.time()
            ui.panels[win_name].print('This is a test! i = {}'.format(i))
            ui.panels[win_name].print('Duration: {} seconds'.format(stop - start))
        ui.spin()

if __name__ == '__main__':
    try:
        curses.wrapper(test)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n\tExiting...\n')