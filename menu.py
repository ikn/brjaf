from math import ceil
from random import randrange, randint

import pygame
import evthandler as eh

from puzzle import Puzzle, BoringBlock
import conf

# TODO:
# - document Menu
# - home/end/page up/page down keys (paging is home/end for non-scrolling pages, else
# - scrollable pages - set maximum number of rows and scroll if exceed it; show arrows in rows above top/below bottom if any up/down there (in far left/right tiles)
# - u/d, l/r should go to prev/next col, row at ends: flatten elements to 1D list
# - keys should select next option, like u/d, l/r: flatten with others removed
# - options:
#       key bindings/repeat rates
#       delete data (progress, custom levels, solution history, local_conf)
#       appearance (select from multiple themes)
#       sound/music volume
# - custom levels delete/rename/duplicate

# Text
# | Option
# | | Button
# | | | Entry
# | | | | TextEntry
# | | | | KeyEntry
# | | Select
# | | | DiscreteSelect
# | | | RangeSelect
# | | | | FloatSelect (.dp)
# Image (.w, .h, .img, .border = (size, colour))

class Text (object):
    """A simple widget to display (immutable) text.

    CONSTRUCTOR

Text(text, special = False[, size])

text: the text to display.
special: whether to display in a different colour.
size: the maximum size of the text.  This is used to determine the menu size.

    METHODS

append
insert
set_text
attach_event
get_id_offset
update

For all methods that manipulate the text, the result is truncated to self.size.

    ATTRIBUTES

text: the widget's text.
size: the maximum length of the text.
current_size: the size of the current text.
pos: the position of the first character in the grid display, or None if
     unknown.
special: whether the text is displayed in a different style; defaults to False.
         Call update after changing to redraw.
ehs: an event: handlers dict of attached event handlers.
menu: the Menu instance the widget exists in, or None if unknown.
puzzle: the Puzzle instance the widget exists in, or None if unknown.

    EVENTS

CHANGE_EVENT: the text changed; called after the change is made.

"""

    def __init__ (self, text, special = False, size = None):
        self.text = u''
        self.size = len(text) if size is None else int(size)
        self.ehs = {}
        self.special = False
        self.pos = None
        self.menu = None
        self.puzzle = None
        self.append(text, True)

    CHANGE_EVENT = 0

    def __str__ (self):
        text = self.text.encode('utf-8')
        return '<{0}: \'{1}\'>'.format(self.__class__.__name__, text)

    __repr__ = __str__

    def append (self, text, is_first_append = False, force_update = False):
        """Append a string to the end of the text.

Returns whether any characters were truncated.

"""
        old_text = self.text
        if not isinstance(text, unicode):
            text = text.decode('utf-8')
        chars = []
        truncated = False
        l = len(self.text)
        for c in text:
            if l + len(chars) == self.size:
                # can't add any more
                truncated = True
                break
            # limit character range
            o = ord(c)
            if o >= conf.MIN_CHAR_ID and o <= conf.MAX_CHAR_ID:
                chars.append(c)
            else:
                # replace other characters with spaces
                chars.append(u' ')
        self.text += ''.join(chars)
        self.current_size = len(self.text)
        if not is_first_append:
            # update if text changed
            if force_update or old_text != self.text:
                self._throw_event(Text.CHANGE_EVENT)
                self.update()
            # regenerate menu access keys if first letter changed
            if (old_text and old_text[0]) != (self.text and self.text[0]):
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
        """Set the value of the text.

Returns whether any characters were truncated.

"""
        update = self.text and not text
        self.text = u''
        return self.append(text, force_update = update)

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

    def get_id_offset (self):
        """Get the number to add to block IDs."""
        return conf.SPECIAL_CHAR_ID_OFFSET if self.special else 0

    def update (self):
        """Make any changes visible."""
        self.menu.refresh_text(widget = self)


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
        self._toggle_keys = set(conf.KEYS_NEXT + (pygame.K_ESCAPE,))

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

TextEntry(max_size, initial_text = '', allowed = conf.PRINTABLE,
      special = False)

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

    def __init__ (self, max_size, initial_text = '', allowed = conf.PRINTABLE,
                  special = False):
        Entry.__init__(self, initial_text, special, max_size)
        self.cursor = self.current_size
        self.allowed = set(allowed)

    CURSOR_EVENT = 4

    def _update_cursor (self):
        """Update the cursor position."""
        if self.focused:
            self.cursor = max(0, min(self.cursor, self.current_size))
            self.puzzle.select(self.pos[0] + self.cursor, self.pos[1])
        else:
            self.puzzle.deselect()

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
        Option.__init__(self, self._set_value(value, True), size = max_size)

    ALTER_EVENT = 5

    def _set_value (self, value, return_only = False):
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


