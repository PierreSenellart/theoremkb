from typing import List, Dict, Optional
import os, pickle, datetime
from dataclasses import dataclass
from tensorflow.keras.layers import (
    Input,
    Conv1D,
    MaxPooling1D,
    BatchNormalization,
    UpSampling1D,
    concatenate,
    Flatten,
    Dense,
    LeakyReLU,
    Embedding,
)
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.optimizers import SGD, Adam
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.regularizers import l1_l2


def net_1d(in_feature_size: int, context_size: int, out_feature_size: int, vocabulary_size: int):
    conv_settings = {
        "activation": "elu",
        "kernel_initializer": "he_normal",
        "kernel_regularizer": l1_l2(l1=1e-2, l2=1e-2),
    }

    input_features = Input((context_size, in_feature_size))

    if vocabulary_size > 0:
        input_words = Input((context_size), dtype=tf.int32)
        word_embedding = Embedding(vocabulary_size, 64, input_length=context_size)(input_words)

        cc_input = concatenate([word_embedding, input_features], axis=2)
        cc_input = Flatten()(cc_input)
    else:
        cc_input = input_features

    x = Dense(512, **conv_settings)(BatchNormalization()(cc_input))
    x = Dense(256, **conv_settings)(BatchNormalization()(x))
    x = Dense(256, **conv_settings)(BatchNormalization()(x))
    x = Dense(256, **conv_settings)(BatchNormalization()(x))
    x = Dense(128, **conv_settings)(BatchNormalization()(x))
    output = Dense(out_feature_size, activation="softmax")(BatchNormalization()(x))

    if vocabulary_size > 0:
        return Model(inputs=[input_features, input_words], outputs=output)
    else:
        return Model(inputs=input_features, outputs=output)


@dataclass
class CNNParams:
    context_size: int
    word_embeddings: int
    balance_classes: int
    n_features: int


def seq2seqofcontexts(sequence, context_size):
    # transforms a (L, ...) tensor into a (L, context_size, ...) dataset of contexts.
    sequence = tf.pad(
        sequence, [[context_size // 2, context_size // 2]] + [[0, 0]] * (len(sequence.shape) - 1)
    )
    return (
        tf.data.Dataset.from_tensor_slices(sequence)
        .window(context_size, shift=1, drop_remainder=True)
        .flat_map(lambda x: x)
        .batch(context_size)
    )


class CNN1DTagger:
    def __init__(self, path: str, labels: List[str]):
        self.path = path
        self.labels = labels

        self._model = None
        self._params = None

    def is_trained(self):
        return os.path.exists(self.path + "/saved_model.pb")

    @property
    def params_path(self):
        return f"{self.path}/params.pkl"

    @property
    def model(self):
        if self._model is None:
            self._model = load_model(self.path)
        return self._model

    @property
    def params(self):
        if self._params is None:
            with open(self.params_path, "rb") as f:
                self._params = pickle.load(f)
        return self._params

    def __call__(self, input):
        def dsmap(a, b):
            a = seq2seqofcontexts(a, self.params.context_size)
            b = seq2seqofcontexts(b, self.params.context_size)
            return tf.data.Dataset.zip((a, b))

        for item in input.flat_map(dsmap).batch(64):
            yield self.model.predict(item)

    def description(self):
        return ""

    def train(
        self,
        dataset: tf.data.Dataset,
        class_weights: Optional[Dict[int, float]],
        n_features: int,
        context_size: int,
        word_embeddings: int,
        n_epoch: int = 100,
        from_latest: bool = False,
        name: str = "",
        **kwargs,
    ):
        # dataset: sequence of (None, n_features), (None, n_labels)
        if class_weights is not None:
            class_weights_tensor = tf.convert_to_tensor(
                list(class_weights.values()), dtype="float32"
            )

        def dsmap(x, y):
            nonlocal word_embeddings, context_size

            if word_embeddings > 0:
                a = seq2seqofcontexts(x[0], context_size)
                b = seq2seqofcontexts(x[1], context_size)
                inputs = tf.data.Dataset.zip((a, b))
            else:
                inputs = seq2seqofcontexts(x, context_size)

            if class_weights is not None:
                y = y * class_weights_tensor
            y = tf.data.Dataset.from_tensor_slices(y)

            return tf.data.Dataset.zip((inputs, y))

        dataset = dataset.flat_map(dsmap).shuffle(4096).batch(2048).prefetch(3)

        if from_latest:
            print("Reloading from checkpoint. Checking that parameters haven't changed.")
            assert word_embeddings == self.params.word_embeddings
            assert context_size == self.params.context_size
            assert n_features == self.params.n_features

            self._model = load_model(self.path + "-chk")
        else:
            self._model = net_1d(n_features, context_size, 1 + len(self.labels), word_embeddings)
            self.model.summary()

        self.model.compile(
            optimizer=SGD(learning_rate=0.01, momentum=0.9, nesterov=True),
            loss="categorical_crossentropy",
        )

        with open(self.params_path, "wb") as f:
            self._params = CNNParams(
                context_size, word_embeddings, class_weights is not None, n_features
            )
            pickle.dump(self._params, f)

        log_dir = f"{self.path}/logs/{name}/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

        self.model.fit(
            dataset,
            epochs=n_epoch,
            verbose=1,
            callbacks=[ModelCheckpoint(self.path + "-chk"), tensorboard_callback],
        )
        self.model.save(self.path)
