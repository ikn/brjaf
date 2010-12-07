from time import time

import pygame
from pygame.time import wait

pygame.init()

from tiler import Tiler
import evthandler as eh
import conf

# TODO:
# test case A
# bouncing blocks
# block orientation - set after motion, use in draw_tile
# more fluid animation
# images for blocks
# messages
# solutions:
#   confirmation; something random (have criteria):
#       "Are you sure you've thought this through?"
#       "Do you intend to play the game yourself at all?" (used solutions often)
#       "Getting lazy again?" (used solutions often)
#       "Phew, I was getting worried you might be getting clever." (used solutions, but not recently)
#       "Not going to think about it for a bit first?" (haven't spent long on the puzzle)
#       "I should start charging for these solutions." (used solutions often)
#       "I knew you'd be back." (used solutions often)
#       "I hope you got here by accident." (haven't spent long on the puzzle)
#       "Do you _really_ want to stoop this low?"
#       "Hey, you have to do some of the work." (used solutions often)
#       "Wheeeeeeeeeeeee!"
#       "It's not that hard, I promise."
#   "Keep trying" / "Do it for me"

def is_immoveable (tile):
    is_block = isinstance(tile, Block)
    is_immoveable_block = is_block and tile.type == conf.B_IMMOVEABLE
    return tile == conf.WALL or is_immoveable_block

def force_dir (axis, force):
    return axis + (2 if force > 0 else 0)

def opposite_dir (direction):
    return (direction + 2) % 4