class DiscreteSelect (Select):
    """Choose from a given list of values.  Inherits from Select.

    CONSTRUCTOR

DiscreteSelect(text, options, index = 0, wrap = False)

options: a list of the options the value can be chosen from.
index: the index in the options list to set as the widget's initial value.
wrap: whether to wrap end values around.

    METHODS

alter

    ATTRIBUTES

options: as given.
index: index of the current value in options.

"""

    def __init__ (self, text, options, index = 0, wrap = False):
        self.options = options
        self.index = int(index)
        self.wrap = wrap
        value = options[self.index]
        max_value_size = max(len(str(val)) for val in options)
        Select.__init__(self, text, value, max_value_size, wrap)

    def alter (self, direction, amount = 1):
        """'Spin' the widget to select a value.

alter(direction, amount = 1)

direction: -1 for left, 1 for right.
amount: 0 to go to start/end, otherwise spin by one step.

"""
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
        # confine index to a value within bounds
        if self.wrap:
            self.index %= len(self.options)
        else:
            self.index = max(min(self.index, len(self.options) - 1), 0)
        # set value to that of next index
        self._set_value(self.options[self.index])

class RangeSelect (Select):
    """Choose from integer values in a range.  Inherits from Select.

    CONSTRUCTOR

RangeSelect(text, a, b[, initial], wrap = False)

a: minimum value.
b: maximum value.
initial: the initial value; defaults to a.

"""

    def __init__ (self, text, a, b, initial = None, wrap = False):
        self.min = int(a)
        self.max = max(self.min, int(b))
        if initial is None:
            initial = self.min
        else:
            # choose next value down if given value not an option
            initial = max(self.min, *(x for x in options if x <= initial))
        # 'longest' number is either most negative or most positive
        max_size = max(len(str(self.min)), len(str(self.max)))
        Select.__init__(self, text, initial, max_size, wrap)

    def alter (self, direction, amount = 1):
        """'Spin' the widget to select a value.

alter(direction, amount = 1)

direction: -1 for left, 1 for right.
amount: 0 to go to start/end, else 1 to 4 for a small to a large step.

"""
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
            value = max(min(self.value + direction * step, self.max), self.min)
        self._set_value(value)


class Image (object):
    pass


class Menu (object):
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
            (conf.KEYS_UP, [(self.move_selection, (-1,))]) + args,
            (conf.KEYS_DOWN, [(self.move_selection, (1,))]) + args,
            (conf.KEYS_ALTER_LEFT, [(self.alter, (-1, 1))]) + args,
            (conf.KEYS_ALTER_RIGHT, [(self.alter, (1, 1))]) + args,
            (conf.KEYS_ALTER_LEFT_BIG, [(self.alter, (-1, 3))]) + args,
            (conf.KEYS_ALTER_RIGHT_BIG, [(self.alter, (1, 3))]) + args,
            (conf.KEYS_ALTER_HOME, [(self.alter, (-1, 0,))]) + args,
            (conf.KEYS_ALTER_END, [(self.alter, (1, 0))]) + args,
            (conf.KEYS_NEXT, self.select, od),
            (conf.KEYS_BACK, self.back, od)
        ])
        self.event_handler = event_handler
        self.FRAME = conf.MENU_FRAME
        self.last_pages = []
        self.captured = False
        self._default_selections = {}
        # call subclass's init method
        page_ID_sub = self.init(*extra_args)
        # page_ID argument to constructor takes precedence over return value
        # from init and defaults to 0
        if page_ID is None:
            page_ID = page_ID_sub or 0
        self.set_page(page_ID)

    def init (self, pages):
        self.pages = []
        for page in pages:
            if isinstance(page[0], (Text, Image)):
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
                          for i in xrange(2))
        # create grid
        self.grid_w = max(self.w, int(ceil(self.h * conf.MAX_RATIO)))
        self.grid_h = max(self.h, int(ceil(self.w * conf.MAX_RATIO)))
        if self.grid_w % 2 != self.w % 2:
            self.grid_w += 1
        if self.grid_h % 2 != self.h % 2:
            self.grid_h += 1
        self.grids = {}

    def page_dim (self, page, padding = True):
        if padding:
            return (sum(max(text.size + 1 for text in c) for c in page) + 1,
                    2 * max(len(c) for c in page) + 1)
        else:
            return (len(page), max(len(c) for c in page))

    def set_page (self, page):
        # change the current menu page and its associated elements
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
            (x0, y) = widget.pos
            puzzle = self.grids[page_ID]
            # remove letters
            for x in xrange(x0, widget.size + x0):
                b = puzzle.grid[x][y][1]
                if b is not None and b.type > conf.MAX_ID:
                    puzzle.rm_block(None, x, y)
                # replace with original random block, if any
                try:
                    puzzle.add_block((BoringBlock, self.definition[1][(x, y)]),
                                     x, y)
                except KeyError:
                    pass
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
                        try:
                            self.keys[k].append((i, j))
                        except KeyError:
                            self.keys[k] = [(i, j)]

    def generate_grid (self):
        # generate a grid containing random stuff and this page's text
        if self.definition is None:
            # create definition for random surfaces and blocks
            definition = ['{0} {1}\n'.format(self.grid_w, self.grid_h)]
            for min_ID, rand_ratio in ((0, conf.RAND_B_RATIO),
                                       (conf.MIN_ID, conf.RAND_S_RATIO)):
                things = {} # blocks or surfaces depending on the iteration
                i = 0
                n = int(min(rand_ratio, 1) * self.grid_w * self.grid_h)
                n = min(n, n - len(things))
                while i < n:
                    pos = (randrange(self.grid_w), randrange(self.grid_h))
                    type_ID = randint(min_ID, conf.MAX_ID)
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
        # texts references to the menu and the puzzle
        for col in self.page:
            for text in col:
                text.menu = self
                text.puzzle = self.grid
        w, h = self.page_dim(self.page)
        x0 = (self.grid_w - w) / 2 + 1
        y0 = (self.grid_h - h) / 2 + 1
        for col in self.page:
            for y, text in enumerate(col):
                text.pos = (x0, y0 + 2 * y)
            x0 += max(0, *(text.size + 1 for text in col))
        # add letters to the puzzle
        self.refresh_text()

    def selected (self, sel = None):
        if sel is None:
            sel = self.sel
        try:
            return self.page[sel[0]][sel[1]]
        except IndexError:
            return None

    def set_selected (self, sel, force = False):
        # set the currently selected option
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

    def move_selection (self, key, event, mods, amount, axis = 1):
        # change the selected option
        if self.sel is None:
            return
        sel = self.sel[:]
        direction = 1 if amount > 0 else -1
        if axis == 0:
            num_elements = len(self.page)
        else:
            num_elements = max(len(col) for col in self.page)
        while amount:
            sel[axis] += amount
            sel[axis] %= num_elements
            selected = self.selected(sel)
            # skip non-existent and non-selectable elements
            while selected is None or not isinstance(selected, Option):
                sel[axis] += amount
                sel[axis] %= num_elements
                selected = self.selected(sel)
            amount -= direction
        # change selection
        self.set_selected(sel)

    def alter (self, key, event, mods, direction, amount):
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
            element.alter(direction, amount)
        else:
            # else move selection left/right
            self.move_selection(None, None, None, direction, 0)
            return

    def select (self, *args):
        # choose the currently selected option, if any
        if self.sel is None:
            return
        option = self.page[self.sel[0]][self.sel[1]]
        if hasattr(option, 'click'):
            option.click()

    def back (self, *args):
        # go back one page, if possible
        self.set_page(-1)

    def _access_keys (self, event):
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
        if self.re_init:
            # pages might have changed
            ID = self.page_ID
            selected = self.sel[:]
            self.init()
            self.set_page(ID)
            self.set_selected(selected)

    def draw (self, screen):
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


