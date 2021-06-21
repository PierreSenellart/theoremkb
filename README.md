# TheoremKB

Collection of tools to extract semantic information from (mathematical) research articles.

## TKB

TKB is the project located in `src/` consisting of a command line interface and a web interface to
manage PDF documents, annotate them and train machine learning models to perform information extraction.  

Extraction of mathematical results is based upon 3 approaches:

1. Using the styling based information
2. Using Computer Vision based object detection to identify mathematical results
3. Using NLP based techniques such as transformers and LSTM networks

### Installation

For Computer Vision and NLP based extractions (Please follow the jupyter notebooks) in the directory 
`/Computer_Vision` and `NLP`

The project makes use of Python for the back-end and Typescript/React for the frontend. 
It's recommended to use virtual environments for Python such as `anaconda`. For the front-end, 
 a Nodejs package manager is needed, such as `yarn` (but `npm` is also possible). 

* library dependencies: `conda install libspatialindex`.
* Python dependencies in `requirements.txt`. Use `pip install -r requirements.txt` to install.
* Web UI dependencies in `src/web/package.json`. Use `cd src/web/ && yarn install` to install.
* **Optional** Install Tensorflow and Keras to make use of Deep Learning-based models. 
* **Optional** Install `pdoc3` to build the docs. (https://pdoc3.github.io/pdoc/)

### Configuration

The configuration file is located in `src/lib/tkb.toml`. A default file is present in `src/lib/tkb.default.toml`. 
For now, there are three settings:
- **MANDATORY** `data_path`: directory in which tkb will store its metadata.
- `rebuild_features`: do not use feature cache and rebuild features each time. 
- `enable_tensorflow`: enable tensorflow-based models.

### Starting the project

Start the WebUI / REST endpoint:
- `make server`: host the API on `localhost:3001`
- `make webui`: host web interface on `localhost:3000`

Use the command line interface: `python src/cli.py`

## How-to ?

### Get help

CLI: `python src/cli.py help`
Dev docs: install `pdoc3` and build docs using `make docs` or `make docs-server` (live reload).

### Add documents in the database

The system takes for input PDF documents.
Using the CLI: `python src/cli.py register <directory>`

### Annotate documents

Using the web interface, it's possible to annotate the documents. There are three kind of annotations:
- segmentation: separates body from metadata such as header, footer, page numbers.
- header: identify header elements, for now it only allow to identify the title.
- results: scientific statements extraction, such as theorems, proofs, lemmas, definitions, etc.  

### Train models

* `python src/cli.py split <tag> -t <training_tag> -v <validation_tag>`: split dataset between training and validation.
* `python src/cli.py train <model> <tag> [model settings]`: perform training 

### Apply models

Using the CLI: `python src/cli.py apply <model> <tag>`: apply model on all documents, tagging the layer with given name.
Using the WebUI: it's possible to create a layer from a model.

## Project architecture

[project overview](assets/tkb_structure.png)

There are several components interacting in this framework:
- **TKB** (`src/lib/tkb.py`): entry point, declaring classes and extractors, and initializing the database.
- **Paper** (`src/lib/paper/`): the abstraction for a research article. 
- **AnnotationLayer** (`src/lib/annotations.py`): a set of bounding boxes.
- **Classes** (`src/lib/classes/`): describes each kind of annotation.
- **Features** (`src/lib/features/`): automatically computer hiearchical descriptors of PDF articles.
- **Extractors** (`src/lib/extractors/`): algorithms performing information extraction over PDFs. An extractor is a function taking a *Paper* for input and outputs an *AnnotationLayer*. An extractor may be trained if it implements the `TrainableExtractor` interface. 
- **Model** (`src/lib/models/`): machine learnings models that are powering the extractors. 

### Creating a new extractor. 

A new extractor can be implemented using either the `Extractor` or the `TrainableExtractor` interface (defined in `src/lib/extractors/__init__.py`). It acts as a black box so it accepts anything to perform the extraction. The only constraint is that it has to produce an *AnnotationLayer*. If the extractor is backed by a machine learning model it's a good idea to separate the model implementation in the `src/lib/models/` directory. 

The extractor needs to be registered in the `src/lib/tkb.py` entrypoint by updating the `__init__` method.  