class Block:
    def __init__ (self, type_ID, level, pos, orientation = None):
        self.type = type_ID
        self.level = level
        self.pos = pos
        self.dir = orientation
        self.forces = []
        self.handled = True

    def __str__ (self):
        return '<block: {0} at {1}>'.format(self.type, self.pos)

    __repr__ = __str__

    def add_force (self, direction, magnitude, source = None):
        print 'forced:', self, direction, magnitude, source
        # add a new force; source is a Block instance or None
        if magnitude == 0:
            return
        elif magnitude < 0:
            direction = opposite_dir(direction)
            magnitude = -magnitude
        magnitude = int(magnitude)
        self.forces.append([direction, magnitude, source, None])
        self.handled = False

    def rm_force (self, index):
        print 'unforced:', self, index, self.forces[index]
        try:
            d, f, source, targets = self.forces[index]
        except TypeError:
            # has been removed already
            return
        f *= 1 if d > 1 else -1
        self.forces[index] = None
        if targets:
            # remove force from blocks it was applied to
            for b, i in targets:
                target_f = b.forces[i]
                if target_f is None:
                    # already removed
                    continue
                b.rm_force(i)
                # multiple local forces might have this target:
                # make up the difference
                target_f = (1 if target_f[0] > 1 else -1) * target_f[1]
                try:
                    difference = target_f - (f / len(targets)) - difference
                except NameError:
                    difference = target_f - (f / len(targets))
                d = opposite_dir(d) if difference < 0 else d
                if difference:
                    b.add_force(d, abs(difference), self)
                    new_i = len(b.forces) - 1
                    # redirect all local forces that had this target
                    target = (b, i)
                    for d, f, source, targets in self.real_forces():
                        if target in targets:
                            targets[targets.index(target)] = (b, new_i)

    def real_forces (self):
        # forces might be None: return a list of those that aren't
        return [f for f in self.forces if f is not None]

    def resultant (self, unhandled_only = False):
        # calculate resultant force on each axis
        resultant = [0, 0]
        for d, f, source, handled in self.real_forces():
            if not unhandled_only or (unhandled_only and handled is None):
                resultant[d % 2] += f if d > 1 else -f
        return resultant

    def reduce_forces (self):
        # replace all forces with resultant on each axis
        resultant = self.resultant()
        self.forces = []
        for i in xrange(2):
            f = resultant[i]
            if f:
                self.add_force(i + 2, f)

    def remove_forces (self, axis):
        # remove all forces on the given axis
        applied_to = []
        for i in xrange(len(self.forces)):
            f = self.forces[i]
            if f is not None and f[0] % 2 == axis:
                # forces need to retain position in list
                if f[3]:
                    applied_to += f[3]
                self.rm_force(i)
        return applied_to

    def target (self, resultant = None):
        # get target tile for a given (or the current) resultant force
        if resultant is None:
            resultant = self.resultant()
        pos = self.pos[:]
        for i in xrange(2):
            if resultant[i]:
                pos[i] += 1 if resultant[i] > 0 else -1
        if 0 <= pos[0] < self.level.w and 0 <= pos[1] < self.level.h:
            return self.level.grid[pos[0]][pos[1]][1]
        else:
            return conf.WALL

    def reaction (self, direction):
        print 'reaction', self, direction
        # can't move: return reaction forces
        react_on = []
        opposite = opposite_dir(direction)
        axis = direction % 2
        for d, f, source, handled in self.real_forces():
            # get blocks that pushed this one in the opposite direction
            if d == opposite and isinstance(source, Block):
                react_on.append(source)
            # redistribute diagonal forces
            if handled and d % 2 != axis:
                # get blocks to transfer them to
                pos = [0, 0]
                targets = []
                for x in (-1, 1):
                    pos[not axis] = x
                    t = self.target(pos[:])
                    if is_immoveable(t):
                        t = None
                    targets.append(t)
                for i, (b, j) in enumerate(handled):
                    if b.forces[j] is None:
                        continue
                    if b.pos[axis] != self.pos[axis]:
                        # transfer
                        t = targets[b.pos[not axis] - self.pos[not axis] > 0]
                        if t:
                            t.add_force(*b.forces[j][:3])
                        # remove
                        b.rm_force(j)
        # remove all forces on this axis
        for b, i in self.remove_forces(direction % 2):
            b.rm_force(i)
        # propagate reaction
        for b in react_on:
            b.reaction(direction)

    def handle_forces (self):
        print 'handle:', self
        resultant = self.resultant(True)
        # check diagonal if need to
        if all(resultant):
            diag = self.target(resultant)
        else:
            diag = False
        # check horizontal and vertical motion
        for i in xrange(2):
            # forces might change in the first iteration
            f = self.resultant(True)[i]
            if not f:
                continue
            d = force_dir(i, resultant[i])
            f = abs(f)
            r = resultant[:]
            r[not i] = 0
            targets = []
            target = self.target(r)
            if is_immoveable(target):
                # can't move on this axis
                self.reaction(opposite_dir(d))
                diag = False
            else:
                # by this point, targets are moveable blocks or empty
                num_to_push = bool(target) + bool(diag)
                if diag and not is_immoveable(diag):
                    if num_to_push == 2:
                        # split forces
                        diag_force = f / 2
                        f -= diag_force
                    else:
                        diag_force = f
                    if diag_force == 0:
                        # not enough force to do anything (1 / 2 = 0)
                        self.remove_forces(i)
                        diag = False
                        break
                    diag.add_force(d, diag_force, self)
                    targets.append((diag, len(diag.forces) - 1))
                if target:
                    target.add_force(d, f, self)
                    targets.append((target, len(target.forces) - 1))
                # mark forces on this axis as handled
                for j in xrange(len(self.forces)):
                    if self.forces[j] is not None:
                        if self.forces[j][0] % 2 == i:
                            self.forces[j][3] = targets
        # if trying to move on both axes and can't move to diagonal, don't move
        if is_immoveable(diag):
            # can't move: reaction along both axes
            for axis, f in enumerate(resultant):
                self.reaction(opposite_dir(force_dir(axis, f)))
            check_axes = False
        self.handled = True

