from __future__ import annotations

import logging
import math
import os
import re
from itertools import compress
import splink

import pandas as pd
import sqlglot
from numpy import nan
from snowflake.snowpark import DataFrame as snowpark_df
from snowflake.snowpark.types import DoubleType, StringType
from snowflake.snowpark.functions import col, lit
from snowflake.snowpark.context import get_active_session

from ..input_column import InputColumn
from ..linker import Linker
from ..misc import ensure_is_list, major_minor_version_greater_equal_than
from ..splink_dataframe import SplinkDataFrame
from ..term_frequencies import colname_to_tf_tablename
from .snowflake_helpers.custom_snowflake_dialect import Dialect

logger = logging.getLogger(__name__)

Dialect["customsnowflake"]


class SnowparkDataFrame(SplinkDataFrame):
    linker: SnowflakeLinker

    # def __init__(self, df_name, physical_name, linker):
    #    super().__init__(df_name, physical_name, linker)
    #    self.created_by_splink = True

    @property
    def columns(self) -> list[InputColumn]:
        # sql = f"select * from {self.physical_name} limit 1"
        # snowpark_df = self.linker.session.sql(sql)
        snowpark_df = self.linker.session.table(self.physical_name)

        col_strings = list(snowpark_df.columns)
        return [InputColumn(c, sql_dialect="snowflake") for c in col_strings]

    def validate(self):
        pass

    def as_record_dict(self, limit=None):
        snf_df = self.linker.session.table(self.physical_name)
        if limit:
            snf_df = snf_df.limit(limit)

        pd_df = snf_df.to_pandas()
        pd_df.columns = pd_df.columns.str.lower()
        return pd_df.to_dict(orient="records")

    def _drop_table_from_database(self, force_non_splink_table=False):
        # MS: For now, need to figure out how the set the splink_table flag to true when creating a table
        force_non_splink_table = True
        self._check_drop_table_created_by_splink(force_non_splink_table)
        self.linker._delete_table_from_database(self.physical_name)
        pass

    def as_pandas_dataframe(self, limit=None):
        snf_df = self.linker.session.table(self.physical_name)
        if limit:
            snf_df = snf_df.limit(limit)

        pd_df = snf_df.to_pandas()
        pd_df.columns = pd_df.columns.str.lower()
        # return self.linker.session.sql(sql).to_pandas()
        return pd_df

    def as_snowpark_dataframe(self):
        return self.linker.session.table(self.physical_name)

    def to_parquet(self, filepath, overwrite=False):
        # MS: REMOVE THIS FUNCTION SINCE WE DO NOT SAVE TO DISC!
        if not overwrite:
            self.check_file_exists(filepath)

        snowpark_df = self.as_snowpark_dataframe()
        snowpark_df.write.mode("overwrite").format("parquet").save(filepath)

    def to_csv(self, filepath, overwrite=False):
        # MS: REMOVE THIS FUNCTION SINCE WE DO NOT SAVE TO DISC!
        if not overwrite:
            self.check_file_exists(filepath)

        snowpark_df = self.as_snowpark_dataframe()
        snowpark_df.write.format("csv").option("header", "true").save(filepath)


