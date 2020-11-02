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
        RIGHT,
        SPLIT_V_STACK,
        SPLIT_H_STACK,
        SINGLE_V,
        SINGLE_H
    )
import traceback
import time
import curses

class LegendManager(object):
    """docstring for LegendManager"""
    def __init__(self, panels, get_legend_dict, type_=SINGLE_V):
        super(LegendManager, self).__init__()
        self.type_ = type_
        self.panels = panels if isinstance(panels, list) else [panels]
        self.get_legend_dict = get_legend_dict
        self.rows, self.columns = self._init_panels()
        self.side = self._init_position()

    @property
    def legend_data(self):
        return(self.get_legend_dict())

    def _init_position(self):
        return(self.panels[0].corner)

    def _init_panels(self):
        [p.add_callback(self.redraw_legend) for p in self.panels]
        self.border_on()
        self.set_sticky_sides()
        for p in self.panels:
            rows = p.rows
            columns = p.columns
        return(rows, columns)

    def get_total_width(self, side):
        if side == RIGHT and self.side == RIGHT:
            return(self.panels[0].columns)
        return(0)

    def get_total_height(self, side):
        if side == TOP and self.side == TOP:
            return(self.panels[0].rows)
        return(0)

    def hline(self, ch=' '):
        return(self.panels[0].hline(ch=ch))

    def move_left(self):
        [p.move_left() for p in self.panels]

    def move_right(self):
        [p.move_right() for p in self.panels]

    def set_sticky_sides(self, flag=True):
        for p in self.panels:
            p.sticky_sides = True

    def update_legend_data(self):
        data = self.legend_data
        if self.type_ == SPLIT_V_STACK:
            datertots = [data['UPPER'], data['LOWER']]
        elif self.type_ == SPLIT_H_STACK:
            datertots = [data['LEFT'], data['RIGHT']]
        else:
            datertots = [data]

        for data, p in zip(datertots, self.panels):
            p.pop_dict_buffer(data)
        
    def add_callback(self, callback):
        [p.add_callback(callback) for p in self.panels]

    def add_state_change_callback(self, callback):
        [p.on_state_change.append(callback) for p in self.panels]

    def border_on(self):
        for p in self.panels:
            p.border_on = True

    def border_off(self):
        for p in self.panels:
            p.border_on = False

    def is_hidden(self):
        # returns True is ALL panels in legend are hidden
        for p in self.panels:
            if not p.is_hidden():
                return(False)
        return(True)

    def toggle_top(self):
        self.toggle_panel(0)

    def toggle_bottom(self):
        self.toggle_panel(-1)

    def toggle_panel(self, index):
        self.panels[index].toggle_visibility()

    def toggle_all(self):
        [p.toggle_visibility() for p in self.panels]

    def hide_all(self):
        for p in self.panels:
            p.hide()

    def show_all(self):
        for p in self.panels:
            p.show()

    def snap_back(self):
        try:
            [p.snap_back() for p in self.panels]
        except ValueError:
            pass

    def redraw_legend(self, term_size=None):
        if self.is_hidden():
            return
        
        self.update_legend_data() # possibly add this as on_state_change callback
                                  # instead of explicitly calling here
        for p in self.panels:
            if p.is_drawn:
                continue
            p.clear_buffer()
            p.buffer.append([CursesPixel(text='', fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_NORMAL)])

            for outer_k, outer_v in p.dict_buffer.items():
                # if key starts with __ that means it's already a list of curses pixels so append as is
                if outer_k[:2] == '__':
                    p.buffer.append(outer_v)
                    continue

                p.buffer.append([
                        CursesPixel(text=' {}'.format(outer_k).center(p.columns - 1), fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_BOLD),
                    ])
                p.buffer.append(p.hline())
                for k, v in outer_v.items():
                    # if key starts with __ that means it's already a list of curses pixels so append as is
                    if k[:2] == '__':
                        p.buffer.append(v)
                        continue

                    p.buffer.append([
                            CursesPixel(text='  {}: '.format(k), fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_BOLD),
                            CursesPixel(text='{}'.format(v), fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_NORMAL)
                        ])
                if k[:2] != '__': p.buffer.append(p.hline(ch=' '))


class PanelManager(object):
    """docstring for PanelManager

    """
    def __init__(self, panel, 
                       window_dimensions, 
                       callback=[], 
                       on_state_change=[], 
                       fill_screen=False,
                       sticky_sides=False,
                       border_on=False,
                       corner=None):
        super(PanelManager, self).__init__()
        self.panel = panel
        self.border_on = border_on
        self.corner = corner
        self.sticky_sides = sticky_sides
        # create empty buffer for data
        self.buffer = []
        self.dict_buffer = {}
        self.callback = callback
        self.on_state_change = on_state_change
        self.fill_screen = fill_screen
        self._term_too_small = False
        self._is_drawn = False # flag for managers of multiple panels
        self._init_window(window_dimensions)

    def _init_window(self, window_dimensions):
        self.cursor = Cursor(max_rows=window_dimensions.rows,
                             min_rows=window_dimensions.y)
        self.window_dimensions = window_dimensions
        if self.border_on:
            self.add_border()

    @property
    def window(self):
        return(self.panel.window())
    
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

    @property
    def is_drawn(self):
        return self._is_drawn
    

    def pop_dict_buffer(self, data):
        self.dict_buffer = data

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

    def handle_state_change(self):
        pass

    def refresh(self):
        curses.panel.update_panels()
        self.window.refresh()
    
    def clear_buffer(self):
        self.buffer = []

    def hard_clear(self):
        pass

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
        self._is_drawn = False
        for call in self.callback:
            call(self.term_size)

        self.redraw_buffer()
        self._is_drawn = True

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
        with open('panel_debug.log', 'a+') as f:
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

    def snap_back(self):
        if self.corner != None:
            self.handle_resize()

    def replace(self, window):
        self.panel.replace(window)
        rows, columns = self.window.getmaxyx()
        y, x = self.window.getparyx()
        window_dimensions = WindowDimensions(x=x,
                                             y=y,
                                             rows=rows,
                                             columns=columns)
        self._init_window(window_dimensions)
        self.handle_resize_warning()

    def resize(self, window_dimensions):
        self.window.resize(window_dimensions.rows, window_dimensions.columns)
        try:
            self.move(x=window_dimensions.x, y=window_dimensions.y)
        except ValueError:
            pass
        else:
            self._init_window(window_dimensions)

    def is_hidden(self):
        return(self.panel.hidden())

    def is_focus(self):
        if self.panel.above() == None:
            return(True)
        return(False)