import os
from math import ceil
from random import randrange, choice

import pygame
import evthandler as eh

from puzzle import Puzzle, BoringBlock
import conf

# TODO: (*usability)
# - scrollable pages - set maximum number of rows and scroll if exceed it
#   - show arrows in rows above top/below bottom if any up/down there (in far left/right tiles) (use puzzle arrows)
#   - change page up/page down action for scrollable pages
#*- show (puzzle) arrows in spaces either side of %x in Selects if wrap or when not at min/max
#   - force Selects to have a space either side of each %x
#   - have Menu.add/rm_arrows(*arrows), each (conf.ARROW_*, (x, y))
# - options pages:
#       delete data: progress, custom levels, solution history, settings (exclude progress, solution history), all
# - nice help messages option
#   - 'be nice to me'/'don't sass me'/?
#   - just ask on first startup?  If not, what's the default?

class BaseText (object):
    """Abstract base class for text widgets.

    CONSTRUCTOR

BaseText(text, size[, rows])

text: the text to display.
size: the maximum length of the text.  This is used to determine the menu size.
rows: maximum number of rows of tiles to take up; if not given, number of rows
      is not restricted.

    METHODS

set_text
attach_event
update

    ATTRIBUTES

text: the widget's text.
size: the maximum length of the text.
current_size: the size of the current text.
rows: the maximum number of rows of tiles the text can take up.
current_rows: the current number of rows of tiles the widget takes up.
pos: the position of the top-left tile in the grid display, or None if unknown.
ehs: an event: handlers dict of attached event handlers.
menu: the Menu instance the widget exists in, or None if unknown.
puzzle: the Puzzle instance the widget exists in, or None if unknown.

    EVENTS

CHANGE_EVENT: the text changed; called after the change is made.

"""
    def __init__ (self, text, size, rows = None):
        self.text = u''
        self.size = int(size)
        self.rows = int(rows) if rows is not None else rows
        self.ehs = {}
        self._is_first_append = True
        self.set_text(text)
        self._is_first_append = False
        self.pos = None
        self.menu = None
        self.puzzle = None

    CHANGE_EVENT = 0

    def __str__ (self):
        text = self.text.encode('utf-8')
        return '<{0}: \'{1}\'>'.format(type(self).__name__, text)

    __repr__ = __str__

    def _chars (self, text):
        """Validify text to display."""
        chars = []
        for c in text:
            # limit character range
            o = ord(c)
            if o >= conf.MIN_CHAR_ID and o <= conf.MAX_CHAR_ID:
                chars.append(c)
            else:
                # replace other characters with spaces
                chars.append(u' ')
        return ''.join(chars)

    def set_text (self, text):
        """Set the value of the text."""
        raise TypeError('not implemented')

    def _throw_event (self, event):
        """Call the handlers attached to the given event ID."""
        if event in self.ehs:
            for handler, args in self.ehs[event]:
                handler(*args)

    def attach_event (self, event, handler, args = ()):
        """Attach a handler to an event.

attach_event(event, handler, args = ())

event: the event ID to run the handler for.
handler: a function to call when the event is thrown.
args: arguments to pass to the handler; no other arguments are passed.

"""
        data = (handler, args)
        try:
            self.ehs[event].append(data)
        except KeyError:
            self.ehs[event] = [data]

    def update (self):
        """Make any changes visible."""
        self.menu.refresh_text(widget = self)

class Text (BaseText):
    """A simple widget to display (immutable) text.

    CONSTRUCTOR

Text(text, special = False[, size])

special: whether to display in a different colour.
size defaults to initial text length.

    METHODS

append
insert
get_id_offset

For all methods that manipulate the text, the result is truncated to self.size.

    ATTRIBUTES

special: whether the text is displayed in a different style; defaults to False.
         Call update after changing to redraw.

"""

    def __init__ (self, text, special = False, size = None):
        self.special = special
        size = len(text) if size is None else size
        self.current_rows = 1
        BaseText.__init__(self, text, size, 1)

    def append (self, text, force_update = False):
        """Append a string to the end of the text.

Returns whether any characters were truncated.

"""
        old_text = self.text
        if not isinstance(text, unicode):
            text = text.decode('utf-8')
        truncated = False
        self.text += self._chars(text)[:self.size - len(self.text)]
        self.current_size = len(self.text)
        if not self._is_first_append:
            # update if text changed
            if force_update or old_text != self.text:
                self._throw_event(BaseText.CHANGE_EVENT)
                self.update()
            # regenerate menu access keys if first letter changed
            if force_update or \
               (old_text and old_text[0]) != (self.text and self.text[0]):
                self.menu.generate_access_keys()
        return not truncated

    def insert (self, index, text):
        """Insert a string at some index into the text.

insert(index, text)

Returns whether any characters were truncated.

"""
        end = self.text[index:]
        self.text = self.text[:index]
        return self.append(text + end)

    def set_text (self, text):
        """Returns whether any characters were truncated."""
        update = self.text and not text
        self.text = u''
        return self.append(text, update)

    def get_id_offset (self):
        """Get the number to add to block IDs."""
        return conf.SPECIAL_CHAR_ID_OFFSET if self.special else 0


class Option (Text):
    """A selectable widget.  Inherits from Text.

    METHODS

set_selected

    ATTRIBUTES

selectable: always True.
selected: whether this widget is currently selected.

    EVENTS

SELECT_EVENT: the selected state has changed.  This is called after the
              selected attribute is changed to the new state.

"""

    def __init__ (self, text, special = False, size = None):
        Text.__init__(self, text, special, size)
        self.selected = False

    SELECT_EVENT = 1

    def set_selected (self, selected):
        """Set the widget's selected state."""
        if selected == self.selected:
            return
        self.selected = selected
        self.update()
        self._throw_event(Option.SELECT_EVENT)

    def get_id_offset (self):
        if self.selected:
            return conf.SELECTED_CHAR_ID_OFFSET
        else:
            return Text.get_id_offset(self)


