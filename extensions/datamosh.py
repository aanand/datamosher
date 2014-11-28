from pymosh import Index
from pymosh.mpeg4 import is_iframe

import logging
log = logging.getLogger(__name__)


def drift(in_filename, out_filename, drift_point=0.5):
    f = Index(in_filename)

    for stream in f.video:
        drifted = list(drift_stream(stream, len(stream)*drift_point))
        stream.replace(drifted)

    f.rebuild()
    f.write(open(out_filename, 'wb'))


def drift_stream(stream, drift_point):
    idx = 0
    repeated_frame = None

    for frame in stream:
        if idx < drift_point:
            yield frame
        elif is_iframe(frame):
            pass
        else:
            if repeated_frame is None:
                repeated_frame = frame
            yield repeated_frame

        idx += 1