# both of these need menu.Menu
import level
import editor

class MainMenu (Menu):
    """The game's main menu."""

    def init (self):
        pages = (
            (
                Button('Play', self.set_page, 1),
                Button('Custom', self.set_page, 2),
                Button('Options', self.set_page, 5),
                RangeSelect('%x', -200, 200)
            ), [], (
                Button('New', self.game.start_backend, editor.Editor),
                Button('Load', self.set_page, 3)
            ), [], (
                Button('Play', self._with_custom_lvl, level.LevelBackend),
                Button('Edit', self._with_custom_lvl, editor.Editor),
                #Button('Delete'),
                #Button('Rename'),
                #Button('Duplicate')
            ), (
                Button('Input', self.set_page, 6),
                Button('Sound', self.set_page, 7)
            ), (
                Text('Key repeat'), # have Puzzle/Menu options, each with Delay/Speed
                Option('Delay 0.2'), # 0.1 - 1.0 | FloatSelect('Delay %x', .1, 1, .1)
                Option('Speed 10'), # 1 - 10 | RangeSelect('Speed %x', 1, conf.FPS, 1) | is 1 / repeat_delay
                Button('Save', self.back)
            ), (
                Text('Volume'),
                Option('Music 50'),
                Option('Sound 50'),
                Button('Save', self.back)
            )
        )

        # create level pages
        for page, custom in ((1, False), (3, True)):
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
                    b = Button(lvl, self.game.start_backend,
                               level.LevelBackend, ID)
                page[col].append(b)
                if not custom:
                    # highlight completed levels
                    if lvl in completed:
                        b.special = True
                    else:
                        # only show a few unfinished levels
                        uncompleted_to_show -= 1
                        if uncompleted_to_show == 0:
                            # only show a certain number of uncompleted levels
                            break
                col += 1
                col %= conf.LEVEL_SELECT_COLS

        return Menu.init(self, pages)

    def _custom_lvl_cb (self, ID):
        """Set up page shown on selecting a custom level."""
        self._custom_lvl_ID = ID
        self.set_page(4)

    def _with_custom_lvl (self, obj):
        """Start backend with self._custom_lvl_ID."""
        self.game.start_backend(obj, self._custom_lvl_ID)