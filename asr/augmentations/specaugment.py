import tensorflow as tf
from asr.utils import shape_util


class FreqMasking(object):
    def __init__(self, num_masks: int = 1, mask_factor: float = 27):
        self.num_masks = num_masks
        self.mask_factor = mask_factor

    @tf.function
    def augment(self, spectrogram: tf.Tensor):
        """
        Masking the frequency channels (shape[1])
        Args:
            spectrogram: shape (T, num_feature_bins, V)
        Returns:
            frequency masked spectrogram
        """
        T, F, V = shape_util.shape_list(spectrogram, out_type=tf.int32)
        for _ in range(self.num_masks):
            f = tf.random.uniform([], minval=0, maxval=self.mask_factor, dtype=tf.int32)
            f = tf.minimum(f, F)
            f0 = tf.random.uniform([], minval=0, maxval=(F - f), dtype=tf.int32)
            mask = tf.concat(
                [
                    tf.ones([T, f0, V], dtype=spectrogram.dtype),
                    tf.zeros([T, f, V], dtype=spectrogram.dtype),
                    tf.ones([T, F - f0 - f, V], dtype=spectrogram.dtype),
                ],
                axis=1,
            )
            spectrogram = spectrogram * mask
        return spectrogram


class TimeMasking(object):
    def __init__(self, num_masks: int = 1, mask_factor: float = 100, p_upperbound: float = 1.0):
        self.num_masks = num_masks
        self.mask_factor = mask_factor
        self.p_upperbound = p_upperbound

    @tf.function
    def augment(self, spectrogram: tf.Tensor):
        """
        Masking the time channel (shape[0])
        Args:
            spectrogram: shape (T, num_feature_bins, V)
        Returns:
            frequency masked spectrogram
        """
        T, F, V = shape_util.shape_list(spectrogram, out_type=tf.int32)
        for _ in range(self.num_masks):
            t = tf.random.uniform([], minval=0, maxval=self.mask_factor, dtype=tf.int32)
            t = tf.minimum(t, tf.cast(tf.cast(T, dtype=tf.float32) * self.p_upperbound, dtype=tf.int32))
            t0 = tf.random.uniform([], minval=0, maxval=(T - t), dtype=tf.int32)
            mask = tf.concat(
                [
                    tf.ones([t0, F, V], dtype=spectrogram.dtype),
                    tf.zeros([t, F, V], dtype=spectrogram.dtype),
                    tf.ones([T - t0 - t, F, V], dtype=spectrogram.dtype),
                ],
                axis=0,
            )
            spectrogram = spectrogram * mask
        return spectrogram
