"""

Directions are:
    0 left
    1 up
    2 right
    3 down

Axes are:
    0 horizontal
    1 vertical

"""
# TODO: document definition format, including solutions

from os import sep as path_sep
from os.path import exists
from random import randrange

import pygame
from tiler import Tiler, draw_rect

import conf

# TODO:
# - document classes
# - portal blocks
# - when we have bouncing blocks wall-to-wall trying to bounce, get infinite loop
#   - maybe take snapshot of all blocks each time we try to get a working configuration and if doesn't change, break
#     - do we even get to next time through loop, or do they just keep telling each other to calculate stuff?
#     - just need dest, or forces too?

def autocrop (s):
    """Return the smallest rect containing all non-transparent pixels.

Returns False if the image is completely transparent.

"""
    alpha = pygame.surfarray.pixels_alpha(s)
    alpha = (alpha, alpha.T)
    w, h = s.get_size()
    borders = []
    for i, pos in enumerate((0, 0, w - 1, h - 1)):
        axis = i % 2
        diff = -1 if i > 1 else 1
        try:
            while not any(alpha[axis][pos]):
                pos += diff
        except IndexError:
            # went out of array bounds, so the whole image is transparent
            return False
        borders.append(pos + (i > 1))
    b = borders
    return (b[0], b[1], b[2] - b[0], b[3] - b[1])

def is_immoveable (tile):
    """Determine whether a tile contains an immoveable object.

Immoveable objects are walls, and the immoveable block if not on a slippery
surface.  The given tile is conf.WALL, a Block instance or something else
(never immoveable).

"""
    if isinstance(tile, Block):
        surface = tile.puzzle.grid[tile.pos[0]][tile.pos[1]][0]
        # immoveable blocks can be moved on slippery surfaces
        immoveable = tile.type == conf.B_IMMOVEABLE and surface != conf.S_SLIDE
    else:
        immoveable = False
    return tile == conf.WALL or immoveable

def force_dir (axis, force):
    """Get the direction of a force.

force_dir(axis, force) -> direction

force is signed.

"""
    return axis + (2 if force > 0 else 0)

def force_axis (direction, force):
    """Get the axis and sign of a force (reverse of force_dir).

force_axis(direction, force) -> (axis, signed_force)

force is unsigned.

"""
    axis = direction % 2
    force = (1 if direction > 1 else -1) * force
    return axis, force

def opposite_dir (direction):
    """Get the opposite of a direction."""
    return (direction + 2) % 4


class BoringBlock (object):
    def __init__ (self, type_ID, puzzle, pos, dirn = None):
        self.type = type_ID
        self.tiler = puzzle.tiler
        self.pos = list(pos)
        if dirn is None:
            dirn = randrange(4)
        self.dirn = dirn

    def __str__ (self):
        return '<block: {0} at {1}>'.format(self.type, self.pos)

    __repr__ = __str__

    def set_direction (self, dirn):
        if dirn != self.dirn:
            self.dirn = dirn
            self.tiler.change(self.pos)


