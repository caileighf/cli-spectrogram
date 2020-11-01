from __future__ import print_function
from common import Cursor
from common import (WindowDimensions, CursesPixel, Cursor, get_term_size)
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
import traceback
import time
import curses

class PanelManager(object):
    """docstring for PanelManager

    """
    def __init__(self, window, 
                       panel, 
                       window_dimensions, 
                       callback=[], 
                       on_state_change=[], 
                       fill_screen=False,
                       sticky_sides=False,
                       border_on=False,
                       corner=None):
        super(PanelManager, self).__init__()
        self.window = window
        self.panel = panel
        self.border_on = border_on
        self.corner = corner
        self.sticky_sides = sticky_sides
        self._init_window(window_dimensions)
        # create empty buffer for data
        self.buffer = []
        self.callback = callback
        self.on_state_change = on_state_change
        self.fill_screen = fill_screen
        self._term_too_small = False

    def _init_window(self, window_dimensions):
        self.cursor = Cursor(max_rows=window_dimensions.rows,
                             min_rows=window_dimensions.y)
        self.window_dimensions = window_dimensions
        if self.border_on:
            self.add_border()

    @property
    def x(self):
        return(self.window_dimensions.x)

    @property
    def y(self):
        return(self.cursor.y)

    @property
    def rows(self):
        return self.window_dimensions.rows

    @property
    def term_size(self):
        rows, columns = get_term_size()
        return(rows, columns)
    
    @property
    def columns(self):
        return self.window_dimensions.columns

    def handle_resize_warning(self):
        # call any on_state_change methods
        for func in self.on_state_change:
            func(event='RESIZE')

    def handle_resize(self):
        height, width = self.term_size
        if self.sticky_sides and self.corner != None:
            # window is smaller then term and has "sticky sides" so we need to move
            # this panel so it can "stick" to the side
            if width - self.window_dimensions.columns < 1:
                # our term is smaller than the minimum width we need
                # switch flag to True and hide() -- next time term is large enough we'll 
                # hit the elif block and show again
                self._term_too_small = True
                self.hide()
                self.handle_resize_warning()
                return
            elif self._term_too_small:
                self._term_too_small = False
                self.show()

            if self.corner == LEFT:
                new_win = WindowDimensions(x=0,
                                           y=self.window_dimensions.y,
                                           rows=self.window_dimensions.rows,
                                           columns=self.window_dimensions.columns)
            elif self.corner == RIGHT:
                new_win = WindowDimensions(x=width - self.window_dimensions.columns,
                                           y=self.window_dimensions.y,
                                           rows=self.window_dimensions.rows,
                                           columns=self.window_dimensions.columns)
            else:
                new_win = self.window_dimensions
            self._init_window(new_win)
            try:
                self.move(x=self.window_dimensions.x, y=self.window_dimensions.y)
            except ValueError:
                from ui import Ui
                self.replace(Ui.get_replacement_window(self.window_dimensions))
                return

        elif self.fill_screen:
            new_win = WindowDimensions(x=0,
                                       y=0,
                                       rows=height,
                                       columns=width)
            self._init_window(new_win)

        elif self.window_dimensions.rows > height or self.window_dimensions.columns > width:
            new_win = WindowDimensions(x=self.window_dimensions.x,
                                       y=self.window_dimensions.y,
                                       rows=height if self.window_dimensions.rows > height else self.window_dimensions.rows,
                                       columns=width if self.window_dimensions.columns > width else self.window_dimensions.columns)
            self._init_window(new_win)

        self.handle_resize_warning()

    def refresh(self):
        curses.panel.update_panels()
        self.window.refresh()
    
    def clear_buffer(self):
        self.buffer = []

    def hard_clear(self):
        self.window.clear()

    def printch(self, ch, attr=None, color=1):
        try:
            self.window.addstr(ch, curses.color_pair(color) | attr)
        except:
            self.log(traceback.format_exc())
            self.log('color={}, attr={}'.format(color, attr))
            self.log('Error at ch: {}, current y,x: {}'.format(ch, self.window.getyx()))
            return(False)
        return(True)

    def redraw_warning(self):
        self.window.move(0, 0)
        for call in self.callback:
            call(self.term_size)

        self.redraw_buffer()

    def redraw_buffer(self):
        for row in self.buffer:
            for pixel in row:
                self.printch(ch=pixel.text, color=pixel.bg, attr=pixel.attr)
            self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)
        self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)

        if self.border_on:
            self.add_border()

        self.log('length of buffer: {}, term_size: {}'.format(len(self.buffer), self.term_size))

    def add_callback(self, callback):
        self.callback.append(callback)

    def log(self, output=None, end='\n'):
        with open('debug.log', 'a+') as f:
            f.write('[{}]: {}{}'.format(int(time.time()), output, end))

    def print(self, output, x=None, y=None, end='\n'):
        if not isinstance(output, list):
            output = [output]

        # loop through output printing each line with delim
        for line in output:
            if line == output[-1]: end=''
            self.print_line(line=line,
                            x=x if x != None else self.x,
                            y=y if y != None else self.y,
                            end=end)
            if y != None: y += 1 

    def print_line(self, line, x, y, end='\n'):
        _, columns = get_term_size()
        self.window.addnstr(y, x, '{}{}'.format(line, end), columns-5)

    def set_focus(self):
        self.panel.top()

    def move(self, x, y):
        try:
            self.panel.move(y, x)
        except:
            # this only happens when the user resizes the window 
            # very quickly while expanding and contracting
            self.log('User tried to resize window too fast! \n{}'.format(traceback.format_exc()))
            raise ValueError('x or y value would put the window off screen!')
        else:
            self.redraw_buffer()

    def hline(self, ch='-'):
        _hline = []
        _hline.extend([
                CursesPixel(text=ch * self.columns, fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_BOLD)
            ])
        return(_hline)

    def move_left(self):
        new_win = WindowDimensions(x=self.window_dimensions.x - 2,
                                   y=self.window_dimensions.y,
                                   rows=self.window_dimensions.rows,
                                   columns=self.window_dimensions.columns)
        self._init_window(new_win)
        try:
            self.move(x=self.window_dimensions.x, y=self.window_dimensions.y)
        except ValueError:
            self.log('User reached the end of the window \n{}'.format(traceback.format_exc()))

    def move_right(self):
        new_win = WindowDimensions(x=self.window_dimensions.x + 2,
                                   y=self.window_dimensions.y,
                                   rows=self.window_dimensions.rows,
                                   columns=self.window_dimensions.columns)
        self._init_window(new_win)
        try:
            self.move(x=self.window_dimensions.x, y=self.window_dimensions.y)
        except ValueError:
            self.log('User reached the end of the window \n{}'.format(traceback.format_exc()))

    def add_border(self):
        self.window.box()

    def hide(self):
        self.panel.hide()

    def show(self):
        self.panel.show()

    def toggle_visibility(self):
        if self.is_hidden():
            self.show()
        else:
            self.hide()

    def replace(self, window):
        self.panel.replace(window)
        self.window = window

    def is_hidden(self):
        return(self.panel.hidden())

    def is_focus(self):
        if self.panel.above() == None:
            return(True)
        return(False)