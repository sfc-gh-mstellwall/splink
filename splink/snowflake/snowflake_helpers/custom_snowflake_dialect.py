from sqlglot import exp
from sqlglot.dialects import Dialect, Snowflake
from sqlglot.generator import Generator


def cast_as_double_edit(self, expression):
    """
    Forces floating point numbers to the double class in Snowflake,
    instead of casting them to decimals.
    This resolves the  issue where decimals only support precision
    up to 38 digits.
    """
    datatype = self.sql(expression, "to")
    if datatype.lower() == "double":
        if expression.this.key == "literal":
            return f"{expression.name}::DOUBLE"

    return expression.sql(dialect="snowflake")


class CustomSnowflake(Snowflake):
    class Parser(Snowflake.Parser):
        FUNCTIONS = {
            **Snowflake.Parser.FUNCTIONS,
        }

        FUNCTION_PARSERS = {
            **Snowflake.Parser.FUNCTION_PARSERS,
        }

    class Generator(Snowflake.Generator):
        TYPE_MAPPING = {
            **Snowflake.Generator.TYPE_MAPPING,
        }

        TRANSFORMS = {
            **Snowflake.Generator.TRANSFORMS,
            exp.Cast: cast_as_double_edit,
            exp.TryCast: cast_as_double_edit,
        }


Dialect["customsnowflake"]