class Block (BoringBlock):
    def __init__ (self, type_ID, puzzle, pos, dirn = None):
        BoringBlock.__init__ (self, type_ID, puzzle, pos, dirn)
        self.puzzle = puzzle
        self.reset()

    def reset (self, keep_resultant = False):
        # reset some stuff to get ready for the next step
        if keep_resultant:
            resultant = self.resultant()
            self.sources = [{}, {}]
            for axis in (0, 1):
                if resultant[axis] != 0:
                    self.sources[axis][None] = [resultant[axis], False]
            self.handled = False
        else:
            self.sources = [{}, {}]
            self.handled = True
        self.targets = [{}, {}]
        self.unhandled_targets = [[], []]
        self.forces = [[], []]

    def resultant (self):
        # calculate resultant force on each axis
        return [sum(f for f, used in self.sources[axis].values())
                for axis in (0, 1)]

    def add_force (self, direction, force):
        # wrapper for adding non-Block force sources
        axis, force = force_axis(direction, force)
        self.add_sources(axis, {None: force})

    def add_sources (self, axis, sources):
        if conf.DEBUG:
            print 'add_sources', self, axis, sources
        sources = dict((k, [v, False]) for k, v in sources.iteritems())
        # None means not from a block; might be more than one
        if sources:
            try:
                self.sources[axis][None][0] += sources[None][0]
            except KeyError:
                pass
            else:
                del sources[None]
            self.sources[axis].update(sources)
            self.handled = False

    def rm_sources (self, axis, *sources):
        if conf.DEBUG:
            print 'rm_sources', self, axis, sources
        if sources:
            for source in sources:
                try:
                    del self.sources[axis][source]
                except KeyError:
                    pass
            self.handled = False

    def add_targets (self, axis, *targets):
        if conf.DEBUG:
            print 'add_targets', self, axis, targets
        if targets:
            u = self.unhandled_targets[axis]
            new = [t for t in targets if t not in u]
            if new:
                u += new
                self.handled = False

    def rm_targets (self, axis, *targets):
        if conf.DEBUG:
            print 'rm_targets', self, axis, targets
        if targets:
            for target in targets:
                try:
                    del self.targets[axis][target]
                except KeyError:
                    # not handled yet
                    u = self.unhandled_targets[axis]
                    if target in u:
                        u.remove(target)
                try:
                    target.rm_sources(axis, self)
                except AttributeError:
                    pass
            self.handled = False

    def target_tile (self, resultant = None):
        # get target tile for a given (or the current) resultant force
        if resultant is None:
            resultant = self.resultant()
        pos = self.pos[:]
        for axis in (0, 1):
            if resultant[axis]:
                pos[axis] += 1 if resultant[axis] > 0 else -1
        # check if calculated target is inside grid
        if 0 <= pos[0] < self.puzzle.w and 0 <= pos[1] < self.puzzle.h:
            return self.puzzle.grid[pos[0]][pos[1]][1]
        else:
            return conf.WALL

    def reaction (self, react_dir):
        if conf.DEBUG:
            print 'reaction', self, react_dir
        # handle reaction force from pushing something immoveable
        # remove forces on this axis
        axis = react_dir % 2
        react_on = []
        sources = self.sources[axis]
        for source, (force, used) in sources.items():
            if used:
                if source is not None:
                    react_on.append(source)
                del sources[source]
        # redistribute diagonal forces
        u = self.unhandled_targets
        t = self.targets
        for axis in (0, 1):
            targets = set(u[axis] + t[axis].keys())
            for target in targets:
                p = target.pos
                if p[0] != self.pos[0] and p[1] != self.pos[1]:
                    # diagonal: remove
                    self.rm_targets(axis, target)
        # propagate reaction
        for b in react_on:
            b.reaction(react_dir)
        self.handled = False

    def update (self):
        if conf.DEBUG:
            print 'update:', self, self.sources
        resultant = self.resultant()
        # mark current sources as used
        for sources in self.sources:
            for source in sources.itervalues():
                source[1] = True
        # check diagonal if need to
        if all(resultant):
            diag = self.target_tile(resultant)
        else:
            diag = False
        # check what's in target tiles on each axis and decide action to take
        react = [False] * 4
        for axis in (0, 1):
            force = resultant[axis]
            if not force:
                if self.sources[axis]:
                    # no resultant force on this axis: reaction
                    react[axis] = react[axis + 2] = (True, False)
                # won't push anything anyway
                continue
            # get adjacent target tile
            r = resultant[:]
            r[not axis] = 0
            adj = self.target_tile(r)
            if is_immoveable(adj):
                self.puzzle.play_snd('wall')
                # can't move on this axis
                react[opposite_dir(force_dir(axis, force))] = (True, True)
                # so can't move diagonally
                self.rm_targets(axis, diag)
            else:
                if adj:
                    self.puzzle.play_snd('hit')
                    self.add_targets(axis, adj)
                if diag and not is_immoveable(diag):
                    self.add_targets(axis, diag)
        # if trying to move on both axes and can't move to diagonal
        if diag and not is_immoveable(diag):
            self.puzzle.play_snd('hit')
        if is_immoveable(diag) and not any(react):
            self.puzzle.play_snd('wall')
            r = [abs(f) for f in resultant]
            if r[0] != r[1]:
                # unequal forces: reaction along weaker one's axis
                axis = r.index(min(r))
                force = resultant[axis]
                react[opposite_dir(force_dir(axis, force))] = (True, False)
            else:
                # equal forces: reaction along both axes
                for axis, force in enumerate(resultant):
                    react[opposite_dir(force_dir(axis, force))] = (True, False)
        # propagate any reactions
        handled = True
        for direction in xrange(len(react)):
            if react[direction]:
                self.reaction(direction)
                # bounce if right type and right sort of reaction
                if self.type is conf.B_BOUNCE and react[direction][1]:
                    self.add_force(direction, abs(resultant[direction % 2]))
                    handled = False

        # apply forces to targets
        for axis in (0, 1):
            # remove old targets
            old = self.targets[axis]
            if old:
                self.rm_targets(axis, *old.keys())
            # distribute forces among new targets
            new = self.unhandled_targets[axis]
            assert len(new) <= 2
            if len(new) == 2:
                force = resultant[axis] / 2
                if force == 0:
                    # not enough force to do anything
                    self.targets[axis] = {}
                else:
                    self.targets[axis] = {new[0]: resultant[axis] - force,
                                          new[1]: force}
            elif len(new) == 1:
                self.targets[axis] = {new[0]: resultant[axis]}
            self.unhandled_targets[axis] = []
            # apply forces to targets
            for target, force in self.targets[axis].iteritems():
                if force != 0:
                    target.add_sources(axis, {self: force})

        self.handled = handled


