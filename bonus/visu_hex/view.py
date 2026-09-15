"""Pixel geometry of a frame — where every room, lane and ant is drawn — kept
independent of the toolkit, which only draws the items it is handed."""

from .layout import LaneLayout, MapLayout, auto_coords, collinear

PALETTE = ((66, 165, 245), (255, 152, 0), (236, 64, 122), (139, 195, 74),
           (255, 235, 59), (0, 188, 212), (171, 71, 188), (205, 220, 57),
           (255, 87, 34), (149, 117, 205))
COLORS = {
    'bg': (24, 26, 32), 'panel': (36, 39, 48), 'text': (225, 228, 235),
    'dim': (120, 126, 140), 'tunnel': (62, 66, 78), 'room': (150, 156, 170),
    'start': (76, 175, 80), 'end': (229, 57, 53), 'ok': (102, 187, 106),
    'bad': (239, 83, 80), 'stray': (255, 213, 79),
}
BAR, FOOT, LANE_HEAD = 30, 52, 190   # title bar, status bar, lane header px
MIN_WIDTH, MIN_HEIGHT = 480, 240
CONTROLS = ('space play/pause   ←/→ step   +/- speed   v view   '
            'drag pan   wheel zoom/scroll   0 reset   r restart   e end   '
            'q quit')


def ease(t):
    return t * t * (3 - 2 * t)


class Ant:
    __slots__ = ('number', 'x', 'y', 'color', 'moving')

    def __init__(self, number, x, y, color, moving):
        self.number = number
        self.x = x
        self.y = y
        self.color = color
        self.moving = moving


