from PIL import Image
from io import BytesIO

import logging
log = logging.getLogger(__name__)


def wordpad(blob, max_size=None, rotate=False):
    log.debug('%-10s %10d bytes', 'in', len(blob))

    img = Image.open(BytesIO(blob))

    if max_size:
        img.thumbnail(max_size)

    if rotate:
        img = img.rotate(90)

    mode = img.mode
    size = img.size
    raw = img.tobytes('raw')
    log.debug('%-10s %10d bytes (%sx%s, %s)', 'raw', len(raw), size[0], size[1], mode)

    glitched = glitch_blob(raw)[:len(raw)]
    log.debug('%-10s %10d bytes', 'glitched', len(glitched))

    result = Image.frombytes(mode, size, glitched, 'raw')

    if rotate:
        result = result.rotate(-90)

    jpg = result.tobytes('jpeg', mode)
    log.debug('%-10s %10d bytes', 'jpg', len(jpg))

    return jpg


def glitch_blob(blob):
    r = BytesIO(blob)
    w = BytesIO()
    glitch(r, w)
    return w.getvalue()


def glitch(r, w):
    while True:
        byte = r.read(1)

        if not byte:
            break
        elif byte == '\x07':
            w.write(' ')
        elif byte == '\r':
            w.write(byte)
            next_byte = r.read(1)
            if next_byte != '\n':
                w.write('\n')
            w.write(next_byte)
        elif byte == '\n' or byte == '\x0D':
            w.write('\r\n')
        else:
            w.write(byte)


def log_to_stderr():
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.DEBUG)
    stderr.setFormatter(logging.Formatter(fmt='%(levelname)8s: %(message)s'))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stderr)


if __name__ == '__main__':
    log_to_stderr()

    import sys
    args = sys.argv[1:]
    blob = wordpad(
        sys.stdin.read(),
        max_size=(1024, 1024),
        rotate=('rotate' in args)
    )
    sys.stdout.write(blob)
