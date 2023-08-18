from ...dialect_base import (
    DialectBase,
)


def size_array_intersect_sql(col_name_l, col_name_r):
    return f"array_size(array_intersection({col_name_l}, {col_name_r}))"


def datediff_sql(
    col_name_l,
    col_name_r,
    date_threshold,
    date_metric,
    cast_str=False,
    date_format=None,
):
    # DATEDIFF( <date_or_time_part>, <date_or_time_expr1>, <date_or_time_expr2> )

    if date_format is None:
        date_format = "yyyy-MM-dd"

    if cast_str:
        col_name_l = f"to_date({col_name_l}, '{date_format}')"
        col_name_r = f"to_date({col_name_r}, '{date_format}')"

    date_f = f"datediff('{date_metric}', {col_name_l}, {col_name_r})"
    return f"""
        {date_f} <= {date_threshold}
    """


def valid_date_sql(col_name, date_format=None):
    if date_format is None:
        date_format = "yyyy-MM-dd"

    return f"""
        to_date({col_name}, '{date_format}')
    """


def regex_extract_sql(col_name, regex):
    if "\\" in regex:
        raise SyntaxError(
            "Regular expressions containing “\\” (the python escape character) "
            "are not compatible with Splink’s Spark linker. "
            "Please consider using alternative syntax, "
            "for example replacing “\\d” with “[0-9]”."
        )
    else:
        return f"""
        regexp_substr({col_name}, '{regex}', 1)
    """


class SnowflakeBase(DialectBase):
    @property
    def _sql_dialect(self):
        return "snowflake"

    @property
    def _datediff_function(self):
        return datediff_sql

    @property
    def _valid_date_function(self):
        return valid_date_sql

    @property
    def _size_array_intersect_function(self):
        return size_array_intersect_sql

    @property
    def _regex_extract_function(self):
        return regex_extract_sql

    @property
    def _jaro_name(self):
        return "JACCARDSIMILARITY"

    @property
    def _damerau_levenshtein_name(self):
        return "DAMERAULEVENSHTEIN"

    @property
    def _jaro_winkler_name(self):
        return "JAROWINKLERSIMILARITY"
