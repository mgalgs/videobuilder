"""Frame-accurate, bounded-memory video asset reader using system ffmpeg."""
from fractions import Fraction
import json
import os
import subprocess

from PIL import Image as PILImage

from .canvas import Image


class Clip:
    """A video file with random frame access. Keep one decoder open per process."""

    def __init__(self, path):
        self.path = os.fspath(path)
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                 '-show_entries', 'stream=width,height,avg_frame_rate,nb_frames',
                                 '-of', 'json', self.path], capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout)['streams']
        if not streams:
            raise ValueError(f'no video stream: {self.path}')
        stream = streams[0]
        self.size = (stream['width'], stream['height'])
        self.fps = Fraction(stream['avg_frame_rate'])
        if self.fps <= 0:
            raise ValueError(f'unknown frame rate: {self.path}')
        if stream.get('nb_frames') not in (None, 'N/A'):
            self.frames = int(stream['nb_frames'])
        else:
            result = subprocess.run(['ffprobe', '-v', 'error', '-count_frames',
                                     '-select_streams', 'v:0', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'default=nw=1:nk=1',
                                     self.path], capture_output=True, text=True, check=True)
            self.frames = int(result.stdout.strip())
        self._decoder = None
        self._next = None
        self._pid = None

    def close(self):
        process = self._decoder
        self._decoder = None
        self._next = None
        if process is not None:
            process.stdout.close()
            process.kill()
            process.wait()

    def _start(self, index):
        self.close()
        timestamp = f'{float(index / self.fps):.9f}'
        self._decoder = subprocess.Popen(
            ['ffmpeg', '-v', 'error', '-ss', timestamp, '-i', self.path,
             '-map', '0:v:0', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
             '-fps_mode', 'passthrough', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._next = index
        self._pid = os.getpid()

    def frame(self, index):
        if not isinstance(index, int) or not 0 <= index < self.frames:
            raise IndexError(index)
        if self._pid != os.getpid():
            self._decoder = None
            self._next = None
        if self._decoder is None or index != self._next:
            self._start(index)
        count = self.size[0] * self.size[1] * 3
        chunks = []
        remaining = count
        while remaining:
            chunk = self._decoder.stdout.read(remaining)
            if not chunk:
                self.close()
                raise RuntimeError(f'could not decode frame {index} from {self.path}')
            chunks.append(chunk)
            remaining -= len(chunk)
        self._next += 1
        return Image.from_pil(PILImage.frombytes('RGB', self.size, b''.join(chunks)))

    def __del__(self):
        if getattr(self, '_decoder', None) is not None:
            self.close()
