## Training data generation from Latex sources containing theorems

### Requirements

* Python packages: `filetype`, `tqdm`, `pandas`, `lxml`.
* [PDFAlto](https://github.com/kermitt2/pdfalto) available in `PATH`.

### Configuration

`config.py` is used to select location of source papers and target directories.

### Extraction

* Step 1: compilation of PDFs from Latex sources with extraction package: `extract_theorems.py`
* Step 2: conversion of PDFs with annotations to XML, using PDFAlto: `convert_to_xml.py`
* Step 3: feature extraction from XML files: `features.py`