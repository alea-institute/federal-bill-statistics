# conform to upstream API naming, which is not snake case
# pylint: disable=invalid-name

# future
from __future__ import annotations

# imports
import datetime
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# constants
BILL_VERSION_CODES = {
    "as": "Amendment Ordered to be Printed (Senate)",
    "ash": "Additional Sponsors House",
    "ath": "Agreed to House",
    "ats": "Agreed to Senate",
    "cdh": "Committee Discharged House",
    "cds": "Committee Discharged Senate",
    "cph": "Considered and Passed House",
    "cps": "Considered and Passed Senate",
    "eah": "Engrossed Amendment House",
    "eas": "Engrossed Amendment Senate",
    "eh": "Engrossed in House",
    "enr": "Enrolled Bill",
    "es": "Engrossed in Senate",
    "fph": "Failed Passage House",
    "fps": "Failed Passage Senate",
    "hds": "Held at Desk Senate",
    "ih": "Introduced in House",
    "iph": "Indefinitely Postponed House",
    "ips": "Indefinitely Postponed Senate",
    "is": "Introduced in Senate",
    "lth": "Laid on Table in House",
    "lts": "Laid on Table in Senate",
    "pap": "Printed as Passed",
    "pcs": "Placed on Calendar Senate",
    "pp": "Public Print",
    "pvtl": "Private Law",
    "pl": "Public Law",
    "rch": "Reference Change House",
    "rcs": "Reference Change Senate",
    "rds": "Received in Senate",
    "rfh": "Referred in House",
    "rfs": "Referred in Senate",
    "rh": "Reported in House",
    "rhuc": "Returned to the House by Unanimous Consent",
    "rih": "Referral Instructions House",
    "rs": "Reported to Senate",
    "rth": "Referred to Committee House",
    "rts": "Referred to Committee Senate",
    "sc": "Sponsor Change",
    "statpvt": "Statutes at Large (Private Law)",
    "stat": "Statute",
}


