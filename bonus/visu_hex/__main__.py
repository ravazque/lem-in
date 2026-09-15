"""visu-hex: animates a lem-in run in a tkinter window.

Usage: ./lem-in < map | ./visu-hex [options]"""

import argparse
import sys

from .colony import VisuError, load
from .replay import Replay

DEFAULT_SPEED = 2.0


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='visu-hex', description=__doc__.split('\n\n')[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='keys: space play/pause, left/right step, +/- speed, v view, '
               'drag pan, wheel zoom or scroll, z/x zoom, 0 reset, '
               'PgUp/PgDn lanes, r restart, e end, q quit.\n'
               'A "##visu speed=4 paused view=lanes" line in the map sets '
               'the defaults.')
    parser.add_argument('--view', choices=('map', 'lanes'),
                        help='start on the coordinate map or on the lanes')
    parser.add_argument('--speed', type=float,
                        help='turns per second (default %g)' % DEFAULT_SPEED)
    parser.add_argument('--paused', action='store_true',
                        help='start paused')
    parser.add_argument('--dump', metavar='DIR',
                        help='save frames as PostScript files into DIR and '
                             'exit, without opening the window')
    parser.add_argument('--frames', type=int, default=6,
                        help='frames saved by --dump (default 6)')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if sys.stdin.isatty():
        print('visu-hex: nothing piped in, use: ./lem-in < map | ./visu-hex',
              file=sys.stderr)
        return 1
    text = sys.stdin.buffer.read().decode('utf-8', 'replace')
    try:
        colony, turns = load(text)
    except VisuError as error:
        print('visu-hex: %s' % error, file=sys.stderr)
        return 1
    replay = Replay(colony, turns)
    speed = args.speed or colony.options.get('speed', DEFAULT_SPEED)
    paused = args.paused or colony.options.get('paused', False)
    if args.view:
        colony.options['view'] = args.view
    from .ui_tk import run
    return run(colony, replay, speed, paused, args.dump, args.frames)


if __name__ == '__main__':
    sys.exit(main())
