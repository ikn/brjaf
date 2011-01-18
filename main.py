import sys
from os import sep
from time import time

import pygame
from pygame.time import wait
pygame.init()
import evthandler as eh

from menu import MainMenu
from level import Level
import conf

class Fonts:
    """Collection of pygame.font.Font instances."""

    def __init__ (self, *fonts):
        self.fonts = {}
        for font in fonts:
            self.add(font)

    def add (self, font, force_reload = False):
        """Load a font and add it to the collection."""
        font = tuple(font)
        if force_reload or font not in self.fonts:
            fn, size, bold = font
            self.fonts[font] = pygame.font.Font(conf.FONT_DIR + sep + fn, int(size), bold = bold)
        return self.fonts[font]

    def text (self, font, text, colour, shadow = None, width = None, just = 0, minimise = False):
        """Render text from a font.

text(font, text, colour[, shadow][, width], just = 0, minimise = False) -> surface

font: (font name, size, is_bold) tuple.
text: text to render.
colour: (R, G, B[, A]) tuple.
shadow: to draw a drop-shadow: (colour, offset) tuple, where offset is (x, y).
width: maximum width of returned surface (wrap text).
just: if the text has multiple lines, justify: 0 = left, 1 = centre, 2 = right.
minimise: if width is set, treat it as a minimum instead of absolute width.

"""
        font = tuple(font)
        self.add(font)
        font, lines = self.fonts[font], []
        if shadow is None:
            offset = (0, 0)
        else:
            shadow_colour, offset = shadow

        # split into lines
        text = text.splitlines()
        if width is None:
            width = max(font.size(line)[0] for line in text)
            lines = text
            minimise = True
        else:
            for line in text:
                if font.size(line)[0] > width:
                    # wrap
                    words = line.split(' ')
                    # check if any words won't fit
                    for word in words:
                        if font.size(word)[0] >= width:
                            raise ValueError('\'{0}\' doesn\'t fit on one line'.format(word))
                    # build line
                    build = ''
                    for word in words:
                        temp = build + ' ' if build else build
                        temp += word
                        if font.size(temp)[0] < width:
                            build = temp
                        else:
                            lines.append(build)
                            build = word
                    lines.append(build)
                else:
                    lines.append(line)
        if minimise:
            width = max(font.size(line)[0] for line in lines)

        # create surface
        h = 0
        for line in lines:
            h += font.size(line)[1]
        surface = pygame.Surface((width + offset[0], h + offset[1])).convert_alpha()
        surface.fill((0, 0, 0, 0))

        # add text
        for colour, mul in (() if shadow is None else ((shadow_colour, 1),)) + ((colour, -1),):
            o = (max(mul * offset[0], 0), max(mul * offset[1], 0))
            h = 0
            for line in lines:
                if line:
                    s = font.render(line, True, colour)
                    if just == 2:
                        surface.blit(s, (width - s.get_width() + o[0], h + o[1]))
                    elif just == 1:
                        surface.blit(s, ((width - s.get_width()) / 2 + o[0], h + o[1]))
                    else:
                        surface.blit(s, (o[0], h + o[1]))
                h += font.size(line)[1]
        return surface