def get_bill_slug(legis_num: str, title: str, version: str, max_chars: int = 64) -> str:
    """
    Generate a URL-safe slug from legislation number and title.

    Args:
        legis_num: Legislation number
        title: Bill title
        version: Bill version
        max_chars: Maximum number of characters in the slug

    Returns:
        URL-safe slug for the bill
    """
    # combine legislation number, title, and version into a single string
    combined_string = f"{legis_num}-{title[:max_chars]}-{version}"

    # convert to lowercase and replace periods with hyphens
    slug = combined_string.lower().replace(".", "-")

    # process the slug
    slug = re.sub(r"[^a-z0-9\-\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    return slug


@dataclass
class SearchResult:
    """
    Represents a single search result from the GovInfo API.
    """

    title: str
    packageId: str
    granuleId: str
    collectionCode: str
    resultLink: str
    relatedLink: str
    lastModified: datetime.date | datetime.datetime
    dateIssued: datetime.date | datetime.datetime
    dateIngested: datetime.date | datetime.datetime
    governmentAuthor: List[str] = field(default_factory=list)
    download: Dict[str, str] = field(default_factory=dict)

    # all other fields are stored in this dictionary
    extra: Dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name):
        """
        Allows accessing items in the extra dict as if they were attributes of the class.
        """
        if name in self.extra:
            return self.extra[name]
        raise AttributeError(f"'SearchResult' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """
        Allows setting items in the extra dict as if they were attributes of the class.
        """
        if name in self.__annotations__ or name in self.__dict__:
            super().__setattr__(name, value)
        else:
            self.extra[name] = value


@dataclass
class SearchResponse:
    """
    Represents a response from the GovInfo API search endpoint.
    """

    count: int
    offsetMark: str = "*"
    results: List[SearchResult] = field(default_factory=list)


@dataclass
class PackageInfo:
    """
    Represents a package of documents from the GovInfo API.
    Core fields are explicitly defined, all other fields are stored in the extra dictionary.
    """

    packageId: str
    docClass: str
    title: str
    congress: str
    lastModified: datetime.date | datetime.datetime
    dateIssued: datetime.date | datetime.datetime
    collectionName: Optional[str] = None
    collectionCode: Optional[str] = None
    category: Optional[str] = None
    packageLink: Optional[str] = None

    # Optional fields that are common but not always present
    session: Optional[str] = None
    branch: Optional[str] = None

    # All other fields are stored in this dictionary
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Convert string dates to datetime objects if they're not already
        if isinstance(self.lastModified, str):
            self.lastModified = datetime.datetime.fromisoformat(
                self.lastModified.rstrip("Z")
            )
        if isinstance(self.dateIssued, str):
            self.dateIssued = datetime.datetime.fromisoformat(self.dateIssued)

    def __getattr__(self, name):
        """
        Allows accessing items in the extra dict as if they were attributes of the class.
        """
        if name in self.extra:
            return self.extra[name]
        raise AttributeError(f"'PackageInfo' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """
        Allows setting items in the extra dict as if they were attributes of the class.
        """
        if name in self.__annotations__ or name in self.__dict__:
            super().__setattr__(name, value)
        else:
            self.extra[name] = value


@dataclass
class CollectionContainer:
    """
    Represents a collection of packages from the GovInfo API.
    """

    count: int
    message: str
    nextPage: str
    previousPage: str
    offsetMark: Optional[str] = "*"
    packages: List[PackageInfo] = field(default_factory=list)


@dataclass
class GranuleMetadata:
    """
    Represents metadata for a granule from the GovInfo API.
    """

    title: str
    granuleId: str
    granuleLink: str
    granuleClass: str
    md5: Optional[str] = None


@dataclass
class GranuleContainer:
    """
    Represents a container of granules from the GovInfo API.
    """

    count: int
    offset: int
    pageSize: int
    nextPage: str
    previousPage: str
    message: Optional[str] = None
    granules: List[GranuleMetadata] = field(default_factory=list)


@dataclass
class SummaryItem:
    """
    Represents a summary item for a collection from the GovInfo API.
    """

    collectionCode: str
    collectionName: str
    packageCount: int
    granuleCount: int


@dataclass
class CollectionSummary:
    """
    Represents a summary of collections from the GovInfo API.
    """

    collections: List[SummaryItem] = field(default_factory=list)


@dataclass
class BillSection:
    """
    Represents a section of a bill from the GovInfo API.
    """

    # basic fields
    enum: Optional[str]
    header: Optional[str]
    toc_id: Optional[str]
    text: str
    markdown: str
    html: str

    # additional stats and structured data
    num_tokens: int
    num_sentences: int
    num_characters: int
    num_nouns: int
    num_verbs: int
    num_adjectives: int
    num_adverbs: int
    num_punctuations: int
    num_numbers: int
    num_entities: int
    avg_token_length: float
    avg_sentence_length: float
    token_entropy: float
    entities: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    money_sentences: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert the BillSection object to a dictionary.
        """
        return {
            "enum": self.enum,
            "header": self.header,
            "toc_id": self.toc_id,
            "text": self.text,
            "markdown": self.markdown,
            "html": self.html,
            "num_tokens": self.num_tokens,
            "num_sentences": self.num_sentences,
            "num_characters": self.num_characters,
            "num_nouns": self.num_nouns,
            "num_verbs": self.num_verbs,
            "num_adjectives": self.num_adjectives,
            "num_adverbs": self.num_adverbs,
            "num_punctuations": self.num_punctuations,
            "num_numbers": self.num_numbers,
            "num_entities": self.num_entities,
            "avg_token_length": self.avg_token_length,
            "avg_sentence_length": self.avg_sentence_length,
            "token_entropy": self.token_entropy,
            "entities": self.entities,
            "summary": self.summary,
            "issues": self.issues,
            "money_sentences": self.money_sentences,
        }


@dataclass
class Bill:
    # basic metadata fields
    title: str
    publisher: str
    date: datetime.date
    congress: str
    session: str
    legis_num: str
    current_chamber: str
    is_appropriation: bool
    bill_version: str
    bill_type: str

    # content representations
    text: str
    markdown: str
    html: str

    # structured data and document stats
    num_pages: Optional[int]
    num_sections: int
    num_tokens: int
    num_sentences: int
    num_characters: int
    num_nouns: int
    num_verbs: int
    num_adjectives: int
    num_adverbs: int
    num_punctuations: int
    num_numbers: int
    num_entities: int
    avg_token_length: float
    avg_sentence_length: float
    token_entropy: float
    entities: List[str] = field(default_factory=list)
    sections: List[BillSection] = field(default_factory=list)
    money_sentences: List[str] = field(default_factory=list)
    short_titles: List[str] = field(default_factory=list)

    # llm-generate fields
    summary: Optional[str] = None
    commentary: Optional[str] = None
    money_commentary: Optional[str] = None
    eli5: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # other deferred fields
    package_id: Optional[str] = None
    llm_model_id: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert the Bill object to a dictionary.
        """
        return {
            "title": self.title,
            "short_titles": self.short_titles,
            "publisher": self.publisher,
            "date": self.date.isoformat(),
            "congress": self.congress,
            "session": self.session,
            "legis_num": self.legis_num,
            "current_chamber": self.current_chamber,
            "is_appropriation": self.is_appropriation,
            "bill_version": self.bill_version,
            "bill_type": self.bill_type,
            "package_id": self.package_id,
            "text": self.text,
            "markdown": self.markdown,
            "html": self.html,
            "num_pages": self.num_pages,
            "num_sections": self.num_sections,
            "num_tokens": self.num_tokens,
            "num_sentences": self.num_sentences,
            "num_characters": self.num_characters,
            "num_nouns": self.num_nouns,
            "num_verbs": self.num_verbs,
            "num_adjectives": self.num_adjectives,
            "num_adverbs": self.num_adverbs,
            "num_punctuations": self.num_punctuations,
            "num_numbers": self.num_numbers,
            "num_entities": self.num_entities,
            "avg_token_length": self.avg_token_length,
            "avg_sentence_length": self.avg_sentence_length,
            "token_entropy": self.token_entropy,
            "entities": self.entities,
            "sections": [section.to_dict() for section in self.sections],
            "summary": self.summary,
            "commentary": self.commentary,
            "money_commentary": self.money_commentary,
            "eli5": self.eli5,
            "issues": self.issues,
            "keywords": self.keywords,
            "money_sentences": self.money_sentences,
            "llm_model_id": self.llm_model_id,
        }

    def get_slug(self) -> str:
        """
        Generate a URL-safe slug from legislation number and title.

        Returns:
            str: URL-safe slug
        """
        return get_bill_slug(self.legis_num, self.title, self.bill_version)
