"""
Readability metrics for text.
"""


def get_ari_raw(metrics: dict) -> float:
    """
    Calculate Automated Readability Index (ARI) raw score.

    Args:
        metrics: Text metrics

    Returns:
        float: ARI raw score
    """
    return (
        4.71 * (metrics["num_characters"] / metrics["num_tokens"])
        + 0.5 * (metrics["num_tokens"] / metrics["num_sentences"])
        - 21.43
    )


def get_ari_years_education(ari_raw: float) -> float:
    """
    Calculate years of education required to understand text.

    Args:
        ari_raw: ARI raw score

    Returns:
        float: Years of education
    """
    return (
        ari_raw - 1
        if ari_raw <= 13  # K-12: subtract 1 since K=0 years
        else 16
        if ari_raw == 14  # Bachelor's degree
        else 16 + (ari_raw - 14) * 2  # Post-bachelor's: 2 years per level
    )
