from . import datamosh

import subprocess
import tempfile
import urllib
import sys
import os

import logging
log = logging.getLogger(__name__)


class Processor:
    def __init__(self,
                 ffmpeg_binary='bin/ffmpeg',
                 ffprobe_binary='bin/ffprobe',
                 tmp_dir='./tmp'):

        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self.tmp_dir = tmp_dir

        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)

    def mosh_url(self, video_url, mosh_type=None):
        """
        Takes a video URL and returns a path to a .gif file
        containing a moshed version of the video.
        """
        log.info("Downloading %s", video_url)
        video_file = tempfile.NamedTemporaryFile(dir=self.tmp_dir, delete=False)
        video_file.write(urllib.urlopen(video_url).read())
        video_file.close()
        return self.mosh_file(video_file.name, mosh_type=mosh_type)

    def mosh_file(self, filename, mosh_type=None):
        frame_rate = self.get_frame_rate(filename) or 24.0
        log.info("Frame rate: {}fps".format(frame_rate))
        avi_filename = self.to_avi(filename)
        _, moshed_filename = tempfile.mkstemp('.mosh.avi', dir=self.tmp_dir)
        log.info("Moshing %s", avi_filename)
        datamosh.mosh(avi_filename, moshed_filename, mosh_type)
        return self.make_gif(moshed_filename, frame_rate)

    def to_avi(self, filename):
        _, avi_filename = tempfile.mkstemp('.avi', dir=self.tmp_dir)
        check_call([self.ffmpeg_binary, '-y', '-i', filename, '-g', '250', avi_filename])
        return avi_filename

    def make_gif(self, filename, frame_rate):
        _, gif_filename = tempfile.mkstemp('.gif', dir=self.tmp_dir)

        all_frames = self.extract_frames(filename, frame_rate)
        step = 1

        max_size = 3 * 1024 * 1024

        while True:
            frames = all_frames[::step]
            if len(frames) < 2:
                raise Exception("Can't make a file small enough (%d frames, step = %s)"
                    % (len(all_frames), step))

            modified_frame_rate = int(round(frame_rate / step))

            cmd = [
                'convert',
                '-loop', '0',
                '-delay', '1x{}'.format(modified_frame_rate),
                '-layers', 'Optimize',
            ]
            cmd += frames
            cmd.append(gif_filename)
            check_call(cmd)

            if os.stat(gif_filename).st_size < max_size:
                break

            step += 1

        return gif_filename

    def extract_frames(self, filename, frame_rate):
        frames_dir = tempfile.mkdtemp(dir=self.tmp_dir)
        check_call([
            self.ffmpeg_binary,
            '-y',
            '-i', filename,
            '-r', str(frame_rate),
            os.path.join(frames_dir, '%04d.png'),
        ])
        return sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir)])

    # Adapted from http://askubuntu.com/a/723362
    def get_frame_rate(self, filename):
        out = check_call([
            self.ffprobe_binary, filename,
            "-v", "0",
            "-select_streams", "v",
            "-print_format", "flat",
            "-show_entries", "stream=avg_frame_rate",
        ])
        rate = out.split('=')[1].strip()[1:-1].split('/')
        if len(rate)==1:
            return float(rate[0])
        if len(rate)==2:
            return float(rate[0])/float(rate[1])

        log.error("Unparseable output: {}".format(out))
        return None


def check_call(cmd, *args, **kwargs):
    log.info("$ %s" % " ".join(cmd))
    output = ""

    try:
        output = subprocess.check_output(cmd, *args, **kwargs)
        return output
    except subprocess.CalledProcessError:
        log.error(output)
        raise
