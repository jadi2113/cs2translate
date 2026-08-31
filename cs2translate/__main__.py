import queue
import sys
import os
import logging as log
import tempfile as tf
import urllib.request, urllib.error
from tkinter import messagebox as mb

from cs2translate.config import Config
from cs2translate.tailer import FileTailerWorker
from cs2translate.translator import (
    LanguageDetector,
    Translator,
    TranslateWorker,
    Translation
)
from cs2translate.ui import (
    AppWindow,
    SettingsWindow,
    configure_ctk_theme
)

# find the correct path to store files
# when compiled with Nuitka, store files together with the executable
if "__compiled__" in globals():
    APP_DIR = globals()["__compiled__"].containing_dir
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LID176_PATH = os.path.join(APP_DIR, "lid.176.ftz")

# url to download language detection model if not present
LID176_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"

class App:
    def __init__(self):
        self.config = Config.load(CONFIG_PATH)
        self.lang_detector = LanguageDetector(LID176_PATH)
        self.translator = Translator(self.config.output_language)
        self.pipeline = Pipeline(self.lang_detector, self.translator)
        self.win = AppWindow(self._on_open_settings_window)

    def _on_open_settings_window(self):
        SettingsWindow(self.win, self.config, self._on_apply_settings)

    def _on_apply_settings(self, config):
        self.config = config
        self.config.save(CONFIG_PATH)
        self.pipeline.restart(self.config)

    def _ensure_model_present(self):
        """ensure language detection model is present, download it if not"""
        if os.path.exists(LID176_PATH):
            return

        filename = os.path.basename(LID176_PATH)
        log.info("Downloading language detection model (%s)", filename)

        # create a temporary file so no incomplete lid.176.ftz is left after a crash
        # no need to keep it open since urlretrieve will reopen it
        dir = os.path.dirname(LID176_PATH)
        fd, temp = tf.mkstemp(dir=dir, suffix=".temp")
        os.close(fd)

        try:
            urllib.request.urlretrieve(LID176_URL, temp)
            os.replace(temp, LID176_PATH) # atomic replace when done
        except (OSError, urllib.error.URLError) as e:
            os.remove(temp)
            raise RuntimeError(
                f"Unable to download {filename} from {LID176_URL}"
            ) from e

    def _update_status(self):
        messages = [
            "Watching console.log for new messages",
            "Missing console.log, please check path",
            "Unable to access console.log"
        ]
        msg = messages[self.pipeline.tailer.status.value]
        self.win.set_status_message(msg)

    def _update(self):
        self._update_status()
        res = self.pipeline.drain_output_queue()
        if res:
            self.win.display_messages(res)
        self.win.after(100, self._update)

    def run(self):
        try:
            self._ensure_model_present()
            self.pipeline.start(self.config)
            self._update()
            self.win.mainloop()
        finally:
            self.pipeline.stop()

class Pipeline:
    def __init__(self, lang_detector: LanguageDetector, translator: Translator):
        self.lang_detector = lang_detector
        self.translator = translator
        self.log_queue = None
        self.res_queue = None
        self.tailer = None
        self.worker = None
        self._running = False

    def start(self, config: Config):
        assert not self._running

        # create fresh queues
        log.info("Starting workers")
        self.log_queue: queue.Queue[list[str]] = queue.Queue()
        self.res_queue: queue.Queue[list[Translation]] = queue.Queue()

        self.tailer = FileTailerWorker(
            config.console_log_path,
            self.log_queue
        )

        self.translator.set_languages(config.output_language)
        self.worker = TranslateWorker(
            self.log_queue,
            self.res_queue,
            self.lang_detector,
            self.translator,
            config
        )

        self.tailer.start()
        self.worker.start()
        self._running = True

    def stop(self):
        log.info("Stopping workers")
        self._running = False

        if self.tailer:
            self.tailer.stop()
        if self.worker:
            self.worker.stop()

    def restart(self, config: Config):
        self.stop()
        self.start(config)

    def drain_output_queue(self):
        assert self._running
        res: list[Translation] = []
        while True:
            try:
                res.extend(self.res_queue.get_nowait())
            except queue.Empty:
                break
        return res

def configure_logging():
    log.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        level=log.INFO
    )

def main():
    configure_logging()
    configure_ctk_theme()
    try:
        app = App()
        app.run()
    except Exception as e:
        mb.showerror(
            "Unexpected Error",
            f"An unexpected error has occurred.\n{exc!s}"
        )
        raise

if __name__ == "__main__":
    main()
