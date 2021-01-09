from __future__ import print_function
from collections import deque
from cached_ui_elements import cache_element
from common import Cursor
from common import (WindowDimensions, CursesPixel, Cursor, get_term_size, is_python_2_7)
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
        SINGLE_H,
        ESC
    )
import traceback
import time
import curses
import curses.textpad

BUMPER_CAR_MODE = False

class LegendManager(object):
    """docstring for LegendManager"""
    def __init__(self, panels, get_legend_dict, type_=SINGLE_V, default_key=None):
        super(LegendManager, self).__init__()
        self.type_ = type_
        self.panels = panels if isinstance(panels, list) else [panels]
        self.get_legend_dict = get_legend_dict
        self.rows, self.columns = self._init_panels()
        self.side = self._init_position()
        self.x_label = self.y_label = None
        self.minimal_mode = False
        self.static_index = -1
        self.done_first_render = False
        self.footer = None
        self.do_update = True
        self.default_key = default_key
        self.elem_cache = {}

    @property
    def legend_data(self):
        if self.minimal_mode:
            return(self.get_legend_dict()['__minimal__'])

        if self.default_key != None:
            try:
                return(self.get_legend_dict()[self.default_key])
            except KeyError:
                return(self.get_legend_dict())
        else:
            return(self.get_legend_dict())

    def toggle_minimal_mode(self):
        self.minimal_mode ^= True

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

    def resize_panels(self, height=None, width=None):
        rows, columns = get_term_size()
        vert_shift = rows - height if height != None else 0
        hori_shift = columns - width if width != None else 0
        if height != None and self.static_index != -1:
            for i, panel in enumerate(self.panels):
                if i != self.static_index:
                    panel.resize(WindowDimensions(x=panel.xy[0],
                                                  y=panel.xy[1],
                                                  rows=height,
                                                  columns=panel.columns))
                else:
                    panel.resize(WindowDimensions(x=panel.xy[0],
                                                  y=height,
                                                  rows=rows - height,
                                                  columns=panel.columns))

    def set_static_index(self, index):
        if index.isdigit():
            self.static_index = index
        else:
            if index == 'UPPER' or index == 'LEFT':
                self.static_index = 0
            else:
                self.static_index = 1
        self.done_first_render = False

    def set_x_label(self, label):
        self.x_label = label

    def set_y_label(self, label):
        self.y_label = label

    def get_total_width(self, side):
        if self.is_hidden():
            return(0)

        if side == self.side:
            return(self.panels[0].columns)
        return(0)

    def get_total_height(self, side):
        if self.is_hidden():
            return(0)

        if side == self.side:
            return(self.panels[0].rows)
        return(0)

    def hline(self, ch=' '):
        return(self.panels[0].hline(ch=ch))

    def refresh(self):
        [p.window.noutrefresh() for p in self.panels]

    def move_left(self):
        [p.move_left() for p in self.panels]
        self.refresh()

    def move_right(self):
        [p.move_right() for p in self.panels]
        self.refresh()

    def reset_position(self):
        [p.reset_position() for p in self.panels]

    def set_sticky_sides(self, flag=True):
        for p in self.panels:
            p.sticky_sides = True

    def update_legend_data(self):
        if BUMPER_CAR_MODE:
            self.side = self._init_position()

        data = self.legend_data
        try:
            if self.type_ == SPLIT_V_STACK:
                datertots = [data['UPPER'], data['LOWER']]
            elif self.type_ == SPLIT_H_STACK:
                datertots = [data['LEFT'], data['RIGHT']]
            else:
                datertots = [data]
        except KeyError:
            # return
            raise ValueError(self.panels[0].window_dimensions.data)

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

    def center_panels(self):
        for p in self.panels:
            if not p.center_panel():
                return(False)
        return(True)

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
        for i, p in enumerate(self.panels):
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
                p.buffer.append(p.hline(ch='-'))
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

        if self.footer != None:
            self.panels[0].buffer.append(self.panels[0].hline(ch=' '))
            self.panels[0].buffer.append([CursesPixel(text='{}'.format(self.footer.center(self.panels[0].columns)), fg=-1, bg=curses.COLOR_BLACK, attr=(curses.A_BOLD | curses.A_REVERSE)),])

