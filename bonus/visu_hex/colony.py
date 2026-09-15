"""Parsing of a lem-in run as printed: the echoed colony (ants, rooms, tunnels,
comments, ##visu options), a blank line, then one line of moves per turn."""

from array import array

MAX_INPUT = 64 * 1024 * 1024


class VisuError(Exception):
    pass


class Room:
    __slots__ = ('name', 'x', 'y', 'id')

    def __init__(self, name, x, y, rid):
        self.name = name
        self.x = x
        self.y = y
        self.id = rid


class Colony:
    def __init__(self):
        self.ants = 0
        self.rooms = []
        self.index = {}
        self.links = []
        self.adj = []
        self.start = -1
        self.end = -1
        self.options = {}

    def add_room(self, name, x, y):
        room = Room(name, x, y, len(self.rooms))
        self.rooms.append(room)
        self.index[name] = room.id
        self.adj.append(set())
        return room

    def add_link(self, a, b):
        self.links.append((a, b))
        self.adj[a].add(b)
        self.adj[b].add(a)

    def name(self, rid):
        return self.rooms[rid].name


def _int(text):
    body = text[1:] if text[:1] in ('+', '-') else text
    if not body or not body.isascii() or not body.isdigit():
        return None
    return int(text)


def _parse_options(line, options):
    """``##visu speed=4 paused view=lanes`` -> {'speed': 4.0, ...}."""
    for word in line.split()[1:]:
        key, _, value = word.partition('=')
        key = key.lower()
        if key == 'speed':
            try:
                options['speed'] = max(0.1, min(60.0, float(value)))
            except ValueError:
                pass
        elif key == 'paused':
            options['paused'] = value.lower() not in ('0', 'no', 'false')
        elif key == 'view' and value.lower() in ('map', 'lanes'):
            options['view'] = value.lower()


def parse_colony(lines):
    """Returns the Colony and the index of the first line after it."""
    colony = Colony()
    i = 0
    while i < len(lines) and lines[i].startswith('#'):
        if lines[i].lower().startswith('##visu'):
            _parse_options(lines[i], colony.options)
        i += 1
    if i >= len(lines) or _int(lines[i]) is None or _int(lines[i]) <= 0:
        raise VisuError('the input does not start with a number of ants')
    colony.ants = _int(lines[i])
    i += 1
    pending = None
    while i < len(lines) and lines[i] != '':
        line = lines[i]
        i += 1
        if line == '##start' or line == '##end':
            pending = line[2:]
        elif line.startswith('#'):
            if line.lower().startswith('##visu'):
                _parse_options(line, colony.options)
        elif '-' in line and ' ' not in line:
            a, _, b = line.partition('-')
            if a not in colony.index or b not in colony.index:
                raise VisuError('tunnel "%s" names an unknown room' % line)
            colony.add_link(colony.index[a], colony.index[b])
        else:
            fields = line.split()
            if len(fields) != 3 or _int(fields[1]) is None \
                    or _int(fields[2]) is None:
                raise VisuError('malformed room line "%s"' % line[:40])
            if fields[0] in colony.index:
                raise VisuError('room "%s" declared twice' % fields[0])
            room = colony.add_room(fields[0], _int(fields[1]),
                                   _int(fields[2]))
            if pending == 'start':
                colony.start = room.id
            elif pending == 'end':
                colony.end = room.id
            pending = None
    if colony.start < 0 or colony.end < 0:
        raise VisuError('the colony has no ##start or no ##end')
    return colony, i


def parse_moves(lines, colony):
    """Turn lines -> one flat array [ant, room, ant, room, ...] per turn."""
    turns = []
    index = colony.index
    for line in lines:
        if line == '':
            if turns:
                break
            continue
        moves = array('i')
        for token in line.split(' '):
            ant, dash, room = token.partition('-')
            number = ant[1:]
            if not ant.startswith('L') or not dash or not number.isascii() \
                    or not number.isdigit() or room not in index:
                raise VisuError('bad move token "%s" on turn %d'
                                % (token[:30], len(turns) + 1))
            ant = int(number)
            if not 1 <= ant <= colony.ants:
                raise VisuError('turn %d moves L%d, the colony has %d ants'
                                % (len(turns) + 1, ant, colony.ants))
            moves.append(ant)
            moves.append(index[room])
        turns.append(moves)
    return turns


def load(text):
    if len(text) > MAX_INPUT:
        raise VisuError('input larger than %d MB, too big to animate'
                        % (MAX_INPUT >> 20))
    if text.startswith('ERROR'):
        raise VisuError('lem-in answered ERROR, there is nothing to show')
    if not text.strip():
        raise VisuError('nothing on stdin (did lem-in print ERROR?), '
                        'use: ./lem-in < map | ./visu-hex')
    lines = text.split('\n')
    colony, pos = parse_colony(lines)
    turns = parse_moves(lines[pos:], colony)
    return colony, turns