class Puzzle (object):
    def __init__ (self, game, defn, physics = False, sound = False,
                  **tiler_kw_args):
        self.game = game
        self.physics = physics
        self.sound = sound
        self.selected = {}
        self.rect = None
        self.load(defn, **tiler_kw_args)

    def _next_ints (self, lines):
        try:
            line = lines.pop(0).strip()
        except IndexError:
            return None
        if line and line[0] == '#':
            # comment
            return self._next_ints(lines)
        else:
            try:
                return [int(c) for c in line.split(' ') if c]
            except ValueError:
                return False

    def reset (self, *tiles):
        if tiles:
            # reset given tiles
            tiles = [(x, y) for x, y in tiles]
        else:
            # reset all tiles
            tiles = [[(i, j) for i in xrange(self.w)] for j in xrange(self.h)]
            tiles = sum(tiles, [])
        # clear tiles we want to change
        for x, y in tiles:
            self.rm_block(None, x, y)
            self.set_surface(x, y)
        # add initial blocks and surfaces back
        cls = Block if self.physics else BoringBlock
        for type_ID, (x, y), dirn in self._init_blocks:
            if (x, y) in tiles:
                self.add_block((cls, type_ID, dirn), x, y)
        for type_ID, x, y in self._init_surfaces:
            if (x, y) in tiles:
                self.set_surface(x, y, type_ID)

    def load (self, defn, **tiler_kw_args):
        """Initialise puzzle from a definition.

Returns whether the puzzle was resized (may leave areas outside the puzzle
dirty).  Preserves any selection, if possible.

"""
        self._draw_cbs = {}
        lines = defn.split('\n')
        # dimensions in first line
        first = self._next_ints(lines)
        try:
            w, h = first
        except ValueError:
            # also got default surface
            w, h, default_s = first
        else:
            default_s = conf.DEFAULT_SURFACE
        self.w = w
        self.h = h
        self.size = (self.w, self.h)
        self.default_s = default_s
        # extract blocks from definition
        bs = []
        line = self._next_ints(lines)
        while line:
            type_ID, i, j = line
            bs.append((type_ID, (i, j), randrange(4)))
            line = self._next_ints(lines)
        self._init_blocks = bs
        self.blocks = []
        # extract non-default surface types from definition
        ss = []
        line = self._next_ints(lines)
        while line:
            ss.append(line)
            line = self._next_ints(lines)
        self._init_surfaces = ss
        # create grid handler if need to
        if hasattr(self, 'tiler'):
            # already initialised: need to resize first
            resized = self.resize_abs(w, h)
        else:
            for key, attr in (('line', 'PUZZLE_LINE_COLOUR'),
                              ('gap', 'PUZZLE_LINE_WIDTH'),
                              ('border', 'PUZZLE_LINE_WIDTH')):
                if key not in tiler_kw_args:
                    tiler_kw_args[key] = getattr(conf, attr)[conf.THEME]
            self.tiler = Tiler(w, h, self.draw_tile, track_tiles = False,
                               **tiler_kw_args)
            resized = False
        # create grid with default surface
        self.grid = []
        for i in xrange(self.w):
            col = []
            for j in xrange(self.h):
                col.append([self.default_s, None, False])
            self.grid.append(col)
        # preserve selection
        sel = self.selected
        self.reset()
        for pos, colour in sel.iteritems():
            try:
                self.select(pos, colour)
            except IndexError:
                # now out of range
                pass
        return resized

    def add_block (self, block, x, y):
        """Add a block, optionally creating it first.

add_block(block, x, y)

block: either a BoringBlock instance or a (block_class, *args) tuple, where:
    block_class: the class to instantiate (BoringBlock or Block).
    args: arguments to pass to the constructor, excluding puzzle and pos.
x, y: tile to place the block on.  If given a Block instance, its pos attribute
      gets set to this value.

"""
        pos = [x, y]
        if isinstance(block, BoringBlock):
            block.pos = pos
        else:
            # create block first; got (class, *args) tuple
            cls, type_ID = block[:2]
            args = block[2:]
            block = cls(type_ID, self, pos, *args)
        # remove existing block, if any
        self.rm_block(None, x, y)
        # add new block
        self.grid[x][y][1] = block
        self.blocks.append(block)
        self.tiler.change((x, y))

    def rm_block (self, block = None, x = None, y = None):
        # remove a block
        if block is None:
            if None not in (x, y):
                block = self.grid[x][y][1]
            # else got nothing
        else:
            x, y = block.pos
        if block is not None:
            self.grid[x][y][1] = None
            self.blocks.remove(block)
            self.tiler.change((x, y))
        # else passed nothing or tile has no block

    def mv_block (self, block, x, y):
        # move a block
        self.rm_block(block)
        self.add_block(block, x, y)

    def set_surface (self, x, y, surface = None):
        # set the surface at a tile
        if surface is None:
            surface = self.default_s
        self.grid[x][y][0] = surface
        self.tiler.change((x, y))

    def select (self, pos, secondary_colour = False):
        """Select a tile.

select(pos, secondary_colour = False)

pos: (x, y) tile position.
secondary_colour: whether to use the secondary cursor colour
                  (conf.SECONDARY_SEL_COLOUR instead of conf.SEL_COLOUR for the
                  current theme).

"""
        pos = tuple(pos[:2])
        try:
            if self.selected[pos] in self.selected:
                return
        except KeyError:
            pass
        # either not selected or different colour
        x, y = pos
        # let out-of-bounds errors propagate
        self.grid[x][y][2] = True
        self.selected[pos] = secondary_colour
        self.tiler.change(pos)

    def deselect (self, *tiles):
        """Deselect the given tiles, if selected.

deselect(*tiles)

tiles: each an (x, y) position; if none are given, deselect every selected
       tile.

"""
        for pos in (tiles if tiles else self.selected.keys()):
            x, y = pos = tuple(pos[:2])
            try:
                del self.selected[pos]
                self.grid[x][y][2] = False
            except (KeyError, IndexError):
                # isn't selected or doesn't exist to deselect
                pass
            else:
                self.tiler.change(pos)

    def move_selected (self, direction, amount = 1):
        """Move all selections relative to the current position.

move_selected(direction, amount = 1)

direction: 0/1/2/3 for L/U/R/D.
amount: number of tiles to move.

If the destination tile is out-of-bounds, select the nearest in-bounds tile.

"""
        selected = self.selected.items()
        # deselect all
        self.deselect()
        # reselect one at a time
        for pos, colour in selected:
            pos = list(pos)
            axis = direction % 2
            pos[axis] += amount * (1 if direction > 1 else -1)
            pos[axis] %= self.size[axis]
            self.select(pos, colour)

    def _reset_tiler (self):
        self.tiler.reset()
        self.text_adjust = []

    def tile_size (self, axis):
        n_tiles = self.size[axis]
        border = self.tiler.border[axis]
        gap = self.tiler.gap[axis]
        tile_size = (self.rect.size[axis] - 2 * border - gap * (n_tiles - 1))
        return tile_size / n_tiles

    def resize (self, amount, direction):
        if amount == 0:
            return False
        # resize one tile at a time
        # get new grid size
        axis = direction % 2
        sign = 1 if amount > 0 else -1
        size = list(self.size)
        size[axis] += sign
        if size[axis] == 0:
            # can't shrink
            return False
        # get amount to offset everything by
        offset = [0, 0]
        offset[axis] += (sign - (1 if direction > 1 else -1)) / 2
        self.size = (w, h) = size
        # resize tiler
        self.tiler.w = w
        self.tiler.h = h
        self._reset_tiler()
        # create new grid
        grid = []
        di, dj = offset
        for i in xrange(w):
            col = []
            i -= di
            for j in xrange(h):
                j -= dj
                if 0 <= i < self.w and 0 <= j < self.h:
                    col.append(self.grid[i][j])
                else:
                    # doesn't come from current grid
                    col.append([self.default_s, None, False])
            grid.append(col)
        self.grid = grid
        self.w, self.h = self.size
        for pos, colour in self.selected.items():
            orig_pos = pos
            # offset selected tiles
            pos = list(pos)
            pos[0] += di
            pos[1] += dj
            x, y = pos
            # push selection back onto the grid
            if not (0 <= x < self.w and 0 <= y < self.h):
                for axis in (0, 1):
                    limit = self.size[axis] - 1
                    pos[axis] = min(max(pos[axis], 0), limit)
            self.deselect(orig_pos)
            self.select(pos, colour)
        self.resize(amount - sign, direction)
        return True

    def resize_abs (self, w, h):
        return self.resize(w - self.w, 2) or  self.resize(h - self.h, 3)

    def definition (self):
        """Return a definition string for the puzzle's current state."""
        # get blocks and surfaces from self.grid
        bs = []
        ss = []
        s_count = {}
        for i in xrange(len(self.grid)):
            col = self.grid[i]
            for j in xrange(len(col)):
                s, b, sel = col[j]
                if b is not None:
                    bs.append('{0} {1} {2}'.format(b.type, i, j))
                ss.append((s, '{0} {1} {2}'.format(s, i, j)))
                try:
                    s_count[s] += 1
                except KeyError:
                    s_count[s] = 1
        # get most common surface type to use as default
        # we only want one, so don't worry about types with the same freqency
        s_count = dict((v, k) for k, v in s_count.iteritems())
        common_s = s_count[max(s_count)]
        default = conf.DEFAULT_SURFACE
        common_s = '' if common_s == default else ' ' + str(common_s)
        # compile definition
        return '{0} {1}{2}{3}{4}\n\n{5}'.format(
            self.w, self.h, common_s,
            '\n' if bs else '',
            '\n'.join(bs),
            # don't need individual tiles for most common surface
            '\n'.join(data for s, data in ss if s != common_s)
        )

    def play_snd (self, ID):
        """Wrapper around Game.play_snd."""
        if self.sound:
            self.game.play_snd(ID)

    def step (self):
        if conf.DEBUG:
            print 'start step'
        # apply arrow forces
        for col in self.grid:
            for s, b, sel in col:
                if s in conf.S_ARROWS and b is not None and not is_immoveable(b):
                    b.add_force(conf.S_ARROWS.index(s), conf.FORCE_ARROW)

        # resolve forces into block destinations
        while 1:
            # handle contact forces
            while 1:
                unhandled = [b for b in self.blocks if not b.handled]
                if unhandled:
                    for b in unhandled:
                        b.update()
                else:
                    break

            # compile block destinations
            dest = {}
            for b in self.blocks:
                resultant = b.resultant()
                # get destination
                pos = b.pos[:]
                for axis, force in enumerate(resultant):
                    if force:
                        pos[axis] += 1 if force > 0 else -1
                if pos != b.pos:
                    # lists aren't hashable
                    pos = tuple(pos)
                    try:
                        dest[pos].append(b)
                    except KeyError:
                        dest[pos] = [b]
            if conf.DEBUG and dest:
                print dest

            # resolve conflicts
            rm = []
            for pos, bs in dest.iteritems():
                if len(bs) == 1:
                    dest[pos] = bs[0]
                else:
                    # check if highest force towards destination is unique
                    max_f = 0
                    for b in bs:
                        force = b.resultant()
                        force = abs(force[0]) + abs(force[1])
                        if force == max_f:
                            unique = False
                        elif force > max_f:
                            max_f = force
                            unique = b
                    if unique:
                        # move block with most force
                        dest[pos] = unique
                        bs.remove(unique)
                    else:
                        # don't move any blocks
                        rm.append(pos)
                    # reaction on all blocks that don't move
                    for b in bs:
                        diff = (b.pos[0] - pos[0], b.pos[1] - pos[1])
                        for axis in (0, 1):
                            if diff[axis]:
                                b.reaction(1 + axis + diff[axis])
            for pos in rm:
                del dest[pos]

            if not [b for b in self.blocks if not b.handled]:
                # done
                break

        if conf.DEBUG and dest:
            print dest

        # move blocks
        change = set()
        retain_forces = []
        if dest:
            self.play_snd('move')
        for pos, b in dest.iteritems():
            # remove
            change.add(tuple(b.pos))
            self.grid[b.pos[0]][b.pos[1]][1] = None
            slide = self.grid[pos[0]][pos[1]][0] == conf.S_SLIDE
            if b.type in (conf.B_SLIDE, conf.B_BOUNCE) or slide:
                retain_forces.append(b)
        for pos, b in dest.iteritems():
            # add
            change.add(pos)
            b.pos = list(pos)
            self.grid[pos[0]][pos[1]][1] = b
        self.tiler.change(*change)
        # reset forces
        for b in self.blocks:
            b.reset(b in retain_forces)
        if conf.DEBUG:
            print 'end step'

    def add_draw_cb (self, f, call_once = False, *tiles):
        for t in tiles:
            assert t not in self._draw_cbs
            self._draw_cbs[t] = (f, call_once)

    def _draw_from_img (self, surface, rect, prefix, ID, dirn = None):
        ID = prefix + str(ID)
        fn_base = conf.IMG_DIR + conf.THEME + path_sep + ID
        # if have a direction, look for specially rotated image before fallback
        suffixes = (None if dirn is None else ('-' + str(dirn)), '')
        got = False
        for fallback, suffix in enumerate(suffixes):
            if suffix is not None:
                fn = fn_base + suffix + '.png'
                if exists(fn):
                    got = True
                    if not fallback:
                        ID += suffix
                        # this is already rotated: no need to rotate in code
                        dirn = None
                    break
        if got:
            # image might be transparent
            if prefix == 's':
                surface.fill(conf.BG[conf.THEME], rect)
            img = self.game.img(ID, fn, rect)
            # rotate if necessary
            if dirn:
                img = pygame.transform.rotate(img, -90 * dirn)
            surface.blit(img, rect)
            return True
        else:
            return False

    def draw_tile (self, surface, rect, i, j):
        # draw a single tile; called by Tiler
        s, b, selected = self.grid[i][j]
        theme = conf.THEME
        # surface
        if s < 0:
            # blit image if exists, else use colour
            if self._draw_from_img(surface, rect, 's', s):
                colour = ()
            else:
                colour = conf.SURFACE_COLOURS[theme][s]
        else:
            # goal: use block colour
            colour = conf.BLOCK_COLOURS[theme][s]
        if colour:
            surface.fill(colour, rect)
        # selection ring
        if selected:
            width = int(rect[2] * conf.SEL_WIDTH[theme])
            width = max(width, conf.MIN_SEL_WIDTH[theme])
            colour = self.selected[(i, j)]
            if colour:
                colour = conf.SECONDARY_SEL_COLOUR[theme]
            else:
                colour = conf.SEL_COLOUR[theme]
            draw_rect(surface, colour, rect, width)
        # block
        if b is not None:
            if b.type < conf.MIN_CHAR_ID:
                # blit image if exists, else use colour
                if not self._draw_from_img(surface, rect, 'b', b.type, b.dirn):
                    rect = pygame.Rect(rect)
                    p = rect.center
                    r = rect.w / 2
                    pygame.draw.circle(surface, (0, 0, 0), p, r)
                    c = conf.BLOCK_COLOURS[theme][b.type]
                    pygame.draw.circle(surface, c, p, int(r * .8))
            else:
                # draw character in tile
                c = b.type
                if c < conf.SELECTED_CHAR_ID_OFFSET:
                    # normal
                    colour = conf.PUZZLE_TEXT_COLOUR[theme]
                elif c < conf.SPECIAL_CHAR_ID_OFFSET:
                    # selected
                    c -= conf.SELECTED_CHAR_ID_OFFSET
                    colour = conf.PUZZLE_TEXT_SELECTED_COLOUR[theme]
                else:
                    # special
                    c -= conf.SPECIAL_CHAR_ID_OFFSET
                    colour = conf.PUZZLE_TEXT_SPECIAL_COLOUR[theme]
                # render character
                c = chr(c).upper() if conf.PUZZLE_TEXT_UPPER else chr(c)
                h = rect[3]
                text, lines = self.game.img((b.type, h),
                                     ((conf.PUZZLE_FONT[theme], h, False),
                                     c, colour), text = True)
                # crop off empty bits
                source = autocrop(text)
                # HACK
                if len(self.text_adjust) < 30 and source:
                    self.text_adjust.append(source[2:])
                if source: # else blank
                    # centre in tile rect
                    target = [rect[0] + (rect[2] - source[2]) / 2,
                              rect[1] + (h - source[3]) / 2]
                    # crop to fit in tile rect (remove previous crop and move
                    # to current target position first)
                    s = pygame.Rect(source).move(-source[0], -source[1])
                    s = s.move(target).clip(rect).move(-target[0], -target[1])
                    # offset the target position by the same amount
                    target = [target[0] + s[0], target[1] + s[1]]
                    source = s.move(source[:2])
                    surface.blit(text, target, source)

    def draw (self, screen, everything = False, size = None):
        # draw grid and tiles
        if everything:
            self._reset_tiler()
        try:
            changed = list(self.tiler._changed)
        except TypeError:
            pass
        rects = self.tiler.draw_changed(screen, size)
        if rects is None:
            cbs = []
            rtn = None
        elif isinstance(rects[0], int):
            # drew everything and got back the tiler rect: store it
            self.rect = pygame.Rect(rects)
            cbs = self._draw_cbs.values()
            rtn = [rects]
        else:
            cbs = [v for k, v in self._draw_cbs.iteritems() if k in changed]
            rtn = rects[1:]
        # call draw callbacks
        cbs = list(set([f for f, once in cbs if once])) + \
              [f for f, once in cbs if not once]
        for f in cbs:
            f(screen)
        return rtn

    def point_tile (self, p):
        """Get tile containing given (x, y) point, or None."""
        if self.rect is None or not self.rect.collidepoint(p):
            return None
        result = []
        for i in (0, 1):
            border = self.tiler.border[i]
            tile_size = self.tile_size(i)
            gap = self.tiler.gap[i]
            n_tiles = self.size[i]
            pos = int(p[i])
            pos -= self.rect[i] + border
            # take gaps between tiles into account
            if pos % (tile_size + gap) >= tile_size:
                # between tiles/on border
                return None
            tile = pos / (tile_size + gap)
            if 0 <= tile < n_tiles:
                result.append(tile)
            else:
                # on border
                return None
        return result