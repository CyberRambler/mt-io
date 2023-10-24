import numpy as np
import matplotlib.pyplot as plt

import tensorflow as tf

from tts.inference import TFAutoModel
from tts.inference import AutoProcessor

processor = AutoProcessor.from_pretrained("tensorspeech/tts-tacotron2-ljspeech-en")

tacotron2 = TFAutoModel.from_pretrained("tensorspeech/tts-tacotron2-ljspeech-en")

tacotron2.setup_window(win_front=6, win_back=6)
tacotron2.setup_maximum_iterations(3000)

# # Save to Pb
# save model into pb and do inference. Note that signatures should be a tf.function with input_signatures.
tf.saved_model.save(tacotron2, "./test_saved", signatures=tacotron2.inference)

# # Load and Inference
tacotron2 = tf.saved_model.load("./test_saved")

input_text = "Unless you work on a ship, it's unlikely that you use the word boatswain in everyday conversation, so it's understandably a tricky one. The word - which refers to a petty officer in charge of hull maintenance is not pronounced boats-wain Rather, it's bo-sun to reflect the salty pronunciation of sailors, as The Free Dictionary explains."
input_ids = processor.text_to_sequence(input_text)

decoder_output, mel_outputs, stop_token_prediction, alignment_history = tacotron2.inference(
    tf.expand_dims(tf.convert_to_tensor(input_ids, dtype=tf.int32), 0),
    tf.convert_to_tensor([len(input_ids)], tf.int32),
    tf.convert_to_tensor([0], dtype=tf.int32)
)


def display_alignment(alignment_history):
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.set_title(f'Alignment steps')
    im = ax.imshow(
        alignment_history[0].numpy(),
        aspect='auto',
        origin='lower',
        interpolation='none')
    fig.colorbar(im, ax=ax)
    plt.xlabel('Decoder timestep')
    plt.ylabel('Encoder timestep')
    plt.tight_layout()
    plt.show()
    plt.close()


display_alignment(alignment_history)


def display_mel(mel_outputs):
    mel_outputs = tf.reshape(mel_outputs, [-1, 80]).numpy()
    fig = plt.figure(figsize=(10, 8))
    ax1 = fig.add_subplot(311)
    ax1.set_title(f'Predicted Mel-after-Spectrogram')
    im = ax1.imshow(np.rot90(mel_outputs), aspect='auto', interpolation='none')
    fig.colorbar(mappable=im, shrink=0.65, orientation='horizontal', ax=ax1)
    plt.show()
    plt.close()


display_mel(mel_outputs)


# # Let inference other input to check dynamic shape

input_text = "The Commission further recommends that the Secret Service coordinate its planning as closely as possible with all of the Federal agencies from which it receives information."
input_ids = processor.text_to_sequence(input_text)

decoder_output, mel_outputs, stop_token_prediction, alignment_history = tacotron2.inference(
    tf.expand_dims(tf.convert_to_tensor(input_ids, dtype=tf.int32), 0),
    tf.convert_to_tensor([len(input_ids)], tf.int32),
    tf.convert_to_tensor([0], dtype=tf.int32),
)

display_alignment(alignment_history)

display_mel(mel_outputs)