class Button (Option):
    """A button widget.  Inherits from Option.

    CONSTRUCTOR

Button(text[, click_handler, *click_args], special = False, [, size])

Passing click_handler and click_args is identical to calling
Button.attach_event(Button.CLICK_EVENT, click_handler, click_args).

special and size are keyword-only arguments.

    METHODS

click

    EVENTS

CLICK_EVENT: the button was clicked.

"""

    def __init__ (self, text, click_handler = None, *click_args, **kw):
        Option.__init__(self, text, kw.get('special', False),
                        kw.get('size', None))
        if click_handler is not None:
            self.attach_event(Button.CLICK_EVENT, click_handler, click_args)

    CLICK_EVENT = 2

    def click (self):
        """Trigger handlers attached to CLICK_EVENT."""
        self._throw_event(Button.CLICK_EVENT)


class Entry (Button):
    """Abstract class for widgets that capture input.  Inherits from Button.

    CONSTRUCTOR

Entry(text, special = False[, size])

    METHODS

toggle_focus
input

    ATTRIBUTES

menu: as given.
focused: whether the Entry has keyboard focus.

    EVENTS

FOCUS_EVENT: focus was toggled; called afterwards.

"""

    def __init__ (self, text, special = False, size = None):
        Button.__init__(self, text, self.toggle_focus, special = special,
                        size = size)
        self.focused = False
        self._toggle_keys = set(conf.KEYS_NEXT_NONPRINTABLE)
        self._toggle_keys.add(pygame.K_ESCAPE)

    FOCUS_EVENT = 3

    def toggle_focus (self):
        """Toggle whether the entry is focused.

When a widget is focused, it catches keypresses.  Only one widget can be
focused at a time, for which reason it may not be possible to toggle focus;
the return value indicates whether it was possible.

"""
        if self.focused:
            self.focused = False
            self._throw_event(Entry.FOCUS_EVENT)
            err = 'something else captured input while {0} had it'.format(self)
            assert self.menu.release_input(self), err
            return True
        else:
            captured = self.menu.capture_input(self)
            if captured:
                self.focused = True
                self._throw_event(Entry.FOCUS_EVENT)
            return captured

    def input (self, event):
        """Takes a keypress event and handles focus toggling."""
        if event.key in self._toggle_keys:
            self.toggle_focus()


class TextEntry (Entry):
    """A fixed-size text entry widget.  Inherits from Entry.

    CONSTRUCTOR

TextEntry(menu, max_size, initial_text = '', allowed = conf.PRINTABLE,
      special = False)

menu: Menu instance containing this widget.
max_size: maximum number of characters the entry can hold.
initial_text: text to start with; gets truncated to max_size.
allowed: list/string of allowed characters (initial_text is not checked for
         compliance).

The widget takes up one more tile than max_size.

    ATTRIBUTES:

cursor: the cursor position (>= 0).
allowed: as given (passed to set).

    EVENTS

CURSOR_EVENT: the cursor changed position; called after the position update.

"""

    def __init__ (self, menu, max_size, initial_text = '',
                  allowed = conf.PRINTABLE, special = False):
        Entry.__init__(self, initial_text, special, max_size)
        self.cursor = self.current_size
        self.allowed = set(allowed)

    CURSOR_EVENT = 4

    def _update_cursor (self):
        """Update the cursor position."""
        # deselect previous
        self.puzzle.deselect()
        # select new
        self.cursor = max(0, min(self.cursor, self.current_size))
        p = (self.pos[0] + self.cursor, self.pos[1])
        self.puzzle.select(p, not self.focused)

    def toggle_focus (self):
        """Also handle cursor updating."""
        focused = self.focused
        Entry.toggle_focus(self)
        if focused != self.focused:
            self._update_cursor()

    def input (self, event):
        """Takes a keypress event to alter the entry's text."""
        k = event.key
        u = event.unicode
        cursor = self.cursor
        # insert character if printable
        if u in self.allowed:
            if self.current_size < self.size:
                self.insert(self.cursor, u)
                self.cursor += 1
        # backspace deletes the previous character
        elif k == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.set_text(self.text[:self.cursor - 1] + \
                              self.text[self.cursor:])
                self.cursor -= 1
        # delete deletes the character under the cursor
        elif k == pygame.K_DELETE:
            if self.cursor < self.size:
                self.set_text(self.text[:self.cursor] + \
                              self.text[self.cursor + 1:])
        # movement keys
        elif k in conf.KEYS_LEFT:
            self.cursor = (cursor - 1) % (self.current_size + 1)
        elif k in conf.KEYS_RIGHT:
            self.cursor = (cursor + 1) % (self.current_size + 1)
        elif k in conf.KEYS_HOME:
            self.cursor = 0
        elif k in conf.KEYS_END:
            self.cursor = self.size
        else:
            Entry.input(self, event)
        if cursor != self.cursor:
            self._throw_event(TextEntry.CURSOR_EVENT)
        self._update_cursor()


class Select (Option):
    """Base class for a 'spin' widget to select a value.  Inherits from Option.

    CONSTRUCTOR

Select(text, value[, max_value_size], wrap = False)

text: text to display; any instances of '%x' are replaced with str(value).
value: initial value for the widget to hold.
max_value_size: the maximum size a value can take; defaults to len(str(value)).
wrap: whether to wrap end values around.

    METHODS

alter

    ATTRIBUTES

orig_text: the 'text' argument passed to the constructor.
value: the current value held by the widget.
wrap: as given.

    EVENTS

ALTER_EVENT: the value held by this widget was changed.  Callbacks are called
             after the widget's text has been updated to reflect the change.

"""

    def __init__ (self, text, value, max_value_size = None, wrap = False):
        self.orig_text = text
        if max_value_size is None:
            max_value_size = len(str(value))
        self.wrap = wrap
        max_size = len(text) + (max_value_size - 2) * text.count('%x')
        self.size = max_size
        Option.__init__(self, self._set_value(value, True), size = max_size)

    ALTER_EVENT = 5

    def __str__ (self):
        text = self.orig_text.encode('utf-8')
        return '<{0}: \'{1}\'>'.format(type(self).__name__, text)

    def set_value (self, value, return_only = False):
        """Set stored value."""
        try:
            if value == self.value:
                return
        except AttributeError:
            pass
        self.value = value
        text = self.orig_text.replace('%x', str(value))
        if return_only:
            return text
        else:
            self.set_text(text)
        self._throw_event(Select.ALTER_EVENT)

    _set_value = set_value


