from pymosh import Index
from pymosh.mpeg4 import is_iframe

import logging
log = logging.getLogger(__name__)

MOSH_TYPES = ['drift', 'echo']


def mosh(in_filename, out_filename, mosh_type=None):
    func_map = {
        'drift': drift_stream,
        'echo': echo_stream,
    }

    mosh_type = mosh_type or 'drift'

    process_streams(in_filename, out_filename, func_map[mosh_type])


def process_streams(in_filename, out_filename, func, *args, **kwargs):
    f = Index(in_filename)

    for stream in f.video:
        drifted = list(func(stream, *args, **kwargs))
        stream.replace(drifted)

    f.rebuild()
    f.write(open(out_filename, 'wb'))


def drift_stream(stream, midpoint=0.5):
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


def echo_stream(stream, midpoint=0.5):
    all_frames = list(stream)
    pframes = [f for f in all_frames if not is_iframe(f)]
    midpoint_idx = int(len(all_frames)*midpoint)

    frames = all_frames[:midpoint_idx]

    while len(frames) < len(all_frames):
        frames += pframes[:(len(all_frames) - len(frames))]

    return frames