class Game:
    """Handles backends.

    METHODS

start_backend
quit_backend
run
refresh_display
minimise
toggle_fullscreen

    ATTRIBUTES

running: set to False to exit the main loop (Game.run).
fonts: a Fonts instance.
backend: the current running backend.
backends: a list of previous (nested) backends, most 'recent' last.
imgs: image cache.
files: loaded image cache (before resize).

"""

    def __init__ (self):
        self.running = False
        self.imgs = {}
        self.files = {}
        # load display settings
        conf.FULLSCREEN = conf.get('fullscreen', conf.FULLSCREEN)
        conf.RES_W = conf.get('res', conf.RES_W)
        self.refresh_display()
        self.fonts = Fonts()
        # start first backend
        self.backends = []
        self.start_backend(MainMenu)

    def start_backend (self, cls, *args):
        """Start a new backend.

start_backend(cls, *args)

cls: the backend class to instantiate.
args: arguments to pass to the constructor.

Backends handle pretty much everything, including drawing, and must have update
and draw methods, as follows:

update(): handle input and make any necessary calculations.
draw(screen) -> drawn: draw anything necessary to screen; drawn is True if the
                       whole display needs to be updated, something falsy if
                       nothing needs to be updated, else a list of rects to
                       update the display in.

A backend should also have a dirty attribute, which indicates whether its draw
method should redraw everything, and a FRAME attribute, which is the length of
one frame in seconds.

A backend is constructed via
backend_class(Game_instance, EventHandler_instance, *args), and should store
EventHandler_instance in its event_handler attribute.

"""
        h = eh.MODE_HELD
        event_handler = eh.EventHandler({
            pygame.VIDEORESIZE: self._resize_cb, # EVENT_ENDMUSIC: self.play_music
        }, [
            (conf.KEYS_FULLSCREEN, self.toggle_fullscreen, eh.MODE_ONDOWN),
            (conf.KEYS_MINIMISE, self.minimise, eh.MODE_ONDOWN),
        ], False, self._quit)
        try:
            self.backends.append(self.backend)
        except AttributeError:
            pass
        self.backend = cls(self, event_handler, *args)

    def quit_backend (self, depth = 1):
        """Quit the currently running backend.

quit_backend(depth = 1)

depth: quit this many backends.

If the running backend is the last (root) one, exit the game.

"""
        depth = int(depth)
        if depth < 1:
            return
        try:
            self.backend = self.backends.pop()
        except IndexError:
            self.running = False
        else:
            self.backend.dirty = True
        depth -= 1
        if depth:
            self.quit_backend(depth)
        else:
            # need to update new backend before drawing
            self.update_again = True

    def set_backend_attrs (self, cls, attr, val, current = True, inherit = True):
        """Set an attribute of all backends with a specific class.

set_backend_attrs(cls, attr, val, current = True, inherit = True)

cls: the backend class to look for.
attr: the name of the attribute to set.
val: the value to set the attribute to.
current: include the current backend in the search.
inherit: also apply to all classes that inherit from the given class.

        """
        for backend in self.backends + ([self.backend] if current else []):
            if isinstance(backend, cls) if inherit else (backend == cls):
                setattr(backend, attr, val)

    def img (self, ID, data, size = None, text = False):
        """Load or render an image, or retrieve it from cache.

img(ID, data[, size], text = False) -> surface

ID: a string identifier unique to the expected result, ignoring size.
data: if text is True, a tuple of args to pass to Fonts.text, else a filename
      to load.
size: if given, scale the image to this size.  Can be a rect, in which case its
      dimension is used.
text: determine how to get the required image (what to do with data).

"""
        if size is not None:
            if len(size) == 4:
                # rect
                size = size[2:]
            size = tuple(size)
        key = (ID, size)
        if key in self.imgs:
            return self.imgs[key]
        # else new: load/render
        if text:
            # TODO: if this raises pygame.error, fallback to some standard font
            img = self.fonts.text(*data)
        else:
            # also cache loaded images to reduce file I/O
            if data in self.files:
                img = self.files[data]
            else:
                img = pygame.image.load(data)
                self.files[data] = img
        # scale
        if size is not None:
            img = pygame.transform.smoothscale(img, size)
        # speed up blitting
        if img.get_alpha() is None:
            img = img.convert()
        else:
            img = img.convert_alpha()
        # add to cache
        self.imgs[key] = img
        return img

    def _quit (self, event = None):
        """pygame.QUIT event callback."""
        self.running = False

    def _update (self):
        """Run the backend's update method."""
        self.backend.event_handler.update()
        self.backend.update()

    def _draw (self):
        """Run the backend's draw method and update the screen."""
        draw = self.backend.draw(self.screen)
        if draw is True:
            pygame.display.update()
        elif draw:
            pygame.display.update(draw)

    def run (self):
        """Main loop."""
        self.running = True
        t0 = time()
        while self.running:
            self.update_again = False
            self._update()
            if self.update_again:
                self._update()
            self._draw()
            t1 = time()
            wait(int(1000 * (self.backend.FRAME - t1 + t0)))
            t0 += self.backend.FRAME
        # save display settings
        conf.set('fullscreen', conf.FULLSCREEN)
        conf.set('res', conf.RES_W)

    def refresh_display (self):
        """Update the display mode from conf, and notify the backend."""
        flags = 0
        if conf.FULLSCREEN:
            flags |= pygame.FULLSCREEN
            self.res = conf.RES_F
        else:
            w = max(conf.MIN_RES_W[0], conf.RES_W[0])
            h = max(conf.MIN_RES_W[1], conf.RES_W[1])
            w = min(w, int(h * conf.MAX_RATIO))
            h = min(h, int(w * conf.MAX_RATIO))
            self.res = (w, h)
        if conf.RESIZABLE:
            flags |= pygame.RESIZABLE
        self.screen = pygame.display.set_mode(self.res, flags)
        try:
            self.backend.dirty = True
        except AttributeError:
            pass
        # clear image cache
        self.imgs = {}

    def toggle_fullscreen (self, *args):
        """Toggle fullscreen mode."""
        conf.FULLSCREEN = not conf.FULLSCREEN
        self.refresh_display()

    def minimise (self, *args):
        """Minimise the display, pausing if possible (and necessary)."""
        if isinstance(self.backend, Level):
             self.backend.pause()
        pygame.display.iconify()

    def _resize_cb (self, event):
        """Callback to handle a window resize."""
        conf.RES_W = (event.w, event.h)
        self.refresh_display()

if __name__ == '__main__':
    if conf.WINDOW_ICON is not None:
        pygame.display.set_icon(pygame.image.load(conf.WINDOW_ICON))
    if conf.WINDOW_TITLE is not None:
        pygame.display.set_caption(conf.WINDOW_TITLE)
    Game().run()

pygame.quit()