class Level:
    def __init__ (self, ID, game):
        self.game = game
        # add gameplay key handlers
        args = (
            eh.MODE_ONDOWN_REPEAT,
            max(int(conf.MOVE_INITIAL_DELAY * conf.FPS), 1),
            max(int(conf.MOVE_REPEAT_DELAY * conf.FPS), 1)
        )
        self.game.event_handler.add_key_handlers([
            (conf.KEYS_LEFT, [(self.move, (0,))]) + args,
            (conf.KEYS_UP, [(self.move, (1,))]) + args,
            (conf.KEYS_RIGHT, [(self.move, (2,))]) + args,
            (conf.KEYS_DOWN, [(self.move, (3,))]) + args,
            (conf.KEYS_RESET, lambda t: self.load(self.ID), eh.MODE_ONDOWN)
        ])
        self.bg_colour = (255, 255, 255)
        self.load(ID)

    def load (self, ID):
        # load a new level
        self.ID = ID
        # get data from file
        def next_ints (f):
            line = f.readline().strip()
            if line and line[0] == '#':
                return next_ints(f)
            else:
                return [int(n) for n in line.split(' ') if n]
        with open(conf.LEVEL_DIR + str(self.ID)) as f:
            self.w, self.h = next_ints(f)
            # create default grid (contains surface types and blocks)
            self.grid = []
            for i in xrange(self.w):
                col = []
                for j in xrange(self.h):
                    col.append([conf.S_STANDARD, None])
                self.grid.append(col)
            # create Block instances and place in grid
            self.blocks = []
            self.players = []
            l = next_ints(f)
            while l:
                type_ID, i, j = l
                b = Block(type_ID, self, [i, j])
                self.blocks.append(b)
                self.grid[i][j][1] = b
                if type_ID == conf.B_PLAYER:
                    self.players.append(b)
                l = next_ints(f)
            # get non-default surface types
            l = next_ints(f)
            while l:
                ID, i, j = l
                self.grid[i][j][0] = ID
                l = next_ints(f)
        # grid handler
        self.tiler = Tiler(self.w, self.h, self.draw_tile, track_tiles = False)
        self.game.dirty = True

    def move (self, is_repeat, direction):
        # key callback to move player
        for player in self.players:
            player.add_force(direction, conf.FORCE_MOVE)

    def step (self):
        # resolve forces into motion
        # apply arrow forces
        for col in self.grid:
            for s, b in col:
                if b is not None and s in conf.S_ARROWS:
                    b.add_force(conf.S_ARROWS.index(s), conf.FORCE_ARROW)
        # handle contact forces
        unhandled = [b for b in self.blocks if not b.handled]
        while unhandled:
            for b in unhandled:
                b.handle_forces()
            unhandled = [b for b in self.blocks if not b.handled]
        for b in self.blocks:
            if b.forces:
                print b, b.forces

        # compile block destinations
        dest = {}
        for b in self.blocks:
            r = b.resultant()
            # get destination
            pos = b.pos[:]
            for i, f in enumerate(r):
                if f:
                    pos[i] += 1 if f > 0 else -1
            if pos != b.pos:
                # wants to move
                # lists aren't hashable
                pos = tuple(pos)
                try:
                    dest[pos].append(b)
                except KeyError:
                    dest[pos] = [b]
        #if dest:
            #print dest
        # resolve conflicts
        # TODO:
        # - have an entry for each of three blocks for diagonally-moving
        #   blocks, but only move it to the diagonal one (if no conflicts)
        # - if find a conflict, call reaction on those that don't move because
        #   of it and re-enter previous loop
        rm = []
        for pos in dest:
            bs = dest[pos]
            if len(bs) == 1:
                dest[pos] = bs[0]
                continue
            # check if highest force towards destination is unique
            max_f = 0
            for b in bs:
                force = abs(b.force[0]) + abs(b.force[1])
                if force == max_f:
                    unique = False
                elif force > max_f:
                    max_f = force
                    unique = b
            if unique:
                # move block with most force
                dest[pos] = unique
            else:
                # don't move any blocks
                rm.append(pos)
        for pos in rm:
            del dest[pos]
        # move blocks
        change = set()
        retain_forces = []
        for pos, b in dest.iteritems():
            # remove
            # lists aren't unhashable
            change.add(tuple(b.pos))
            self.grid[b.pos[0]][b.pos[1]][1] = None
            if b.type in (conf.B_SLIDE, conf.B_BOUNCE):
                retain_forces.append(b)
        for pos, b in dest.iteritems():
            # add
            change.add(pos)
            b.pos = list(pos)
            self.grid[pos[0]][pos[1]][1] = b
        self.tiler.change(*change)
        # reset forces
        for b in self.blocks:
            if b in retain_forces:
                b.reduce_forces()
            else:
                b.forces = []
        # TODO: check victory conditions

    def draw_tile (self, surface, rect, i, j):
        # draw a single tile; called by Tiler
        s, b = self.grid[i][j]
        if s < 0:
            colour = conf.surface_colours[s]
        else:
            colour = conf.block_colours[s]
        surface.fill(colour, rect)
        if b is not None:
            rect = pygame.Rect(rect)
            p = rect.center
            r = rect.w / 2
            pygame.draw.circle(surface, (0, 0, 0), p, r)
            pygame.draw.circle(surface, conf.block_colours[b.type], p, int(r * .8))

    def draw (self):
        # draw grid and tiles; returns whether grid may have changed size
        if self.game.dirty:
            self.tiler.reset()
        rects = self.tiler.draw_changed(self.game.screen)
        if rects is not None:
            if isinstance(rects[0], int):
                pygame.display.update()
            else:
                pygame.display.update(*rects[1:])

