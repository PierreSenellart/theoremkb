from typing import List, Dict
from keras.layers import Input, Conv2D, MaxPooling2D, UpSampling2D, concatenate, LeakyReLU, Embedding
from keras.models import Model, load_model

import os

from keras.optimizers import SGD, Adam
import tensorflow as tf
import tensorflow.keras.backend as K
from keras.callbacks import ModelCheckpoint
from keras.regularizers import l1_l2
from keras.losses import categorical_crossentropy

import datetime


gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
  try:
    for gpu in gpus:
      tf.config.experimental.set_memory_growth(gpu, True)
  except RuntimeError as e:
    print(e)

def unet(in_feature_size: int, out_feature_size: int, vocabulary_size: int, enable_words: bool):
    conv_settings = {
        "padding": "same",
        "activation": LeakyReLU(alpha=0.05),
        "kernel_initializer": "he_normal",
        # "kernel_regularizer": l1_l2(l1=1e-5, l2=1e-4)
    }
    input_img = Input( (512, 512, in_feature_size))

    if enable_words:
        input_words = Input((512, 512), dtype=tf.int32)

        word_embedding = Embedding(vocabulary_size, 64)(input_words)
        cc_input = concatenate([word_embedding, input_img], axis=3)
    else:
        cc_input  = input_img

    conv1 = Conv2D(64, 3, **conv_settings)(cc_input)
    conv1 = Conv2D(64, 3, **conv_settings)(conv1)
    conv1 = Conv2D(64, 3, **conv_settings)(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)

    conv3 = Conv2D(64, 3, **conv_settings)(pool1)
    conv3 = Conv2D(64, 3, **conv_settings)(conv3)
    conv3 = Conv2D(64, 3, **conv_settings)(conv3)
    pool3 = MaxPooling2D(pool_size=(4, 4))(conv3)

    conv5 = Conv2D(128, 3, **conv_settings)(pool3)
    conv5 = Conv2D(128, 3, **conv_settings)(conv5)
    conv5 = Conv2D(128, 3, **conv_settings)(conv5)

    up7 = Conv2D(256, 2, **conv_settings)(UpSampling2D(size=(4, 4))(conv5))
    merge7 = concatenate([conv3, up7], axis=3)
    conv7 = Conv2D(128, 3, **conv_settings)(merge7)
    conv7 = Conv2D(128, 3, **conv_settings)(conv7)
    conv7 = Conv2D(128, 3, **conv_settings)(conv7)

    up9 = Conv2D(64, 2, **conv_settings)(UpSampling2D(size=(2, 2))(conv7))
    merge9 = concatenate([conv1, up9], axis=3)
    conv9 = Conv2D(64, 3, **conv_settings)(merge9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    conv9 = Conv2D(32, 3, **conv_settings)(conv9)
    # TODO: pixel-wise softmax ?
    conv10 = Conv2D(out_feature_size, 1, activation="softmax")(conv9)

    if enable_words:
        return Model(inputs=[input_img, input_words], outputs=conv10)
    else:
        return Model(inputs=[input_img], outputs=conv10)


class CNNTagger:
    def __init__(self, path: str, labels: List[str], ENABLE_WORDS: bool):
        self.path = path
        self.labels = labels
        self.trained = False
        self.model = None
        self.model_first_layer = None
        self.ENABLE_WORDS = ENABLE_WORDS

    def is_trained(self):
        return os.path.exists(self.path + "/saved_model.pb")

    def __call__(self, input):
        if self.model is None:
            self.model = load_model(self.path)
        return self.model.predict(input)

    def first_layer(self, input):
        if self.model is None:
            self.model = load_model(self.path)

        if self.model_first_layer is None:
            self.model_first_layer = Model(
                inputs=self.model.inputs, outputs=self.model.layers[1].output
            )

        return self.model_first_layer.predict(input)

    def train(
        self,
        dataset: tf.data.Dataset,
        class_weights: Dict[int, float],
        n_features: int,
        vocab_size: int,
        from_latest: bool = False,
        name: str = "",
    ):
        print("Class weights: ", list(class_weights.values()))

        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()), dtype="float32")

        dataset = dataset.map(lambda ipt, y: (ipt, y * class_weights_tensor))

        if from_latest:
            print("Reloading from checkpoint.")
            self.model = load_model(self.path + "-chk")
        else:
            self.model = unet(n_features, 1 + len(self.labels), vocab_size, self.ENABLE_WORDS)
            self.model.summary()
            self.model.compile(
                optimizer= SGD(learning_rate=0.01, momentum=0.9, nesterov=True),
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
