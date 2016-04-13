from pymosh import Index
from pymosh.mpeg4 import is_iframe

import logging
log = logging.getLogger(__name__)


def drift(in_filename, out_filename, midpoint=0.5):
    mosh(in_filename, out_filename, drift_stream, midpoint)


def echo(in_filename, out_filename, midpoint=0.5):
    mosh(in_filename, out_filename, echo_stream, midpoint)


def mosh(in_filename, out_filename, func, *args, **kwargs):
    f = Index(in_filename)

    for stream in f.video:
        drifted = list(func(stream, *args, **kwargs))
        stream.replace(drifted)

    f.rebuild()
    f.write(open(out_filename, 'wb'))


def drift_stream(stream, midpoint):
    repeated_frame = None

    for idx, frame in enumerate(stream):
        if idx < len(stream)*midpoint:
            yield frame
        elif is_iframe(frame):
            pass
        else:
            if repeated_frame is None:
                repeated_frame = frame
            yield repeated_frame


def echo_stream(stream, midpoint):
    all_frames = list(stream)
    pframes = [f for f in all_frames if not is_iframe(f)]
    midpoint_idx = int(len(all_frames)*midpoint)

    frames = all_frames[:midpoint_idx]

    while len(frames) < len(all_frames):
        frames += pframes[:(len(all_frames) - len(frames))]

    return frames
