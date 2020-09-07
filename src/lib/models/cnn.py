from typing import List, Dict
from keras.layers import Input, Conv2D, MaxPooling2D, UpSampling2D, concatenate
from keras.models import Model, load_model

import os

from keras.optimizers import SGD
import tensorflow as tf
import tensorflow.keras.backend as K
from keras.callbacks import ModelCheckpoint

import datetime


def unet(in_feature_size: int, out_feature_size: int, pretrained_weights=None):
    input_size = (768, 768, in_feature_size)
    inputs = Input(input_size)
    conv1 = Conv2D(16, 3, activation="relu", padding="same", kernel_initializer="he_normal")(inputs)
    conv1 = Conv2D(32, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv1)
    pool1 = MaxPooling2D(pool_size=(3, 3))(conv1)
    conv2 = Conv2D(64, 3, activation="relu", padding="same", kernel_initializer="he_normal")(pool1)
    conv2 = Conv2D(64, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv2)
    pool2 = MaxPooling2D(pool_size=(4, 4))(conv2)
    conv3 = Conv2D(128, 3, activation="relu", padding="same", kernel_initializer="he_normal")(pool2)
    conv3 = Conv2D(128, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv3)
    pool3 = MaxPooling2D(pool_size=(4, 4))(conv3)

    conv5 = Conv2D(256, 3, activation="relu", padding="same", kernel_initializer="he_normal")(pool3)
    conv5 = Conv2D(256, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv5)

    up7 = Conv2D(128, 2, activation="relu", padding="same", kernel_initializer="he_normal")(
        UpSampling2D(size=(4, 4))(conv5)
    )
    merge7 = concatenate([conv3, up7], axis=3)
    conv7 = Conv2D(128, 3, activation="relu", padding="same", kernel_initializer="he_normal")(
        merge7
    )
    conv7 = Conv2D(128, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv7)

    up8 = Conv2D(64, 2, activation="relu", padding="same", kernel_initializer="he_normal")(
        UpSampling2D(size=(4, 4))(conv7)
    )
    merge8 = concatenate([conv2, up8], axis=3)
    conv8 = Conv2D(64, 3, activation="relu", padding="same", kernel_initializer="he_normal")(merge8)
    conv8 = Conv2D(64, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv8)

    up9 = Conv2D(32, 2, activation="relu", padding="same", kernel_initializer="he_normal")(
        UpSampling2D(size=(3, 3))(conv8)
    )
    merge9 = concatenate([conv1, up9], axis=3)
    conv9 = Conv2D(32, 3, activation="relu", padding="same", kernel_initializer="he_normal")(merge9)
    conv9 = Conv2D(16, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv9)
    conv9 = Conv2D(16, 3, activation="relu", padding="same", kernel_initializer="he_normal")(conv9)
    # TODO: pixel-wise softmax ?
    conv10 = Conv2D(out_feature_size, 1, activation="softmax")(conv9)

    return Model(inputs=inputs, outputs=conv10)


class CNNTagger:
    def __init__(self, path: str, labels: List[str]):
        self.path = path
        self.labels = labels
        self.trained = False
        self.model = None
        self.model_first_layer = None

    def is_trained(self):
        return os.path.exists(self.path+"/saved_model.pb")

    def __call__(self, input):
        if self.model is None:
            self.model = load_model(self.path)

        print("Call on ", input.shape)
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
        validation_dataset: tf.data.Dataset,
        class_weights: Dict[int, float],
        n_features: int,
        from_latest: bool = False,
        name: str = "",
    ):
        print("Class weights: ", list(class_weights.values()))

        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()), dtype="float32")

        dataset = dataset.map(lambda x, y: (x, y * class_weights_tensor)).prefetch(2)
        
        if from_latest:
            print("Reloading from checkpoint.")
            self.model = load_model(self.path + "-chk")
        else:
            self.model = unet(n_features, 1 + len(self.labels))
            self.model.compile(
                optimizer=SGD(learning_rate=0.01, momentum=0.9, nesterov=True),
                loss="categorical_crossentropy",
            )

        log_dir = f"{self.path}/logs/{name}/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

        self.model.fit(
            dataset,
            epochs=300,
            verbose=1,
            callbacks=[ModelCheckpoint(self.path + "-chk"), tensorboard_callback],
            validation_data=validation_dataset,
        )
        self.trained = True
        self.model.save(self.path)
