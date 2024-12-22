"""
Basic rendering engine to convert JSON bill analysis to HTML and PDF
using Jinja2 templates and Chrome.
"""

# imports
import datetime
import gzip
import json
import statistics
import subprocess
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any, Dict

# packages
from jinja2 import Environment, FileSystemLoader
import markdown

# project
from fbs.logger import LOGGER
from fbs.sources.govinfo.govinfo_types import BILL_VERSION_CODES, get_bill_slug
from fbs.utils.readability import get_ari_years_education, get_ari_raw

# default bill stats path
DEFAULT_STATS_PATH = Path.home() / ".cache" / "fbs" / "stats.json"


@cache
def load_bill_stats(file_path: str | Path = DEFAULT_STATS_PATH) -> Dict[str, Any]:
    """Load bill statistics from the specified file path.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dict containing the JSON data

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    try:
        # read raw data
        with open(file_path, "rt") as input_file:
            data = json.load(input_file)

        # calculate the deciles for each metric
        for metric in data.keys():
            data[metric]["deciles"] = statistics.quantiles(
                data[metric]["values"], n=10, method="inclusive"
            )

        return data

    except FileNotFoundError:
        LOGGER.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        LOGGER.error(f"Invalid JSON in file: {file_path}")
        raise


def get_decile_number(value: float, deciles: list[float]) -> int:
    """Get the decile number for the specified value.

    Args:
        value: Value to get the decile number for
        deciles: List of decile values

    Returns:
        int: Decile number
    """
    for i, decile in enumerate(deciles):
        if value <= decile:
            return i + 1
    return 10


def enrich_bill_data(
    bill_data: Dict[str, Any], stats: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enrich the bill data with additional fields for rendering.

    Args:
        bill_data: Dictionary containing the bill data
        stats: Dictionary containing the bill statistics

    Returns:
        Dict[str, Any]: Enriched bill data
    """
    # get ari_raw and ari_years_education from bill_stats
    bill_data["ari_raw"] = get_ari_raw(bill_data)
    bill_data["ari_years_education"] = get_ari_years_education(bill_data["ari_raw"])

    # get aggregate bill stats to use for percentiles
    bill_stats = load_bill_stats()

    # calculate the decile number for each selected metric
    bill_data["num_characters_decile"] = get_decile_number(
        bill_data["num_characters"], bill_stats["num_characters"]["deciles"]
    )

    bill_data["num_tokens_decile"] = get_decile_number(
        bill_data["num_tokens"], bill_stats["num_tokens"]["deciles"]
    )

    bill_data["num_sentences_decile"] = get_decile_number(
        bill_data["num_sentences"], bill_stats["num_sentences"]["deciles"]
    )

    bill_data["num_sections_decile"] = get_decile_number(
        bill_data["num_sections"], bill_stats["num_sections"]["deciles"]
    )

    bill_data["avg_token_length_decile"] = get_decile_number(
        bill_data["avg_token_length"], bill_stats["avg_token_length"]["deciles"]
    )

    bill_data["avg_sentence_length_decile"] = get_decile_number(
        bill_data["avg_sentence_length"], bill_stats["avg_sentence_length"]["deciles"]
    )

    bill_data["token_entropy_decile"] = get_decile_number(
        bill_data["token_entropy"], bill_stats["token_entropy"]["deciles"]
    )

    bill_data["ari_raw_decile"] = get_decile_number(
        bill_data["ari_raw"], bill_stats["ari_raw"]["deciles"]
    )

    bill_data["ari_years_education_decile"] = get_decile_number(
        bill_data["ari_years_education"], bill_stats["ari_years_education"]["deciles"]
    )

    # convert entities to lowercase and strip whitespace
    entity_count = Counter()
    filter_entities = [e.lower().strip() for e in bill_data["entities"]]
    for section_data in bill_data["sections"]:
        for entity in section_data["entities"]:
            if entity.lower().strip() in filter_entities:
                entity_count[entity] += 1

    # set entity_counts dictionary into data
    bill_data["entity_counts"] = entity_count

    # render all section summary fields to html as well
    for section_data in bill_data["sections"]:
        section_data["summary"] = markdown.markdown(section_data["summary"])

    # render markdown to html fields
    bill_data["eli5"] = markdown.markdown(bill_data["eli5"])
    bill_data["summary"] = markdown.markdown(bill_data["summary"])
    bill_data["commentary"] = markdown.markdown(bill_data["commentary"])
    bill_data["issues"] = [markdown.markdown(issue) for issue in bill_data["issues"]]

    # shift all h1/h2/h3 headers down by two levels
    for header_level in range(4, 0, -1):
        bill_data["commentary"] = (
            bill_data["commentary"]
            .replace(f"<h{header_level}>", f"<h{header_level + 1}>")
            .replace(f"</h{header_level}>", f"</h{header_level + 1}>")
        )

    # do the same with money_commentary if it isn't None
    if bill_data["money_commentary"] is not None:
        bill_data["money_commentary"] = markdown.markdown(bill_data["money_commentary"])
        for header_level in range(4, 0, -1):
            bill_data["money_commentary"] = (
                bill_data["money_commentary"]
                .replace(f"<h{header_level}>", f"<h{header_level + 1}>")
                .replace(f"</h{header_level}>", f"</h{header_level + 1}>")
            )

    # join keywords to keyword_string
    bill_data["keyword_string"] = ", ".join(bill_data["keywords"])

    # get the bill version as a descriptive string
    bill_data["bill_version_description"] = BILL_VERSION_CODES.get(
        bill_data["bill_version"], "Unknown"
    )

    # timestamp
    bill_data["timestamp"] = datetime.datetime.now().isoformat()

    # set download_url from slug + .pdf
    bill_data["slug"] = get_bill_slug(
        bill_data["legis_num"], bill_data["title"], bill_data["bill_version"]
    )
    bill_data["pdf_url"] = f"{bill_data['slug']}.pdf"
    bill_data["json_url"] = f"{bill_data['slug']}.json"

    return bill_data


