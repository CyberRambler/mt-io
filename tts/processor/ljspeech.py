"""Perform preprocessing and raw feature extraction for LJSpeech dataset."""

import os
import re

from g2p_en import G2p

import numpy as np
import soundfile as sf
from dataclasses import dataclass
from tts.processor import BaseProcessor
from tts.utils import cleaners
from tts.utils.utils import PROCESSOR_FILE_NAME

valid_symbols = [
    "AA",
    "AA0",
    "AA1",
    "AA2",
    "AE",
    "AE0",
    "AE1",
    "AE2",
    "AH",
    "AH0",
    "AH1",
    "AH2",
    "AO",
    "AO0",
    "AO1",
    "AO2",
    "AW",
    "AW0",
    "AW1",
    "AW2",
    "AY",
    "AY0",
    "AY1",
    "AY2",
    "B",
    "CH",
    "D",
    "DH",
    "EH",
    "EH0",
    "EH1",
    "EH2",
    "ER",
    "ER0",
    "ER1",
    "ER2",
    "EY",
    "EY0",
    "EY1",
    "EY2",
    "F",
    "G",
    "HH",
    "IH",
    "IH0",
    "IH1",
    "IH2",
    "IY",
    "IY0",
    "IY1",
    "IY2",
    "JH",
    "K",
    "L",
    "M",
    "N",
    "NG",
    "OW",
    "OW0",
    "OW1",
    "OW2",
    "OY",
    "OY0",
    "OY1",
    "OY2",
    "P",
    "R",
    "S",
    "SH",
    "T",
    "TH",
    "UH",
    "UH0",
    "UH1",
    "UH2",
    "UW",
    "UW0",
    "UW1",
    "UW2",
    "V",
    "W",
    "Y",
    "Z",
    "ZH",
]

_pad = "pad"
_eos = "eos"
_punctuation = "!'(),.:;? "
_special = "-"
_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# Prepend "@" to ARPAbet symbols to ensure uniqueness (some are the same as uppercase letters):
_arpabet = ["@" + s for s in valid_symbols]

# Export all symbols:
LJSPEECH_SYMBOLS = (
    [_pad] + list(_special) + list(_punctuation) + list(_letters) + _arpabet + [_eos]
)

# Regular expression matching text enclosed in curly braces:
# _curly_re = re.compile(r"(.*?)\{(.+?)\}(.*)")
_curly_re = re.compile(r"\{(.+?)\}")


g2p = G2p()


@dataclass
class LJSpeechProcessor(BaseProcessor):
    """LJSpeech processor."""

    cleaner_names: str = "english_cleaners"
    positions = {
        "wave_file": 0,
        "text": 1,
        "text_norm": 2,
    }
    train_f_name: str = "metadata.csv"

    def create_items(self):
        if self.data_dir:
            with open(os.path.join(self.data_dir, self.train_f_name), encoding="utf-8") as f:
                self.items = [self.split_line(self.data_dir, line, "|") for line in f]

    def split_line(self, data_dir, line, split):
        parts = line.strip().split(split)
        wave_file = parts[self.positions["wave_file"]]
        text_norm = parts[self.positions["text_norm"]]
        wav_path = os.path.join(data_dir, "wavs", f"{wave_file}.wav")
        speaker_name = "ljspeech"
        return text_norm, wav_path, speaker_name

    def setup_eos_token(self):
        return _eos

    def save_pretrained(self, saved_path):
        os.makedirs(saved_path, exist_ok=True)
        self._save_mapper(os.path.join(saved_path, PROCESSOR_FILE_NAME), {})

    def get_one_sample(self, item):
        text, wav_path, speaker_name = item

        text = self.get_phoneme(text)

        # normalize audio signal to be [-1, 1], soundfile already norm.
        audio, rate = sf.read(wav_path)
        audio = audio.astype(np.float32)

        # convert text to ids
        text_ids = np.asarray(self.text_to_sequence(text), np.int32)

        sample = {
            "raw_text": text,
            "text_ids": text_ids,
            "audio": audio,
            "utt_id": os.path.split(wav_path)[-1].split(".")[0],
            "speaker_name": speaker_name,
            "rate": rate,
        }

        return sample

    def text_to_sequence(self, text, inference=True):
        sequence = []
        # Check for curly braces and treat their contents as ARPAbet:
        # while len(text):
        #     m = _curly_re.match(text)
        #     if not m:
        #         sequence += self._symbols_to_sequence(self._clean_text(text, [self.cleaner_names]))
        #         break
        #     sequence += self._symbols_to_sequence(self._clean_text(m.group(1), [self.cleaner_names]))
        #     sequence += self._arpabet_to_sequence(m.group(2))
        #     text = m.group(3)

        m = _curly_re.match(text)
        if not m:
            sequence += self._symbols_to_sequence(self._clean_text(text, [self.cleaner_names]))
        else:
            phoneme = m.group(1)
            if inference:
                print(phoneme)
            sequence += self._arpabet_to_sequence(phoneme)

        # add eos tokens
        sequence += [self.eos_id]

        return sequence

    def _clean_text(self, text, cleaner_names):
        for name in cleaner_names:
            cleaner = getattr(cleaners, name)
            if not cleaner:
                raise Exception("Unknown cleaner: %s" % name)
            text = cleaner(text)
        return text

    def _symbols_to_sequence(self, symbols):
        return [self.symbol_to_id[s] for s in symbols if self._should_keep_symbol(s)]

    def _arpabet_to_sequence(self, text):
        return self._symbols_to_sequence(["@" + s if s not in _punctuation else s for s in text.split()])

    def _should_keep_symbol(self, s):
        return s in self.symbol_to_id and s != "_" and s != "~"

    def txt2phoneme(self, txt):
        return " ".join(g2p(txt))

    def get_phoneme(self, txt):
        return "{" + self.txt2phoneme(txt) + "}"


if __name__ == "__main__":
    preprocessor = LJSpeechProcessor(data_dir=None, symbols=LJSPEECH_SYMBOLS)
    txt = "This is a book, and I like it."
    ids = preprocessor.text_to_sequence(txt)
    print(ids)
    symbols = [preprocessor.id_to_symbol[id] for id in ids]
    print(symbols)

    pron = preprocessor.get_phoneme(txt)
    print(pron)
    ids = preprocessor.text_to_sequence(pron)
    print(ids)
    symbols = [preprocessor.id_to_symbol[id] for id in ids]
    print(symbols)