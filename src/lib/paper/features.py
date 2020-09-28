from __future__ import annotations

import pandas as pd
from lxml import etree as ET
from typing import Dict, Optional
from collections import Counter
from sklearn import preprocessing

from ..features import get_feature_extractors
from ..misc.namespaces import *
from ..misc import remove_prefix
from . import features

ALTO_HIERARCHY = [
    f"{ALTO}Page",
    f"{ALTO}PrintSpace",
    f"{ALTO}TextBlock",
    f"{ALTO}TextLine",
    f"{ALTO}String",
]


def _standardize(features: pd.DataFrame) -> pd.DataFrame:
    """Perform document-wide normalization on numeric features

    Args:
        features (List[dict]): list of features.

    Returns:
        List[dict]: list of normalized features.
    """
    numeric_df = features.select_dtypes(include="number")
    boolean_df = features.select_dtypes(include="bool")
    other_df = features.select_dtypes(exclude=["number", "bool"])

    normalized_numerics = preprocessing.scale(numeric_df)
    normalized_df = pd.DataFrame(normalized_numerics, columns=numeric_df.columns)
    boolean_df = 2 * boolean_df.astype("float") - 1

    return pd.concat([boolean_df, normalized_df, other_df], axis=1)


def build_features_dict(xml: ET.ElementTree) -> Dict[str, pd.DataFrame]:
    feature_extractors = get_feature_extractors(xml)

    features_by_node = {k: [] for k in feature_extractors.keys()}
    indices = {k: 0 for k in feature_extractors.keys()}

    ancestors = []

    def dfs(node: ET.Element):
        nonlocal ancestors, indices
        if node.tag in features_by_node:
            ancestors.append(node.tag)
            indices[node.tag] += 1

            features_by_node[node.tag].append(feature_extractors[node.tag].get(node))
            if len(ancestors) > 1:
                features_by_node[node.tag][-1][ancestors[-2]] = (
                    indices[ancestors[-2]] - 1
                )

        for children in node:
            dfs(children)

        if node.tag in features_by_node:
            ancestors.pop()

    dfs(xml)

    features_dict = {k: pd.DataFrame.from_dict(v) for k, v in features_by_node.items()}

    for features in features_dict.values():
        for column in features.columns:
            if column.startswith("#"):
                features[column[1:]] = features[column].astype("category")
                features.drop(column, axis=1, inplace=True)

    return features_dict


def get_features(
    features_dict: Dict[str, pd.DataFrame],
    leaf_node: str,
    standardize: bool = True,
    add_context: bool = True,
) -> pd.DataFrame:
    """
    Generate features for each kind of token in PDF XML file.
    """

    try:
        leaf_index = ALTO_HIERARCHY.index(leaf_node)
    except ValueError:
        raise Exception("Could not find requested leaf node in the xml hierarchy.")

    # STEP 2: aggregate features
    prefix = ""
    result_df: Optional[pd.DataFrame] = None

    for index, node in reversed(list(enumerate(ALTO_HIERARCHY))):
        if node in features_dict:
            old_prefix = prefix

            if result_df is None:
                prefix = remove_prefix(node) + "."
                result_df = features_dict[node].add_prefix(prefix)
            else:
                if index >= leaf_index:

                    result_df_numerics = (
                        result_df.select_dtypes(include=["bool", "number"])
                        .groupby(by=old_prefix + node)
                        .agg(["min", "max", "std", "mean"])
                        .fillna(0)
                    )
                    result_df_numerics.columns = result_df_numerics.columns.map(
                        "_".join
                    )

                    df_non_numeric = pd.concat(
                        [
                            result_df.select_dtypes(exclude=["bool", "number"]),
                            result_df[old_prefix + node],
                        ],
                        axis=1,
                    ).groupby(by=old_prefix + node)
                    result_df_words = df_non_numeric.agg(lambda x: dict(Counter(x)))

                    df_groupby = result_df.groupby(by=old_prefix + node)

                    result_df_first_word = df_groupby.nth(0)
                    result_df_first_word = result_df_first_word.add_suffix(".first")

                    result_df_second_word = df_groupby.nth(1)
                    result_df_second_word = result_df_second_word.add_suffix(".second")

                    result_df_last_word = df_groupby.nth(-1)
                    result_df_last_word = result_df_last_word.add_suffix(".last")

                    result_df = pd.concat(
                        [
                            result_df_numerics,
                            result_df_words,
                            result_df_first_word,
                            result_df_second_word,
                            result_df_last_word,
                        ],
                        axis=1,
                    )

                prefix = remove_prefix(node) + "."
                target = features_dict[node].add_prefix(prefix)
                result_df = result_df.join(target, on=old_prefix + node)

                if old_prefix + node in result_df.columns:
                    result_df = result_df.drop(old_prefix + node, axis=1)
    if result_df is None:
        raise Exception("No features generated.")

    result_df.index.name = None

    # STEP 3: add deltas:
    if add_context:
        numeric_features = result_df.select_dtypes(include="number")
        numeric_features_next = numeric_features.diff(periods=-1).add_suffix("_next")
        numeric_features_prev = numeric_features.diff(periods=1).add_suffix("_prev")
        result_df = pd.concat(
            [result_df, numeric_features_next, numeric_features_prev], axis=1
        )

    # STEP 4: standardize
    if standardize:
        std = _standardize(result_df)

        return std
    else:
        return result_df
