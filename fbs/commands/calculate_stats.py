#!/usr/bin/env python3
"""
Update the statistics for all parsed bills.
"""

# Standard library imports
import json
import gzip
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import statistics

# Third-party imports

# Project imports
from fbs.logger import LOGGER
from fbs.utils.readability import get_ari_raw, get_ari_years_education

# Constants
DEFAULT_BILLS_PATH = Path.home() / ".cache" / "fbs" / "bills"
STATS_OUTPUT_PATH = Path.home() / ".cache" / "fbs" / "stats.json"


def get_metrics(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract metrics from bill data.

    Args:
        data (Dict[str, Any]): Bill data.

    Returns:
        Dict[str, float]: Extracted metrics.
    """
    metrics = {
        "num_characters": data.get("num_characters", 0),
        "num_tokens": data.get("num_tokens", 0),
        "num_sentences": data.get("num_sentences", 0),
        "num_sections": data.get("num_sections", 0),
        "num_nouns": data.get("num_nouns", 0),
        "num_verbs": data.get("num_verbs", 0),
        "num_adjectives": data.get("num_adjectives", 0),
        "num_adverbs": data.get("num_adverbs", 0),
        "num_punctuations": data.get("num_punctuations", 0),
        "num_numbers": data.get("num_numbers", 0),
        "num_entities": data.get("num_entities", 0),
        "avg_token_length": data.get("avg_token_length", 0),
        "avg_sentence_length": data.get("avg_sentence_length", 0),
        "token_entropy": data.get("token_entropy", 0),
        "ari_raw": data.get("ari_raw", 0),
        "ari_years_education": data.get("ari_age", 0),
    }

    # add them to dict
    metrics["ari_raw"] = get_ari_raw(metrics)
    metrics["ari_years_education"] = get_ari_years_education(metrics["ari_raw"])

    return metrics


def calculate_aggregate_stats(
    metrics: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate aggregate statistics for each metric.

    Args:
        metrics (List[Dict[str, float]]): List of metrics from all bills.

    Returns:
        Dict[str, Dict[str, float]]: Aggregate statistics for each metric.
    """
    stats = defaultdict(lambda: {"mean": 0, "median": 0, "min": 0, "max": 0})

    for metric in metrics[0].keys():
        values = [m[metric] for m in metrics]
        stats[metric] = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }

    return dict(stats)


def update_stats(bills_path: Path = DEFAULT_BILLS_PATH) -> None:
    """
    Update statistics for all parsed bills.

    Args:
        bills_path (Path): Path to the directory containing bill data files.
    """
    LOGGER.info(f"Updating statistics from bills in {bills_path}")

    all_metrics = []
    for file_path in bills_path.rglob("*"):
        try:
            try:
                with gzip.open(file_path, "rt") as input_file:
                    bill_data = json.load(input_file)
            except Exception:
                with open(file_path, "rt") as input_file:
                    bill_data = json.load(input_file)
            metrics = get_metrics(bill_data)
            all_metrics.append(metrics)
        except Exception as e:
            LOGGER.error(f"Error processing {file_path}: {str(e)}")
            raise e

    LOGGER.info(f"Processed {len(all_metrics)} bill files")

    # get the aggregate stats
    aggregate_stats = calculate_aggregate_stats(all_metrics)

    # add the raw values to each aggregate
    for metric in aggregate_stats:
        if "values" not in aggregate_stats[metric]:
            aggregate_stats[metric]["values"] = []
        for metric_data in all_metrics:
            aggregate_stats[metric]["values"].append(metric_data[metric])

    STATS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_OUTPUT_PATH, "wt") as output_file:
        json.dump(aggregate_stats, output_file, indent=2)

    LOGGER.info(f"Statistics updated and saved to {STATS_OUTPUT_PATH}")


def main() -> None:
    """
    Main function to update bill statistics.
    """
    try:
        update_stats()
    except Exception as e:
        LOGGER.error(f"Error updating statistics: {str(e)}")
        raise


if __name__ == "__main__":
    main()