def handle_exit_input(key):
    if key == curses.ascii.NL or key == 10:
        return curses.ascii.BEL
    elif key == ESC:
        raise ValueError('Escape key -- cancel edit')

    #   Next section allows cmd history to be accessed with arrow keys
    #
    elif key == curses.KEY_UP or key == curses.KEY_DOWN:
        global text_box; text_box.win.clear()
        text_box.win.refresh()
        global current_history_index;
        global text_box_history;

        if key == curses.KEY_UP:
            if current_history_index == None:
                current_history_index = 0
            else:
                current_history_index += 1
        else:
            if current_history_index != None and current_history_index >= 1:
                current_history_index -= 1
            else:
                return key

        try:
            text_box.win.addstr(text_box_history[current_history_index])
        except IndexError:
            text_box.win.addstr(text_box_history[-1])
        else:
            return None

    return key

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
        self.border_ch = None
        self.footer = None
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
        self.basic_buffer = False
        self.elem_cache = {}
        self._init_window(window_dimensions)

    def _init_window(self, window_dimensions):
        if self.border_on:
            self.add_border()
            self.cursor = Cursor(max_rows=window_dimensions.rows,
                                 min_rows=1)
        else:
            self.cursor = Cursor(max_rows=window_dimensions.rows,
                                 min_rows=0)
        self.window_dimensions = window_dimensions
        
    @property
    def window(self):
        return(self.panel.window())

    @property
    def xy(self):
        return(self.window_dimensions.x, self.window_dimensions.y)
    
    @property
    def x(self):
        if self.border_on:
            return(2 + self.window_dimensions.x)
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

    def get_window_size(self):
        rows, columns = self.window.getmaxyx()
        return(rows, columns)

    def create_text_box(self):
        self.text_box_win = self.window.derwin(1, 0, 1, 2)
        global text_box
        text_box = curses.textpad.Textbox(self.text_box_win, 
                                          insert_mode=True)

        global text_box_history; text_box_history = deque(maxlen=500)
        global current_history_index; current_history_index = None

    def get_user_input(self):
        if not hasattr(self, 'text_box_win'):
            self.create_text_box()

        self.printch(' :', attr=curses.A_BOLD, color=None)
        self.clean_window()
        self.window.refresh()

        global text_box
        global text_box_history

        try:
            cmd = text_box.edit(handle_exit_input)
        except ValueError:
            cmd = None
        else:
            cmd = cmd.strip(' x')
            text_box_history.appendleft(cmd)
        finally:
            global current_history_index; current_history_index = None
            self.window.erase()
            self.text_box_win.erase()
        return(cmd)
    
    def border(self, flag=True, ch=None):
        self.border_ch = ch
        if self.border_on != flag:
            self.border_on = flag
            self._init_window(self.window_dimensions)

    def set_basic_buffer(self, flag=True):
        if self.basic_buffer != flag:
            self.basic_buffer = flag
            self._init_window(self.window_dimensions)

    def pop_dict_buffer(self, data):
        self.dict_buffer = data

    def handle_resize_warning(self):
        # call any on_state_change methods
        for func in self.on_state_change:
            func(event='RESIZE')

    def handle_resize(self):
        if self.is_hidden():
            self.handle_resize_warning()
            return

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
        pass
    
    def clear_buffer(self):
        self.buffer = []

    def printch(self, ch, attr=None, color=-1):
        try:
            if color == None:
                self.window.addstr(ch, attr)
            else:
                self.window.addstr(ch, curses.color_pair(color) | attr)
        except curses.error:
            if ch == '\n':
                pass # we wrote past window
        except:
            self.log(traceback.format_exc())
            self.log('color={}, attr={}'.format(color, attr))
            self.log('Error at ch: {}, current y,x: {}'.format(ch, self.window.getyx()))
            return(False)
        return(True)

    def log(self, output, end='\n'):
        with open('debug.log', 'a+') as f:
            f.write('[{}]: {}{}'.format(int(time.time()), output, end))

    def redraw_warning(self):
        self.window.move(0, 0) # move cursor to position (0,0)
        self._is_drawn = False
        for call in self.callback:
            call(self.term_size)

        self.redraw_buffer()
        self._is_drawn = True

    def redraw_buffer(self):
        for i, row in enumerate(self.buffer):
            if i > self.rows - 2: 
                break
            if row != None:
                for pixel in row:
                    self.printch(ch=pixel.text, color=pixel.bg, attr=pixel.attr)
                self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)
        self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)

        if not self.basic_buffer:
            self.clean_window()

        if self.border_on:
            self.add_border()

        self.log('length of buffer: {}, term_size: {}'.format(len(self.buffer), self.term_size))

    def add_callback(self, callback):
        self.callback.append(callback)

    def print(self, output, x=None, y=None, end='\n', post_clean=True):
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
        if post_clean and not self.basic_buffer:
            self.clean_window()

    def print_line(self, line, x, y, end='\n', center=False):
        if isinstance(line, CursesPixel) or\
           isinstance(line, list) and isinstance(line[0], CursesPixel):
            for row in line:
                try:
                    for pixel in row:
                        self.printch(ch=pixel.text, color=pixel.bg, attr=pixel.attr)
                    self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)
                except AttributeError:
                    pass
                else:
                    if self.border_on:
                        self.add_border()
                    return

        _, columns = get_term_size()
        try:
            if center:
                self.window.addnstr(y, x, '{}{}'.format(line.center(self.columns-4), end), columns-5)
            else:
                self.window.addnstr(y, x, '{}{}'.format(line, end), columns-5)
        except curses.error:
            pass

    def set_footer(self, footer_text):
        self.footer = []
        self.footer.append(self.hline(ch=' '))
        self.footer.append([CursesPixel(text='{}'.format(footer_text.center(self.columns)), fg=-1, bg=curses.COLOR_BLACK, attr=(curses.A_BOLD | curses.A_REVERSE))],)

    def print_footer(self):
        if self.footer != None:
            for row in self.footer:
                for pixel in row:
                    self.printch(ch=pixel.text, color=pixel.bg, attr=pixel.attr)
                self.printch(ch='\n', color=curses.COLOR_BLACK, attr=curses.A_NORMAL)
        if self.border_on:
            self.add_border()

    def set_focus(self):
        self.panel.top()

    @cache_element(cache='elem_cache', target_kwarg='ch')
    def hline(self, ch):
        _hline = []
        _hline.extend([
                CursesPixel(text=ch * self.columns, fg=-1, bg=curses.COLOR_BLACK, attr=curses.A_BOLD)
            ])
        return(_hline)

    def clean_window(self):
        self.window.clrtobot()
        if self.border_on:
            self.add_border()

    def clear(self):
        self.window.move(0, 0)
        self.clean_window()

    def reset_position(self):
        self.move(x=self.window_dimensions.x, y=self.window_dimensions.y)

    def center_panel(self):
        target_x = self.window_dimensions.x
        target_y = self.window_dimensions.y
        max_y, max_x = self.term_size
        # if this panel is larger than the available console, just bump to top right corner
        if self.rows < max_y:
            target_y = (max_y - self.rows) / 2
        else:
            target_y = 0

        if self.columns < max_x:
            target_x = (max_x - self.columns) / 2
        else:
            target_x = 0

        # if no change to panel position, no need to create a new window
        if target_x != self.window_dimensions.x or\
           target_y != self.window_dimensions.y:
            new_win = WindowDimensions(x=target_x,
                                       y=target_y,
                                       rows=self.window_dimensions.rows,
                                       columns=self.window_dimensions.columns)
            self._init_window(new_win)
            self.reset_position()
            return(True)
        return(False)

    def move(self, x, y):
        try:
            self.panel.move(y, x)
        except:
            # this only happens when the window would be moved off the page
            if BUMPER_CAR_MODE:
                max_rows, max_columns = get_term_size()
                if self.corner == RIGHT and x <= 0:
                    self.corner = LEFT
                elif self.corner == LEFT and x <= max_columns:
                    self.corner = RIGHT
                elif self.corner == TOP and y <= 0:
                    self.corner = BOTTOM
                elif self.corner == BOTTOM and y <= max_rows:
                    self.corner = TOP

            self.log('''
                User tried to resize window too fast!
                x or y value would put the window off screen!\n{}
                '''.format(traceback.format_exc()))
            return(False)
        
        self.redraw_buffer()
        return(True)

    def move_left(self):
        if self.move(x=self.window_dimensions.x - 1, y=self.window_dimensions.y):
            new_win = WindowDimensions(x=self.window_dimensions.x - 1,
                                       y=self.window_dimensions.y,
                                       rows=self.window_dimensions.rows,
                                       columns=self.window_dimensions.columns)
            self._init_window(new_win)
        else:
            return(False)

    def move_right(self):
        if self.move(x=self.window_dimensions.x + 1, y=self.window_dimensions.y):
            new_win = WindowDimensions(x=self.window_dimensions.x + 1,
                                       y=self.window_dimensions.y,
                                       rows=self.window_dimensions.rows,
                                       columns=self.window_dimensions.columns)
            self._init_window(new_win)
        else:
            return(False)

    def set_background_color(self, color, ch=' '):
        self.window.bkgdset(ch, curses.color_pair(color))

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
        rows, columns = self.term_size
        y, x = self.window.getparyx()
        window_dimensions = WindowDimensions(x=x,
                                             y=y,
                                             rows=rows,
                                             columns=columns)
        self._init_window(window_dimensions)
        self.handle_resize_warning()

    def resize(self, window_dimensions):
        self.window.resize(window_dimensions.rows, window_dimensions.columns)
        self._init_window(window_dimensions)
        self.reset_position()

    def is_hidden(self):
        return(self.panel.hidden())

    def is_focus(self):
        if self.panel.above() == None:
            return(True)
        return(False)