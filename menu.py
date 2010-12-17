from math import ceil
from random import randrange, randint

import evthandler as eh

import level
from puzzle import Puzzle

import conf

# TODO:
# document Menu and derivatives
# select options by first letter
# text placement needs fixing for smaller pages (centre on both axes)
# scrollable element sets - set maximum number and scroll if exceed it

# Text (.size, .text)
# | Option (.attach(event, handler))
# | | Button (.select; event:select)
# | | Select (abstract; .wrap; event:change; put arrows in edge blocks; text contains %x to replace with current value)
# | | | DiscreteSelect (.options)
# | | | RangeSelect (.min, .max, .step)
# | | | | FloatSelect (.dp)
# | | Entry (event:change)
# | | | KeyEntry
# Image (.w, .h, .img, .border = (size, colour))

class Text:
    """A simple widget to display (immutable) text.

    CONSTRUCTOR

Text(text, special = False)

text: the text to display.
special: whether to display in a different style.

    ATTRIBUTES

text: the widget's text.
size: the length of the text.
selectable: whether the widget can be selected (always False).
pos: the position of the first character in the grid display, or None if
     unknown.
puzzle: the Puzzle instance the widget exists in, or None if unknown.
special: whether the text is displayed in a different style.

"""

    def __init__ (self, text, special = False):
        chars = []
        for c in text:
            o = ord(c)
            if o >= conf.MIN_CHAR_ID and o <= conf.MAX_CHAR_ID:
                chars.append(c)
            else:
                chars.append(' ')
        self.text = ''.join(chars)
        self.size = len(self.text)
        self.selectable = False
        self.pos = None
        self.puzzle = None
        self.special = special

    def __str__ (self):
        return '<{0}: \'{1}\'>'.format(self.__class__.__name__, self.text)

    __repr__ = __str__

class Option (Text):
    """A selectable widget.  Inherits from Text.

    METHODS

attach_event
set_selected

    ATTRIBUTES

selectable: always True.
selected: whether this widget is currently selected.
ehs: an event: handlers dict of attached event handlers.

    EVENTS

SELECT_EVENT: the selected state has changed.  This is called after the
              selected attribute is changed to the new state.

"""

    def __init__ (self, text):
        Text.__init__(self, text)
        self.selectable = True
        self.selected = False
        self.ehs = {}

    SELECT_EVENT = 0

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

    def set_selected (self, selected):
        """Set the widget's selected state."""
        if selected == self.selected:
            return
        # move blocks
        change = set()
        pos = list(self.pos)
        for dx in xrange(self.size):
            change.add(tuple(pos))
            ID = ord(self.text[dx])
            if selected:
                ID += conf.SELECTED_CHAR_ID_OFFSET
            elif self.special:
                ID += conf.SPECIAL_CHAR_ID_OFFSET
            self.puzzle.grid[pos[0]][pos[1]][1].type = ID
            pos[0] += 1
        self.puzzle.tiler.change(*change)
        self.selected = selected
        self._throw_event(Option.SELECT_EVENT)

class Button (Option):
    """A button widget.  Inherits from Option.

    CONSTRUCTOR

Button(text[, click_handler, *click_args])

Passing click_handler and click_args is identical to calling
Button.attach_event(Button.CLICK_EVENT, click_handler, click_args).

    METHODS

click

    EVENTS

CLICK_EVENT: the button was clicked.

"""

    def __init__ (self, text, click_handler = None, *click_args):
        Option.__init__(self, text)
        if click_handler is not None:
            self.attach_event(Button.CLICK_EVENT, click_handler, click_args)

    CLICK_EVENT = 1

    def click (self):
        """Trigger handlers attached to CLICK_EVENT."""
        self._throw_event(Button.CLICK_EVENT)

class Select (Option):
    pass

class Image:
    pass