class DiscreteSelect (Select):
    """Choose from a given list of values.  Inherits from Select.

    CONSTRUCTOR

DiscreteSelect(text, options, initial = 0, wrap = False)

options: a list of the options the value can be chosen from.
initial: the index of the option in the options list to set as the widget's
         initial value.
wrap: whether to wrap end values around.

    ATTRIBUTES

options: as given.
index: index of the current value in options.

"""

    def __init__ (self, text, options, initial = 0, wrap = False):
        self.options = options
        self.index = int(initial)
        value = options[self.index]
        max_value_size = max(len(str(val)) for val in options)
        Select.__init__(self, text, value, max_value_size, wrap)

    def alter (self, direction, amount = 1):
        """'Spin' the widget to select a value.

alter(direction, amount = 1)

direction: -1 for left, 1 for right.
amount: 0 to go to start/end, otherwise spin by one step.

Returns whether the change was successful (can fail if wrapping is disabled).

"""
        rtn = 1
        old_index = self.index
        if direction != 1:
            direction = -1
        if amount == 0:
            if direction == 1:
                amount = len(self.options) - 1 - self.index
            else:
                amount = self.index
        else:
            amount = 1
        # alter index
        self.index += amount * direction
        if self.index == old_index:
            rtn = 0
        # confine index to a value within bounds
        if self.wrap:
            self.index %= len(self.options)
        else:
            index = self.index
            self.index = max(min(self.index, len(self.options) - 1), 0)
            if self.index != index and self.index == old_index:
                # tried to change, but couldn't
                rtn = 2
        # set value to that of next index
        self.set_value(self.index)
        return rtn

    def set_value (self, value, *args, **kw):
        self.index = int(value)
        value = self.options[value]
        return Select.set_value(self, value, *args, **kw)


class RangeSelect (Select):
    """Choose from integer values in a range.  Inherits from Select.

    CONSTRUCTOR

RangeSelect(text, a, b[, initial], wrap = False)

a: minimum value.
b: maximum value.
initial: the initial value; defaults to a.

    ATTRIBUTES

min: a as given.
max: b as given.

"""

    def __init__ (self, text, a, b, initial = None, wrap = False):
        self.min = int(a)
        self.max = max(self.min, int(b))
        if initial is None:
            initial = self.min
        # 'longest' number is either most negative or most positive
        max_size = max(len(str(self.min)), len(str(self.max)))
        Select.__init__(self, text, initial, max_size, wrap)

    def alter (self, direction, amount = 1):
        """'Spin' the widget to select a value.

alter(direction, amount = 1)

direction: -1 for left, 1 for right.
amount: 0 to go to start/end, else 1 to 4 for a small to a large step.

Returns whether the change was successful (can fail if wrapping is disabled).

"""
        rtn = 1
        if amount == 0:
            value = self.max if direction == 1 else self.min
        else:
            # get wanted step
            step = conf.SELECT_STEP[amount - 1]
            if step < 1:
                step = int(step * (self.max - self.min))
            # constrain by defined minimum
            min_step = conf.MIN_SELECT_STEP[amount - 1]
            if min_step < 1:
                min_step = int(min_step * (self.max - self.min))
            step = max(step, min_step)
            # get new value
            value = self.value + direction * step
            if self.wrap:
                value = (value - self.min) % (self.max - self.min + 1)
                value += self.min
            else:
                old_val = value
                value = max(min(value, self.max), self.min)
                if value != old_val and value == self.value:
                    # tried to change, but couldn't
                    rtn = 2
        if rtn == 1 and value == self.value:
            rtn = 0
        self._set_value(value)
        return rtn


class FloatSelect (RangeSelect):
    """Choose from decimal values in a range.  Inherits from RangeSelect.

    CONSTRUCTOR

FloatSelect(text, a, b, dp[, initial], wrap = False, pad = False)

dp: number of decimal places to display.  Must be greater than 0.
pad: whether to pad the start of the displayed number so that the decimal point
     remains stationary for all possible values.

    ATTRIBUTES

dp: as given.
pad: as given.

"""

    def __init__ (self, text, a, b, dp, initial = None, wrap = False,
                  pad = False):
        self.dp = max(1, int(dp))
        self.pad = pad
        # min, max, value should be ints
        a = int(round(a * 10 ** self.dp))
        b = max(int(round(b * 10 ** self.dp)), a)
        if initial is not None:
            initial = int(round(initial * 10 ** self.dp))
        # trick RangeSelect by increasing max to take up one more digit, so
        # that the proper max size gets propagated without doing much work here
        c = 10 * max(abs(a * 10) if a < 0 else abs(a), b)
        if abs(a) < 10 and abs(b) < 10:
            c *= 10
        # but make sure that initial value is still constrained properly
        if initial is not None:
            initial = min(initial, b)
        RangeSelect.__init__(self, text, a, c, initial, wrap)
        self.max = b

    def _set_value (self, value, return_only = False):
        """Same as set_value, but takes integer as stored."""
        if hasattr(self, 'value') and value == self.value:
            return value if return_only else None
        actual_value = value
        neg = value < 0
        value = str(abs(value))
        # If we have no units/lower, add 0s until we do
        while len(value) <= self.dp:
            value = '0' + value
        # pad front to keep . in the same place
        if self.pad:
            while self.size > len(value) + 1 + neg:
                value = ' ' + value
        neg = '-' if neg else ''
        value = neg + value[:-self.dp] + '.' + value[-self.dp:]
        rtn = RangeSelect.set_value(self, value, return_only)
        # value should remain int so RangeSelect.alter works
        self.value = actual_value
        return rtn

    def set_value (self, value, return_only = False):
        return self._set_value(int(round(value * 10 ** self.dp)), return_only)


