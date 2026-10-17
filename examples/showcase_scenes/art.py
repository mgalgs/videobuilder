"""The Looks family: one scene (videobuilder.looks' lighthouse) repainted
in three looks, cut on the beat. Film time runs on through the cuts, so the
boat and the sky keep moving while the look changes under them."""
from videobuilder import looks

from . import kit
from .looks import chip

LOOKS = {'art-swirl': 'swirl', 'art-woodblock': 'woodblock', 'art-pop': 'pop-art'}
SFX_F = kit.font(44, 900)


def art(cv, s, st):
    name = LOOKS[s.name]
    into_group = s.parents[-1][1] if s.parents else s.f
    t, age = into_group / kit.FPS, s.f / kit.FPS
    opts = {'sfx': 'LAUNCH!', 'font': SFX_F} if name == 'pop-art' else {}
    looks.paint(cv, name, looks.lighthouse(st.frame.w, st.frame.h, t), t, age + 1.0, **opts)
    chip(cv, st, looks.get(name).title)


SCENES = {name: art for name in LOOKS}
