from ...comparison_level_library import (
    ArrayIntersectLevelBase,
    ColumnsReversedLevelBase,
    DamerauLevenshteinLevelBase,
    DatediffLevelBase,
    DistanceFunctionLevelBase,
    DistanceInKMLevelBase,
    ElseLevelBase,
    ExactMatchLevelBase,
    JaccardLevelBase,
    JaroLevelBase,
    JaroWinklerLevelBase,
    LevenshteinLevelBase,
    NullLevelBase,
    PercentageDifferenceLevelBase,
)
from ...comparison_library import (
    ArrayIntersectAtSizesBase,
    DamerauLevenshteinAtThresholdsBase,
    DatediffAtThresholdsBase,
    DistanceFunctionAtThresholdsBase,
    DistanceInKMAtThresholdsBase,
    ExactMatchBase,
    JaccardAtThresholdsBase,
    JaroAtThresholdsBase,
    JaroWinklerAtThresholdsBase,
    LevenshteinAtThresholdsBase,
)
from ...comparison_template_library import (
    DateComparisonBase,
    EmailComparisonBase,
    ForenameSurnameComparisonBase,
    NameComparisonBase,
    PostcodeComparisonBase,
)
from .snowflake_base import (
    SnowflakeBase,
)


# Class used to feed our comparison_library classes
class SnowflakeComparisonProperties(SnowflakeBase):
    @property
    def _exact_match_level(self):
        return exact_match_level

    @property
    def _null_level(self):
        return null_level

    @property
    def _else_level(self):
        return else_level

    @property
    def _datediff_level(self):
        return datediff_level

    @property
    def _array_intersect_level(self):
        return array_intersect_level

    @property
    def _columns_reversed_level(self):
        return columns_reversed_level

    @property
    def _distance_in_km_level(self):
        return distance_in_km_level

    @property
    def _distance_function_level(self):
        return distance_function_level

    @property
    def _levenshtein_level(self):
        return levenshtein_level

    @property
    def _damerau_levenshtein_level(self):
        return damerau_levenshtein_level

    @property
    def _jaro_level(self):
        return jaro_level

    @property
    def _jaro_winkler_level(self):
        return jaro_winkler_level

    @property
    def _jaccard_level(self):
        return jaccard_level


#########################
### COMPARISON LEVELS ###
#########################
class null_level(SnowflakeBase, NullLevelBase):
    pass


class exact_match_level(SnowflakeBase, ExactMatchLevelBase):
    pass


class else_level(SnowflakeBase, ElseLevelBase):
    pass


class columns_reversed_level(SnowflakeBase, ColumnsReversedLevelBase):
    pass


class distance_function_level(SnowflakeBase, DistanceFunctionLevelBase):
    pass


class levenshtein_level(SnowflakeBase, LevenshteinLevelBase):
    pass


class damerau_levenshtein_level(SnowflakeBase, DamerauLevenshteinLevelBase):
    pass


class jaro_level(SnowflakeBase, JaroLevelBase):
    pass


class jaro_winkler_level(SnowflakeBase, JaroWinklerLevelBase):
    pass


class jaccard_level(SnowflakeBase, JaccardLevelBase):
    pass


class array_intersect_level(SnowflakeBase, ArrayIntersectLevelBase):
    pass


class percentage_difference_level(SnowflakeBase, PercentageDifferenceLevelBase):
    pass


class distance_in_km_level(SnowflakeBase, DistanceInKMLevelBase):
    pass


class datediff_level(SnowflakeBase, DatediffLevelBase):
    pass


##########################
### COMPARISON LIBRARY ###
##########################
class exact_match(SnowflakeComparisonProperties, ExactMatchBase):
    pass


class distance_function_at_thresholds(
    SnowflakeComparisonProperties, DistanceFunctionAtThresholdsBase
):
    @property
    def _distance_level(self):
        return self._distance_function_level


class levenshtein_at_thresholds(SnowflakeComparisonProperties, LevenshteinAtThresholdsBase):
    @property
    def _distance_level(self):
        return self._levenshtein_level


class damerau_levenshtein_at_thresholds(
    SnowflakeComparisonProperties, DamerauLevenshteinAtThresholdsBase
):
    @property
    def _distance_level(self):
        return self._damerau_levenshtein_level


class jaro_at_thresholds(SnowflakeComparisonProperties, JaroAtThresholdsBase):
    @property
    def _distance_level(self):
        return self._jaro_level


class jaro_winkler_at_thresholds(
    SnowflakeComparisonProperties, JaroWinklerAtThresholdsBase
):
    @property
    def _distance_level(self):
        return self._jaro_winkler_level


class jaccard_at_thresholds(SnowflakeComparisonProperties, JaccardAtThresholdsBase):
    @property
    def _distance_level(self):
        return self._jaccard_level


class array_intersect_at_sizes(SnowflakeComparisonProperties, ArrayIntersectAtSizesBase):
    pass


class datediff_at_thresholds(SnowflakeComparisonProperties, DatediffAtThresholdsBase):
    pass


class distance_in_km_at_thresholds(
    SnowflakeComparisonProperties, DistanceInKMAtThresholdsBase
):
    pass


###################################
### COMPARISON TEMPLATE LIBRARY ###
###################################
class date_comparison(SnowflakeComparisonProperties, DateComparisonBase):
    @property
    def _distance_level(self):
        return distance_function_level


class name_comparison(SnowflakeComparisonProperties, NameComparisonBase):
    @property
    def _distance_level(self):
        return distance_function_level


class forename_surname_comparison(
    SnowflakeComparisonProperties, ForenameSurnameComparisonBase
):
    @property
    def _distance_level(self):
        return distance_function_level


class postcode_comparison(SnowflakeComparisonProperties, PostcodeComparisonBase):
    pass


class email_comparison(SnowflakeComparisonProperties, EmailComparisonBase):
    @property
    def _distance_level(self):
        return distance_function_level