class Game:
    def __init__ (self, level = 1):
        self.event_handler = eh.EventHandler({
            pygame.VIDEORESIZE: self.resize_output, # EVENT_ENDMUSIC: self.play_music
        }, [
            (conf.KEYS_FULLSCREEN, self.toggle_fullscreen, eh.MODE_ONDOWN),
            (conf.KEYS_MINIMISE, self.minimise, eh.MODE_ONDOWN),
            (conf.KEYS_PAUSE, self.toggle_paused, eh.MODE_ONDOWN),
            (conf.KEYS_UNPAUSE, self.unpause, eh.MODE_ONDOWN)
        ])
        self.res = [conf.RES_W, conf.RES_F]
        self.fullscreen = conf.FULLSCREEN
        self.set_mode()

        self.level = Level(level, self)

        self.dirty = True
        self.running = True
        self.paused = False

    def update (self):
        self.level.step()

    def draw (self):
        # update interface
        self.level.draw()
        self.dirty = False

    def run (self):
        # main loop
        self.keys = set()
        t0 = time()
        while self.running:
            self.event_handler.update()
            self.update()
            self.draw()
            t1 = time()
            wait(int(1000 * (conf.FRAME - t1 + t0)))
            t0 += conf.FRAME

    def pause (self):
        if not self.paused:
            self.paused = True

    def unpause (self, *a):
        if self.paused:
            self.paused = False

    def toggle_paused (self, *a):
        if self.paused:
            self.unpause()
        else:
            self.pause()

    def minimise (self, *a):
        self.pause()
        pygame.display.iconify()

    def set_mode (self):
        flags = 0
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        if conf.RESIZABLE:
            flags |= pygame.RESIZABLE
        self.screen = pygame.display.set_mode(self.res[self.fullscreen], flags)

    def toggle_fullscreen (self, *a):
        self.fullscreen = not self.fullscreen
        self.dirty = True
        self.set_mode()

    def resize_output (self, event):
        self.res[0] = event.w, event.h
        self.set_mode()
        self.dirty = True

if __name__ == '__main__':
    if conf.WINDOW_ICON is not None:
        pygame.display.set_icon(pygame.image.load(conf.WINDOW_ICON))
    if conf.WINDOW_TITLE is not None:
        pygame.display.set_caption(conf.WINDOW_TITLE)
    Game('A').run()