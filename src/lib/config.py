import os, sys
from sqlalchemy import create_engine

from dynaconf import Dynaconf, Validator, validator, LazySettings


is_bool = lambda x: type(x) == bool

tkb_file = os.path.join(os.path.dirname(__file__),"tkb.toml")
tkb_default_file = os.path.join(os.path.dirname(__file__),"tkb.default.toml")

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


DATA_PATH  = settings.data_path
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
SQL_ENGINE = create_engine(f"sqlite:///{DATA_PATH}/tkb.sqlite")#, echo=True)

REBUILD_FEATURES = settings.REBUILD_FEATURES
ENABLE_TENSORFLOW = settings.enable_tensorflow

TKB_VERSION = "0"