class LongText (BaseText):
    """A text for longer strings that can span multiple rows.

    CONSTRUCTOR

LongText(menu, text, size[, rows])

menu: Menu instance.

    ATTRIBUTES

surface: rendered text.

"""

    def __init__ (self, menu, text, size, rows = None):
        self.menu = menu
        BaseText.__init__ (self, text, size, rows)
        self.set_text(text)

    def __str__ (self):
        text = self.text.encode('utf-8')
        return '<{0}: \'{1}\'>'.format(type(self).__name__, text)

    __repr__ = __str__

    def _surface (self, pzl = None):
        """Generate surface for this widget.

_surface([pzl]) -> surface

pzl: Puzzle instance to use.  If not given, use guessed values, just to get the
     number of rows this widget needs.

surface: the generated surface.

Stores the number of lines of text in current_rows (or, if too large, raises
ValueError).

"""
        if pzl is None:
            tile_h = 100
            gap = (0, 0)
        else:
            tile_h = pzl.tile_size(1)
            gap = pzl.tiler.gap
        ID = (str(self), tile_h)
        theme = conf.THEME
        # not sure why we need to take off 1, so I guess this is a HACK
        font = (conf.PUZZLE_FONT[theme], tile_h - 1, False)
        colour = conf.PUZZLE_TEXT_COLOUR[theme]
        n = self.size
        width = n * tile_h + (n - 1) * conf.PUZZLE_LINE_WIDTH[theme]
        font_args = (font, self.text, colour, None, width, 0, False, gap[1])
        surface, lines = self.menu.game.img(ID, font_args, text = True)
        # check and store number of lines used
        if self.rows is not None and lines > self.rows:
            msg = 'text too long: takes up {0} lines; maximum is {1}'
            raise ValueError(msg.format(lines, self.rows))
        self.current_rows = lines
        return surface

    def set_text (self, text):
        old_text = self.text
        self.text = self._chars(text)
        if conf.PUZZLE_TEXT_UPPER:
            self.text = self.text.upper()
        if self.text != old_text:
            if not self._is_first_append:
                self._throw_event(BaseText.CHANGE_EVENT)
                self.update()
            self._surface()

    def draw (self, screen = None):
        """Draw to the grid."""
        # create surface
        pzl = self.puzzle
        surface = self._surface(pzl)
        if screen is not None:
            # get position to draw at
            tile = self.pos
            rect = pzl.rect
            border = pzl.tiler.border
            gap = pzl.tiler.gap
            pos = []
            for i in (0, 1):
                tile_size = pzl.tile_size(i)
                x0 = rect[i] + border[i]
                x0 += tile[i] * tile_size + (tile[i] - 1) * gap[i]
                # adjust to look centred-ish (HACK)
                pzls =  self.menu.grids.itervalues()
                sizes = [[s[i] for s in p.text_adjust] for p in pzls]
                sizes = sum(sizes, [])
                try:
                    size = max((sizes.count(s), s) for s in sizes)[1]
                except ValueError:
                    # nothing to go off of
                    size = 0
                x0 += (tile_size - size) / 2
                pos.append(x0)
            # draw to screen
            screen.blit(surface, pos)


