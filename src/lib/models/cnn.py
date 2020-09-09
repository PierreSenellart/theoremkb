from typing import List, Dict
from keras.layers import Input, Conv2D, MaxPooling2D, UpSampling2D, concatenate, LeakyReLU
from keras.models import Model, load_model

import os

from keras.optimizers import SGD, Adam
import tensorflow as tf
import tensorflow.keras.backend as K
from keras.callbacks import ModelCheckpoint
from keras.regularizers import l1_l2
from keras.losses import categorical_crossentropy

import datetime


def unet(in_feature_size: int, out_feature_size: int):
    conv_settings = {
        "padding": "same",
        "activation": LeakyReLU(alpha=0.05),
        "kernel_initializer": "he_normal",
        "kernel_regularizer": l1_l2(l1=1e-5, l2=1e-4)
    }

    input_size = (512, 512, in_feature_size)
    inputs = Input(input_size)
    conv1 = Conv2D(32, 3, **conv_settings)(inputs)
    conv1 = Conv2D(32, 3, **conv_settings)(conv1)
    pool1 = MaxPooling2D(pool_size=(2, 2))(conv1)
    conv2 = Conv2D(64, 3, **conv_settings)(pool1)
    conv2 = Conv2D(64, 3, **conv_settings)(conv2)
    pool2 = MaxPooling2D(pool_size=(4, 4))(conv2)
    conv3 = Conv2D(64, 3, **conv_settings)(pool2)
    conv3 = Conv2D(64, 3, **conv_settings)(conv3)
    pool3 = MaxPooling2D(pool_size=(4, 4))(conv3)

    conv5 = Conv2D(64, 3, **conv_settings)(pool3)
    conv5 = Conv2D(64, 3, **conv_settings)(conv5)

    up7 = Conv2D(64, 2, **conv_settings)(
        UpSampling2D(size=(4, 4))(conv5)
    )
    merge7 = concatenate([conv3, up7], axis=3)
    conv7 = Conv2D(64, 3, **conv_settings)(
        merge7
    )
    conv7 = Conv2D(64, 3, **conv_settings)(conv7)

    up8 = Conv2D(64, 2, **conv_settings)(
        UpSampling2D(size=(4, 4))(conv7)
    )
    merge8 = concatenate([conv2, up8], axis=3)
    conv8 = Conv2D(64, 3, **conv_settings)(merge8)
    conv8 = Conv2D(64, 3, **conv_settings)(conv8)

    up9 = Conv2D(32, 2, **conv_settings)(
        UpSampling2D(size=(2, 2))(conv8)
    )
    merge9 = concatenate([conv1, up9], axis=3)
    conv9 = Conv2D(32, 3, **conv_settings)(merge9)
    conv9 = Conv2D(16, 3, **conv_settings)(conv9)
    conv9 = Conv2D(16, 3, **conv_settings)(conv9)
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
        class_weights: Dict[int, float],
        n_features: int,
        from_latest: bool = False,
        name: str = "",
    ):
        print("Class weights: ", list(class_weights.values()))

        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()), dtype="float32")

        #dataset = dataset.map(lambda x, y: (x, y * class_weights_tensor))
        
        def custom_loss(y_true, y_pred):
            # (BATCH_SIZE, 512, 512, n_classes + 1)
            return categorical_crossentropy(y_true[:,:,:,1:],y_pred[:,:,:,1:])

        if from_latest:
            print("Reloading from checkpoint.")
            self.model = load_model(self.path + "-chk")
        else:
            self.model = unet(n_features, 1 + len(self.labels))
            self.model.summary()
            self.model.compile(
                optimizer=Adam(),#SGD(learning_rate=0.01, momentum=0.9, nesterov=True),
                loss=custom_loss,
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
