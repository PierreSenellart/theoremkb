# TheoremKB

Collection of tools to extract semantic information from (mathematical) research articles.

<img src="assets/multi-t-3.png" width="300">

Extraction of mathematical results is based upon 3 approaches:

1. Using the styling based information
2. Using Computer Vision based object detection to identify mathematical results

<img src="assets/res-tkb-data-416-multi.png" width="300"> <img src="assets/tkb-data-416-unified.png" width="300"> 

3. Using NLP based techniques such as transformers and LSTM networks for sequence prediction

### Installation

For Computer Vision and NLP based extractions (Please follow the jupyter notebooks) in the directory 
`/Computer_Vision` and `NLP`

- Computer Vision notebooks

`/Computer_Vision/1.1 Computer vision preprocessing.ipynb` contains the preprocessing step and preparing the data into YOLO format
`/Computer_Vision/obj.data`, `/Computer_Vision/obj.names` , `/Computer_Vision/yolov4-obj.cfg` contains the image annotations directory path, class labels and configuration file of the YOLO network trained

- NLP notebooks

`/2.1 NLP text data preprocessing.ipynb` contains the preprocessing step and preparing of the xml files
`/transformers_tkb.ipynb` contains application of several AutoEncoding Transformers all base models (SciBert, Bert, DistilBert)
`/lstm_tkb_full.ipynb` contains LSTM implementation on Full data
`/lstm_trimmed.ipynb` contains LSTM implementation on imbalanced data

- Style based

See the instructions within the [Styling](Styling) directory.
