#!/usr/bin/env python
# coding=utf-8

import numpy
import os
import unittest

from aeneas.audiofilemfcc import AudioFileMFCC
from aeneas.audiofile import AudioFileMonoWAVE
from aeneas.audiofile import AudioFileUnsupportedFormatError
import aeneas.globalfunctions as gf

class TestAudioFileMFCC(unittest.TestCase):

    AUDIO_FILE_WAVE = "res/audioformats/mono.16000.wav"
    AUDIO_FILE_EMPTY = "res/audioformats/p001.empty"
    AUDIO_FILE_NOT_WAVE = "res/audioformats/p001.mp3"
    NOT_EXISTING_FILE = "res/audioformats/x/y/z/not_existing.wav"

    def load(self, path):
        audiofile = AudioFileMFCC(gf.absolute_path(path, __file__))
        self.assertIsNotNone(audiofile.all_mfcc)
        self.assertFalse(audiofile.is_reversed)
        self.assertNotEqual(audiofile.all_length, 0)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.tail_length, 0)
        self.assertNotEqual(audiofile.middle_length, 0)
        self.assertNotEqual(audiofile.audio_length, 0)
        return audiofile

    def test_load_on_none(self):
        with self.assertRaises(ValueError):
            audiofile = self.load(None)
    
    def test_load_audio_file(self):
        af = AudioFileMonoWAVE(gf.absolute_path(self.AUDIO_FILE_WAVE, __file__))
        audiofile = AudioFileMFCC(audio_file=af)
        self.assertIsNotNone(audiofile.all_mfcc)
        self.assertAlmostEqual(audiofile.audio_length, 53.3, places=1) # 53.266

    def test_load_mfcc_matrix(self):
        mfccs = numpy.zeros((13, 250))
        audiofile = AudioFileMFCC(mfcc_matrix=mfccs)
        self.assertIsNotNone(audiofile.all_mfcc)
        self.assertAlmostEqual(audiofile.audio_length, 10.0, places=1)

    def test_load_path(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertEqual(audiofile.all_mfcc.shape[0], 13)
        self.assertEqual(audiofile.all_mfcc.shape[1], 1331)
        self.assertAlmostEqual(audiofile.audio_length, 53.3, places=1) # 53.266

    def test_load_on_non_existing_path(self):
        with self.assertRaises(OSError):
            audiofile = self.load(self.NOT_EXISTING_FILE)

    def test_load_on_empty(self):
        with self.assertRaises(AudioFileUnsupportedFormatError):
            audiofile = self.load(self.AUDIO_FILE_EMPTY)

    def test_load_not_wave_file(self):
        with self.assertRaises(AudioFileUnsupportedFormatError):
            audiofile = self.load(self.AUDIO_FILE_NOT_WAVE)

    def test_reverse(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertFalse(audiofile.is_reversed)
        all_mfcc_pre = audiofile.all_mfcc
        audiofile.reverse()
        all_mfcc_post = audiofile.all_mfcc
        self.assertTrue(audiofile.is_reversed)
        self.assertTrue((all_mfcc_pre == all_mfcc_post[:, ::-1]).all())
        audiofile.reverse()
        all_mfcc_post = audiofile.all_mfcc
        self.assertFalse(audiofile.is_reversed)
        self.assertTrue((all_mfcc_pre == all_mfcc_post).all())

    def test_middle_begin_bad1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        with self.assertRaises(ValueError):
            audiofile.middle_begin = -1

    def test_middle_begin_bad2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        with self.assertRaises(ValueError):
            audiofile.middle_begin = 10000

    def test_middle_begin_good1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_begin = 0
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 1331)
        self.assertEqual(audiofile.tail_length, 0)

    def test_middle_begin_good2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_begin = 10
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 10)
        self.assertEqual(audiofile.middle_length, 1321)
        self.assertEqual(audiofile.tail_length, 0)

    def test_middle_begin_good3(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_begin = 1331
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 1331)
        self.assertEqual(audiofile.middle_length, 0)
        self.assertEqual(audiofile.tail_length, 0)

    def test_middle_end_bad1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        with self.assertRaises(ValueError):
            audiofile.middle_end = -1

    def test_middle_end_bad2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        with self.assertRaises(ValueError):
            audiofile.middle_end = 10000

    def test_middle_end_good1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_end = 0
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 0)
        self.assertEqual(audiofile.tail_length, 1331)

    def test_middle_end_good2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_end = 10
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 10)
        self.assertEqual(audiofile.tail_length, 1321)

    def test_middle_end_good3(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_end = 1331
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 1331)
        self.assertEqual(audiofile.tail_length, 0)

    def test_middle_begin_end(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_begin = 100
        audiofile.middle_end = 400
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 100)
        self.assertEqual(audiofile.middle_length, 300)
        self.assertEqual(audiofile.tail_length, 931)

    def test_middle_map(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.middle_begin = 100
        audiofile.middle_end = 400
        self.assertEqual(len(audiofile.middle_map), 300)

    def test_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.run_vad()
        self.assertIsNotNone(audiofile.masked_mfcc)
        self.assertIsNotNone(audiofile.masked_map)
        self.assertNotEqual(audiofile.masked_length, 0)
        self.assertIsNotNone(audiofile.masked_middle_mfcc)
        self.assertNotEqual(audiofile.masked_middle_length, 0)
        self.assertIsNotNone(audiofile.masked_middle_map)

    def test_masked_mfcc_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertIsNotNone(audiofile.masked_mfcc)

    def test_masked_map_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertIsNotNone(audiofile.masked_map)

    def test_masked_length_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertNotEqual(audiofile.masked_length, 0)

    def test_masked_middle_mfcc_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertIsNotNone(audiofile.masked_middle_mfcc)

    def test_masked_middle_map_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertIsNotNone(audiofile.masked_middle_map)

    def test_masked_middle_length_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        self.assertNotEqual(audiofile.masked_middle_length, 0)

    def test_set_head1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(head_length=0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 1331)
        self.assertEqual(audiofile.tail_length, 0)

    def test_set_head2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(head_length=1.0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 25)
        self.assertEqual(audiofile.middle_length, 1306)
        self.assertEqual(audiofile.tail_length, 0)

    def test_set_middle1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(middle_length=0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 0)
        self.assertEqual(audiofile.tail_length, 1331)

    def test_set_middle2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(middle_length=10)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 250)
        self.assertEqual(audiofile.tail_length, 1081)

    def test_set_tail1(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(tail_length=0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 1331)
        self.assertEqual(audiofile.tail_length, 0)

    def test_set_tail2(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(tail_length=1.0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 1306)
        self.assertEqual(audiofile.tail_length, 25)

    def test_set_head_tail(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(head_length=2.0, tail_length=2.0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 50)
        self.assertEqual(audiofile.middle_length, 1231)
        self.assertEqual(audiofile.tail_length, 50)

    def test_set_head_middle(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(head_length=2.0, middle_length=18.0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 50)
        self.assertEqual(audiofile.middle_length, 450)
        self.assertEqual(audiofile.tail_length, 831)

    def test_set_middle_tail(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.set_head_middle_tail(middle_length=20.0, tail_length=50.0)
        self.assertEqual(audiofile.all_length, 1331)
        self.assertEqual(audiofile.head_length, 0)
        self.assertEqual(audiofile.middle_length, 500)
        self.assertEqual(audiofile.tail_length, 831)

    def test_inside_nonspeech(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.run_vad()
        for index in [
            -2,
            -1,
            audiofile.all_length,
            audiofile.all_length + 1,
            audiofile.all_length + 2
        ]:
            self.assertIsNone(audiofile.inside_nonspeech(index))
        for begin, end in audiofile.intervals(False, False):
            self.assertIsNone(audiofile.inside_nonspeech(begin - 1))
            self.assertEqual(audiofile.inside_nonspeech(begin), (begin, end))
            self.assertEqual(audiofile.inside_nonspeech(begin + 1), (begin, end))
            self.assertEqual(audiofile.inside_nonspeech(end - 1), (begin, end))
            self.assertIsNone(audiofile.inside_nonspeech(end))
            self.assertIsNone(audiofile.inside_nonspeech(end + 1))

    def test_inside_nonspeech_no_explicit_run_vad(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        for index in [
            -2,
            -1,
            audiofile.all_length,
            audiofile.all_length + 1,
            audiofile.all_length + 2
        ]:
            self.assertIsNone(audiofile.inside_nonspeech(index))
        for begin, end in audiofile.intervals(False, False):
            self.assertIsNone(audiofile.inside_nonspeech(begin - 1))
            self.assertEqual(audiofile.inside_nonspeech(begin), (begin, end))
            self.assertEqual(audiofile.inside_nonspeech(begin + 1), (begin, end))
            self.assertEqual(audiofile.inside_nonspeech(end - 1), (begin, end))
            self.assertIsNone(audiofile.inside_nonspeech(end))
            self.assertIsNone(audiofile.inside_nonspeech(end + 1))

    def test_masked_with_head_tail(self):
        audiofile = self.load(self.AUDIO_FILE_WAVE)
        audiofile.run_vad()
        self.assertIsNotNone(audiofile.masked_middle_mfcc)
        self.assertNotEqual(audiofile.masked_middle_length, 0)
        self.assertIsNotNone(audiofile.masked_middle_map)
        pre = audiofile.masked_middle_length
        audiofile.set_head_middle_tail(head_length=0.440, tail_length=1.200)
        self.assertEqual(pre, audiofile.masked_middle_length)
        audiofile.set_head_middle_tail(head_length=0.480, tail_length=1.240)
        self.assertNotEqual(pre, audiofile.masked_middle_length)
        pre = audiofile.masked_middle_length
        audiofile.set_head_middle_tail(head_length=10.000, tail_length=10.000)
        self.assertNotEqual(pre, audiofile.masked_middle_length)



if __name__ == '__main__':
    unittest.main()



