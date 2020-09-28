import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from dynaconf import Dynaconf, Validator, validator, LazySettings


is_bool = lambda x: type(x) == bool

tkb_file = os.path.join(os.path.dirname(__file__),"tkb.toml")
tkb_default_file = os.path.join(os.path.dirname(__file__),"tkb.default.toml")



class TKBConfig:
    def __init__(self):
        settings = Dynaconf(
            settings_files=[tkb_default_file, tkb_file],
            envvar_prefix="TKB",
            validators=[
                Validator("data_path", must_exist=True),
                Validator("rebuild_features", condition=is_bool, default=False),
                Validator("enable_tensorflow", condition=is_bool, default=True)
            ]
        )
        try:
            settings.validators.validate()
        except validator.ValidationError as e:
            print("Error in configuration:", e)
            exit(1)


        self.DATA_PATH  = settings.data_path
        self.REBUILD_FEATURES = settings.REBUILD_FEATURES
        self.ENABLE_TENSORFLOW = settings.enable_tensorflow

    @property
    def DATA_PATH(self):
        return self._DATA_PATH


    @DATA_PATH.setter
    def DATA_PATH(self, value):
        self._DATA_PATH = value
        if not os.path.exists(self._DATA_PATH):
            os.makedirs(self._DATA_PATH)
        self.SQL_ENGINE = create_engine(f"sqlite:///{self._DATA_PATH}/tkb.sqlite", echo=False)
        session_factory = sessionmaker(bind=self.SQL_ENGINE)
        self.Session = scoped_session(session_factory)



config = TKBConfig()