class Menu (object):
    """Abstract base class for a menu with navigable pages containing widgets.

    CONSTRUCTOR

Menu(game, event_handler[, page_ID], *args)

game: running Game instance.
event_handler: evthandler.EventHandler instance to use for keybindings.
page_ID: ID of page to start at.
args: positional arguments to pass to subclass's init method.

Subclasses should override this class's init method and call Menu.init therein.
Widgets are Text instances (and subclasses).

    METHODS

init
page_dim
set_page
refresh_text
generate_access_keys
generate_grid
selected
set_selected
move_selection
alter
select
back
capture_input
release_input
update
draw

    and for subclasses:

_quit_then
_new_select

    ATTRIBUTES

game: as passed to constructor.
event_handler: as passed to constructor.
last_pages: navigation stack: list of previous (self.page_ID, self.sel) tuples.
captured: the widget that has captured input, or False.
pages: list of pages, each a list of columns, each a list of rows, each a list
       of widgets.
re_init: set this to True to have the menu reinitialised (init called and
         page/selection restored).
sel: selected widget on the current page: [col, row] or None.
page_ID: the index of the current page in self.pages.
page: the current page from self.pages.
definition: data structure defining contents of the puzzle for the current
            page, excluding widgets.  See generate_grid method documentation
            for details.
w: width of the widget area of the menu in tiles.
h: height of the widget area of the menu in tiles.
grid_w: width of the menu puzzle in tiles (larger to accommodate window
        resizing.
grid_h: height of the menu puzzle in tiles.
grids: (page_ID: puzzle) dict for pages that have been loaded.
grid: the current puzzle.
keys: widget access keys: (keycode: widgets) dict where widgets is a list of
      (col, row) tuples.

    and for subclasses:

_default_selections: (page_ID: (col, row)) dict of initial widgets to select
                     where different from the first selectable widget.

"""

    def __init__ (self, game, event_handler, page_ID = None, *extra_args):
        self.game = game
        event_handler.add_event_handlers({pygame.KEYDOWN: self._access_keys})
        od = eh.MODE_ONDOWN
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MENU_INITIAL_DELAY * conf.MENU_FPS), 1),
            max(int(conf.MENU_REPEAT_DELAY * conf.MENU_FPS), 1)
        )
        event_handler.add_key_handlers([
            (conf.KEYS_UP, [(self._move_selection, (-1,))]) + args,
            (conf.KEYS_DOWN, [(self._move_selection, (1,))]) + args,
            (conf.KEYS_ALTER_LEFT, [(self.alter, (-1, 1))]) + args,
            (conf.KEYS_ALTER_RIGHT, [(self.alter, (1, 1))]) + args,
            (conf.KEYS_ALTER_LEFT_BIG, [(self.alter, (-1, 3))]) + args,
            (conf.KEYS_ALTER_RIGHT_BIG, [(self.alter, (1, 3))]) + args,
            (conf.KEYS_ALTER_HOME, [(self.alter, (-1, 0,))]) + args,
            (conf.KEYS_ALTER_END, [(self.alter, (1, 0))]) + args,
            (conf.KEYS_HOME, [(self._set_selected, (0,))]) + args,
            (conf.KEYS_END, [(self._set_selected, (1,))]) + args,
            (conf.KEYS_PAGE_UP, [(self._set_selected, (2,))]) + args,
            (conf.KEYS_PAGE_DOWN, [(self._set_selected, (3,))]) + args,
            (conf.KEYS_NEXT, self.select, od),
            (conf.KEYS_BACK, self.back, od)
        ])
        self.event_handler = event_handler
        self.FRAME = conf.MENU_FRAME
        self.last_pages = []
        self.captured = False
        self._default_selections = {}
        self._selects = {}
        # call subclass's init method
        page_ID_sub = self.init(*extra_args)
        # page_ID argument to constructor takes precedence over return value
        # from init and defaults to 0
        if page_ID is None:
            page_ID = page_ID_sub or 0
        self.set_page(page_ID)

    def init (self, pages):
        """Load the given pages into the menu.

The argument is a list of pages, each a list of columns, each a list of rows.
Rows are lists of widgets (Text or LongText instances) they contain.  If a page
has only one column, it can just be a list of rows.

"""
        self.pages = []
        for page in pages:
            if isinstance(page[0], (BaseText)):
                # one column
                page = [page]
            page = [col for col in page if col]
            self.pages.append(page)
        self.re_init = False
        self.dirty = True
        self.sel = None
        self.page_ID = None
        self.page = None
        self.definition = None

        # get maximum page width and height
        self.w, self.h = (max(self.page_dim(page)[i] for page in self.pages)
                          for i in (0, 1))
        # create grid
        self.grid_w = max(self.w, int(ceil(self.h * conf.MAX_RATIO[0])))
        self.grid_h = max(self.h, int(ceil(self.w * conf.MAX_RATIO[1])))
        if self.grid_w % 2 != self.w % 2:
            self.grid_w += 1
        if self.grid_h % 2 != self.h % 2:
            self.grid_h += 1
        self.grids = {}

    def page_dim (self, page, in_tiles = True):
        """Get the dimensions of a page.

page_dim(page, in_tiles = True) -> (width, height)

page: list of columns, each a list of widgets.
in_tiles: whether to give page dimensions in tiles (else in widgets).

"""
        if in_tiles:
            w = sum(max(text.size + 1 for text in c) for c in page) + 1
            h = max(sum(text.current_rows + 1 for text in c) for c in page) + 1
            return (w, h)
        else:
            return (len(page), max(len(c) for c in page))

    def set_page (self, page):
        """Set the page to the given ID."""
        if page == self.page_ID:
            return
        select = None
        if page == -1:
            # return to last page
            try:
                page, select = self.last_pages.pop()
            except IndexError:
                # no last page (this is the root page)
                self.game.quit_backend()
                return
        elif self.page_ID is not None:
            # save current selection
            self.last_pages.append((self.page_ID, self.sel))
        # clear selection on current page
        self.set_selected(None)
        # create grid if need to
        self.page_ID = page
        self.page = self.pages[self.page_ID]
        try:
            self.grid = self.grids[page]
        except KeyError:
            self.generate_grid()
        # compile options' first letters for access keys
        self.generate_access_keys()
        # set selection
        if select is None:
            # use default selection, then first selectable option if possible
            try:
                select = self._default_selections[self.page_ID]
            except KeyError:
                select = [0, 0]
        self.set_selected(select)
        # set values of Selects
        for col in self.page:
            for w in col:
                if isinstance(w, Select) and w in self._selects:
                    val = self._get_initial(self._selects[w][0])
                    w.set_value(val)
                    # store initialisation value
                    self._selects[w][1] = val
        self.dirty = True

    def refresh_text (self, page_ID = None, widget = None):
        """Update text widgets.

refresh_text([page_ID][, widget])

page_ID: page to refresh text for; defaults to the current page.
widget: widget (Text instance) to refresh text for; defaults to all widgets on
        the page.

"""
        if page_ID is None:
            page_ID = self.page_ID
        page = self.pages[page_ID]
        if widget is None:
            # do for all widgets
            for col in page:
                for widget in col:
                    self.refresh_text(page_ID, widget)
        else:
            # do for given widget
            is_long = isinstance(widget, LongText)
            (x0, y0) = widget.pos
            puzzle = self.grids[page_ID]
            # remove letters
            for y in xrange(y0, y0 + widget.current_rows):
                for x in xrange(x0, x0 + widget.size):
                    b = puzzle.grid[x][y][1]
                    if b is not None and (b.type > conf.MAX_ID or is_long):
                        puzzle.rm_block(None, x, y)
                    if not is_long:
                        # replace with original random block, if any
                        try:
                            puzzle.add_block((BoringBlock,
                                            self.definition[1][(x, y)]),
                                            x, y)
                        except KeyError:
                            pass
            if not is_long:
                # add letters back
                id_offset = widget.get_id_offset()
                for x, c in enumerate(widget.text):
                    o = ord(c) + id_offset
                    puzzle.add_block((BoringBlock, o), x0 + x, y)

    def generate_access_keys (self):
        """Generate the access keys dict for keyboard control of menus.

Options' first letters are used to select them.

"""
        self.keys = {}
        for i, col in enumerate(self.page):
            for j, element in enumerate(col):
                if isinstance(element, Option) and element.text:
                    # ignore caps - add for each variation
                    c = element.text[0]
                    ks = set((c, c.lower(), c.upper()))
                    for k in ks:
                        if k not in conf.IGNORED_ACCESS_KEY_CHARS:
                            try:
                                self.keys[k].append((i, j))
                            except KeyError:
                                self.keys[k] = [(i, j)]

    def generate_grid (self):
        """Generate the Puzzle for the current page.

The puzzle is stored in this Menu instance's grid and grids attributes, and the
definition attribute is set.  refresh_text is called.

The definition attribute is a list: [size, blocks, surfaces], where:

size: as the first line of a puzzle definition.
blocks, surfaces: both ((col, row): ID) dicts for things in the puzzle.

"""
        if self.definition is None:
            # create definition for random surfaces and blocks
            definition = ['{0} {1}\n'.format(self.grid_w, self.grid_h)]
            t = conf.THEME
            for min_ID, rand_ratio in ((0, conf.RAND_B_RATIO[t]),
                                       (conf.MIN_ID, conf.RAND_S_RATIO[t])):
                things = {} # blocks or surfaces depending on the iteration
                i = 0
                n = int(min(rand_ratio, 1) * self.grid_w * self.grid_h)
                n = min(n, n - len(things))
                while i < n:
                    pos = (randrange(self.grid_w), randrange(self.grid_h))
                    x = xrange(min_ID, conf.MAX_ID + 1)
                    # exclude arrows so we can use them for paging
                    type_ID = choice([j for j in x if j not in conf.S_ARROWS])
                    if pos not in things:
                        things[pos] = type_ID
                        i += 1
                definition.append(things)
            self.definition = definition
        else:
            definition = self.definition
        things = dict(definition[1])
        # generate expected format definition
        definition = definition[0] + '\n\n'.join(
            '\n'.join(
                '{0} {1} {2}'.format(type_ID, *pos)
                for pos, type_ID in things.iteritems()
            ) for things in (things, definition[2])
        )
        self.grid = Puzzle(self.game, definition, False, overflow = 'grow')
        self.grids[self.page_ID] = self.grid
        # give texts a position and references to the menu and the puzzle
        w, h = self.page_dim(self.page)
        x = (self.grid_w - w) / 2 + 1
        y0 = (self.grid_h - h) / 2 + 1
        for col in self.page:
            y = y0
            for text in col:
                text.menu = self
                text.puzzle = self.grid
                text.pos = (x, y)
                # update selection for TextEntry widgets
                if isinstance(text, TextEntry):
                    text._update_cursor()
                # add draw callbacks for LongText widgets
                if isinstance(text, LongText):
                    # get tiles covered
                    tiles = [[(x + i, y + j) for i in xrange(text.size)] \
                             for j in xrange(text.current_rows)]
                    tiles = sum(tiles, [])
                    # add draw callback for covered tiles
                    self.grid.add_draw_cb(text.draw, True, *tiles)
                y += text.current_rows + 1
            x += max(0, *(text.size + 1 for text in col))
        # add letters to the puzzle
        self.refresh_text()

    def selected (self, sel = None):
        """Get the widget given by a selection.

selected([sel]) -> widget

sel defaults to self.sel if not given, and so is (col, row).  If there is no
widget at the give position (selection is out of bounds), None is returned.

"""
        if sel is None:
            sel = self.sel
        try:
            return self.page[sel[0]][sel[1]]
        except IndexError:
            return None

    def _set_selected (self, key, event, mods, what):
        """Key callback for home/end/page up/page down."""
        if what == 0 or what == 2:
            # home
            self.set_selected((0, 0))
        elif what == 1 or what == 3:
            # end
            page = self.page
            es = self._flattened_elements(page, conf.DEFAULT_SELECT_ORDER)
            i = len(es) - 1
            while i >= 0:
                x, y = es[i]
                if isinstance(page[x][y], Option):
                    self.set_selected((x, y))
                    return
                i -= 1

    def set_selected (self, sel, force = False):
        """Set the currently selected widget.

set_selected(sel, force = False)

sel: (col, row) position of the widget to select, or None to deselect any
     currently selected widget.
force: re-select the widget even if it is already the selected widget.

If sel points to a widget that cannot be selected (not an Option instance),
this function selects the next selectable widget (that for which
(col, row) > sel and (col, row) is minimal), if any.  If there are none, no
widget is selected (but any currently selected widget _is_ deselected).

Behaviour in the case that sel does not point to a widget (out of bounds) is
undefined.

"""
        if sel is not None:
            sel = list(sel)
        if sel != self.sel or force:
            if self.sel is not None:
                # deselect current option
                self.selected().set_selected(False)
            if sel is not None:
                # select new option
                option = self.selected(sel)
                if not isinstance(option, Option):
                    # select next selectable element if possible
                    # get list of selectable elements
                    selectable = []
                    for i in xrange(len(self.page)):
                        for j in xrange(len(self.page[i])):
                            element = self.page[i][j]
                            if isinstance(element, Option):
                                selectable.append([i, j])
                    if selectable:
                        # check if any elements before the end are selectable
                        following = [x for x in selectable if x > sel]
                        if following:
                            sel = min(following)
                        else:
                            sel = min(selectable)
                    else:
                        sel = None
                if sel is not None:
                    self.selected(sel).set_selected(True)
            self.sel = sel

    def _flattened_elements (self, page, order):
        """Return a flattened list of the elements in the given page.

flattened_elements(page, order) -> element_list

page: list of columns, each a list of elements.
order: 0 for rows to take precedence, 1 for columns.

element_list: each element is represented by its row i and column j as (i, j).

"""
        pos = [[(i, j) for j in xrange(len(page[i]))]
               for i in xrange(len(page))]
        elements = sum(pos, [])
        # sort elements to match selection order
        if order == 0:
            elements.sort(cmp = lambda a, b: cmp((a[1], a[0]), (b[1], b[0])))
        else:
            elements.sort()
        return elements

    def _move_selection (self, key, event, mods, direction, axis = 1,
                        source = None):
        """Change the currently selected option (key callback)."""
        if self.sel is None:
            return
        sel = tuple(self.sel)
        direction = 1 if direction > 0 else -1
        num_elements = self.page_dim(self.page, False)
        # flatten elements grid to get a list in the order we'll select them
        elements = self._flattened_elements(self.page, axis)
        if source is None:
            source = elements
        again = True
        # find new selected element
        while again:
            pos = elements.index(sel)
            pos += direction
            pos %= len(elements)
            sel = elements[pos]
            selected = self.selected(sel)
            # skip non-existent and non-selectable elements
            if selected is not None and isinstance(selected, Option) and \
               sel in source:
                again = False
        # change selection
        if sel != self.sel:
            self.game.play_snd('move_selection')
        self.set_selected(sel)

    def move_selection (self, direction, axis = 1, source = None):
        """Change the currently selected option.

move_selection(direction, axis = 1[, source])

direction: 1 to move right/down, -1 to move up/left.
axis: 0 for horizontal, 1 for vertical.
source: list of (x, y) tuples indicating an element's (col, row) position for
        elements to select from; defaults to all elements on the page.

"""
        self._move_selection(None, None, None, direction, axis, source)

    def alter (self, key, event, mods, direction, amount):
        """Alter the currently selected Select widget (key callback.)"""
        if self.sel is None:
            return
        else:
            x, y = self.sel
        element = self.page[x][y]
        # if can alter this element,
        if isinstance(element, Select):
            # do so
            if event == 2 and amount:
                # go faster if holding the key
                amount += 1
            altered = element.alter(direction, amount)
            if altered == 1:
                self.game.play_snd('alter')
            elif altered == 2:
                self.game.play_snd('alter_fail')
        else:
            # else move selection left/right
            self.move_selection(direction, 0)
            return

    def select (self, *args):
        """Choose the currently selected Option widget, if any.

'Choosing' a widget means calling its click method.  We also play a sound
effect if defined by the theme.

"""
        if self.sel is None:
            return
        option = self.page[self.sel[0]][self.sel[1]]
        if hasattr(option, 'click'):
            self.game.play_snd('select')
            option.click()

    def back (self, *args):
        """Go backwards one page, if possible."""
        self.set_page(-1)

    def _access_keys (self, event):
        """Callback for all keypresses to check against access keys."""
        if self.captured:
            # pass input to capture function
            self.captured.input(event)
            return
        # select options by pressing their first letter
        try:
            elements = self.keys[event.unicode]
        except KeyError:
            # no matches
            return
        if len(elements) == 1:
            # one match: select it and try to click it
            self.set_selected(elements[0])
            self.select()
        else:
            # multiple matches: select next one
            self.move_selection(1, conf.DEFAULT_SELECT_ORDER, elements)
            return
            x, y = self.sel
            w, h = self.page_dim(self.page, False)
            sel = min(((j - y) % h, (i - x) % w, i, j)
                      for i, j in elements if i != x or j != y)[2:]
            self.set_selected(sel)

    def capture_input (self, element):
        """Capture all keyboard input.

Takes an element to pass all keypress events to the input method of.  Returns
whether the capture was allowed.

"""
        if self.captured:
            return False
        else:
            self.event_handler.keys_active = False
            self.captured = element
            return True

    def release_input (self, element):
        """Undo the capture set up through Menu.capture_input.

Takes the same element as was used to capture input; if this does not match, no
change is made.  Returns whether input was released (or was never captured
to start with).

"""
        if element is self.captured:
            self.event_handler.keys_active = True
            self.captured = False
            return True
        elif self.captured:
            return False
        else:
            return True

    def update (self):
        """Check if need to reinitialise."""
        if self.re_init:
            # pages might have changed
            ID = self.page_ID
            selected = self.sel[:]
            self.init()
            self.set_page(ID)
            self.set_selected(selected)

    def draw (self, screen):
        """Draw the menu."""
        if self.dirty:
            # make sure the options fit nicely on the screen in both dimensions
            res = self.game.res
            tile_size = min(float(res[0]) / self.w, float(res[1]) / self.h)
            grid_w = int(tile_size * self.grid_w)
            grid_h = int(tile_size * self.grid_h)
            self.grid.tiler.mode = ('grid', grid_w, grid_h)
        drawn = self.grid.draw(screen, self.dirty)
        self.dirty = False
        return drawn

    def _quit_then (self, f, *args):
        """Quit the menu then call the given function.

_quit_then(f, *args)

f: the function to call.
args: positional arguments to pass to the function.

"""
        self.game.quit_backend()
        f(*args)

    def _get_initial (self, initial):
        """Compute initialisation value from object stored in self._selects."""
        if hasattr(initial, '__call__'):
            return initial()
        else:
            try:
                return initial[0](*initial[1])
            except (TypeError, IndexError):
                return initial

    def _new_select (self, cls, initial, *args, **kw):
        """Add a Select instance and define how to initialise its value.

_new_select(cls, initial, ...) -> select_instance

cls: subclass of Select to instantiate.
initial: value to set the widget to on page load, or a function that returns
         the value to use, or (function, args) to do function(*args) to get the
         value.

Arguments to the created Select instance follow, excluding the 'initial'
argument.

select_instance: the created Select instance.

"""
        # zero-indexed
        init_arg_pos = {DiscreteSelect: 2, RangeSelect: 3, FloatSelect: 4}
        # add initial value to args
        val = self._get_initial(initial)
        i = init_arg_pos[cls]
        if len(args) > i:
            args = list(args)
            args.insert(i, val)
        else:
            kw['initial'] = val
        # create widget
        s = cls(*args, **kw)
        self._selects[s] = [initial, val]
        return s


