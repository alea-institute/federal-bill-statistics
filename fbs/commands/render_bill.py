#!/usr/bin/env python3
"""
Convert a JSON bill analysis file to HTML using templates.

Usage:
    python3 -m fbs.commands.render_bill  path/to/input.json
"""

# standard library imports
import argparse
import shutil
from pathlib import Path

# packages

# project imports
from fbs.logger import LOGGER
from fbs.render.bill import load_json_data, render_template_html, render_template_pdf
from fbs.sources.govinfo.govinfo_types import get_bill_slug


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Convert a JSON bill analysis file to HTML using templates."
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input JSON file",
    )

    # default template dir to templates/
    parser.add_argument(
        "--template_dir",
        type=str,
        default="templates",
        help="Path to the template directory",
    )

    # default output dir to dist/
    parser.add_argument(
        "--output_dir",
        type=str,
        default="dist",
        help="Path to the output directory",
    )

    return parser.parse_args()


def main() -> None:
    """Main function to convert JSON to HTML using the template."""
    try:
        # Parse command line arguments
        args = parse_args()

        # Convert to Path objects
        input_path = Path(args.input_file)
        template_dir = Path(args.template_dir)

        # read the input path json data
        bill_data = load_json_data(input_path)

        # get bill slug from data
        bill_slug = get_bill_slug(
            bill_data["legis_num"], bill_data["title"], bill_data["bill_version"]
        )

        # get output path from slug
        output_path_html = Path(args.output_dir) / f"{bill_slug}.html"
        output_path_pdf = Path(args.output_dir) / f"{bill_slug}.pdf"

        # make sure output exists
        output_path_html.parent.mkdir(parents=True, exist_ok=True)

        if output_path_html.exists():
            LOGGER.warning(f"Output HTML exists: {output_path_html}")
        else:
            # Render the template
            LOGGER.info("Rendering template")
            render_template_html(bill_data, str(template_dir), str(output_path_html))

        if output_path_pdf.exists():
            LOGGER.warning(f"Output PDF exists: {output_path_pdf}")
        else:
            # Render the PDF
            LOGGER.info("Rendering PDF")
            render_template_pdf(str(output_path_html), str(output_path_pdf))

        # copy the json file to the slug path
        output_path_json = Path(args.output_dir) / f"{bill_slug}.json"
        if output_path_json.exists():
            LOGGER.warning(f"Output JSON exists: {output_path_json}")
        else:
            LOGGER.info(f"Copying JSON to {output_path_json}")
            shutil.copy(input_path, output_path_json)

        LOGGER.info("Conversion completed successfully")

    except Exception as e:
        LOGGER.error(f"Error during conversion: {str(e)}")
        raise


if __name__ == "__main__":
    main()