def load_json_data(file_path: str | Path) -> Dict[str, Any]:
    """Load JSON data from the specified file path.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dict containing the JSON data

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    try:
        try:
            with open(file_path, "rt") as input_file:
                data = json.load(input_file)
        except Exception:
            # try with gzip
            try:
                with gzip.open(file_path, "rt") as input_file:
                    data = json.load(input_file)
            except Exception as e:
                LOGGER.error(f"Error reading file: {str(e)}")
                raise RuntimeError(f"Error reading file: {str(e)}") from e

        # enrich the data
        data = enrich_bill_data(data, load_bill_stats())

        return data

    except FileNotFoundError:
        LOGGER.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        LOGGER.error(f"Invalid JSON in file: {file_path}")
        raise


def render_template_html(
    data: Dict[str, Any], template_path: str, output_path: str
) -> None:
    """Render the Jinja2 template with the provided data and save to output file.

    Args:
        data: Dictionary containing the data to render
        template_path: Path to the template directory
        output_path: Path where the rendered HTML should be saved

    Raises:
        jinja2.TemplateNotFound: If template file does not exist
        OSError: If output file cannot be written
    """
    try:
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("bill_details.html.j2")

        rendered_html = template.render(
            data=data,
            timestamp=datetime.datetime.now().isoformat(),
            llm_model_id=data["llm_model_id"],
        )

        with open(output_path, "wt") as output_file:
            output_file.write(rendered_html)

        LOGGER.info(f"Successfully rendered template to {output_path}")

    except Exception as e:
        LOGGER.error(f"Error rendering template: {str(e)}")
        raise


def render_template_pdf(output_path_html: str, output_path_pdf: str) -> bool:
    """Render the HTML file to PDF using Chrome headless.

    Args:
        output_path_html: Path to the HTML file
        output_path_pdf: Path to the PDF file

    Returns:
        bool: True if successful, False otherwise
    """

    # assume that we are rendering from localhost:9000 but strip the dist/ prefix
    render_url = f"http://localhost:9000/{output_path_html.replace("dist/", "")}"
    print(render_url)

    # use subprocess to safely handle and collect return status
    try:
        subprocess.run(
            [
                "google-chrome",
                "--headless",
                "--disable-gpu",
                "--run-all-compositor-stages-before-draw",
                "--no-margins",
                "--no-pdf-header-footer",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={output_path_pdf}",
                render_url,
            ],
            check=True,
            shell=False,
        )
        LOGGER.info(f"Successfully rendered PDF to {output_path_pdf}")
        return True
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Error rendering PDF: {str(e)}")
        return False
    except Exception as e:
        LOGGER.error(f"Error rendering PDF: {str(e)}")
        return False