# both of these need Menu
import level
import editor

class MainMenu (Menu):
    """The game's main menu."""

    def init (self):
        # some shortcuts
        s = self._new_select
        g = lambda i: (conf.get, (i,))
        w = self._with_custom_lvl
        snd_theme_index = lambda: conf.SOUND_THEMES.index(conf.SOUND_THEME)
        theme_index = lambda: conf.THEMES.index(conf.THEME)
        pages = (
            (
                Button('Play', self.set_page, 1),
                Button('Custom', self.set_page, 2),
                Button('Options', self.set_page, 7)
            ), [], (
                Button('New', self.game.start_backend, editor.Editor),
                Button('Load', self.set_page, 3),
                Button('Load draft', self.set_page, 4)
            ), [], [], (
                Button('Play', w, level.LevelBackend),
                Button('Edit', w, editor.Editor),
                Button('Delete', w, editor.DeleteMenu, 1, None, self.back),
                Button('Rename', self._rename),
                Button('Duplicate', self._rename, False)
            ), (
                Button('Edit', w, editor.Editor),
                Button('Delete', w, editor.DeleteMenu, 1, None, self.back),
                Button('Rename', self._rename),
                Button('Duplicate', self._rename, False)
            ), (
                Button('Sound', self.set_page, 8),
                Button('Gameplay', self.set_page, 9),
                Button('Display', self.set_page, 10),
                #Button('Delete data', self.set_page, 11)
            ), (
                s(RangeSelect, g('music_volume'), 'Music: %x', 0, 100),
                s(RangeSelect, g('sound_volume'), 'Sound: %x', 0, 100),
                s(DiscreteSelect, snd_theme_index, 'Theme: %x',
                  conf.SOUND_THEMES, True),
                Button('Save', self._save, (
                    ((8, 0), 'music_volume', self._update_music_vol),
                    ((8, 1), 'sound_volume', self._update_snd_vol),
                    ((8, 2), ('sound_theme', False), self._refresh_sounds)
                ))
            ), (
                s(RangeSelect, g('fps'), 'Speed: %x', 1, 50),
                s(DiscreteSelect, g('show_msg'), 'Message: %x', ('off', 'on'),
                  True),
                Button('Save', self._save, (
                    ((9, 0), 'fps'),
                    ((9, 1), 'show_msg')
                ))
            ), (
                s(DiscreteSelect, theme_index, 'Theme: %x', conf.THEMES, True),
                s(DiscreteSelect, g('fullscreen'), '%x',
                  ('Windowed', 'Fullscreen'), True),
                Button('Save', self._save, (
                    ((10, 0), ('theme', False), self._refresh_graphics),
                    ((10, 1), 'fullscreen', self.game.refresh_display)
                ))
            )
        )

        # create level pages
        for page, custom in ((1, 0), (3, 1), (4, 2)):
            lvls = level.get_levels(custom)
            page = pages[page]
            if not lvls:
                # nothing to show
                page.append(Text('Empty'))
                continue
            if not custom:
                completed = conf.get('completed_levels', [])
                uncompleted_to_show = conf.NUM_UNCOMPLETED_LEVELS
            # create columns
            col = 0
            for i in xrange(conf.LEVEL_SELECT_COLS):
                page.append([])
            # add buttons
            for lvl in lvls:
                ID = (custom, lvl)
                if custom:
                    b = Button(lvl, self._custom_lvl_cb, ID)
                else:
                    # highlight completed levels
                    b = Button(lvl, self.game.start_backend,
                               level.LevelBackend, ID,
                               special = lvl in completed)
                page[col].append(b)
                if not custom and lvl not in completed:
                    # only show a few unfinished levels
                    uncompleted_to_show -= 1
                    if uncompleted_to_show == 0:
                        # only show a certain number of uncompleted levels
                        break
                col += 1
                col %= conf.LEVEL_SELECT_COLS

        return Menu.init(self, pages)

    def _done_rename (self, name, old_name, d, then_del):
        """Cleanup after renaming/duplicating a level."""
        if old_name != name:
            if then_del:
                try:
                    os.remove(d + old_name)
                except OSError:
                    pass
            self.re_init = True
        self.back()

    def _rename (self, then_del = True):
        """Rename a level.  Pass False to skip deleting it afterwards."""
        # get definition
        ID = self._custom_lvl_ID
        d = conf.LEVEL_DIR_CUSTOM if ID[0] == 1 else conf.LEVEL_DIR_DRAFT
        name = ID[1]
        with open(d + name) as f:
            defn = f.read()
        # ask for new name
        self.game.start_backend(editor.SaveMenu, None, d, defn, name,
                                self._done_rename, name, d, then_del)

    def _update_snd_vol (self, vol):
        """Set the volume of existing sounds."""
        for snd in self.game.sounds.itervalues():
            snd.set_volume(vol * .01)

    def _update_music_vol (self, vol):
        """Set the volume of the currently playing music."""
        pygame.mixer.music.set_volume(vol * .01)

    def _refresh_sounds (self, theme):
        """Clear all cached game sounds and music files."""
        self.game.sounds = {}
        self.game.find_music()
        self.game.play_music()

    def _refresh_graphics (self, theme):
        """Clear cached game images and reinitialise the menu."""
        self.re_init = True
        self.game.files = {}
        self.game.imgs = {}

    def _custom_lvl_cb (self, ID):
        """Set up page shown on selecting a custom level."""
        self._custom_lvl_ID = ID
        self.set_page(6 if ID[0] == 2 else 5)

    def _with_custom_lvl (self, obj, ID_pos = 0, *args):
        """Start backend with self._custom_lvl_ID."""
        args = list(args)
        args.insert(ID_pos, self._custom_lvl_ID)
        self.game.start_backend(obj, *args)

    def _save (self, settings, back = True):
        """Save settings in the menu.

_save(settings, back = True)

settings: a list of (pos, setting[, cb, *args]) tuples, where:
    pos: (page_ID, col, row) tuple indicating the widget's location.
         (page_ID, row) can be used if the page has only one column.
    setting: setting ID to pass to with conf.set, or (setting_ID, False) to
             save the value attribute of a DiscreteSelect instance (rather
             than the index attribute).
    cb: a function to call after the setting has been saved; it is passed the
        new value.
    args: positional arguments to pass to cb (after the compulsory argument).
back: go back a page after saving.

Text instances are supported, where we save widget.value if widget is a Select
instance, widget.index (or widget.value) if it is a DiscreteSelect instance,
else widget.text.

"""
        to_save = {}
        cbs = []
        for data in settings:
            if len(data) >= 3:
                cb = data[2]
                args = data[3:]
                data = data[:2]
            else:
                cb = None
                args = ()
            pos, ID = data
            if isinstance(ID, basestring):
                ID = (ID, True)
            ID, save_index = ID
            # get widget
            if len(pos) == 2:
                pos = (pos[0], 0, pos[1])
            page, col, row = pos
            widget = self.pages[page][col][row]
            # get new value for the setting
            if isinstance(widget, DiscreteSelect):
                if save_index:
                    val = widget.index
                else:
                    val = widget.value
                real_val = widget.index
            elif isinstance(widget, FloatSelect):
                real_val = val = widget.value * 10 ** -widget.dp
            elif isinstance(widget, Select):
                real_val = val = widget.value
            else:
                real_val = val = widget.text
            
            if widget in self._selects and \
               self._selects[widget][1] == real_val:
                # value didn't change: don't save
                # (do this only for registered Selects since all other widgets
                #  have static initial values and so this check is easy)
                pass
            else:
                # store data to save all settings together
                to_save[ID] = val
                cbs.append((cb, val, args))
        # save settings
        if to_save:
            conf.set(**to_save)
        # call callbacks
        for cb, val, args in cbs:
            if cb is not None:
                cb(val, *args)
        if back:
            self.back()