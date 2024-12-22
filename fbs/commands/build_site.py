#!/usr/bin/env python3
"""
Generate index.html and sitemap.xml files for all bills in ~/.cache/fbs/bills.

Usage:
    python3 -m fbs.commands.build_site
"""

# Standard library imports
import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, NamedTuple

# packages
import markdown
from jinja2 import Environment, FileSystemLoader
from xml.etree import ElementTree as ET

# project
from fbs.logger import LOGGER
from fbs.sources.govinfo.govinfo_types import get_bill_slug

# Constants
DEFAULT_BILLS_PATH = Path.home() / ".cache" / "fbs" / "bills"
DEFAULT_OUTPUT_PATH = Path("dist")
DEFAULT_TEMPLATE_DIR = Path("templates")
BASE_DOMAIN = "https://usbills.ai/"


class BillGroup(NamedTuple):
    """
    Represents a group of bills for a specific month.
    """

    year_month: str  # YYYY-MM format
    month_name: str  # Month YYYY format
    bills: List[Dict[str, Any]]


def load_bills(bills_path: Path = DEFAULT_BILLS_PATH) -> List[Dict[str, Any]]:
    """
    Load all bill JSON data from the bills directory.

    Args:
        bills_path: Path to bills directory

    Returns:
        List of bill data dictionaries
    """
    bills = []
    for file_path in bills_path.rglob("*"):
        try:
            with gzip.open(file_path, "rt") as f:
                bill_data = json.load(f)
                bills.append(bill_data)
        except Exception as e:
            LOGGER.error(f"Error loading bill {file_path}: {str(e)}")
            continue
    return bills