class Menu:
    def __init__ (self, game, event_handler):
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MENU_INITIAL_DELAY * conf.MENU_FPS), 1),
            max(int(conf.MENU_REPEAT_DELAY * conf.MENU_FPS), 1)
        )
        event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.alter, (-1,))]) + args,
            (conf.KEYS_UP, [(self.move_selection, (-1,))]) + args,
            (conf.KEYS_RIGHT, [(self.alter, (1,))]) + args,
            (conf.KEYS_DOWN, [(self.move_selection, (1,))]) + args,
            (conf.KEYS_BACK, self.back, eh.MODE_ONDOWN),
            (conf.KEYS_NEXT, self.select, eh.MODE_ONDOWN)
        ])
        self.event_handler = event_handler
        self.game = game
        self.FRAME = conf.MENU_FRAME
        self.last_pages = []
        self.init()
        self.set_page(0)

    def init (self, pages):
        if not conf.SILENT:
            print 'init', self
        self.pages = []
        for page in pages:
            if isinstance(page[0], (Text, Image)):
                # one column
                page = [page]
            self.pages.append(page)
        self.re_init = False
        self.dirty = True
        self.sel = None
        self.page_ID = None
        self.page = None
        self.definition = None

        # get maximum page width and height
        w = 0
        h = 0
        for page in self.pages:
            page_w = sum(max(text.size + 1 for text in c) for c in page)
            w = max(w, page_w)
            h = max(h, *(len(col) for col in page))
        # add padding
        self.w = w + 1
        self.h = 2 * h + 1
        # create grid
        self.grid_w = max(self.w, int(ceil(self.h * conf.MAX_RATIO)))
        self.grid_h = max(self.h, int(ceil(self.w * conf.MAX_RATIO)))
        if self.grid_w % 2 != self.w % 2:
            self.grid_w += 1
        if self.grid_h % 2 != self.h % 2:
            self.grid_h += 1
        self.grids = {}

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
            self.grids[self.page_ID] = self.grid
        # set selection
        if select is None:
            # select first selectable option if possible
            select = [0, 0]
        self.set_selected(select)
        self.dirty = True

    def generate_grid (self):
        # generate a grid containing random stuff and this page's text
        if self.definition is None:
            # create definition for random surfaces and blocks
            definition = ['{0} {1}\n'.format(self.grid_w, self.grid_h)]
            data = ((0, conf.RAND_B_RATIO), (conf.MIN_ID, conf.RAND_S_RATIO))
            for min_ID, rand_ratio in data:
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
        # letters count as blocks; add to the right part of the definition
        x0 = (self.grid_w - self.w) / 2 + 1
        y0 = (self.grid_h - self.h) / 2 + 1
        for col in self.page:
            for y, text in enumerate(col):
                text.pos = (x0, y0 + 2 * y)
                for x, c in enumerate(text.text):
                    # just replace any blocks that might be here already
                    o = ord(c)
                    if text.special:
                        o += conf.SPECIAL_CHAR_ID_OFFSET
                    things[(x0 + x, y0 + 2 * y)] = o
            x0 += max(0, *(text.size + 1 for text in col))
        # generate expected format definition
        definition = definition[0] + '\n\n'.join(
            '\n'.join(
                '{0} {1} {2}'.format(type_ID, *pos)
                for pos, type_ID in things.iteritems()
            ) for things in (things, definition[2])
        )
        self.grid = Puzzle(self.game, definition, False, overflow = 'grow')
        # Texts need a reference to Tiler to change their appearance
        for col in self.page:
            for text in col:
                text.puzzle = self.grid

    def selected (self, sel = None):
        if sel is None:
            sel = self.sel
        try:
            return self.page[sel[0]][sel[1]]
        except IndexError:
            return None

    def set_selected (self, sel):
        # set the currently selected option
        if sel != self.sel:
            if self.sel is not None:
                # deselect current option
                self.selected().set_selected(False)
            if sel is not None:
                # select new option
                option = self.selected(sel)
                if not option.selectable:
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

    def move_selection (self, event, amount, axis = 1):
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
            while selected is None or not selected.selectable:
                sel[axis] += amount
                sel[axis] %= num_elements
                selected = self.selected(sel)
            amount -= direction
        # change selection
        self.set_selected(sel)

    def alter (self, event, amount):
        if self.sel is None:
            return
        element = self.page[self.sel[0]][self.sel[1]]
        if not isinstance(element, Select):
            self.move_selection(None, amount, 0)
            return
        # TODO: alter

    def back (self, event = None):
        # go back one page, if possible
        self.set_page(-1)

    def select (self, event = None):
        # choose the currently selected option, if any
        if self.sel is None:
            return
        option = self.page[self.sel[0]][self.sel[1]]
        if hasattr(option, 'click'):
            option.click()

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

class MainMenu (Menu):
    def init (self):
        pages = (
            (
                Button('Play', self.set_page, 1),
                Button('Options', self.set_page, 2),
                Button('Quit', self.game.quit_backend)
            ), [], (
                Button('Input', self.set_page, 3),
                Button('Sound', self.set_page, 4)
            ), (
                Text('Key repeat'),
                Option('Delay 0.2'), # 0.1 - 1.0 | FloatSelect('Delay %x', .1, 1, .1)
                Option('Speed 10'), # 1 - 10 | RangeSelect('Speed %x', 1, 10, 1) | is 1 / repeat_delay
                Button('Save', self.back)
            ), (
                Text('Volume'),
                Option('Music 50'),
                Option('Sound 50'),
                Button('Save', self.back)
            )
        )
        completed = conf.get('completed_levels', [])
        uncompleted_to_show = conf.NUM_UNCOMPLETED_LEVELS
        for lvl in level.get_levels():
            lvl = str(lvl)
            b = Button(lvl, self.game.start_backend, level.Level, (False, lvl))
            if lvl in completed:
                b.special = True
            else:
                uncompleted_to_show -= 1
            pages[1].append(b)
            if uncompleted_to_show == 0:
                # only show a certain number of uncompleted levels
                break
        Menu.init(self, pages)

class PauseMenu (Menu):
    def init (self):
        Menu.init(self, (
            (
                Button('Continue', self.game.quit_backend),
                Button('Hint', self.set_page, 1),
                Button('Quit', self.game.quit_backend, 2)
            ),
        ))