"""A cached ManimGX shot. Build first: .venv/bin/python examples/shot3d_demo.py --build"""
from pathlib import Path
import sys
import time

import videobuilder as vb
from videobuilder import text
from videobuilder.shot3d import ShotCache

HERE = Path(__file__).resolve().parent
text.register(HERE / 'assets' / 'Cantarell-VF.otf')
FPS = 30
SHOT_FRAMES = 150
SIZE = (1080, 1920)
CACHE = ShotCache(HERE.parent / '.shot3d-cache', __file__, SIZE, FPS, SHOT_FRAMES)


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
        cv.image(CACHE.image(n - 30), 0, 0, cv.width, cv.height)
        cv.rect(0, 1580, cv.width, 340, '#0b1020', alpha=0.72)
        text.draw(cv, 'FORM IN MOTION', vb.Font('Cantarell', 72, weight=750),
                  90, 1635, '#f3f2ed')
        text.draw(cv, 'Rendered once. Ready at any frame.', vb.Font('Cantarell', 40),
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
    start = time.monotonic()
    built = CACHE.build(lambda: frames(Orbital, SIZE, SHOT_FRAMES, FPS))
    elapsed = time.monotonic() - start
    print(f'cache={CACHE.path} built={built} seconds={elapsed:.2f} '
          f'per_frame={elapsed / SHOT_FRAMES:.3f}')


if __name__ == '__main__' and '--build' in sys.argv:
    build()
