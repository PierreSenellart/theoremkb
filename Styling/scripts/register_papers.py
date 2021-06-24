import sys,os
sys.path.append(os.path.dirname(__file__)+"/../src/")
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
from lib.tkb import TheoremKB
from lib.config import config

session_factory = sessionmaker(bind=config.SQL_ENGINE)
Session = scoped_session(session_factory)

tkb = TheoremKB()
session = Session()
added_papers = 0

path = "/users/valda/senellar/data/pdf"

for dirpath, _, filenames in tqdm(os.walk(path)):
    for paper_pdf in filenames:
        if not paper_pdf.lower().endswith(".pdf"):
            continue

        base_name = paper_pdf[:-4]
        pdf_dir = os.path.abspath(dirpath) + "/" + paper_pdf

        tkb.add_paper(session, base_name, pdf_dir)
        added_papers += 1

session.commit()
print("Added", added_papers, "papers!")
