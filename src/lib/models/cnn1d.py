from typing import List, Dict
from keras.layers import (
    Input,
    Conv1D,
    MaxPooling1D,
    UpSampling1D,
    concatenate,
    Flatten,
    Dense,
    LeakyReLU,
)
from keras.models import Model, load_model

import os

from keras.optimizers import SGD, Adam
import tensorflow as tf
import tensorflow.keras.backend as K
from keras.callbacks import ModelCheckpoint
from keras.regularizers import l1_l2
from keras.losses import categorical_crossentropy
from keras.preprocessing import timeseries_dataset_from_array
import keras.backend as K

import datetime

CONTEXT_SIZE = 33


def unet_1d(in_feature_size: int, out_feature_size: int):
    conv_settings = {
        "padding": "same",
        "activation": LeakyReLU(alpha=0.05),
        "kernel_initializer": "he_normal",
        "kernel_regularizer": l1_l2(l1=1e-5, l2=1e-4),
    }

    inputs = Input((CONTEXT_SIZE, in_feature_size))
    conv1 = Conv1D(256, 5, **conv_settings)(inputs)
    conv1 = Conv1D(128, 5, **conv_settings)(conv1)
    conv1 = Conv1D(64, 5, **conv_settings)(conv1)
    conv1 = Conv1D(64, 5, **conv_settings)(conv1)
    conv1 = Conv1D(64, 5, **conv_settings)(conv1)
    conv1 = Conv1D(64, 5, **conv_settings)(conv1)
    conv1 = Conv1D(32, 5, **conv_settings)(conv1)
    conv1 = Conv1D(16, 5, **conv_settings)(conv1)
    flat = Flatten()(conv1)
    output = Dense(out_feature_size)(flat)

    return Model(inputs=inputs, outputs=output)


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

        raise NotImplementedError

    def train(
        self,
        dataset: tf.data.Dataset,
        class_weights: Dict[int, float],
        n_features: int,
        from_latest: bool = False,
        name: str = "",
    ):
        # dataset: sequence of (None, n_features), (None, n_labels)
        print("Class weights:", list(class_weights.values()))

        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()), dtype="float32")

        def dsmap(x,y):
            x = K.concat([K.repeat_elements(x[:1], CONTEXT_SIZE//2, 0), x, K.repeat_elements(x[-1:], CONTEXT_SIZE//2, 0)], axis=0)
            x = timeseries_dataset_from_array(x, None, sequence_length=CONTEXT_SIZE)
            y = y * class_weights_tensor
            return x,y

        dataset = dataset.map(dsmap)

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
