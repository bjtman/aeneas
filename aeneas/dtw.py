#!/usr/bin/env python
# coding=utf-8

"""
This module contains the implementation
of dynamic time warping (DTW) algorithms
to align two audio waves, represented by their
Mel-frequency cepstral coefficients (MFCCs).

The two classes provided by this module are:

1. :class:`aeneas.dtw.DTWAlgorithm`
   is an enumeration of the available algorithms.
2. :class:`aeneas.dtw.DTWAligner`
   is the actual feature extractor and aligner.

To align two wave files:

1. build an :class:`aeneas.dtw.DTWAligner` object
   passing the paths of the two wave files
   in the constructor, possibly with custom arguments
   to fine-tune the alignment;
2. call ``compute_path`` to compute the min cost path between
   the MFCC representations of the two wave files;
3. obtain the path between the two wave files by reading the
   ``computed_path`` property.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import numpy

from aeneas.audiofilemfcc import AudioFileMFCC
from aeneas.logger import Logger
from aeneas.runtimeconfiguration import RuntimeConfiguration
import aeneas.globalfunctions as gf

__author__ = "Alberto Pettarin"
__copyright__ = """
    Copyright 2012-2013, Alberto Pettarin (www.albertopettarin.it)
    Copyright 2013-2015, ReadBeyond Srl   (www.readbeyond.it)
    Copyright 2015-2016, Alberto Pettarin (www.albertopettarin.it)
    """
__license__ = "GNU AGPL v3"
__version__ = "1.5.0"
__email__ = "aeneas@readbeyond.it"
__status__ = "Production"

class DTWAlgorithm(object):
    """
    Enumeration of the DTW algorithms that can be used
    for the alignment of two audio waves.
    """

    EXACT = "exact"
    """ Classical (exact) DTW algorithm.

    This implementation has ``O(nm)`` time and space complexity,
    where ``n`` (respectively, ``m``) is the number of MFCCs
    of the real (respectively, synthesized) wave. """

    STRIPE = "stripe"
    """ DTW algorithm restricted to a stripe around the main diagonal
    (Sakoe-Chiba Band), for optimized memory usage and processing.

    Note that this is an heuristic approximation of the optimal (exact) path.

    This implementation has ``O(nd)`` time and space complexity,
    where ``n`` is the number of MFCCs of the real wave,
    and ``d`` is the number of MFCCs
    corresponding to the margin. """

    ALLOWED_VALUES = [EXACT, STRIPE]
    """ List of all the allowed values """



class DTWAlignerNotInitialized(Exception):
    """
    Error raised when trying to compute
    using an DTWAligner object whose real and/or synt waves
    are not initialized yet.
    """
    pass



class DTWAligner(object):
    """
    The audio wave aligner.

    The two waves, henceforth named real and synthesized,
    can be passed as ``AudioFileMFCC`` objects
    or as file paths.
    In the latter case, MFCCs will be extracted
    upon object creation, unless the corresponding
    ``AudioFileMFCC`` object has been passed as well.

    :param real_wave_mfcc: the real audio file
    :type  real_wave_mfcc: :class:`aeneas.audiofile.AudioFileMFCC`
    :param synt_wave_mfcc: the synthesized audio file
    :type  synt_wave_mfcc: :class:`aeneas.audiofile.AudioFileMFCC`
    :param string real_wave_path: the path to the real audio file
    :param string synt_wave_path: the path to the synthesized audio file
    :param rconf: a runtime configuration. Default: ``None``, meaning that
                  default settings will be used.
    :type  rconf: :class:`aeneas.runtimeconfiguration.RuntimeConfiguration`
    :param logger: the logger object
    :type  logger: :class:`aeneas.logger.Logger`

    :raise ValueError: if ``real_wave_mfcc`` or ``synt_wave_mfcc`` is not ``None``
                       but not of type ``AudioFileMFCC``
    :raise ValueError: if ``real_wave_path`` or ``synt_wave_path`` is not ``None``
                       but it cannot be read
    """

    TAG = u"DTWAligner"

    def __init__(
        self,
        real_wave_mfcc=None,
        synt_wave_mfcc=None,
        real_wave_path=None,
        synt_wave_path=None,
        rconf=None,
        logger=None
    ):
        if (real_wave_mfcc is not None) and (type(real_wave_mfcc) is not AudioFileMFCC):
            raise ValueError("Real wave mfcc must be None or of type AudioFileMFCC")
        if (synt_wave_mfcc is not None) and (type(synt_wave_mfcc) is not AudioFileMFCC):
            raise ValueError("Synt wave mfcc must be None or of type AudioFileMFCC")
        if (real_wave_path is not None) and (not gf.file_can_be_read(real_wave_path)):
            raise ValueError("Real wave cannot be read")
        if (synt_wave_path is not None) and (not gf.file_can_be_read(synt_wave_path)):
            raise ValueError("Synt wave cannot be read")
        if (rconf is not None) and (rconf["dtw_algorithm"] not in DTWAlgorithm.ALLOWED_VALUES):
            raise ValueError("Algorithm value not allowed")
        self.logger = logger if logger is not None else Logger()
        self.rconf = rconf if rconf is not None else RuntimeConfiguration()
        self.real_wave_mfcc = real_wave_mfcc
        self.synt_wave_mfcc = synt_wave_mfcc
        self.real_wave_path = real_wave_path
        self.synt_wave_path = synt_wave_path
        self.computed_path = None
        if (self.real_wave_mfcc is None) and (self.real_wave_path is not None):
            self.real_wave_mfcc = AudioFileMFCC(self.real_wave_path, rconf=self.rconf, logger=self.logger)
        if (self.synt_wave_mfcc is None) and (self.synt_wave_path is not None):
            self.synt_wave_mfcc = AudioFileMFCC(self.synt_wave_path, rconf=self.rconf, logger=self.logger)

    def _log(self, message, severity=Logger.DEBUG):
        """ Log """
        self.logger.log(message, severity, self.TAG)

    @property
    def computed_path(self):
        """
        Return the computed path between the two waves,
        as a tuple of two numpy 1D array of int indices: ::

        ([r_1, r_2, ..., r_k], [s_1, s_2, ..., s_k])

        where ``r_i`` are the indices in the real wave
        and ``s_i`` are the indices in the synthesized wave,
        and ``k`` is the length of the min cost path.

        :rtype: tuple (see above)
        """
        return self.__computed_path
    @computed_path.setter
    def computed_path(self, computed_path):
        self.__computed_path = computed_path

    def compute_accumulated_cost_matrix(self):
        """
        Compute the accumulated cost matrix,
        and return it.

        :rtype: numpy 2D array

        :raise RuntimeError: if both the C extension and
                             the pure Python code did not succeed.

        .. versionadded:: 1.2.0
        """
        dtw = self._setup_dtw()
        self._log(u"Returning accumulated cost matrix")
        return dtw.compute_accumulated_cost_matrix()

    def compute_path(self):
        """
        Compute the min cost path between the two waves,
        and store it internally.

        :raise RuntimeError: if both the C extension and
                             the pure Python code did not succeed.
        """
        dtw = self._setup_dtw()
        self._log(u"Computing path...")
        wave_path = dtw.compute_path()
        self._log(u"Computing path... done")
        self._log(u"Translating path to full wave indices...")
        real_indices = numpy.array([t[0] for t in wave_path])
        synt_indices = numpy.array([t[1] for t in wave_path])
        # TODO this depends whether we are masking or not
        real_indices += self.real_wave_mfcc.head_length
        self.computed_path = (real_indices, synt_indices)
        self._log(u"Translating path to full wave indices... done")

    def _setup_dtw(self):
        """
        Set the DTW object up.
        """
        # check we have the AudioFileMFCC objects
        if (self.real_wave_mfcc is None) or (self.real_wave_mfcc.middle_mfcc is None):
            raise DTWAlignerNotInitialized("The real wave MFCCs are not initialized")
        if (self.synt_wave_mfcc is None) or (self.synt_wave_mfcc.middle_mfcc is None):
            raise DTWAlignerNotInitialized("The synt wave MFCCs are not initialized")

        # setup
        algorithm = self.rconf["dtw_algorithm"]
        delta = int(2 * self.rconf["dtw_margin"] / self.rconf["mfcc_win_shift"])
        mfcc2_length = self.synt_wave_mfcc.middle_length
        self._log([u"Requested algorithm: '%s'", algorithm])
        self._log([u"delta = %d", delta])
        self._log([u"m = %d", mfcc2_length])
        # check if delta is >= length of synt wave
        if mfcc2_length <= delta:
            self._log(u"We have mfcc2_length <= delta")
            if (self.rconf["c_ext"]) and (gf.can_run_c_extension()):
                # the C code can be run: since it is still faster, do not run EXACT
                self._log(u"C extensions enabled and loaded: not selecting EXACT algorithm")
            else:
                self._log(u"Selecting EXACT algorithm")
                algorithm = DTWAlgorithm.EXACT

        # execute the selected algorithm
        if algorithm == DTWAlgorithm.EXACT:
            self._log(u"Computing with EXACT algo")
            dtw = DTWExact(
                self.real_wave_mfcc.middle_mfcc,
                self.synt_wave_mfcc.middle_mfcc,
                self.logger
            )
        else:
            self._log(u"Computing with STRIPE algo")
            dtw = DTWStripe(
                self.real_wave_mfcc.middle_mfcc,
                self.synt_wave_mfcc.middle_mfcc,
                delta,
                self.logger
            )
        return dtw




class DTWStripe(object):

    TAG = u"DTWStripe"

    def __init__(self, m1, m2, delta, logger=None):
        self.m1 = m1
        self.m2 = m2
        self.delta = delta
        self.logger = logger if logger is not None else Logger()

    def _log(self, message, severity=Logger.DEBUG):
        """ Log """
        self.logger.log(message, severity, self.TAG)

    def compute_accumulated_cost_matrix(self):
        return gf.run_c_extension_with_fallback(
            self._log,
            "cdtw",
            self._compute_acm_c_extension,
            self._compute_acm_pure_python,
            (),
            c_extension=True
        )

    def _compute_acm_c_extension(self):
        self._log(u"Computing acm using C extension...")
        try:
            self._log(u"Importing cdtw...")
            import aeneas.cdtw.cdtw
            self._log(u"Importing cdtw... done")
            # discard first MFCC component
            mfcc1 = self.m1[1:, :]
            mfcc2 = self.m2[1:, :]
            n = mfcc1.shape[1]
            m = mfcc2.shape[1]
            delta = self.delta
            self._log([u"n m delta: %d %d %d", n, m, delta])
            if delta > m:
                self._log(u"Limiting delta to m")
                delta = m
            cost_matrix, centers = aeneas.cdtw.cdtw.compute_cost_matrix_step(mfcc1, mfcc2, delta)
            accumulated_cost_matrix = aeneas.cdtw.cdtw.compute_accumulated_cost_matrix_step(cost_matrix, centers)
            self._log(u"Computing acm using C extension... done")
            return (True, accumulated_cost_matrix)
        except Exception as exc:
            self._log(u"Computing acm using C extension... failed")
            self._log(u"An unexpected exception occurred while running cdtw:", Logger.WARNING)
            self._log([u"%s", exc], Logger.WARNING)
        return (False, None)

    def _compute_acm_pure_python(self):
        self._log(u"Computing acm using pure Python code...")
        try:
            cost_matrix, centers = self._compute_cost_matrix()
            accumulated_cost_matrix = self._compute_accumulated_cost_matrix(cost_matrix, centers)
            self._log(u"Computing acm using pure Python code... done")
            return (True, accumulated_cost_matrix)
        except Exception as exc:
            self._log(u"Computing acm using pure Python code... failed")
            self._log(u"An unexpected exception occurred while running pure Python code:", Logger.WARNING)
            self._log([u"%s", exc], Logger.WARNING)
        return (False, None)

    def compute_path(self):
        return gf.run_c_extension_with_fallback(
            self._log,
            "cdtw",
            self._compute_path_c_extension,
            self._compute_path_pure_python,
            (),
            c_extension=True
        )

    def _compute_path_c_extension(self):
        self._log(u"Computing path using C extension...")
        try:
            self._log(u"Importing cdtw...")
            import aeneas.cdtw.cdtw
            self._log(u"Importing cdtw... done")
            # discard first MFCC component
            mfcc1 = self.m1[1:, :]
            mfcc2 = self.m2[1:, :]
            n = mfcc1.shape[1]
            m = mfcc2.shape[1]
            delta = self.delta
            self._log([u"n m delta: %d %d %d", n, m, delta])
            if delta > m:
                self._log(u"Limiting delta to m")
                delta = m
            best_path = aeneas.cdtw.cdtw.compute_best_path(
                mfcc1,
                mfcc2,
                delta
            )
            self._log(u"Computing path using C extension... done")
            return (True, best_path)
        except Exception as exc:
            self._log(u"Computing path using C extension... failed")
            self._log(u"An unexpected exception occurred while running cdtw:", Logger.WARNING)
            self._log([u"%s", exc], Logger.WARNING)
        return (False, None)

    def _compute_path_pure_python(self):
        self._log(u"Computing path using pure Python code...")
        try:
            cost_matrix, centers = self._compute_cost_matrix()
            accumulated_cost_matrix = self._compute_accumulated_cost_matrix(cost_matrix, centers)
            best_path = self._compute_best_path(accumulated_cost_matrix, centers)
            self._log(u"Computing path using pure Python code... done")
            return (True, best_path)
        except Exception as exc:
            self._log(u"Computing path using pure Python code... failed")
            self._log(u"An unexpected exception occurred while running cdtw:", Logger.WARNING)
            self._log([u"%s", exc], Logger.WARNING)
        return (False, None)

    def _compute_cost_matrix(self):
        self._log(u"Computing cost matrix...")
        # discard first MFCC component
        mfcc1 = self.m1[1:, :]
        mfcc2 = self.m2[1:, :]
        norm2_1 = numpy.sqrt(numpy.sum(mfcc1 ** 2, 0))
        norm2_2 = numpy.sqrt(numpy.sum(mfcc2 ** 2, 0))
        n = mfcc1.shape[1]
        m = mfcc2.shape[1]
        delta = self.delta
        self._log([u"n m delta: %d %d %d", n, m, delta])
        if delta > m:
            self._log(u"Limiting delta to m")
            delta = m
        cost_matrix = numpy.zeros((n, delta))
        centers = numpy.zeros(n)
        for i in range(n):
            # center j at row i
            center_j = (m * i) // n
            #self._log([u"Center at row %d is %d", i, center_j])
            range_start = max(0, center_j - (delta // 2))
            range_end = range_start + delta
            if range_end > m:
                range_end = m
                range_start = range_end - delta
            centers[i] = range_start
            #self._log([u"Range at row %d is %d %d", i, range_start, range_end])
            for j in range(range_start, range_end):
                tmp = mfcc1[:, i].transpose().dot(mfcc2[:, j])
                tmp /= norm2_1[i] * norm2_2[j]
                cost_matrix[i][j - range_start] = 1 - tmp
        self._log(u"Computing cost matrix... done")
        return (cost_matrix, centers)

    def _compute_accumulated_cost_matrix(self, cost_matrix, centers):
        # create accumulated cost matrix
        #
        # a[i][j] = c[i][j] + min(c[i-1][j-1], c[i-1][j], c[i][j-1])
        #
        return self._compute_acm_in_place(cost_matrix, centers)

    def _compute_acm_in_place(self, cost_matrix, centers):
        self._log(u"Computing the acm with the in-place algorithm...")
        n, delta = cost_matrix.shape
        self._log([u"n delta: %d %d", n, delta])
        current_row = numpy.copy(cost_matrix[0, :])
        #cost_matrix[0][0] = current_row[0]
        for j in range(1, delta):
            cost_matrix[0][j] = current_row[j] + cost_matrix[0][j-1]
        # fill table
        for i in range(1, n):
            current_row = numpy.copy(cost_matrix[i, :])
            offset = centers[i] - centers[i-1]
            for j in range(delta):
                cost0 = numpy.inf
                if (j+offset) < delta:
                    cost0 = cost_matrix[i-1][j+offset]
                cost1 = numpy.inf
                if j > 0:
                    cost1 = cost_matrix[i][j-1]
                cost2 = numpy.inf
                if ((j+offset-1) < delta) and ((j+offset-1) >= 0):
                    cost2 = cost_matrix[i-1][j+offset-1]
                cost_matrix[i][j] = current_row[j] + min(cost0, cost1, cost2)
        self._log(u"Computing the acm with the in-place algorithm... done")
        return cost_matrix

    # DISABLED
    #def _compute_acm_not_in_place(self, cost_matrix, centers):
    #    self._log(u"Computing the acm with the not-in-place algorithm...")
    #    acc_matrix = numpy.zeros(cost_matrix.shape)
    #    n, delta = acc_matrix.shape
    #    self._log([u"n delta: %d %d", n, delta])
    #    # first row
    #    acc_matrix[0][0] = cost_matrix[0][0]
    #    for j in range(1, delta):
    #        acc_matrix[0][j] = acc_matrix[0][j-1] + cost_matrix[0][j]
    #    # fill table
    #    for i in range(1, n):
    #        offset = centers[i] - centers[i-1]
    #        for j in range(delta):
    #            cost0 = numpy.inf
    #            if (j+offset) < delta:
    #                cost0 = acc_matrix[i-1][j+offset]
    #            cost1 = numpy.inf
    #            if j > 0:
    #                cost1 = acc_matrix[i][j-1]
    #            cost2 = numpy.inf
    #            if ((j+offset-1) < delta) and ((j+offset-1) >= 0):
    #                cost2 = acc_matrix[i-1][j+offset-1]
    #            acc_matrix[i][j] = cost_matrix[i][j] + min(cost0, cost1, cost2)
    #    self._log(u"Computing the acm with the not-in-place algorithm... done")
    #    return acc_matrix

    def _compute_best_path(self, acc_matrix, centers):
        self._log(u"Computing best path...")
        # get dimensions
        n, delta = acc_matrix.shape
        self._log([u"n delta: %d %d", n, delta])
        i = n - 1
        j = delta - 1 + centers[i]
        path = [(i, j)]
        # compute best (min cost) path
        while (i > 0) or (j > 0):
            if i == 0:
                path.append((0, j-1))
                j -= 1
            elif j == 0:
                path.append((i-1, 0))
                i -= 1
            else:
                offset = centers[i] - centers[i-1]
                r_j = j - centers[i]
                cost0 = numpy.inf
                if (r_j+offset) < delta:
                    cost0 = acc_matrix[i-1][r_j+offset]
                cost1 = numpy.inf
                if r_j > 0:
                    cost1 = acc_matrix[i][r_j-1]
                cost2 = numpy.inf
                if (r_j > 0) and ((r_j+offset-1) < delta) and ((r_j+offset-1) >= 0):
                    cost2 = acc_matrix[i-1][r_j+offset-1]
                costs = [
                    cost0,
                    cost1,
                    cost2
                ]
                moves = [
                    (i-1, j),
                    (i, j-1),
                    (i-1, j-1)
                ]
                min_cost = numpy.argmin(costs)
                #self._log([u"Selected min cost move %d", min_cost])
                min_move = moves[min_cost]
                path.append(min_move)
                i, j = min_move
        # reverse path and return
        path.reverse()
        self._log(u"Computing best path... done")
        return path



class DTWExact(object):

    TAG = u"DTWExact"

    def __init__(self, m1, m2, logger=None):
        self.m1 = m1
        self.m2 = m2
        self.logger = logger if logger is not None else Logger()

    def _log(self, message, severity=Logger.DEBUG):
        """ Log """
        self.logger.log(message, severity, self.TAG)

    def compute_accumulated_cost_matrix(self):
        self._log(u"Computing acm using pure Python code...")
        cost_matrix = self._compute_cost_matrix()
        accumulated_cost_matrix = self._compute_accumulated_cost_matrix(cost_matrix)
        self._log(u"Computing acm using pure Python code... done")
        return accumulated_cost_matrix

    def compute_path(self):
        self._log(u"Computing path using pure Python code...")
        accumulated_cost_matrix = self.compute_accumulated_cost_matrix()
        best_path = self._compute_best_path(accumulated_cost_matrix)
        self._log(u"Computing path using pure Python code... done")
        return best_path

    def _compute_cost_matrix(self):
        self._log(u"Computing cost matrix...")
        # discard first MFCC component
        mfcc1 = self.m1[1:, :]
        mfcc2 = self.m2[1:, :]
        norm2_1 = numpy.sqrt(numpy.sum(mfcc1 ** 2, 0))
        norm2_2 = numpy.sqrt(numpy.sum(mfcc2 ** 2, 0))
        # compute dot product
        self._log(u"Computing matrix with transpose+dot...")
        cost_matrix = mfcc1.transpose().dot(mfcc2)
        self._log(u"Computing matrix with transpose+dot... done")
        # normalize
        self._log(u"Normalizing matrix...")
        norm_matrix = numpy.outer(norm2_1, norm2_2)
        cost_matrix = 1 - (cost_matrix / norm_matrix)
        self._log(u"Normalizing matrix... done")
        self._log(u"Computing cost matrix... done")
        return cost_matrix

    def _compute_accumulated_cost_matrix(self, cost_matrix):
        # create accumulated cost matrix
        #
        # a[i][j] = c[i][j] + min(c[i-1][j-1], c[i-1][j], c[i][j-1])
        #
        return self._compute_acm_in_place(cost_matrix)

    def _compute_acm_in_place(self, cost_matrix):
        self._log(u"Computing the acm with the in-place algorithm...")
        n, m = cost_matrix.shape
        self._log([u"n m: %d %d", n, m])
        current_row = numpy.copy(cost_matrix[0, :])
        #cost_matrix[0][0] = current_row[0]
        for j in range(1, m):
            cost_matrix[0][j] = current_row[j] + cost_matrix[0][j-1]
        for i in range(1, n):
            current_row = numpy.copy(cost_matrix[i, :])
            cost_matrix[i][0] = cost_matrix[i-1][0] + current_row[0]
            for j in range(1, m):
                cost_matrix[i][j] = current_row[j] + min(
                    cost_matrix[i-1][j],
                    cost_matrix[i][j-1],
                    cost_matrix[i-1][j-1]
                )
        self._log(u"Computing the acm with the in-place algorithm... done")
        return cost_matrix

    # DISABLED
    #def _compute_acm_not_in_place(self, cost_matrix):
    #    self._log(u"Computing the acm with the not-in-place algorithm...")
    #    acc_matrix = numpy.zeros(cost_matrix.shape)
    #    n, m = acc_matrix.shape
    #    self._log([u"n m: %d %d", n, m])
    #    acc_matrix[0][0] = cost_matrix[0][0]
    #    for j in range(1, m):
    #        acc_matrix[0][j] = acc_matrix[0][j-1] + cost_matrix[0][j]
    #    for i in range(1, n):
    #        acc_matrix[i][0] = acc_matrix[i-1][0] + cost_matrix[i][0]
    #    for i in range(1, n):
    #        for j in range(1, m):
    #            acc_matrix[i][j] = cost_matrix[i][j] + min(
    #                acc_matrix[i-1][j],
    #                acc_matrix[i][j-1],
    #                acc_matrix[i-1][j-1]
    #            )
    #    self._log(u"Computing the acm with the not-in-place algorithm... done")
    #    return acc_matrix

    def _compute_best_path(self, acc_matrix):
        self._log(u"Computing best path...")
        # get dimensions
        n, m = acc_matrix.shape
        self._log([u"n m: %d %d", n, m])
        i = n - 1
        j = m - 1
        path = [(i, j)]
        # compute best (min cost) path
        while (i > 0) or (j > 0):
            if i == 0:
                path.append((0, j-1))
                j -= 1
            elif j == 0:
                path.append((i-1, 0))
                i -= 1
            else:
                costs = [
                    acc_matrix[i-1][j],
                    acc_matrix[i][j-1],
                    acc_matrix[i-1][j-1]
                ]
                moves = [
                    (i-1, j),
                    (i, j-1),
                    (i-1, j-1)
                ]
                min_cost = numpy.argmin(costs)
                #self._log([u"Selected min cost move %d", min_cost])
                min_move = moves[min_cost]
                path.append(min_move)
                i, j = min_move
        # reverse path and return
        path.reverse()
        self._log(u"Computing best path... done")
        return path