class View:
    def __init__(self, colony, replay):
        self.colony = colony
        self.replay = replay
        self.lanes = LaneLayout(replay)
        self.flat = collinear(colony.rooms)
        coords = pitch = None
        if self.flat:
            coords, pitch = auto_coords(colony, replay.routes)
        self.map = MapLayout(colony, cell_aspect=1.0, coords=coords,
                             pitch=pitch)
        default = 'lanes' if self.flat and replay.routes else 'map'
        self.mode = colony.options.get('view', default)
        self.width = self.height = 0
        self.scroll = 0.0
        self.follow = {}
        self._moves_turn = -1
        self._moves = {}
        self.generation = 0

    def resize(self, width, height):
        if (width, height) != (self.width, self.height):
            self.width, self.height = width, height
            self.map.resize(width, height - BAR - FOOT, margin=50)
            self.generation += 1

    def toggle(self):
        self.mode = 'map' if self.mode == 'lanes' else 'lanes'

    def zoom(self, factor, at=None):
        if self.mode != 'map':
            return
        before = self.map.zoom
        self.map.zoom_by(factor)
        actual = self.map.zoom / before
        if at is not None and actual != 1.0:
            cx, cy = self.width / 2.0, self.body_height() / 2.0
            dx, dy = at[0] - cx, at[1] - BAR - cy
            self.map.pan_by(dx - dx * actual, dy - dy * actual)
        self.generation += 1

    def pan(self, dx, dy):
        if self.mode == 'map':
            self.map.pan_by(dx, dy)
            self.generation += 1
        else:
            self.scroll_by(-dy)

    def reset(self):
        self.map.reset()
        self.scroll = 0.0
        self.generation += 1

    def scroll_by(self, pixels):
        limit = max(0.0, self.lane_geometry()['total'] - self.body_height())
        self.scroll = max(0.0, min(limit, self.scroll + pixels))

    def body_height(self):
        return max(1, self.height - BAR - FOOT)

    def color_of(self, ant):
        route = self.replay.route_of[ant]
        if route == 0:
            return COLORS['stray']
        return PALETTE[(route - 1) % len(PALETTE)]

    def route_color(self, index):
        return PALETTE[index % len(PALETTE)]

    def moving(self, turn):
        if turn != self._moves_turn:
            self._moves_turn = turn
            self._moves = {ant: (a, b)
                           for ant, a, b in self.replay.moves(turn + 1)}
        return self._moves

    def map_xy(self, room):
        x, y = self.map.positions[room]
        return x, y + BAR

    def room_radius(self):
        return max(1.0, min(9.0, self.map.pitch() * 0.4))

    def mark_radius(self):
        return int(max(8, self.room_radius() + 4))

    def show_map_labels(self):
        return self.map.pitch() >= 40

    def visible_room(self, x, y, margin=20):
        return -margin <= x <= self.width + margin \
            and BAR - margin <= y <= self.height - FOOT + margin

    def lane_geometry(self):
        longest = max(1, self.lanes.longest)
        usable = max(1, self.width - LANE_HEAD - 60)
        spacing = max(14.0, min(64.0, usable / float(longest + 0.5)))
        labels = spacing >= 30
        row = 46 if labels else 28
        return {'spacing': spacing, 'row': row, 'labels': labels,
                'total': row * len(self.lanes.routes) + 12}

    def lane_offset(self, index, geometry, still, going):
        """Shift of a lane wider than the window, keeping its ants in view."""
        route = self.lanes.routes[index]
        width = (route.length + 0.5) * geometry['spacing']
        room = self.width - LANE_HEAD - 60
        if width <= room:
            return 0.0
        cols = []
        for ant, at in still:
            col = self.lanes.locate(index, at)
            if col is not None:
                cols.append(col)
        for ant, src, dst in going:
            col = self.lanes.locate(index, dst)
            if col is not None:
                cols.append(col)
        if not cols:
            return self.follow.get(index, 0.0)
        center = sum(cols) / float(len(cols)) * geometry['spacing']
        offset = max(0.0, min(width - room, center - room / 2.0))
        self.follow[index] = offset
        return offset

    def lane_xy(self, index, col, geometry, offset=0.0):
        x = LANE_HEAD + 20 + col * geometry['spacing'] - offset
        y = BAR + 26 + index * geometry['row'] - self.scroll
        return x, y

    def visible_lanes(self, geometry):
        first = int(self.scroll // geometry['row'])
        count = int(self.body_height() // geometry['row']) + 2
        return range(max(0, first), min(len(self.lanes.routes),
                                        first + count))

    def by_route(self, turn):
        route_of = self.replay.route_of
        moving = self.moving(turn)
        still, going = {}, {}
        for room, ant in self.replay.transit(turn).items():
            if ant not in moving:
                still.setdefault(route_of[ant] - 1, []).append((ant, room))
        for ant, (src, dst) in moving.items():
            going.setdefault(route_of[ant] - 1, []).append((ant, src, dst))
        return still, going

    def ants(self, turn, phase):
        """Every ant to draw at (turn, phase); none inside ##start or ##end."""
        if self.mode == 'map':
            return self._map_ants(turn, phase)
        return self._lane_ants(turn, phase)

    def _map_ants(self, turn, phase):
        colony = self.colony
        moving = self.moving(turn)
        out = []
        for room, ant in self.replay.transit(turn).items():
            if ant not in moving:
                x, y = self.map_xy(room)
                out.append(Ant(ant, x, y, self.color_of(ant), False))
        t = ease(phase)
        for ant, (src, dst) in moving.items():
            if t <= 0.0 and src == colony.start:
                continue
            if t >= 1.0 and dst == colony.end:
                continue
            ax, ay = self.map_xy(src)
            bx, by = self.map_xy(dst)
            out.append(Ant(ant, ax + (bx - ax) * t, ay + (by - ay) * t,
                           self.color_of(ant), True))
        return out

    def _lane_ants(self, turn, phase):
        geometry = self.lane_geometry()
        still, going = self.by_route(turn)
        t = ease(phase)
        out = []
        for index in self.visible_lanes(geometry):
            offset = self.lane_offset(index, geometry, still.get(index, ()),
                                      going.get(index, ()))
            color = self.route_color(index)
            for ant, room in still.get(index, ()):
                col = self.lanes.locate(index, room)
                if col is not None:
                    x, y = self.lane_xy(index, col, geometry, offset)
                    out.append(Ant(ant, x, y, color, False))
            for ant, src, dst in going.get(index, ()):
                a = self.lanes.locate(index, src)
                b = self.lanes.locate(index, dst)
                if a is None or b is None:
                    continue
                if (t <= 0.0 and a == 0) \
                        or (t >= 1.0 and dst == self.colony.end):
                    continue
                x, y = self.lane_xy(index, a + (b - a) * t, geometry, offset)
                out.append(Ant(ant, x, y, color, True))
        return out

    def title(self, turn, playing, speed):
        return 'turn %d / %d   %s   x%g' % (turn, self.replay.count,
                                            'playing' if playing else 'paused',
                                            round(speed, 2))

    def stats(self, turn):
        colony, replay = self.colony, self.replay
        at_start, on_way, at_end = replay.census(turn)
        left = ('ants %d   rooms %d   tunnels %d   routes %d   turns %d'
                % (colony.ants, len(colony.rooms), len(colony.links),
                   len(replay.routes), replay.count))
        progress = 'start %d   moving %d   arrived %d' % (at_start, on_way,
                                                          at_end)
        if replay.valid:
            verdict = 'valid'
        else:
            verdict = 'INVALID: ' + replay.errors[0]
        return left, progress, verdict
