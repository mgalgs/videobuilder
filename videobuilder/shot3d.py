"""Encode a sequential RGBA shot as a committed video asset."""
import os
from contextlib import suppress
from pathlib import Path
import subprocess
import tempfile


def build(path, source, size, fps, frames, crf=14):
    """Consume (index, RGBA bytes) in order and atomically publish an MP4."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.stem}-', suffix='.mp4', dir=path.parent)
    os.close(fd)
    width, height = size
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
               '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', f'{width}x{height}',
               '-framerate', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
               '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p',
               '-g', '15', '-bf', '0', '-frames:v', str(frames), temporary]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        expected = 0
        stream = source()
        try:
            for index, rgba in stream:
                if index != expected or index >= frames:
                    raise ValueError(f'expected frame {expected}, got {index}')
                if len(rgba) != width * height * 4:
                    raise ValueError(f'frame {index} has {len(rgba)} bytes; expected {width * height * 4}')
                process.stdin.write(rgba)
                expected += 1
        finally:
            close = getattr(stream, 'close', None)
            if close is not None:
                close()
        if expected != frames:
            raise ValueError(f'expected {frames} frames, got {expected}')
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('ffmpeg failed to encode shot')
        os.replace(temporary, path)
    except BaseException:
        process.kill()
        process.wait()
        with suppress(BrokenPipeError):
            process.stdin.close()
        raise
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path
