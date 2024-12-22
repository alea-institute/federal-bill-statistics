"""
GovInfo bill parser to generate clean structure from XML.
"""

# imports
import datetime
import time
import warnings
from collections import Counter
from pathlib import Path
from typing import Optional

# packages
import alea_preprocess
import lxml.etree
import numpy
import spacy
from alea_llm_client import BaseAIModel

# project
from fbs.sources.govinfo.govinfo_types import BillSection, Bill
from fbs.sources.govinfo.govinfo_prompts import (
    summarize_bill,
    summarize_bill_section,
    audit_bill,
    audit_bill_section,
    generate_bill_commentary,
    generate_money_commentary,
    generate_bill_eli5,
    filter_named_entities,
    extract_bill_keywords,
)

# disable future warnings
warnings.simplefilter(action="ignore", category=FutureWarning)

# constants

# delay per section for rpm limits
SECTION_DELAY = 1.0

# default spacy model name
DEFAULT_SPACY_MODEL_NAME = "en_core_web_trf"

# load spacy default model
DEFAULT_SPACY_MODEL = spacy.load(DEFAULT_SPACY_MODEL_NAME)


def load_xsl_transformer() -> lxml.etree.XSLT:
    """
    Load assuming all files in cwd.

    Returns:
        XSLT transformer.
    """
    xsl_path = Path(__file__).parent / "billres.xsl"
    return lxml.etree.XSLT(lxml.etree.parse(str(xsl_path.absolute())))


# load the default transformer once at the module level
DEFAULT_TRANSFORMER = load_xsl_transformer()


def get_section_enum(section_element: lxml.etree.Element) -> Optional[str]:
    """
    Get the section enum.

    Args:
        section_element: Section element.

    Returns:
        Section enum.
    """
    section_enum_list = section_element.xpath(".//enum")
    if len(section_enum_list) > 0:
        return lxml.etree.tostring(
            section_enum_list[0], encoding="unicode", method="text"
        ).strip()
    return None


def get_section_heading(section_element: lxml.etree.Element) -> Optional[str]:
    """
    Get the section heading.

    Args:
        section_element: Section element.

    Returns:
        Section heading.
    """
    section_heading_list = section_element.xpath(".//header")
    if len(section_heading_list) > 0:
        return lxml.etree.tostring(
            section_heading_list[0], encoding="unicode", method="text"
        ).strip()
    return None


def get_section_html(section_element: lxml.etree.Element) -> lxml.etree.Element:
    """
    Get the section HTML.

    Args:
        section_element: Section element.

    Returns:
        Section HTML.
    """
    # convert to html by wrapping in a bill/legis-body hierarchy
    bill_element = lxml.etree.Element("bill")
    body_element = lxml.etree.Element("legis-body")
    body_element.append(section_element)
    bill_element.append(body_element)

    # apply the default transformer
    section_html = DEFAULT_TRANSFORMER(bill_element)

    # remove the Be it enacted <em> added by the default XSLT
    for em in section_html.xpath("//em"):
        if "Be it enacted by the Senate and House of Representatives" in em.text:
            em.getparent().remove(em)

    return section_html


def get_spacy_data(text: str) -> dict:
    """
    Get basic statistics about the document by parsing with spacy and then:
     - extracting the named entities
     - counting the number of tokens, sentences, nouns, verbs, adjectives, adverbs, punctuations, and entities.
     - calculating the average token and sentence length.
     - calculating the token entropy
     - calculating the readability scores

    Args:
        text: Text to get spacy stats from.

    Returns:
        Spacy stats.
    """
    # get spacy doc
    doc = DEFAULT_SPACY_MODEL(text)

    # get stats
    num_sentences = len(list(doc.sents))
    num_characters = len(text)
    num_tokens = 0
    num_nouns = 0
    num_verbs = 0
    num_adjectives = 0
    num_adverbs = 0
    num_punctuations = 0
    num_numbers = 0

    for token in doc:
        num_tokens += 1
        if token.pos_ in ("NOUN", "PROPN", "PRON"):
            num_nouns += 1
        elif token.pos_ in ("VERB",):
            num_verbs += 1
        elif token.pos_ == "ADJ":
            num_adjectives += 1
        elif token.pos_ == "ADV":
            num_adverbs += 1
        else:
            if token.is_punct or token.pos_ in ("PUNCT",):
                num_punctuations += 1
            elif token.like_num or token.pos_ in ("NUM",):
                num_numbers += 1
            elif token.pos_ not in (
                "DET",
                "ADP",
                "CCONJ",
                "SCONJ",
                "PART",
                "AUX",
                "SPACE",
            ):
                # print(f"Unknown token POS: {token} -> {token.pos_}")
                pass

    # get the number of entities
    num_entities = len(list(doc.ents))

    # calculate the average token and sentence length
    avg_token_length = sum(len(token) for token in doc) / num_tokens
    avg_sentence_length = sum(len(sent) for sent in doc.sents) / num_sentences

    # calculate the token entropy
    token_freqs = Counter(token.text for token in doc)
    token_probs = numpy.array(list(token_freqs.values())) / num_tokens
    token_entropy = -numpy.sum(token_probs * numpy.log(token_probs))

    # get the NEs
    named_entities = [ent.text for ent in doc.ents]

    # get every sentence that includes a $ or dollar
    money_sentences = [
        sent.text
        for sent in doc.sents
        if "$" in sent.text or " dollar" in sent.text.lower()
    ]

    return {
        "num_characters": num_characters,
        "num_tokens": num_tokens,
        "num_sentences": num_sentences,
        "num_nouns": num_nouns,
        "num_verbs": num_verbs,
        "num_adjectives": num_adjectives,
        "num_adverbs": num_adverbs,
        "num_numbers": num_numbers,
        "num_punctuations": num_punctuations,
        "num_entities": num_entities,
        "avg_token_length": avg_token_length,
        "avg_sentence_length": avg_sentence_length,
        "token_entropy": token_entropy,
        "entities": named_entities,
        "money_sentences": money_sentences,
    }


