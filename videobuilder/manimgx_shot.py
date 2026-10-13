"""Optional ManimGX adapter for ShotCache. ManimGX is imported only on use."""
from queue import Queue
from threading import Thread


def frames(scene_type, size, count, fps):
    """Yield sequential RGBA frames, expanding ManimGX hold records."""
    import manimgx as m
    from manimgx.rendering.film import Cut

    queue = Queue(maxsize=2)
    done = object()

    def render():
        try:
            m.config.pixel_width, m.config.pixel_height = size
            m.config.frame_rate = fps

            def sink(frame):
                rgba = frame.pixels()  # must draw before ManimGX advances
                for index in range(frame.index, min(frame.index + frame.repeat, count)):
                    queue.put((index, rgba))
                if frame.index + frame.repeat >= count:
                    raise Cut

            scene_type().render(frames=sink)
        except BaseException as exc:
            queue.put(exc)
        finally:
            queue.put(done)

    worker = Thread(target=render, daemon=True)
    worker.start()
    while True:
        item = queue.get()
        if item is done:
            break
        if isinstance(item, BaseException):
            raise item
        yield item
    worker.join()