def generate_sitemap(
    bills: List[Dict[str, Any]], bill_groups: Dict[str, BillGroup], output_path: Path
) -> None:
    """
    Generate sitemap.xml for all bills and month indexes.

    Args:
        bills: List of bill data dictionaries
        bill_groups: Dictionary of BillGroups by year-month
        output_path: Output directory path
    """
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # Add homepage
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = BASE_DOMAIN
    ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(url, "changefreq").text = "daily"
    ET.SubElement(url, "priority").text = "1.0"

    # Add month index pages
    for year_month in bill_groups.keys():
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"{BASE_DOMAIN}index-{year_month}.html"
        ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")
        ET.SubElement(url, "changefreq").text = "weekly"
        ET.SubElement(url, "priority").text = "0.9"

    # Add bill pages
    for bill in bills:
        url = ET.SubElement(urlset, "url")
        bill_slug = get_bill_slug(
            bill["legis_num"], bill["title"], bill["bill_version"]
        )
        ET.SubElement(url, "loc").text = f"{BASE_DOMAIN}{bill_slug}.html"
        ET.SubElement(url, "lastmod").text = bill["date"]
        ET.SubElement(url, "changefreq").text = "weekly"
        ET.SubElement(url, "priority").text = "0.8"

    tree = ET.ElementTree(urlset)
    tree.write(output_path / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def group_bills_by_month(bills: List[Dict[str, Any]]) -> Dict[str, BillGroup]:
    """
    Group bills by year-month and create BillGroup objects.

    Args:
        bills: List of bill data dictionaries

    Returns:
        Dictionary mapping year-month to BillGroup
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for bill in bills:
        bill_date = datetime.strptime(bill["date"], "%Y-%m-%d")
        year_month = bill_date.strftime("%Y-%m")
        month_name = bill_date.strftime("%B %Y")

        if year_month not in groups:
            groups[year_month] = BillGroup(
                year_month=year_month, month_name=month_name, bills=[]
            )

        groups[year_month].bills.append(
            {
                "legis_num": bill["legis_num"],
                "title": bill["title"],
                "date": bill["date"],
                "num_pages": bill.get("num_pages", 0),
                "num_sections": bill.get("num_sections", 0),
                "num_tokens": bill.get("num_tokens", 0),
                "eli5": markdown.markdown(bill.get("eli5", "")),
                "slug": get_bill_slug(
                    bill["legis_num"], bill["title"], bill["bill_version"]
                ),
            }
        )

    # Sort bills within each group by date
    for group in groups.values():
        group.bills.sort(key=lambda x: x["date"], reverse=True)

    return groups


def generate_month_index(
    month_group: BillGroup, template_dir: Path, output_path: Path
) -> None:
    """
    Generate index file for a specific month.

    Args:
        month_group: BillGroup containing month's bills
        template_dir: Template directory path
        output_path: Output directory path
    """
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html.j2")

    html = template.render(
        bills={month_group.month_name: month_group.bills},
        timestamp=datetime.now().isoformat(),
        total_bills=len(month_group.bills),
    )

    output_path = output_path / f"index-{month_group.year_month}.html"
    with open(output_path, "wt") as output_path:
        output_path.write(html)


def generate_main_index(
    bill_groups: Dict[str, BillGroup], template_dir: Path, output_path: Path
) -> None:
    """
    Generate main index.html showing recent months and archive links.

    Args:
        bill_groups: Dictionary of BillGroups by year-month
        template_dir: Template directory path
        output_path: Output directory path
    """
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("index.html.j2")

    # Sort groups by year-month descending
    sorted_months = sorted(bill_groups.keys(), reverse=True)

    # Get recent months and archive months
    recent_months = sorted_months[:3]
    archive_months = sorted_months[3:]

    # Build recent bills dict
    recent_bills = {}
    total_bills = 0
    for month in recent_months:
        group = bill_groups[month]
        recent_bills[group.month_name] = group.bills
        total_bills += len(group.bills)

    # Build archive data
    archives = [
        {
            "year_month": month,
            "month_name": bill_groups[month].month_name,
            "count": len(bill_groups[month].bills),
        }
        for month in archive_months
    ]

    html = template.render(
        bills=recent_bills,
        archives=archives,
        timestamp=datetime.now().isoformat(),
        total_bills=total_bills,
    )

    with open(output_path / "index.html", "w") as f:
        f.write(html)


def render_privacy_notice(template_dir: Path, output_path: Path) -> None:
    """
    Render the privacy notice page.

    Args:
        template_dir: Template directory path
        output_path: Output directory path
    """
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("privacy.html.j2")

    html = template.render(timestamp=datetime.now().isoformat())
    with open(output_path / "privacy.html", "wt") as output_file:
        output_file.write(html)


def render_about_page(template_dir: Path, output_path: Path) -> None:
    """
    Render the about page.

    Args:
        template_dir: Template directory path
        output_path: Output directory path
    """
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("about.html.j2")

    html = template.render(timestamp=datetime.now().isoformat())
    with open(output_path / "about.html", "wt") as output_file:
        output_file.write(html)


def generate_index_json(bills: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Generate index.json file with bill data.

    Args:
        bills: List of bill data dictionaries
        output_path: Output directory path
    """
    # get a copy without the text, html, markdown fields at the top level or section level
    output_data = bills.copy()
    for bill in output_data:
        # add the slug and json url
        bill["slug"] = get_bill_slug(
            bill["legis_num"], bill["title"], bill["bill_version"]
        )
        bill["json_url"] = f"{BASE_DOMAIN}{bill['slug']}.json"

        # remove text fields
        bill.pop("text", None)
        bill.pop("html", None)
        bill.pop("markdown", None)
        for section in bill.get("sections", []):
            section.pop("text", None)
            section.pop("html", None)
            section.pop("markdown", None)

    with open(output_path / "index.json", "wt") as output_file:
        json.dump(output_data, output_file, indent=4)


def generate_robots_txt(output_path: Path) -> None:
    """
    Generate robots.txt file to allow all bots.

    Args:
        output_path: Output directory path
    """
    # initial buffer
    robots_buffer = """User-Agent: *"""

    # add the sitemap.xml link
    robots_buffer += f"\nSitemap: {BASE_DOMAIN}sitemap.xml"

    # add empty disallow
    robots_buffer += "\nDisallow:"

    # write the buffer to the file
    with open(output_path / "robots.txt", "wt") as output_file:
        output_file.write(robots_buffer)


def main() -> None:
    """Main function to generate site files."""
    try:
        # Load all bills
        LOGGER.info("Loading bills...")
        bills = load_bills()
        LOGGER.info(f"Loaded {len(bills)} bills")

        # Create output directory
        DEFAULT_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

        # Sort bills by date
        bills.sort(key=lambda x: x["date"], reverse=True)

        # Group bills by month
        LOGGER.info("Grouping bills by month...")
        bill_groups = group_bills_by_month(bills)

        # Generate sitemap
        LOGGER.info("Generating sitemap...")
        generate_sitemap(bills, bill_groups, DEFAULT_OUTPUT_PATH)

        # Generate month indexes
        LOGGER.info("Generating month indexes...")
        for group in bill_groups.values():
            generate_month_index(group, DEFAULT_TEMPLATE_DIR, DEFAULT_OUTPUT_PATH)

        # Generate main index
        LOGGER.info("Generating main index...")
        generate_main_index(bill_groups, DEFAULT_TEMPLATE_DIR, DEFAULT_OUTPUT_PATH)

        # now render the privacy notice
        LOGGER.info("Rendering privacy notice...")
        render_privacy_notice(DEFAULT_TEMPLATE_DIR, DEFAULT_OUTPUT_PATH)

        # now render the about page
        LOGGER.info("Rendering about page...")
        render_about_page(DEFAULT_TEMPLATE_DIR, DEFAULT_OUTPUT_PATH)

        # Generate robots.txt
        LOGGER.info("Generating robots.txt...")
        generate_robots_txt(DEFAULT_OUTPUT_PATH)

        # Generate index.json
        LOGGER.info("Generating index.json...")
        generate_index_json(bills, DEFAULT_OUTPUT_PATH)

        LOGGER.info("Site generation complete")

    except Exception as e:
        LOGGER.error(f"Error generating site: {str(e)}")
        raise


if __name__ == "__main__":
    main()
