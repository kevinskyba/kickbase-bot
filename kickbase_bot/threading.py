import threading
import time
from threading import Thread
from typing import Callable


def _start_thread_periodically(dt: int, func: Callable) -> Thread:
    thread = threading.Thread(target=_periodically(dt, func))
    thread.daemon = True
    thread.start()
    return thread


def _periodically(dt: int, func: Callable):
    def fun():
        func(silent=True)
        while True:
            time.sleep(dt)
            func(silent=False)
    return fun
