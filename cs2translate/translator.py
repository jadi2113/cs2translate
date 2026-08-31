import logging as log
import queue
import threading
from collections import OrderedDict
from dataclasses import dataclass

from deep_translator import GoogleTranslator
import fasttext as ft

from cs2translate.config import Config
from cs2translate.parser import ChatMessage, parse_message

# common untranslatable phrases used in CS chat
# should I add weapon names here aswell? they're translatable but unnecessary
UNTRANSLATABLES = {
    # 1 letter
    "a", "b", "k",
    # 2 letters
    "gg", "gh", "gl", "hf", "nt", "wh", "wp", "ez", "ns", "np",
    "ty", "xd", "kk", "ok", "hm", "oh", "ah", "lo", "lm", "ha",
    "hs", "gj",
    # 3 letters
    "mid", "con", "cat", "ahh", "afk", "lol", "pls", "rip", "bro", "hah",
    "brb", "kek", "thx", "mvp", "gtg", "smh", "pog", "omg", "1v1", "1v2",
    "1v5", "2v1", "5v1", "2v2",
    # 4 letters
    "tilt", "rekt", "noob", "lmao", "peek", "haha", "nice",
    # more than 4 letters
    "gl hf", "lmfao", "a site", "b site", "plant"
}

# TODO: replace with lingua + heuristics, detection quality on short strings is bad
class LanguageDetector:
    """fastext lid.176 model wrapper for detecting languages"""
    def __init__(self, path: str):
        self.path = path
        self._model = None

    def detect(self, text: str) -> tuple[str, float]:
        if self._model is None:
            self._model = ft.load_model(self.path)

        labels, probs = self.model.predict(text)
        return (
            labels[0].replace("__label__", ""),
            float(probs[0])
        )

class Translator:
    """deep_translator wrapper with cache incase players are spamming"""
    def __init__(
        self,
        target: str,
        source: str = "auto",
        cache_size: int = 256
    ):
        self.cache_size = cache_size
        self._client = GoogleTranslator(source, target)
        self._cache = OrderedDict()

    def set_languages(self, target: str, source: str = "auto"):
        self._client.target = target
        self._client.source = source

    def _check_cache(self, key: tuple[str, str, str]) -> str | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        else:
            return None

    def _truncate_cache(self):
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def translate(self, text: str) -> str:
        cache_key = (self._client.source, self._client.target, text)
        res = self._check_cache(cache_key)
        if res is None:
            res = self._client.translate(text)
            self._cache[cache_key] = res

        self._truncate_cache()
        return res

@dataclass
class Translation:
    message: ChatMessage # original chat message
    lang: str | None = None # none if skipped before language detection or too short
    text: str | None = None # none if skipped
    error: str | None = None

class TranslateWorker:
    def __init__(
        self,
        in_queue: queue.Queue[list[str]],          # input queue of log lines
        out_queue: queue.Queue[list[Translation]], # output queue of translated chat messages
        lang_detector: LanguageDetector,
        translator: Translator,
        config: Config
    ):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.lang_detector = lang_detector
        self.translator = translator
        self.config = config
        self._own_username = config.own_username.strip().lower()
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
                # block while waiting for the trailer to read a new batch of lines
                # use timeout to be able to poll _stop_event regularly
                lines = self.in_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            results: list[Translation] = []
            for line in lines:
                # attempt to parse, ignore eveything that is not a message
                message = parse_message(line)
                if not message:
                    continue

                # attempt to translate the message if necessary
                res, translate = self._classify(message)
                if translate:
                    try:
                        res.text = self.translator.translate(res.message.text)
                        res.error = None

                        # deep_translator returns googles error page as text
                        if "that's an error" in res.text.lower():
                            raise RuntimeError("Server error")

                    except Exception as e:
                        res.text = None
                        res.error = str(e)
                        log.warning("Translator error: %s", res.error)

                # TODO: use translate_batch to save on requests
                results.append(res)

            self.out_queue.put(results)

    def _log_reject(self, message: ChatMessage, reason: str):
        log.info("Rejected message (reason: %s): %s", reason, message.text)

    def _classify(self, message: ChatMessage) -> tuple[Translation, bool]:
        res = Translation(message)

        # pass through own messages
        if self.config.ignore_own_messages:
            sender = message.player.strip().lower()
            if self._own_username == sender:
                self._log_reject(message, f"sent by {message.player}")
                return res, False

        # pass through common untranslatable phrases
        # the translator will usually skip these but this way we avoid spamming it
        if message.text.strip().lower() in UNTRANSLATABLES:
            self._log_reject(message, "untranslatable")
            return res, False

        # detect language and perform language specific filtering
        # only when message is long enough
        if len(message.text) > 3:
            lang, confidence = self.lang_detector.detect(message.text)
            res.lang = lang

            if confidence > 0.5:
                # pass through messages already in target language
                if lang == self.config.output_language:
                    self._log_reject(message, "target language")
                    return res, False

                # pass through messages in english if enabled
                if self.config.ignore_english and lang == "en":
                    self._log_reject(message, "english")
                    return res, False

        # True as second return value marks the message as translatable
        return res, True