def parse_xml_section(section_element: lxml.etree.Element) -> BillSection:
    """
    Parse a section element.

    Args:
        section_element: Section element.

    Returns:
        Parsed section.
    """
    # get toc id
    toc_id = section_element.attrib.get("id", None)

    # get <enum> if present
    section_enum = get_section_enum(section_element)

    # get <heading> if present
    section_header = get_section_heading(section_element)

    # convert to html by wrapping in a bill/legis-body hierarchy
    section_html = get_section_html(section_element)
    section_html_buffer = lxml.etree.tostring(section_html, encoding="utf-8").decode()

    # convert to text and markdown
    section_text = alea_preprocess.parsers.html.conversion.extract_buffer_text(
        section_html_buffer
    )
    section_markdown = alea_preprocess.parsers.html.conversion.extract_buffer_markdown(
        section_html_buffer, output_links=False, output_images=False
    )

    # get spacy data
    spacy_data = get_spacy_data(section_text)

    return BillSection(
        # main fields
        enum=section_enum,
        header=section_header,
        toc_id=toc_id,
        text=section_text,
        markdown=section_markdown,
        html=lxml.etree.tostring(section_html, encoding="unicode", method="xml"),
        # stats fields
        **spacy_data,
    )


def parse_xml_bill(
    xml_doc: lxml.etree.Element, summary_data: dict, llm_model: BaseAIModel
) -> Bill:
    """
    Parse a bill XML document.

    Args:
        xml_doc: Bill XML document.
        summary_data: Summary data.
        llm_model: LLM model.

    Returns:
        Parsed bill.
    """
    # parse the simple summary data fields
    title = summary_data.get("title", "")
    short_titles = [
        st.get("title", None)
        for st in summary_data.get("shortTitles", [])
        if st.get("title", None)
    ]
    publisher = summary_data.get("publisher", "")
    congress = summary_data.get("congress", "")
    session = summary_data.get("session", "")
    current_chamber = summary_data.get("currentChamber", "")
    num_pages = summary_data.get("pages", None)
    is_appropriation = summary_data.get("isAppropriation", False)
    bill_version = summary_data.get("billVersion", "")
    bill_type = summary_data.get("billType", "")

    # get date safely
    try:
        date = datetime.date.fromisoformat(summary_data.get("dateIssued", ""))
    except ValueError:
        date = None

    # get legis-num from xml
    try:
        legis_num = lxml.etree.tostring(
            xml_doc.xpath(".//legis-num")[0], encoding="unicode", method="text"
        ).strip()
    except IndexError:
        legis_num = ""

    # get text, markdown, and html versions of whole bill
    bill_html = DEFAULT_TRANSFORMER(xml_doc)

    # convert to text and markdown
    bill_text = alea_preprocess.parsers.html.conversion.extract_buffer_text(
        lxml.etree.tostring(bill_html, encoding="utf-8").decode()
    )

    bill_markdown = alea_preprocess.parsers.html.conversion.extract_buffer_markdown(
        lxml.etree.tostring(bill_html, encoding="utf-8").decode(),
        output_links=False,
        output_images=False,
    )

    # get spacy data
    spacy_data = get_spacy_data(bill_text)

    # parse sections
    sections = []
    for section_element in xml_doc.xpath(".//section"):
        section_data = parse_xml_section(section_element)
        section_data.summary = summarize_bill_section(section_data, llm_model)
        section_data.issues = audit_bill_section(section_data, llm_model)
        sections.append(section_data)
        time.sleep(SECTION_DELAY)

    # get initial bill object
    bill = Bill(
        # main fields
        title=title,
        short_titles=short_titles,
        num_pages=num_pages,
        publisher=publisher,
        date=date,
        congress=congress,
        session=session,
        legis_num=legis_num,
        current_chamber=current_chamber,
        is_appropriation=is_appropriation,
        bill_version=bill_version,
        bill_type=bill_type,
        # content representations
        text=bill_text,
        markdown=bill_markdown,
        html=lxml.etree.tostring(bill_html, encoding="unicode", method="xml"),
        # structured data and document stats
        num_sections=len(sections),
        sections=sections,
        llm_model_id=llm_model.model,
        **spacy_data,
    )

    # get summary
    bill.summary = summarize_bill(bill, summary_data, llm_model)
    bill.issues = audit_bill(bill, llm_model)
    bill.commentary = generate_bill_commentary(bill, llm_model)

    # get money commentary if there are money sentences
    if len(bill.money_sentences) > 0:
        bill.money_commentary = generate_money_commentary(bill, llm_model)
    else:
        bill.money_commentary = None

    # get the eli5
    bill.eli5 = generate_bill_eli5(bill, llm_model)

    # filter named entities
    bill.entities = filter_named_entities(bill, llm_model)

    # tag it
    bill.keywords = extract_bill_keywords(bill, llm_model)

    return bill
