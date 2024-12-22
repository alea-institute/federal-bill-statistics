#!/usr/bin/env python3
"""
Parse bills from GovInfo and store them in the filesystem cache.

Usage:
    python3 -m fbs.commands.parse_bills --date YYYY-MM-DD
    python3 -m fbs.commands.parse_bills --start-date YYYY-MM-DD --end-date YYYY-MM-DD
"""

# standard library imports
import argparse
import datetime
import sys
import time

# third party imports
from alea_llm_client import OpenAIModel, GrokModel

# project imports
from fbs.logger import LOGGER
from fbs.sources.govinfo.govinfo_source import GovInfoSource

# constants
DEFAULT_PAGE_SIZE = 100
DEFAULT_SLEEP = 1.0


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Parse bills from GovInfo and store them in the filesystem cache."
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Date to parse bills for (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date to parse bills for (YYYY-MM-DD)",
    )

    # Add end date if start date is specified
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date to parse bills for (YYYY-MM-DD)",
    )

    # Add model selection argument
    parser.add_argument(
        "--model",
        type=str,
        choices=["grok-2-1212", "gpt-4o", "claude-3.5-sonnet", "gemini-2.0"],
        default="gpt-4o",
        help="LLM model to use for analysis",
    )

    # Parse args
    args = parser.parse_args()

    # Validate start/end date combination
    if args.start_date and not args.end_date:
        args.end_date = datetime.date.today().isoformat()

    # if no dates are provided, then set date to today
    if not args.date and not args.start_date:
        args.date = datetime.date.today().isoformat()

    return args


def get_date_range(
    args: argparse.Namespace,
) -> tuple[datetime.date, datetime.date]:
    """
    Get the date range from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        tuple[datetime.date, datetime.date]: Start and end dates

    Raises:
        ValueError: If dates are invalid
    """
    if args.date:
        try:
            date = datetime.date.fromisoformat(args.date)
            return date, date
        except ValueError as e:
            raise ValueError(f"Invalid date format: {args.date}") from e

    try:
        start_date = datetime.date.fromisoformat(args.start_date)
        end_date = datetime.date.fromisoformat(args.end_date)
        if end_date < start_date:
            raise ValueError("End date must be after start date")
        return start_date, end_date
    except ValueError as e:
        raise ValueError("Invalid date format") from e


def get_model(model_name: str) -> OpenAIModel | GrokModel:
    """
    Get the appropriate LLM model.

    Args:
        model_name: Name of model to use

    Returns:
        BaseAIModel: Model instance

    Raises:
        ValueError: If model name is invalid
    """
    if model_name == "gpt-4o":
        return OpenAIModel(model="gpt-4o")
    elif model_name == "grok-2-1212":
        return GrokModel(model="grok-2-1212")
    else:
        raise ValueError(f"Invalid model name: {model_name}")


def main() -> None:
    """
    Main entry point.
    """
    # Parse command line arguments
    args = parse_args()

    try:
        # Get date range
        start_date, end_date = get_date_range(args)
        LOGGER.info(
            "Processing bills from %s to %s",
            start_date.isoformat(),
            end_date.isoformat(),
        )

        # Get model
        model = get_model(args.model)
        LOGGER.info("Using model: %s", model.model)

        # Initialize GovInfo client
        with GovInfoSource() as govinfo:
            current_date = start_date
            while current_date <= end_date:
                # Build query for current date
                query = f"collection:BILLS AND (publishdate:{current_date.isoformat()} OR ingestdate:{current_date.isoformat()})"

                # Search for bills
                LOGGER.info("Searching for bills on %s", current_date.isoformat())
                search_results = govinfo.search(
                    query=query, page_size=DEFAULT_PAGE_SIZE
                )

                # get all of them
                while True:
                    if not search_results.results or len(search_results.results) == 0:
                        break

                    for result in search_results.results:
                        try:
                            LOGGER.info("Processing bill %s", result.packageId)
                            bill = govinfo.get_bill(result, model)
                            LOGGER.info(
                                "Successfully processed bill %s: %s",
                                bill.legis_num,
                                bill.title,
                            )

                            # sleep
                            time.sleep(DEFAULT_SLEEP)
                        except Exception as e:
                            LOGGER.error(
                                "Error processing bill %s: %s",
                                result.packageId,
                                str(e),
                            )
                            continue

                    search_results = govinfo.search(
                        query=query,
                        page_size=DEFAULT_PAGE_SIZE,
                        offset_mark=search_results.offsetMark,
                    )

                # Move to next date
                current_date += datetime.timedelta(days=1)

    except Exception as e:
        LOGGER.error("Error: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
