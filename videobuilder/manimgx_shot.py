"""Optional ManimGX adapter. ManimGX is imported only on use."""
from queue import Full, Queue
from threading import Event, Thread


def frames(scene_type, size, count, fps):
    """Yield sequential RGBA frames, expanding ManimGX hold records."""
    import manimgx as m
    from manimgx.rendering.film import Cut

    queue = Queue(maxsize=2)
    done = object()
    stop = Event()

    def offer(item):
        while not stop.is_set():
            try:
                queue.put(item, timeout=0.1)
                return
            except Full:
                pass
        raise Cut

    def render():
        try:
            m.config.pixel_width, m.config.pixel_height = size
            m.config.frame_rate = fps

            def sink(frame):
                if stop.is_set():
                    raise Cut
                rgba = frame.pixels()  # must draw before ManimGX advances
                for index in range(frame.index, min(frame.index + frame.repeat, count)):
                    offer((index, rgba))
                if frame.index + frame.repeat >= count:
                    raise Cut

            scene_type().render(frames=sink)
        except Cut:
            pass
        except BaseException as exc:
            if not stop.is_set():
                offer(exc)
        finally:
            if not stop.is_set():
                offer(done)

    worker = Thread(target=render, daemon=True)
    worker.start()
    try:
        while True:
            item = queue.get()
            if item is done:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        stop.set()
        worker.join()
