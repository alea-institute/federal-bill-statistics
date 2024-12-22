#!/usr/bin/env python3
"""
Render all bill analysis JSON files from cache directory to HTML and PDF.

Usage:
    python3 -m fbs.commands.render_all_bills [--path /path/to/bills/]
"""

# standard library imports
import argparse
import gzip
from pathlib import Path

# project imports
from fbs.logger import LOGGER
from fbs.render.bill import load_json_data, render_template_html, render_template_pdf
from fbs.sources.govinfo.govinfo_types import get_bill_slug

# constants
DEFAULT_BILLS_PATH = Path.home() / ".cache" / "fbs" / "bills"
DEFAULT_TEMPLATE_DIR = "templates"
DEFAULT_OUTPUT_DIR = "dist"


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Render all bill analysis JSON files from cache directory to HTML and PDF."
    )

    parser.add_argument(
        "--path",
        type=str,
        default=str(DEFAULT_BILLS_PATH),
        help="Path to bills cache directory",
    )

    parser.add_argument(
        "--template_dir",
        type=str,
        default=DEFAULT_TEMPLATE_DIR,
        help="Path to the template directory",
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Path to the output directory",
    )

    return parser.parse_args()


def render_bill_file(input_path: Path, template_dir: Path, output_dir: Path) -> None:
    """
    Render a single bill JSON file to HTML and PDF.

    Args:
        input_path: Path to the input JSON file
        template_dir: Path to template directory
        output_dir: Path to output directory

    Raises:
        Exception: If rendering fails
    """
    try:
        # read the input path json data
        bill_data = load_json_data(input_path)

        # get bill slug from data
        bill_slug = get_bill_slug(
            bill_data["legis_num"], bill_data["title"], bill_data["bill_version"]
        )

        # get output paths
        output_path_html = output_dir / f"{bill_slug}.html"
        output_path_pdf = output_dir / f"{bill_slug}.pdf"
        output_path_json = output_dir / f"{bill_slug}.json"

        # make sure output exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # render HTML if needed
        if output_path_html.exists():
            LOGGER.warning(f"Output HTML exists: {output_path_html}")
        else:
            LOGGER.info(f"Rendering {input_path} to {output_path_html}")
            render_template_html(bill_data, str(template_dir), str(output_path_html))

        # render PDF if needed
        if output_path_pdf.exists():
            LOGGER.warning(f"Output PDF exists: {output_path_pdf}")
        else:
            LOGGER.info(f"Rendering {input_path} to {output_path_pdf}")
            render_template_pdf(
                str(output_path_html),
                str(output_path_pdf),
            )
        # copy the json file to the slug path
        if output_path_json.exists():
            LOGGER.warning(f"Output JSON exists: {output_path_json}")
        else:
            LOGGER.info(f"Copying JSON to {output_path_json}")
            with gzip.open(input_path, "rt") as input_file:
                with open(output_path_json, "wt") as output_file:
                    output_file.write(input_file.read())

    except Exception as e:
        LOGGER.error(f"Error rendering {input_path}: {str(e)}")
        raise


def main() -> None:
    """Main function to render all bill JSON files."""
    try:
        # Parse command line arguments
        args = parse_args()

        # Convert to Path objects
        bills_path = Path(args.path)
        template_dir = Path(args.template_dir)
        output_dir = Path(args.output_dir)

        # Get all JSON and gzipped JSON files
        json_files = list(bills_path.rglob("*"))

        LOGGER.info(f"Found {len(json_files)} bill files in {bills_path}")

        # Process each file
        for input_file in json_files:
            try:
                render_bill_file(input_file, template_dir, output_dir)
            except Exception as e:
                LOGGER.error(f"Failed to render {input_file}: {str(e)}")
                continue

        LOGGER.info("Completed rendering all bills")

    except Exception as e:
        LOGGER.error(f"Error during rendering: {str(e)}")
        raise


if __name__ == "__main__":
    main()
