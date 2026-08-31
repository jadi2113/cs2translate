import os
import queue
import threading
from enum import Enum

class FileTailerWorker:
    class Status(Enum):
        OK = 0
        FILE_MISSING = 1
        FILE_READ_ERROR = 2

    def __init__(
        self,
        path: str,
        out_queue: queue.Queue[list[str]],
        interval: float = 0.25,
        start_at_end: bool = True
    ):
        self.path = path
        self.out_queue = out_queue
        self.interval = interval
        self.start_at_end = start_at_end
        self.status = FileTailerWorker.Status.FILE_MISSING

        self._pos = 0
        self._inode = None
        self._opened_before = False
        self._partial_line = ""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stop_event = threading.Event()

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._poll_once()
                self.status = self.Status.OK
            except FileNotFoundError:
                self.status = self.Status.FILE_MISSING
                self._inode = None
            except OSError:
                self.status = self.Status.FILE_READ_ERROR
            finally:
                self._stop_event.wait(self.interval)

    def _poll_once(self):
        # raises FileNotFoundError or OSError if inaccessible
        stat = os.stat(self.path)

        if self._inode is None:
            self._inode = stat.st_ino
            self._pos = 0

            # start from the end only if file was never accessible before
            # otherwise it was recreated, start from the beginning
            if self.start_at_end and not self._opened_before:
                self._pos = stat.st_size

            self._opened_before = True
            return

        if (
            stat.st_ino != self._inode or # file was recreated
            stat.st_size < self._pos      # file shrank, probably cleared
        ):
            self._inode = stat.st_ino
            self._pos = 0
            self._partial_line = ""

        if stat.st_size <= self._pos:
            return # nothing new was added

        # read new contents
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(self._pos)
            chunk = f.read()
            self._pos = f.tell()

        # if a line was read before it was fully written, store it temporarily
        # if it is complete (ends with \n), _partial_line will be an empty string
        chunk = self._partial_line + chunk
        *lines, self._partial_line = chunk.split("\n")

        # add all non-empty lines to the output queue
        lines = [s for line in lines if (s := line.strip())]
        self.out_queue.put(lines)
