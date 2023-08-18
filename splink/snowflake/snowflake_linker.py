import warnings

from ..exceptions import SplinkDeprecated
from .linker import SnowparkDataFrame, SnowflakeLinker  # noqa: F401

warnings.warn(
    "Importing directly from `splink.snowflake.snowflake_linker` "
    "is deprecated and will be removed in Splink v4. "
    "Please import from `splink.snowflake.linker` going forward.",
    SplinkDeprecated,
    stacklevel=2,
)
