"""A committed ManimGX shot. Build: /opt/manimgx/bin/python examples/shot3d_demo.py --build"""
from pathlib import Path
import sys
import time
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import videobuilder as vb
from videobuilder import text
from videobuilder.shot3d import build as build_shot

HERE = Path(__file__).resolve().parent
text.register(HERE / 'assets' / 'Cantarell-VF.otf')
FPS = 30
SHOT_FRAMES = 60
SIZE = (720, 1280)
ASSET = HERE / 'assets' / 'orbit.mp4'
CLIP = vb.Clip(ASSET) if ASSET.exists() else None


def draw(n, cv):
    if n < 30:
        cv.rect(0, 0, cv.width, cv.height, '#0b1020')
        cv.rect(85, 550, 9, 260, '#58d8d1')
        text.draw(cv, 'FORM IN', vb.Font('Cantarell', 115, weight=750),
                  130, 575, '#f3f2ed')
        text.draw(cv, 'MOTION', vb.Font('Cantarell', 115, weight=750),
                  130, 700, '#f3f2ed')
        text.draw(cv, 'A 3D study', vb.Font('Cantarell', 51),
                  135, 875, '#84aaa9')
    else:
        if CLIP is None:
            raise FileNotFoundError(f'build the shot first: {ASSET}')
        cv.image(CLIP.frame(n - 30), 0, 0, cv.width, cv.height)
        cv.rect(0, 1580, cv.width, 340, '#0b1020', alpha=0.72)
        text.draw(cv, 'FORM IN MOTION', vb.Font('Cantarell', 72, weight=750),
                  90, 1635, '#f3f2ed')
        text.draw(cv, 'Light follows the turning ring.', vb.Font('Cantarell', 40),
                  94, 1740, '#a5d7d0')


FILM = vb.Film(draw, fps=FPS, frames=30 + SHOT_FRAMES,
               formats=('9x16',), background='#0b1020')


def build():
    import manimgx as m
    from videobuilder.manimgx_shot import frames

    class Orbital(m.ThreeDScene):
        def construct(self):
            self.set_camera_orientation(phi=65 * m.DEGREES,
                                        theta=-50 * m.DEGREES, zoom=1.08)
            sun = m.SunLight(location=5 * m.LEFT + 3 * m.UP + 7 * m.OUT,
                             intensity=1.2)
            self.add(sun, m.AmbientLight(intensity=0.3))
            ring = m.Torus(major_radius=2.1, minor_radius=0.58,
                           resolution=(64, 32),
                           checkerboard_colors=False, color=m.TEAL)
            ring.set_stroke(width=0)
            ring.set_material(m.Material())
            core = m.Sphere(radius=0.9, resolution=(48, 32), checkerboard_colors=False, color=m.GOLD)
            core.set_stroke(width=0)
            core.set_material(m.Material())
            core.set_fill(m.GOLD)
            self.add(ring, core)
            self.play(m.Rotate(ring, 2 * m.PI, axis=m.RIGHT + m.UP),
                      m.Rotate(core, 2 * m.PI, axis=m.OUT),
                      run_time=SHOT_FRAMES / FPS, rate_func=m.linear)

    m.config.background_color = m.ManimColor('#0b1020')
    def source():
        hashes = []
        for index, rgba in frames(Orbital, SIZE, SHOT_FRAMES, FPS):
            hashes.append(hashlib.sha256(rgba).hexdigest())
            yield index, rgba
        print(f'raw frame hashes: {hashlib.sha256("".join(hashes).encode()).hexdigest()}')

    start = time.monotonic()
    build_shot(ASSET, source, SIZE, FPS, SHOT_FRAMES)
    elapsed = time.monotonic() - start
    print(f'asset={ASSET} seconds={elapsed:.2f} per_frame={elapsed / SHOT_FRAMES:.3f}')


if __name__ == '__main__' and '--build' in sys.argv:
    build()
