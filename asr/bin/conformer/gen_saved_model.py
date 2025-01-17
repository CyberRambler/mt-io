import os
import fire

from asr.utils import env_util

logger = env_util.setup_environment()
import tensorflow as tf

DEFAULT_YAML = os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.yml")


from asr.configs.config import Config
from asr.helpers import featurizer_helpers
from asr.models.transducer.conformer import Conformer


def main(
    config: str = DEFAULT_YAML,
    h5: str = None,
    sentence_piece: bool = False,
    subwords: bool = False,
    output_dir: str = None,
):
    assert h5 and output_dir
    config = Config(config)
    tf.random.set_seed(0)
    tf.keras.backend.clear_session()

    speech_featurizer, text_featurizer = featurizer_helpers.prepare_featurizers(
        config=config,
        subwords=subwords,
        sentence_piece=sentence_piece,
    )

    # build model
    conformer = Conformer(**config.model_config, vocabulary_size=text_featurizer.num_classes)
    conformer.make(speech_featurizer.shape)
    conformer.load_weights(h5, by_name=True)
    conformer.summary(line_length=100)
    conformer.add_featurizers(speech_featurizer, text_featurizer)

    class ConformerModule(tf.Module):
        def __init__(self, model: Conformer, name=None):
            super().__init__(name=name)
            self.model = model
            self.num_rnns = config.model_config["prediction_num_rnns"]
            self.rnn_units = config.model_config["prediction_rnn_units"]
            self.rnn_nstates = 2 if config.model_config["prediction_rnn_type"] == "lstm" else 1

        @tf.function(input_signature=[tf.TensorSpec(shape=[None], dtype=tf.float32)])
        def pred(self, signal):
            predicted = tf.constant(0, dtype=tf.int32)
            states = tf.zeros([self.num_rnns, self.rnn_nstates, 1, self.rnn_units], dtype=tf.float32)
            features = self.model.speech_featurizer.tf_extract(signal)
            encoded = self.model.encoder_inference(features)
            hypothesis = self.model._perform_greedy(encoded, tf.shape(encoded)[0], predicted, states, tflite=False)
            transcript = self.model.text_featurizer.indices2upoints(hypothesis.prediction)
            return transcript

    module = ConformerModule(model=conformer)
    tf.saved_model.save(module, export_dir=output_dir, signatures=module.pred.get_concrete_function())


if __name__ == "__main__":
    fire.Fire(main)
