from typing import List, Dict
from keras.layers import Input, Conv2D, MaxPooling2D, UpSampling2D, Dropout, concatenate
from keras.models import Model, load_model
from keras.losses import CategoricalCrossentropy
import keras
from keras.optimizers import Adam
import tensorflow as tf
import tensorflow.keras.backend as K

print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))



def unet(in_feature_size: int, out_feature_size: int, pretrained_weights = None):
    input_size = (768, 768, in_feature_size)
    inputs = Input(input_size)
    conv1 = Conv2D(16, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(inputs)
    conv1 = Conv2D(32, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv1)
    pool1 = MaxPooling2D(pool_size=(3, 3))(conv1)
    conv2 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(pool1)
    conv2 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv2)
    pool2 = MaxPooling2D(pool_size=(4, 4))(conv2)
    conv3 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(pool2)
    conv3 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv3)
    pool3 = MaxPooling2D(pool_size=(4, 4))(conv3)

    conv5 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(pool3)
    conv5 = Conv2D(256, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv5)

    up7 = Conv2D(128, 2, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(UpSampling2D(size = (4,4))(conv5))
    merge7 = concatenate([conv3,up7], axis = 3)
    conv7 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(merge7)
    conv7 = Conv2D(128, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv7)

    up8 = Conv2D(64, 2, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(UpSampling2D(size = (4,4))(conv7))
    merge8 = concatenate([conv2,up8], axis = 3)
    conv8 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(merge8)
    conv8 = Conv2D(64, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv8)

    up9 = Conv2D(32, 2, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(UpSampling2D(size = (3,3))(conv8))
    merge9 = concatenate([conv1,up9], axis = 3)
    conv9 = Conv2D(32, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(merge9)
    conv9 = Conv2D(16, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv9)
    conv9 = Conv2D(16, 3, activation = 'relu', padding = 'same', kernel_initializer = 'he_normal')(conv9)
    # TODO: pixel-wise softmax ? 
    conv10 = Conv2D(out_feature_size, 1, activation = 'softmax')(conv9)

    return Model(inputs = inputs, outputs = conv10)



class CNNTagger:
    
    def __init__(self, path: str, labels: List[str]):
        self.path = path
        try: 
            self.trained = True
            self.model = load_model(path)
            # TODO: assert that len(labels) hasn't changed.
        except:
            self.trained = False
            self.model = unet(3, 1+len(labels))


    def __call__(self, input):
        print("Call on ", input.shape)
        return self.model.predict(input)

    def train(self, dataset: tf.data.Dataset, class_weights: Dict[int, float]):
        class_weights_tensor = tf.convert_to_tensor(list(class_weights.values()))
        
        dataset = dataset.map(lambda x,y: (x, y*class_weights_tensor))

        self.model.compile(optimizer=Adam(),loss='categorical_crossentropy')
        self.model.fit(dataset, epochs=10, verbose=1)
        self.trained = True
        self.model.save(self.path)



