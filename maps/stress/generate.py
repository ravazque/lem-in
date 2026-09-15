#!/usr/bin/env python3
"""`make maps`: writes the large stress colonies (a 100k-room corridor, 5 000
routes, a 100x100 grid, 60 000 tunnels, two dense layers) into generated/."""

import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'generated')


def chain(rooms, ants):
    yield '%d\n##start\nr0 0 0\n' % ants
    for i in range(1, rooms - 1):
        yield 'r%d %d 0\n' % (i, i)
    yield '##end\nr%d %d 0\n' % (rooms - 1, rooms - 1)
    for i in range(rooms - 1):
        yield 'r%d-r%d\n' % (i, i + 1)


def star(routes, ants):
    yield '%d\n##start\ns 0 0\n##end\ne 10 10\n' % ants
    for i in range(routes):
        yield 'm%d %d 5\n' % (i, i)
    for i in range(routes):
        yield 's-m%d\nm%d-e\n' % (i, i)


def grid(side, ants):
    last = side - 1
    yield '%d\n##start\ng0_0 0 0\n##end\ng%d_%d %d %d\n' % (ants, last, last,
                                                            last, last)
    for y in range(side):
        for x in range(side):
            if (x, y) not in ((0, 0), (last, last)):
                yield 'g%d_%d %d %d\n' % (x, y, x, y)
    for y in range(side):
        for x in range(side):
            if x < last:
                yield 'g%d_%d-g%d_%d\n' % (x, y, x + 1, y)
            if y < last:
                yield 'g%d_%d-g%d_%d\n' % (x, y, x, y + 1)


def dense(rooms, tunnels, ants, seed=1):
    rnd = random.Random(seed)
    yield '%d\n##start\nn0 0 0\n##end\nn1 1 1\n' % ants
    for i in range(2, rooms):
        yield 'n%d %d %d\n' % (i, i, i % 97)
    seen = set()
    while len(seen) < tunnels:
        a, b = rnd.randrange(rooms), rnd.randrange(rooms)
        if a != b and (a, b) not in seen and (b, a) not in seen:
            seen.add((a, b))
            yield 'n%d-n%d\n' % (a, b)


def layers(width, ants):
    yield '%d\n##start\ns 0 0\n##end\ne 3 0\n' % ants
    for i in range(width):
        yield 'a%d 1 %d\n' % (i, i)
    for i in range(width):
        yield 'b%d 2 %d\n' % (i, i)
    for i in range(width):
        yield 's-a%d\n' % i
    for i in range(width):
        for j in range(width):
            yield 'a%d-b%d\n' % (i, j)
    for i in range(width):
        yield 'b%d-e\n' % i


MAPS = {
    'chain_100k': lambda: chain(100000, 10),
    'star_5000': lambda: star(5000, 5000),
    'grid_100x100': lambda: grid(100, 500),
    'dense_4000': lambda: dense(4000, 60000, 1000),
    'layers_50': lambda: layers(50, 4000),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, lines in MAPS.items():
        path = os.path.join(OUT, name + '.map')
        with open(path, 'w') as out:
            out.writelines(lines())
        print('%-14s %8d KB' % (name, os.path.getsize(path) >> 10))


if __name__ == '__main__':
    main()
