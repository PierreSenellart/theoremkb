import sys,os
sys.path.append(os.path.dirname(__file__)+"/../src/")
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
from lib.tkb import TheoremKB
from lib.config import config
from lib.misc.namespaces import ALTO

session_factory = sessionmaker(bind=config.SQL_ENGINE)
Session = scoped_session(session_factory)

tkb = TheoremKB()
session = Session()

paper = tkb.list_papers(session)[0]
features = paper.get_features(f"{ALTO}TextBlock", standardize=False, add_context=False)
print("All columns:", features.columns)
print("Sample line:", features.iloc[0])
