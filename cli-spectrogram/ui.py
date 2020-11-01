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
import time, os
import curses, curses.panel
import traceback

from common import (KeystrokeCallable, WindowDimensions, Cursor, get_term_size)
from panel_manager import PanelManager
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
    
class Ui(object):
    """docstring for Ui

    The Ui class manages all things related to curses and what is displayed
    """
    def __init__(self, stdscr, refresh_hz=1):
        super(Ui, self).__init__()
        self.base_window = stdscr
        self.refresh_rate = refresh_hz
        # holds all panels (other classes can add panels)
        self.panels = {
            'main': self._init_panel(),
        }
        # key map callables (on key do x)
        self.keymap = {
            curses.KEY_DC: KeystrokeCallable(key_id=curses.KEY_DC,
                                             key_name='DELETE',
                                             call=[self.log_keystroke, self._kill],
                                             case_sensitive=True),
            curses.KEY_RESIZE: KeystrokeCallable(key_id=curses.KEY_RESIZE,
                                                 key_name='RESIZE',
                                                 call=[self.log_keystroke, self.handle_resize],
                                                 case_sensitive=True),
        }
        # set base window to nodelay so getch will be non-blocking
        self.base_window.nodelay(True)
        curses.curs_set(False)

    @property
    def main_window(self):
        return(self.panels['main'])

    def handle_resize(self, args):
        {panel.handle_resize() for panel_id, panel in self.panels.items() if panel_id != 'main'}

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

        return(self.new_window(x, y, rows, columns, name, output, set_focus, overwrite, callback))

    def new_window(self, x, y, rows, columns, name, 
                         output=None, set_focus=True, 
                         overwrite=False, callback=[]):
        if name == 'main': raise AttributeError('Cannot overwrite the main panel')

        if name in self.panels:
            if not overwrite:
                return(None)
            else:
                win = self._init_panel(WindowDimensions(x=x, y=y, rows=rows, columns=columns))
                self.panels[name].replace(window=win)
        else:
            self.panels[name] = self._init_panel(WindowDimensions(x=x, y=y, rows=rows, columns=columns))

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

    def _init_panel(self, window_dimensions=None, callback=[]):
        if window_dimensions == None:
            rows, columns = get_term_size()
            window_dimensions = WindowDimensions(x=0, y=0, rows=rows, columns=columns)

        window = curses.newwin(window_dimensions.rows,
                               window_dimensions.columns,
                               window_dimensions.y,
                               window_dimensions.x)
        panel = curses.panel.new_panel(window)

        return(PanelManager(window=window,
                            panel=panel,
                            window_dimensions=window_dimensions,
                            callback=callback))

    def _handle_keystokes(self):
        start = time.time()
        while time.time() - start <= self.refresh_rate:
            key = self.base_window.getch()
            if key != -1:
                if key in self.keymap:
                    [func(self.keymap[key]) for func in self.keymap[key].call]

                try:
                    self.log_keystroke(self.keymap[key])
                except KeyError:
                    self.log_keystroke(KeystrokeCallable(key_id=-1,
                                                         key_name='ERROR Unregistered key: {}'.format(key),
                                                         call=[],
                                                         case_sensitive=True))

    def _kill(self, *arg):
        raise KeyboardInterrupt





def test(stdscr):
    ui = Ui(stdscr=stdscr)
    i = 0
    while True:
        if i >= 3:
            pan = curses.panel.bottom_panel()
            pan.hide()
            ui.spin()
        win_name = 'Test_{}'.format(i)
        ui.new_window(3+i, 3+i, 30, 50, win_name, 'This is a test!')
        i+=1
        ui.panels[win_name].add_border()
        ui.panels[win_name].print(time.time())
        ui.spin()

if __name__ == '__main__':
    try:
        curses.wrapper(test)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n\tExiting...\n')