class SnowflakeLinker(Linker):
    def __init__(
            self,
            input_table_or_tables,
            settings_dict: dict | str = None,
            set_up_basic_logging=True,
            input_table_aliases: str | list = None,
            session=None,
            validate_settings: bool = True,
            schema=None,
            database=None,
            force_install: bool = False,
    ):
        """Initialise the linker object, which manages the data linkage process and
                holds the data linkage model.

        Args:
            input_table_or_tables: Input data into the linkage model.  Either a
                single table or a list of tables.  Tables can be provided either as
                a Snowpark DataFrame, or as the name of the table as a string
            settings_dict (dict | Path, optional): A Splink settings dictionary, or
                 a path to a json defining a settingss dictionary or pre-trained model.
                  If not provided when the object is created, can later be added using
                `linker.load_settings()` or `linker.load_model()` Defaults to None.
            set_up_basic_logging (bool, optional): If true, sets ups up basic logging
                so that Splink sends messages at INFO level to stdout. Defaults to True.
            input_table_aliases (Union[str, list], optional): Labels assigned to
                input tables in Splink outputs.  If the names of the tables in the
                input database are long or unspecific, this argument can be used
                to attach more easily readable/interpretable names. Defaults to None.
            session: The Snowflake session. Required only if `input_table_or_tables` are
                provided as string - otherwise will be active session. MS: Do we need this or can we always pick active sessiion?
            validate_settings (bool, optional): When True, check your settings
                dictionary for any potential errors that may cause splink to fail.
            schema:
            database:
            force_install (bool, optional): By default additional functions are only installed if missing, setting this to True force a installation of functions

        """

        self._sql_dialect_ = "snowflake"

        input_tables = ensure_is_list(input_table_or_tables)

        input_aliases = self._ensure_aliases_populated_and_is_list(
            input_table_or_tables, input_table_aliases
        )

        accepted_df_dtypes = (pd.DataFrame, snowpark_df)

        self._get_active_session_if_not_provided(session)

        self._set_schema_and_database_if_not_provided(schema, database)

        self._drop_splink_cached_tables()

        super().__init__(
            input_tables,
            settings_dict,
            accepted_df_dtypes,
            set_up_basic_logging,
            input_table_aliases=input_aliases,
            validate_settings=validate_settings,
        )
        # Add missing functions
        if not self._functions_exists() or force_install:
            self._register_udfs_from_jar()
            self._create_log2_function()

    def _get_active_session_if_not_provided(self, session):
        self.session = session
        if session is None:
            self.session = get_active_session()
        if self.session is None:
            raise ValueError(
                "There is no active Snowflake session, you must pass in the snowflake session using the snowflake="
                " argument when you initialise the linker."
            )

    def _set_schema_and_database_if_not_provided(self, schema, database):
        self.schema = (
            schema if schema is not None else self.session.get_current_schema()
        )

        self.database = (
            database if database is not None else self.session.get_current_database()
        )

        # this defines the catalog.database location where splink's data outputs will
        # be stored.
        self.splink_data_store = ".".join(
            filter(lambda x: x, [self.database, self.schema])
        )

    def _drop_splink_cached_tables(self):
        # Clean up Splink cache that may exist from any previous splink session

        # if we change the default database and schema. This approach prevents side effects.
        splink_tables = self.session.sql(
            f"show tables like '__splink__%' in {self.splink_data_store}"

        )
        temp_tables = splink_tables.filter(col('"kind"') == 'TEMPORARY').collect()
        drop_tables = list(
            map(lambda x: x.name, filter(lambda x: x.kind == 'TEMPORARY', temp_tables))
        )
        # drop old temp tables
        # specifying a catalog and database doesn't work for temp tables.
        for x in drop_tables:
            self.session.sql(f"drop table IF EXISTS {x}")

    def _delete_table_from_database(self, name):
        drop_sql = f"DROP TABLE IF EXISTS {name};"
        self._run_sql_execution(drop_sql)

    def _functions_exists(self):
        udf_funcs = ['JACCARDSIMILARITY', 'JAROWINKLERSIMILARITY', 'LOG2']

        n_udfs = self.session.table(f"{self.database}.INFORMATION_SCHEMA.FUNCTIONS").filter(
            (col("FUNCTION_SCHEMA") == lit(self.schema.strip('"'))) & (col("FUNCTION_NAME").in_(udf_funcs))).count()

        if n_udfs == len(udf_funcs):
            return True
        else:
            return False

    def _register_udfs_from_jar(self):
        # MS: Needs to be rewritten to Snowpark...
        # register udf functions
        # will for loop through this list to register UDFs.
        # List is a tuple of structure (UDF Name, class path, spark return type)
        path = splink.__file__[0:-11] + "files/snowflake_jars/"

        # Create the stage
        sql = "CREATE OR REPLACE STAGE SFSIMILARITY COMMENT = 'Similarity and Distance functions for Snowflake'"

        _ = self._run_sql_execution(sql).collect()
        #udf_jars = ['commons-lang3-3.12.0.jar', 'commons-text-1.9.jar', 'sfsimilarity-1.0.jar']

        self.session.file.put(path + '*.jar', '@SFSimilarity/jars')

        sql = """
        CREATE or REPLACE FUNCTION JaccardSimilarity(left string, right string)
            RETURNS float
            LANGUAGE java
            IMPORTS = ('@SFSimilarity/jars/commons-text-1.9.jar', '@SFSimilarity/jars/sfsimilarity-1.0.jar')
            HANDLER = 'com.snowflake.similarity.Similarity.jaccardSimilarity'
            COMMENT = 'Measures the Jaccard similarity (aka Jaccard index) of two sets of character sequence. Jaccard similarity is the size of the intersection divided by the size of the union of the two sets.'
        """

        _ = self._run_sql_execution(sql).collect()

        sql = """
        CREATE or REPLACE FUNCTION JaroWinklerSimilarity(left string, right string)
            RETURNS float
            LANGUAGE java
            IMPORTS = ('@SFSimilarity/jars/commons-text-1.9.jar', '@SFSimilarity/jars/commons-lang3-3.12.0.jar', '@SFSimilarity/jars/sfsimilarity-1.0.jar')
            HANDLER = 'com.snowflake.similarity.Similarity.jaroWinklerSimilarity'
            COMMENT = 'A similarity algorithm indicating the percentage of matched characters between two character sequences. 
            The Jaro measure is the weighted sum of percentage of matched characters from each file and transposed characters. Winkler increased this measure for matching initial characters.'
        """

        _ = self._run_sql_execution(sql).collect()

    def _create_log2_function(self):
        sql = """
        CREATE OR REPLACE FUNCTION log2(n double)
            RETURNS double AS $$
            log(2.0, n::double)::double
            $$
        """
        self._run_sql_execution(sql).collect()

    def _table_to_splink_dataframe(self, templated_name, physical_name):
        return SnowparkDataFrame(templated_name, physical_name, self)

    def _execute_sql_against_backend(self, sql: str, templated_name: str, physical_name: str):

        sql = sqlglot.transpile(sql, read="snowflake", write="customsnowflake", pretty=True)[0]
        snowpark_df = self._log_and_run_sql_execution(sql, templated_name, physical_name)
        snowpark_df.write.mode("overwrite").save_as_table(physical_name, table_type="temporary")

        output_df = self._table_to_splink_dataframe(templated_name, physical_name)
        return output_df

    def _run_sql_execution(self, final_sql, templated_name: str = None, physical_name: str = None):
        return self.session.sql(final_sql)

    @property
    def _infinity_expression(self):
        return "'infinity'"

    def register_table(self, input, table_name, overwrite=False):
        """
        Register a table to your backend database, to be used in one of the
        splink methods, or simply to allow querying.

        Tables can be of type: dictionary, record level dictionary,
        pandas dataframe, pyarrow table and in the spark case, a spark df.

        Examples:
            >>> test_dict = {"a": [666,777,888],"b": [4,5,6]}
            >>> linker.register_table(test_dict, "test_dict")
            >>> linker.query_sql("select * from test_dict")

        Args:
            input: The data you wish to register. This can be either a dictionary,
                pandas dataframe, pyarrow table or a snowpark dataframe.
            table_name (str): The name you wish to assign to the table.
            overwrite (bool): Overwrite the table in the underlying database if it
                exists

        Returns:
            SplinkDataFrame: An abstraction representing the table created by the sql
                pipeline
        """

        # If the user has provided a table name, return it as a SplinkDataframe
        if isinstance(input, str):
            return self._table_to_splink_dataframe(table_name, input)

        # Check if table name is already in use
        exists = self._table_exists_in_database(table_name)
        if exists:
            if not overwrite:
                raise ValueError(
                    f"Table '{table_name}' already exists in database. "
                    "Please use the 'overwrite' argument if you wish to overwrite"
                )

        self._table_registration(input, table_name)
        return self._table_to_splink_dataframe(table_name, table_name)

    def _table_registration(self, input, table_name):
        if isinstance(input, dict):
            input = pd.DataFrame(input)
        elif isinstance(input, list):
            input = pd.DataFrame.from_records(input)

        if isinstance(input, pd.DataFrame):
            input = self._clean_pandas_df(input)
            input = self.session.createDataFrame(input)

        #input.createOrReplaceTempView(table_name)

        input.write.mode("overwrite").save_as_table(table_name, table_type="temporary")

    def _clean_pandas_df(self, df):
        return df.fillna(nan).replace([nan, pd.NA], [None, None])

    def _random_sample_sql(
            self, proportion, sample_size, seed=None, table=None, unique_id=None
    ):
        if proportion == 1.0:
            return ""
        percent = proportion * 100
        if seed:
            return f" ORDER BY rand({seed}) LIMIT {round(sample_size)}"
        else:
            return f" TABLESAMPLE ({percent}) "

    def _table_exists_in_database(self, table_name):
        query_result = self.session.sql(
            f"show tables like '{table_name}' in {self.splink_data_store}"
        ).collect()
        if len(query_result) > 1:
            # this clause accounts for temp tables which can have the same name as
            # persistent table without issue
            if (
                    len({x.name for x in query_result}) == 1
            ) and (  # table names are the same
                    len({x.kind == 'TEMPORARY' for x in query_result}) == 2
            ):  # if tmp then kind == TEMPORARY
                return True
            else:
                raise ValueError(
                    f"Table name {table_name} not unique. Does it contain a wild card?"
                )
        elif len(query_result) == 1:
            return True
        elif len(query_result) == 0:
            return False

    def register_tf_table(self, df, col_name, overwrite=False):
        self.register_table(df, colname_to_tf_tablename(col_name), overwrite)
