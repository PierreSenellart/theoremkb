# TheoremKB

TheoremKB is a research project and a corresponding collection of tools
to extract semantic information from (mathematical) research articles.
This is an ongoing project, with preliminary code available from this
repository.

<img src="assets/multi-t-3.png" width="300">

## Bibliography

For a high-level overview of the project, see [this set of slides](https://pierre.senellart.com/talks/sinfra-20191213.pdf).

For a more in-depth look at some of the aspects of the project interms of publications/internship reports (chronologically sorted), see:

- [Lucas Pluvinage](https://www.lortex.org/)'s Master Thesis on using
  style-based information for [Extracting scientific results from
  research articles](https://hal.inria.fr/hal-02956526).
- [Théo Delemazure](https://theo.delemazure.fr/)'s Master Thesis on
  first steps towards [A Knowledge Base of Mathematical Results](https://hal.inria.fr/hal-02940819).
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s paper on [Towards Extraction of Theorems and Proofs in Scholarly Articles](https://hal.archives-ouvertes.fr/hal-03293643) comparing various techniques
  evaluated individually at a single line level.
- [Yacine Brihmouche](https://www.linkedin.com/in/yacine-brihmouche/)'s Master's thesis on [TheoremKB: a knowledge base of
Mathematical results](https://inria.hal.science/hal-03897168) connecting proofs and theorems from different papers.
- [Antoine Gauquier](https://www.linkedin.com/in/antoine-gauquier-0a176b152/)'s Master's thesis on [Impact of the document class in the automatic extraction of mathematical environments in the scientific literature](https://hal.archives-ouvertes.fr/hal-03293643](https://inria.hal.science/hal-04220990/document))
- [Antoine Gauquier](https://www.linkedin.com/in/antoine-gauquier-0a176b152/)'s paper on [Automatically inferring the document class used in a scientific article](https://inria.hal.science/hal-04379415/file/Final_report__AI311_GAUQUIER_Antoine.pdf).
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s paper on [Multimodal Machine Learning for Extraction of Theorems and Proofs in the Scientific Literature](https://arxiv.org/abs/2307.09047).
- [Shufan JIANG](https://shufanjiang.github.io)'s paper on  [Extracting Definienda in Mathematical Scholarly Articles with Transformers](https://arxiv.org/pdf/2311.12448.pdf).
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s paper on  [First Steps in Building a Knowledge Base of Mathematical Results ](https://arxiv.org/pdf/2311.12448.pdf](https://aclanthology.org/2024.sdp-1.16/)).
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s PhD thesis on [Multimodal Extraction of Proofs and Theorems from the Scientific Literature](https://theses.hal.science/tel-04665528v1)
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s paper on [Modular Multimodal Machine Learning for Extraction
of Theorems and Proofs in Long Scientific Documents(Extended Version)](https://arxiv.org/pdf/2307.09047)
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/)'s System Demo: [TheoremView – Extracting and Visualizing Mathematical Results from Scientific Papers](https://www.youtube.com/watch?v=Q5piykv0vDI)
  
## Dataset

One of our dataset of reference is formed of 4400 articles extracted from
[arXiv](https://arXiv.org/), see [arXiv Bulk Data
Access](https://arxiv.org/help/bulk_data) for bulk access to the data.
For licensing reasons, this datasets cannot be reshared, but we provide
in [Dataset/links.csv](Dataset/links.csv) the reference to all articles of the
dataset.

## Tools

We are currently experimenting with the extraction of mathematical results 
based upon 3 approaches:

1. Using style-based information
2. Using Computer Vision based object detection to identify mathematical results [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1PwwU76yo0gzEl7hF7DhkU_wP-MNGlqx3?usp=sharing)

<img src="assets/res-tkb-data-416-multi.png" width="300"> <img src="assets/multi.png" width="300">
<img src="assets/tkb-data-416-unified.png" width="300"> 


3. Using NLP based techniques such as transformers and LSTM networks for sequence prediction

## Installation

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


## Participants and contact

The project is led by [Pierre Senellart](https://pierre.senellart.com/),
within the [Valda](https://team.inria.fr/valda/) research group joint
between [ENS, PSL University](https://www.ens.psl.eu/),
[CNRS](http://www.cnrs.fr/) and [Inria](https://www.inria.fr/).

The project has also involved:

- [Théo Delemazure](https://theo.delemazure.fr/), Master's student, ENS
- [Lucas Pluvinage](https://www.lortex.org/), Master's student, ENS
- [Shrey Mishra](https://www.linkedin.com/in/shreymishramv96/), PhD candidate, ENS
- [Antoine Gauquier](https://www.linkedin.com/in/antoine-gauquier-0a176b152/), PhD candidate, ENS
- [Shufan JIANG](https://shufanjiang.github.io), Postdoctoral Candidate, ENS

Contact Pierre Senellart for further information.

## Citation

If you find our work useful and would like to cite it, please use the following BibTeX entry:

```bibtex
@inproceedings{mishra-etal-2024-first,
    title = "First Steps in Building a Knowledge Base of Mathematical Results",
    author = "Mishra, Shrey  and
      Brihmouche, Yacine  and
      Delemazure, Th{\'e}o  and
      Gauquier, Antoine  and
      Senellart, Pierre",
    editor = "Ghosal, Tirthankar  and
      Singh, Amanpreet  and
      Waard, Anita  and
      Mayr, Philipp  and
      Naik, Aakanksha  and
      Weller, Orion  and
      Lee, Yoonjoo  and
      Shen, Shannon  and
      Qin, Yanxia",
    booktitle = "Proceedings of the Fourth Workshop on Scholarly Document Processing (SDP 2024)",
    month = aug,
    year = "2024",
    address = "Bangkok, Thailand",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2024.sdp-1.16",
    pages = "165--174",
    abstract = "This paper explores the initial steps towards extracting information about theorems and proofs from scholarly documents to build a knowledge base of interlinked results. Specifically, we consider two main tasks: extracting results and their proofs from the PDFs of scientific articles and establishing which results are used in the proofs of others across the scientific literature. We discuss the problem statement, methodologies, and preliminary findings employed in both phases of our approach, highlighting the challenges faced.",
}
```

```bibtex
@inproceedings{DBLP:conf/doceng/MishraPS21,
  author       = {Shrey Mishra and
                  Lucas Pluvinage and
                  Pierre Senellart},
  editor       = {Patrick Healy and
                  Mihai Bilauca and
                  Alexandra Bonnici},
  title        = {Towards extraction of theorems and proofs in scholarly articles},
  booktitle    = {DocEng '21: {ACM} Symposium on Document Engineering 2021, Limerick,
                  Ireland, August 24-27, 2021},
  pages        = {25:1--25:4},
  publisher    = {{ACM}},
  year         = {2021},
  url          = {https://doi.org/10.1145/3469096.3475059},
  doi          = {10.1145/3469096.3475059},
  timestamp    = {Fri, 20 Aug 2021 15:13:08 +0200},
  biburl       = {https://dblp.org/rec/conf/doceng/MishraPS21.bib},
  bibsource    = {dblp computer science bibliography, https://dblp.org}
}
```

## License
All code is provided as open-source software under the MIT License. See [LICENSE](LICENSE).

## Funding

This work has been funded by the French government under
management of [Agence Nationale de la Recherche](https://anr.fr/) as part of the
“Investissements d’avenir” program, reference [ANR-19-P3IA-0001](https://anr.fr/ProjetIA-19-P3IA-0001)
([PRAIRIE 3IA Institute](https://prairie-institute.fr/)).

Pierre Senellart's work is also supported by his secondment to [Institut
Universitaire de France](https://www.iufrance.fr/).
