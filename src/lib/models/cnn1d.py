from typing import List, Dict
from tensorflow.keras.layers import (
    Input,
    Conv1D,
    MaxPooling1D,
    UpSampling1D,
    concatenate,
    Flatten,
    Dense,
    LeakyReLU,
    Embedding,
)
from tensorflow.keras.models import Model, load_model

import os

from tensorflow.keras.optimizers import SGD, Adam
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.regularizers import l1_l2
from tensorflow.keras.losses import categorical_crossentropy
from tensorflow.keras.preprocessing import timeseries_dataset_from_array
import tensorflow.keras.backend as K

import datetime

CONTEXT_SIZE = 33


def unet_1d(in_feature_size: int, out_feature_size: int, vocabulary_size: int):
    conv_settings = {
        "padding": "same",
        "activation": "relu", #LeakyReLU(alpha=0.05),
        "kernel_initializer": "he_normal",
        "kernel_regularizer": l1_l2(l1=1e-5, l2=1e-4),
    }

    input_words = Input((CONTEXT_SIZE), dtype=tf.int32)
    word_embedding = Embedding(vocabulary_size, 64)(input_words)

    input_features = Input((CONTEXT_SIZE, in_feature_size))
    cc_input = concatenate([word_embedding, input_features], axis=2)
    conv1 = Conv1D(256, 5, **conv_settings)(cc_input)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    flat = Flatten()(conv1)
    output = Dense(out_feature_size, activation="softmax")(flat)

    return Model(inputs=[input_features, input_words], outputs=output)


class CNN1DTagger:
    def __init__(self, path: str, labels: List[str]):
        self.path = path
        self.labels = labels
        self.trained = False
        self.model = None
        self.model_first_layer = None

    def is_trained(self):
        return os.path.exists(self.path + "/saved_model.pb")

    def __call__(self, input):
        if self.model is None:
            self.model = load_model(self.path)

        def dsmap(a, b):

            a = tf.concat(
                [
                    K.repeat_elements(a[:1], CONTEXT_SIZE // 2, 0),
                    a,
                    K.repeat_elements(a[-1:], CONTEXT_SIZE // 2, 0),
                ],
                axis=0,
            )
            a = (
                tf.data.Dataset.from_tensor_slices(a)
                .window(CONTEXT_SIZE, drop_remainder=True)
                .flat_map(lambda x: x)
                .batch(CONTEXT_SIZE)
            )
            print(a)
            print("b?")
            b = tf.concat(
                [
                    K.repeat_elements(b[:1], CONTEXT_SIZE // 2, 0),
                    b,
                    K.repeat_elements(b[-1:], CONTEXT_SIZE // 2, 0),
                ],
                axis=0,
            )
            b = (
                tf.data.Dataset.from_tensor_slices(b)
                .window(CONTEXT_SIZE, drop_remainder=True)
                .flat_map(lambda x: x)
                .batch(CONTEXT_SIZE)
            )
            return tf.data.Dataset.zip((a, b))
            
        for item in input.flat_map(dsmap).batch(64):
            yield self.model.predict(item)

    def train(
        self,
        dataset: tf.data.Dataset,
        class_weights: Dict[int, float],
        n_features: int,
        MAX_VOCAB,
        from_latest: bool = False,
        name: str = "",
    ):
        # dataset: sequence of (None, n_features), (None, n_labels)
        print("Class weights:", list(class_weights.values()))

        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()), dtype="float32")

        def dsmap(x, y):
            a, b = x

            a = tf.concat(
                [
                    K.repeat_elements(a[:1], CONTEXT_SIZE // 2, 0),
                    a,
                    K.repeat_elements(a[-1:], CONTEXT_SIZE // 2, 0),
                ],
                axis=0,
            )
            a = (
                tf.data.Dataset.from_tensor_slices(a)
                .window(CONTEXT_SIZE, drop_remainder=True)
                .flat_map(lambda x: x)
                .batch(CONTEXT_SIZE)
            )
            b = tf.concat(
                [
                    K.repeat_elements(b[:1], CONTEXT_SIZE // 2, 0),
                    b,
                    K.repeat_elements(b[-1:], CONTEXT_SIZE // 2, 0),
                ],
                axis=0,
            )
            b = (
                tf.data.Dataset.from_tensor_slices(b)
                .window(CONTEXT_SIZE, drop_remainder=True)
                .flat_map(lambda x: x)
                .batch(CONTEXT_SIZE)
            )
            #y = y * class_weights_tensor
            y = tf.data.Dataset.from_tensor_slices(y)
            inputs = tf.data.Dataset.zip((a, b))
            
            return tf.data.Dataset.zip((inputs, y))

        dataset = dataset.flat_map(dsmap).shuffle(256).batch(64)

        print(iter(dataset).get_next())

        print("input dataset: ", dataset)

        if from_latest:
            print("Reloading from checkpoint.")
            self.model = load_model(self.path + "-chk")
        else:
            self.model = unet_1d(n_features, 1 + len(self.labels), MAX_VOCAB)
            self.model.summary()
            self.model.compile(
                optimizer=SGD(learning_rate=0.01, momentum=0.9, nesterov=True),#Adam(learning_rate=0.1),
                loss="categorical_crossentropy",
            )

        log_dir = f"{self.path}/logs/{name}/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

        self.model.fit(
            dataset,
            epochs=300,
            verbose=1,
            callbacks=[ModelCheckpoint(self.path + "-chk"), tensorboard_callback],
        )
        self.trained = True
        self.model.save(self.path)
