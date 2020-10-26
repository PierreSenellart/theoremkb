"""Convolutional neural network"""
import os, pickle, datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

import tensorflow as tf
from keras.models import Model, load_model
from keras.optimizers import SGD
from keras.callbacks import ModelCheckpoint
from keras.layers import (
    Input,
    Conv2D,
    MaxPooling2D,
    UpSampling2D,
    concatenate,
    LeakyReLU,
    Embedding,
)


gpus = tf.config.experimental.list_physical_devices("GPU")
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)


@dataclass
class CNNParams:
    render_size: int
    word_embeddings: int
    balance_classes: int
    n_features: int


def unet(
    in_feature_size: int, render_size: int, out_feature_size: int, vocabulary_size: int
):
    conv_settings = {
        "padding": "same",
        "activation": LeakyReLU(alpha=0.05),
        "kernel_initializer": "he_normal",
        # "kernel_regularizer": l1_l2(l1=1e-5, l2=1e-4)
    }
    input_img = Input((render_size, render_size, in_feature_size))

    if vocabulary_size > 0:
        input_words = Input((render_size, render_size), dtype=tf.int32)

        word_embedding = Embedding(vocabulary_size, 64)(input_words)
        cc_input = concatenate([word_embedding, input_img], axis=3)
    else:
        cc_input = input_img

    conv1 = Conv2D(64, 3, **conv_settings)(cc_input)
    conv1 = Conv2D(64, 3, **conv_settings)(conv1)
    conv1 = Conv2D(64, 3, **conv_settings)(conv1)
    pool1 = MaxPooling2D(pool_size=(4, 4))(conv1)

    conv2 = Conv2D(64, 3, **conv_settings)(pool1)
    conv2 = Conv2D(64, 3, **conv_settings)(conv2)
    pool2 = MaxPooling2D(pool_size=(4, 4))(conv2)

    conv3 = Conv2D(64, 3, **conv_settings)(pool2)
    conv3 = Conv2D(64, 3, **conv_settings)(conv3)
    pool3 = MaxPooling2D(pool_size=(4, 4))(conv3)

    conv5 = Conv2D(256, 3, **conv_settings)(pool3)
    conv5 = Conv2D(256, 3, **conv_settings)(conv5)
    conv5 = Conv2D(256, 3, **conv_settings)(conv5)

    up7 = Conv2D(256, 2, **conv_settings)(UpSampling2D(size=(4, 4))(conv5))
    merge7 = concatenate([conv3, up7], axis=3)
    conv7 = Conv2D(128, 3, **conv_settings)(merge7)
    conv7 = Conv2D(128, 3, **conv_settings)(conv7)
    conv7 = Conv2D(128, 3, **conv_settings)(conv7)

    up8 = Conv2D(256, 2, **conv_settings)(UpSampling2D(size=(4, 4))(conv7))
    merge8 = concatenate([conv2, up8], axis=3)
    conv8 = Conv2D(128, 3, **conv_settings)(merge8)
    conv8 = Conv2D(64, 3, **conv_settings)(conv8)
    conv8 = Conv2D(64, 3, **conv_settings)(conv8)

    up9 = Conv2D(64, 2, **conv_settings)(UpSampling2D(size=(4, 4))(conv8))
    merge9 = concatenate([conv1, up9], axis=3)
    conv9 = Conv2D(64, 3, **conv_settings)(merge9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    # TODO: pixel-wise softmax ?
    conv10 = Conv2D(out_feature_size, 1, activation="softmax")(conv9)

    if vocabulary_size > 0:
        return Model(inputs=[input_img, input_words], outputs=conv10)
    else:
        return Model(inputs=[input_img], outputs=conv10)


class CNNTagger:
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

    def description(self):
        return ""

    @property
    def params(self):
        if self._params is None:
            with open(self.params_path, "rb") as f:
                self._params = pickle.load(f)
        return self._params

    def __call__(self, input):
        return self.model.predict(input)

    def first_layer(self, input):
        model_first_layer = Model(
            inputs=self.model.inputs, outputs=self.model.layers[1].output
        )
        return model_first_layer.predict(input)

    def train(
        self,
        dataset: tf.data.Dataset,
        class_weights: Optional[Dict[int, float]],
        n_features: int,
        render_size: int,
        word_embeddings: int,
        from_latest: bool,
        name: str = "",
        **kwargs,
    ):
        if class_weights is not None:
            class_weights_tensor = tf.convert_to_tensor(
                list(class_weights.values()), dtype="float32"
            )
            dataset = dataset.map(lambda ipt, y: (ipt, y * class_weights_tensor))

        if from_latest:
            print(
                "Reloading from checkpoint. Checking that parameters haven't changed."
            )
            assert word_embeddings == self.params.word_embeddings
            assert render_size == self.params.render_size
            assert n_features == self.params.n_features

            self._model = load_model(self.path + "-chk")
        else:
            self._model = unet(
                n_features, render_size, 1 + len(self.labels), word_embeddings
            )
            self.model.summary()

        self.model.compile(
            optimizer=SGD(learning_rate=0.01, momentum=0.9, nesterov=True),
            loss="categorical_crossentropy",
        )

        with open(self.params_path, "wb") as f:
            self._params = CNNParams(
                render_size, word_embeddings, class_weights is not None, n_features
            )
            pickle.dump(self._params, f)

        log_dir = f"{self.path}/logs/{name}/" + datetime.datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
        tensorboard_callback = tf.keras.callbacks.TensorBoard(
            log_dir=log_dir, histogram_freq=1
        )

        self.model.fit(
            dataset,
            epochs=300,
            verbose=1,
            callbacks=[ModelCheckpoint(self.path + "-chk"), tensorboard_callback],
        )
        self.model.save(self.path)
