"""The tkinter front end: every ant owns one canvas oval moved in place; the
static map is rebuilt only on pan or zoom, the lanes only when they shift."""

import sys
import time

from .player import Player
from .view import BAR, COLORS, CONTROLS, FOOT, LANE_HEAD, MIN_HEIGHT, \
    MIN_WIDTH, View

WINDOW = (1200, 760)
ZOOM_STEP = 1.2
FRAME_MS = 16
POOL_LIMIT = 4096
FONT_FAMILIES = ('DejaVu Sans Mono', 'Menlo', 'Consolas', 'Liberation Mono',
                 'Courier New')
KEY_PAN = {'w': (0, 40), 's': (0, -40), 'a': (40, 0), 'd': (-40, 0)}


def _import_tk():
    try:
        import tkinter
        import tkinter.font  # noqa: F401  (registers tkinter.font)
    except ImportError:
        print('visu-hex: the tkinter module is missing; install Tk for your '
              'python3 (python3-tk on Debian/Ubuntu, tk on Arch, part of '
              'the python.org installer on macOS)', file=sys.stderr)
        return None
    return tkinter


def rgb(color):
    return '#%02x%02x%02x' % color


class Window:
    def __init__(self, tk, view, player):
        self.tk = tk
        self.view = view
        self.player = player
        self.root = tk.Tk()
        self.root.title('lem-in visu-hex')
        self.root.geometry('%dx%d' % WINDOW)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.canvas = tk.Canvas(self.root, bg=rgb(COLORS['bg']),
                                highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.font = self._font(tk, 11)
        self.small = self._font(tk, 9)
        self.width, self.height = WINDOW
        self.static_generation = -1
        self.lane_key = None
        self.pool = {}
        self.shown = set()
        self.dragging = None
        self.running = True
        self.last = time.monotonic()
        self.canvas.bind('<Configure>', self.on_resize)
        self.root.bind('<KeyPress>', self.on_key)
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.canvas.bind('<MouseWheel>', self.on_wheel)
        self.canvas.bind('<Button-4>', lambda e: self.wheel(1, e))
        self.canvas.bind('<Button-5>', lambda e: self.wheel(-1, e))
        self.root.protocol('WM_DELETE_WINDOW', self.quit)

    def _font(self, tk, size):
        families = set(tk.font.families(self.root))
        for family in FONT_FAMILIES:
            if family in families:
                return tk.font.Font(family=family, size=size)
        font = tk.font.nametofont('TkFixedFont').copy()
        font.configure(size=size)
        return font

    def draw(self):
        canvas, view = self.canvas, self.view
        view.resize(self.width, self.height)
        canvas.delete('note')
        if self.width < MIN_WIDTH or self.height < MIN_HEIGHT:
            canvas.delete('static', 'lanes', 'counts', 'bars')
            self.static_generation = -1
            self.lane_key = None
            self.hide_ants()
            canvas.create_text(10, 10, anchor='nw', fill=rgb(COLORS['bad']),
                               font=self.font, tags='note',
                               text='window too small (%dx%d needed)'
                               % (MIN_WIDTH, MIN_HEIGHT))
            return
        if view.mode == 'map':
            canvas.delete('lanes')
            self.lane_key = None
            self.draw_map()
        else:
            canvas.delete('static', 'counts')
            self.static_generation = -1
            self.draw_lanes()
        self.draw_ants()
        self.draw_bars()

    def draw_map(self):
        canvas, view = self.canvas, self.view
        if self.static_generation != view.generation:
            self.render_static()
            self.static_generation = view.generation
        canvas.delete('counts')
        colony = view.colony
        gap = view.mark_radius() + 4
        at_start, _, at_end = view.replay.census(self.player.turn)
        for room, count, color in ((colony.start, at_start, COLORS['start']),
                                   (colony.end, at_end, COLORS['end'])):
            x, y = view.map_xy(room)
            item = canvas.create_text(x + gap + 4, y, text=str(count),
                                      anchor='w', fill=rgb(color),
                                      font=self.font, tags='counts')
            box = canvas.create_rectangle(canvas.bbox(item),
                                          fill=rgb(COLORS['bg']), outline='',
                                          tags='counts')
            canvas.tag_lower(box, item)

    def render_static(self):
        canvas, view = self.canvas, self.view
        colony = view.colony
        canvas.delete('static')
        radius = view.room_radius()
        tunnel = rgb(COLORS['tunnel'])
        for a, b in colony.links:
            ax, ay = view.map_xy(a)
            bx, by = view.map_xy(b)
            if view.visible_room(ax, ay, 2000) \
                    or view.visible_room(bx, by, 2000):
                canvas.create_line(ax, ay, bx, by, fill=tunnel, tags='static')
        used = {}
        for route in view.replay.routes:
            for room in route.rooms:
                used.setdefault(room, view.route_color(route.index))
        labels = view.show_map_labels()
        background, dim = rgb(COLORS['bg']), rgb(COLORS['dim'])
        for room in colony.rooms:
            x, y = view.map_xy(room.id)
            if not view.visible_room(x, y):
                continue
            color = rgb(used.get(room.id, COLORS['room']))
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                               outline=color, fill=background, tags='static')
            if labels:
                canvas.create_text(x, y + radius + 3, text=room.name[:16],
                                   anchor='n', fill=dim, font=self.small,
                                   tags='static')
        for room, mark, color in ((colony.start, 'S', COLORS['start']),
                                  (colony.end, 'E', COLORS['end'])):
            x, y = view.map_xy(room)
            big = view.mark_radius()
            canvas.create_oval(x - big, y - big, x + big, y + big,
                               fill=rgb(color), outline='', tags='static')
            canvas.create_text(x, y, text=mark, fill=background,
                               font=self.small, tags='static')
        canvas.tag_lower('static')

    def draw_lanes(self):
        canvas, view = self.canvas, self.view
        colony = view.colony
        geometry = view.lane_geometry()
        still, going = view.by_route(self.player.turn)
        lanes = list(view.visible_lanes(geometry))
        offsets = [view.lane_offset(index, geometry, still.get(index, ()),
                                    going.get(index, ())) for index in lanes]
        key = (self.width, self.height, round(view.scroll),
               tuple(round(o) for o in offsets))
        if key == self.lane_key:
            return
        self.lane_key = key
        canvas.delete('lanes')
        radius = max(3, min(8, int(geometry['spacing'] / 4)))
        tunnel, background = rgb(COLORS['tunnel']), rgb(COLORS['bg'])
        room_color, dim = rgb(COLORS['room']), rgb(COLORS['dim'])
        top, bottom = BAR, self.height - FOOT
        for index, offset in zip(lanes, offsets):
            route = view.lanes.routes[index]
            color = rgb(view.route_color(index))
            x0, y = view.lane_xy(index, 0, geometry, offset)
            if y < top - radius or y > bottom + radius:
                continue
            x1, _ = view.lane_xy(index, route.length, geometry, offset)
            canvas.create_line(x0, y, x1, y, fill=tunnel, width=2,
                               tags='lanes')
            for col, room in enumerate(route.rooms):
                x, _ = view.lane_xy(index, col, geometry, offset)
                if x < LANE_HEAD - 10 or x > self.width + 10:
                    continue
                if room == colony.start or room == colony.end:
                    fill = COLORS['start' if room == colony.start else 'end']
                    big = radius + 3
                    canvas.create_oval(x - big, y - big, x + big, y + big,
                                       fill=rgb(fill), outline='',
                                       tags='lanes')
                else:
                    canvas.create_oval(x - radius, y - radius, x + radius,
                                       y + radius, fill=background,
                                       outline=room_color, tags='lanes')
                if geometry['labels']:
                    name = colony.name(room)[:max(2, int(geometry['spacing']
                                                         / 7))]
                    canvas.create_text(x, y + radius + 4, text=name,
                                       anchor='n', fill=dim, font=self.small,
                                       tags='lanes')
            canvas.create_rectangle(0, y - 14, LANE_HEAD, y + 14,
                                    fill=background, outline='', tags='lanes')
            head = '#%d  len %d  ants %d' % (route.index + 1, route.length,
                                             route.ants)
            canvas.create_text(12, y, text=head, anchor='w', fill=color,
                               font=self.font, tags='lanes')
        canvas.tag_lower('lanes')

    def draw_ants(self):
        canvas, view = self.canvas, self.view
        if view.mode == 'map':
            radius = max(3, int(view.room_radius() * 0.8))
            labels = view.map.pitch() >= 40
        else:
            spacing = view.lane_geometry()['spacing']
            radius = max(3, min(7, int(spacing / 4) - 1))
            labels = spacing >= 40
        shown = set()
        for ant in view.ants(self.player.turn, self.player.phase):
            if not view.visible_room(ant.x, ant.y):
                continue
            items = self.pool.get(ant.number)
            if items is None:
                color = rgb(ant.color)
                items = (canvas.create_oval(0, 0, 0, 0, fill=color,
                                            outline='', tags='ants'),
                         canvas.create_text(0, 0, text='L%d' % ant.number,
                                            fill=color, font=self.small,
                                            anchor='s', state='hidden',
                                            tags='ants'))
                self.pool[ant.number] = items
            oval, label = items
            canvas.coords(oval, ant.x - radius, ant.y - radius,
                          ant.x + radius, ant.y + radius)
            if labels:
                canvas.coords(label, ant.x, ant.y - radius - 2)
            if ant.number not in self.shown:
                canvas.itemconfigure(oval, state='normal')
            canvas.itemconfigure(label, state='normal' if labels
                                 else 'hidden')
            shown.add(ant.number)
        for number in self.shown - shown:
            oval, label = self.pool[number]
            canvas.itemconfigure(oval, state='hidden')
            canvas.itemconfigure(label, state='hidden')
        self.shown = shown
        if len(self.pool) > POOL_LIMIT:
            for number in [n for n in self.pool if n not in shown]:
                canvas.delete(*self.pool.pop(number))
        canvas.tag_raise('ants')

    def hide_ants(self):
        for number in self.shown:
            for item in self.pool[number]:
                self.canvas.itemconfigure(item, state='hidden')
        self.shown = set()

    def draw_bars(self):
        canvas, view, player = self.canvas, self.view, self.player
        width, height = self.width, self.height
        canvas.delete('bars')
        panel, text, dim = rgb(COLORS['panel']), rgb(COLORS['text']), \
            rgb(COLORS['dim'])
        canvas.create_rectangle(0, 0, width, BAR, fill=panel, outline='',
                                tags='bars')
        canvas.create_rectangle(0, height - FOOT, width, height, fill=panel,
                                outline='', tags='bars')
        canvas.create_text(12, BAR / 2, anchor='w', fill=text, font=self.font,
                           text='lem-in visu-hex   [%s]' % view.mode,
                           tags='bars')
        canvas.create_text(width - 12, BAR / 2, anchor='e', fill=text,
                           font=self.font, tags='bars',
                           text=view.title(player.turn, player.playing,
                                           player.speed))
        left, progress, verdict = view.stats(player.turn)
        y = height - FOOT + 16
        item = canvas.create_text(12, y, text=left, anchor='w', fill=text,
                                  font=self.font, tags='bars')
        used = canvas.bbox(item)[2]
        canvas.create_text(used + 40, y, text=progress, anchor='w', fill=dim,
                           font=self.font, tags='bars')
        color = COLORS['ok'] if view.replay.valid else COLORS['bad']
        canvas.create_text(width - 12, y, anchor='e', fill=rgb(color),
                           font=self.font, tags='bars',
                           text=verdict[:max(8, (width - used - 60) // 8)])
        note = ''
        if view.mode == 'lanes' and len(view.replay.routes) > 1:
            geometry = view.lane_geometry()
            first = view.visible_lanes(geometry)
            last = min(first.stop,
                       first.start + view.body_height() // geometry['row'])
            note = 'lanes %d-%d / %d' % (first.start + 1, last,
                                         len(view.replay.routes))
        elif view.mode == 'map' and view.flat:
            note = 'coordinates carry no shape: laid out by distance from S'
        item = canvas.create_text(12, y + 22, text=CONTROLS, anchor='w',
                                  fill=dim, font=self.small, tags='bars')
        if self.small.measure(note) + canvas.bbox(item)[2] + 40 <= width:
            canvas.create_text(width - 12, y + 22, text=note, anchor='e',
                               fill=dim, font=self.small, tags='bars')
        canvas.tag_raise('bars')

    def on_resize(self, event):
        self.width, self.height = event.width, event.height

    def on_key(self, event):
        view, player = self.view, self.player
        key, char = event.keysym, event.char
        if key in ('q', 'Q', 'Escape'):
            self.quit()
        elif key == 'space':
            player.toggle()
        elif key == 'Right':
            player.seek(player.turn + 1)
        elif key == 'Left':
            player.seek(player.turn - 1)
        elif char in ('+', '=') or key in ('plus', 'equal', 'KP_Add'):
            player.faster(1.5)
        elif char == '-' or key in ('minus', 'KP_Subtract'):
            player.faster(1 / 1.5)
        elif key in ('r', 'Home'):
            player.seek(0)
        elif key in ('e', 'End'):
            player.seek(player.replay.count)
            player.playing = False
        elif key == 'v':
            view.toggle()
        elif char == '0' or key == 'KP_0':
            view.reset()
        elif key == 'z':
            view.zoom(ZOOM_STEP)
        elif key == 'x':
            view.zoom(1 / ZOOM_STEP)
        elif key == 'Prior':
            view.scroll_by(-view.body_height() * 0.8)
        elif key == 'Next':
            view.scroll_by(view.body_height() * 0.8)
        elif key in KEY_PAN:
            view.pan(*KEY_PAN[key])

    def on_press(self, event):
        self.dragging = (event.x, event.y)

    def on_drag(self, event):
        if self.dragging:
            self.view.pan(event.x - self.dragging[0],
                          event.y - self.dragging[1])
            self.dragging = (event.x, event.y)

    def on_release(self, event):
        self.dragging = None

    def on_wheel(self, event):
        self.wheel(1 if event.delta > 0 else -1, event)

    def wheel(self, direction, event):
        if self.view.mode == 'map':
            self.view.zoom(ZOOM_STEP ** direction, (event.x, event.y))
        else:
            self.view.scroll_by(-direction * 40)

    def tick(self):
        if not self.running:
            return
        now = time.monotonic()
        self.player.advance(now - self.last)
        self.last = now
        self.draw()
        self.root.after(FRAME_MS, self.tick)

    def loop(self):
        self.root.after(FRAME_MS, self.tick)
        self.root.mainloop()

    def quit(self):
        if self.running:
            self.running = False
            self.root.destroy()

    def dump(self, directory, frames):
        """Saves `frames` evenly spaced turns as PostScript, window hidden."""
        import os
        os.makedirs(directory, exist_ok=True)
        self.root.withdraw()
        self.width, self.height = WINDOW
        self.canvas.configure(width=self.width, height=self.height)
        self.root.update_idletasks()
        count = self.player.replay.count
        for i in range(frames):
            turn = count * i // max(1, frames - 1) if frames > 1 else 0
            self.player.seek(turn)
            self.player.phase = 0.5 if 0 < turn < count else 0.0
            self.draw()
            self.canvas.tag_lower(self.canvas.create_rectangle(
                0, 0, self.width, self.height, fill=rgb(COLORS['bg']),
                outline='', tags='paper'))
            self.root.update_idletasks()
            self.canvas.postscript(
                file=os.path.join(directory, 'frame_%02d_%s.ps'
                                  % (i, self.view.mode)),
                colormode='color', width=self.width, height=self.height,
                pagewidth=self.width - 1)
            self.canvas.delete('paper')
        self.quit()


def run(colony, replay, speed, paused, dump=None, frames=6):
    tk = _import_tk()
    if tk is None:
        return 1
    view = View(colony, replay)
    player = Player(replay, speed, paused)
    try:
        window = Window(tk, view, player)
    except tk.TclError as error:
        print('visu-hex: cannot open a window (%s)' % error, file=sys.stderr)
        return 1
    if dump:
        window.dump(dump, frames)
    else:
        window.loop()
    return 0
