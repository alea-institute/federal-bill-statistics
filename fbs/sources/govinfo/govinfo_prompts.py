"""
LLM prompts/execution for generating summaries, audits, and commentaries on bills from GovInfo.
"""

# imports

# packages
from alea_llm_client import BaseAIModel
from alea_llm_client.llms.prompts.sections import format_prompt, format_instructions

# project
from fbs.sources.govinfo.govinfo_types import Bill, BillSection

# token limit for prompt type switch
DEFAULT_PROMPT_LIMIT = 128000


def summarize_bill(bill: Bill, summary_data: dict, llm_model: BaseAIModel) -> str:
    """
    Summarize a bill with an LLM.

    Args:
        bill: Bill.
        summary_data: Summary data.
        llm_model: LLM model.

    Returns:
        Bill summary.
    """
    # check for the number of tokens
    approx_token_count = len(bill.markdown.split()) * 1.5
    if approx_token_count > DEFAULT_PROMPT_LIMIT:
        # summarize from the list of section summaries
        instructions = [
            "You are an expert attorney summarizing a bill from the United States Congress.",
            "Carefully review the EXAMPLE above.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the summaries of each section above in SECTIONS.",
            "Provide a summary of the bill that is:\n"
            "  - Two to four sentences long\n"
            "  - Written in plain language that a high school student could understand\n"
            "  - Written in the third person with a neutral style\n"
            "  - Richly formatted with Markdown\n",
            "Do not include any heading or footer. Only return the summary text.",
        ]

        prompt = format_prompt(
            {
                "example": "**S. 1234**, the Widget Act, is a 37 page bill that would regulate the manufacturing of widgets in the United States.",
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "num_pages": bill.num_pages,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                    "committees": summary_data.get("committees", []),
                    "members": summary_data.get("members", []),
                },
                "sections": [
                    {
                        "enum": section.enum,
                        "header": section.header,
                        "summary": section.summary,
                    }
                    for section in bill.sections
                ],
                "instructions": format_instructions(instructions),
            }
        )
    else:
        # summarize from the entire text directly
        instructions = [
            "You are an expert attorney summarizing a bill from the United States Congress.",
            "Carefully review the EXAMPLE above.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the bill text above in TEXT.",
            "Provide a summary of the bill that is:\n"
            "  - Two to four sentences long\n"
            "  - Written in plain language that a high school student could understand\n"
            "  - Written in the third person with a neutral style\n"
            "  - Richly formatted with Markdown\n",
            "Do not include any heading or footer. Only return the summary text.",
        ]

        prompt = format_prompt(
            {
                "example": "**S. 1234** provides a framework for the regulating the manufacturing of widgets in the United States.",
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "text": bill.markdown,
                "instructions": format_instructions(instructions),
            }
        )

    # generate the summary
    summary = llm_model.chat(prompt)
    return summary.text


def summarize_bill_section(bill_section: BillSection, llm_model: BaseAIModel) -> str:
    """
    Summarize a bill section with an LLM.

    Args:
        bill_section: Bill section.
        llm_model: LLM model.

    Returns:
        Section summary.
    """
    # set up basic prompt
    instructions = [
        "You are an expert attorney summarizing a section of a bill from the United States Congress.",
        "Carefully review the EXAMPLE above.",
        "Carefully read the section text above in TEXT.",
        "Provide a summary of the section that is:\n"
        "  - One to two sentences long\n"
        "  - Written in plain language that a high school student could understand\n"
        "  - Written in the third person with a neutral style\n"
        "  - Richly formatted with Markdown\n",
        "Do not include any heading or footer. Only return the summary text.",
    ]

    prompt = format_prompt(
        {
            "example": "This section defines the terms related to widgets.",
            "text": bill_section.markdown,
            "instructions": format_instructions(instructions),
        }
    )

    # generate the summary
    summary = llm_model.chat(prompt)
    return summary.text


def audit_bill_section(bill_section: BillSection, llm_model: BaseAIModel) -> list[str]:
    """
    Audit a bill section with an LLM.

    Args:
        bill_section: Bill section.
        llm_model: LLM model.

    Returns:
        Section summary.
    """
    # set up basic prompt
    instructions = [
        "You are an expert auditor reviewing a section of a bill from the United States Congress.",
        "Carefully read the section text above in TEXT.",
        "Audit the section for any potential issues, such as:\n"
        "  - Spending that might be wasteful\n"
        "  - Spending that appears to favor a particular organization or individual\n"
        "  - Language that is unclear or ambiguous\n"
        "  - Language that is overly complex or difficult to understand\n"
        "  - Any other issues that might be of concern\n",
        "Return the list of issues as a JSON list of strings.",
        "Respond in JSON using the SCHEMA below.",
    ]

    prompt = format_prompt(
        {
            "example": "This section defines the terms related to widgets.",
            "text": bill_section.markdown,
            "instructions": format_instructions(instructions),
            "schema": """{"issues": list[str]}""",
        }
    )

    # generate the summary
    issues = llm_model.json(prompt)
    return issues.data.get("issues", [])


def audit_bill(bill: Bill, llm_model: BaseAIModel) -> list[str]:
    """
    Audit a bill with an LLM.

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        Bill audit.
    """
    # check for the number of tokens
    approx_token_count = len(bill.markdown.split()) * 1.5
    if approx_token_count > DEFAULT_PROMPT_LIMIT:
        # flatten sections from all sections
        sections = [
            {
                "enum": section.enum,
                "header": section.header,
                "summary": section.summary,
                "issues": section.issues,
            }
            for section in bill.sections
        ]

        # set up basic prompt
        instructions = [
            "You are an expert auditor reviewing a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the summaries and issues of each section above in SECTIONS.",
            "Synthesize the information into a list of salient issues as follows:\n"
            "  - Include issues that might be significant to the general public for political, legal, ethical, or financial reasons.\n"
            "  - Explicitly cite the sections that relate to each issue.\n",
            "Rank order the issues by importance, starting from the most important or controversial issues first.",
            "Return the list of bill issues as a JSON list of strings.",
            "Respond in JSON using the SCHEMA below.",
        ]

        prompt = format_prompt(
            {
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "sections": sections,
                "instructions": format_instructions(instructions),
                "schema": """{"issues": list[str]}""",
            }
        )
    else:
        # flatten sections from all sections
        sections = [
            {
                "enum": section.enum,
                "header": section.header,
                "issues": section.issues,
            }
            for section in bill.sections
        ]

        # set up basic prompt
        instructions = [
            "You are an expert auditor reviewing a list of issues with a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the issues by section above in SECTIONS.",
            "Carefully read the bill text above in TEXT.",
            "Synthesize the information into a list of salient issues as follows:\n"
            "  - Include issues that might be significant to the general public for political, legal, ethical, or financial reasons.\n"
            "  - Explicitly cite the sections that relate to each issue.\n",
            "Rank order the issues by importance, starting from the most important or controversial issues first.",
            "Return the list of bill issues as a JSON list of strings.",
            "Respond in JSON using the SCHEMA below.",
        ]

        prompt = format_prompt(
            {
                "example": "The definition of **widget** in *Section 301* might unfairly favor larger manufacturers.",
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "sections": sections,
                "text": bill.markdown,
                "instructions": format_instructions(instructions),
                "schema": """{"issues": list[str]}""",
            }
        )

    # generate the summary
    issues = llm_model.json(prompt)
    return issues.data.get("issues", [])


def generate_bill_commentary(bill: Bill, llm_model: BaseAIModel) -> str:
    """
    Generate editorial commentary about the bill based on the bill and bill section information, including:
     - A general summary of the bill
     - A summary of significant issues
     - Reasoning about how the bill might impact the public broadly
     - Reasoning about how the bill might positively or negatively impact specific stakeholders

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        Bill commentary.
    """
    # check for the number of tokens
    approx_token_count = len(bill.markdown.split()) * 1.5
    if approx_token_count > DEFAULT_PROMPT_LIMIT:
        # flatten sections from all sections
        sections = [
            {
                "enum": section.enum,
                "header": section.header,
                "summary": section.summary,
                "issues": section.issues,
            }
            for section in bill.sections
        ]

        # set up basic prompt
        instructions = [
            "You are an expert attorney drafting editorial commentary on a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the summaries and issues of each section above in SECTIONS.",
            "Write for a general audience with a high school education."
            "Your editorial commentary should address:\n"
            "  - A general summary of the bill\n"
            "  - A summary of significant issues\n"
            "  - Reasoning about how the bill might impact the public broadly\n"
            "  - Reasoning about how the bill might positively or negatively impact specific stakeholders\n",
            "Clearly organize your commentary into sections and paragraphs. Do not include a title header.",
            "Write in the third person with a neutral style.",
            "Richly format your commentary with Markdown.",
            "Respond only with your editorial commentary as a Markdown-formatted text.",
        ]

        # generate the commentary
        prompt = format_prompt(
            {
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "sections": sections,
                "instructions": format_instructions(instructions),
            }
        )
    else:
        # set up basic prompt
        instructions = [
            "You are an expert attorney drafting editorial commentary on a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the bill text above in TEXT.",
            "Carefully read the issues by section above in SECTIONS.",
            "Carefully read the list of issues above in ISSUES.",
            "Write for a general audience with a high school education.",
            "Your editorial commentary should address:\n"
            "  - A general summary of the bill\n"
            "  - A summary of significant issues\n"
            "  - Reasoning about how the bill might impact the public broadly\n"
            "  - Reasoning about how the bill might positively or negatively impact specific stakeholders\n",
            "Clearly organize your commentary into sections and paragraphs. Do not include a title header.",
            "Write in the third person with a neutral style.",
            "Richly format your commentary with Markdown.",
            "Respond only with your editorial commentary as a Markdown-formatted text.",
        ]

        # generate the commentary
        prompt = format_prompt(
            {
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "text": bill.markdown,
                "sections": [
                    {
                        "enum": section.enum,
                        "header": section.header,
                        "summary": section.summary,
                        "issues": section.issues,
                    }
                    for section in bill.sections
                ],
                "issues": bill.issues,
                "instructions": format_instructions(instructions),
            }
        )

    commentary = llm_model.chat(prompt)
    return commentary.text


def generate_money_commentary(bill: Bill, llm_model: BaseAIModel) -> str:
    """
    Generate editorial commentary about the bill based on the bill and bill section information, including:
     - A general summary of the bill
     - A summary of significant issues
     - Reasoning about how the bill might impact the public broadly
     - Reasoning about how the bill might positively or negatively impact specific stakeholders

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        Bill commentary.
    """
    # check for the number of tokens
    approx_token_count = len(bill.markdown.split()) * 1.5
    if approx_token_count > DEFAULT_PROMPT_LIMIT:
        # flatten sections from all sections
        sections = [
            {
                "enum": section.enum,
                "header": section.header,
                "money_sentences": section.money_sentences,
            }
            for section in bill.sections
        ]

        # set up basic prompt
        instructions = [
            "You are an expert attorney drafting commentary on how money is being used or referenced in a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the financial references of each section above in SECTIONS.",
            "Carefully read the bill summary above in SUMMARY.",
            "Carefully read the list of issues above in ISSUES.",
            "Write for a general audience with a high school education.",
            "Your commentary should focus exclusively on the financial references, including:\n"
            "  - A summary of any spending, appropriations, or financial allocations\n"
            "  - How the financial allocations or references relate to issues identified above\n",
            "Clearly organize your commentary into sections and paragraphs. Do not include a title header.",
            "Write in the third person with a neutral style.",
            "Richly format your commentary with Markdown. Bold any financial references or amounts.",
            "Respond only with your commentary as a Markdown-formatted text.",
        ]

        # generate the commentary
        prompt = format_prompt(
            {
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "sections": sections,
                "summary": bill.summary,
                "issues": bill.issues,
                "instructions": format_instructions(instructions),
            }
        )
    else:
        # set up basic prompt
        instructions = [
            "You are an expert attorney drafting commentary on how money is being used or referenced in a bill from the United States Congress.",
            "Carefully review the bill metadata above in METADATA.",
            "Carefully read the bill text above in TEXT.",
            "Carefully read the money references by section above in SECTIONS.",
            "Carefully read the bill summary above in SUMMARY.",
            "Carefully read the list of issues above in ISSUES.",
            "Write for a general audience with a high school education.",
            "Your commentary should focus exclusively on the financial references, including:\n"
            "  - A summary of any spending, appropriations, or financial allocations\n"
            "  - How the financial allocations or references relate to issues identified above\n",
            "Clearly organize your commentary into sections and paragraphs. Do not include a title header.",
            "Write in the third person with a neutral style.",
            "Richly format your commentary with Markdown. Bold any financial references or amounts.",
            "Respond only with your commentary as a Markdown-formatted text.",
        ]

        # generate the commentary
        prompt = format_prompt(
            {
                "metadata": {
                    "title": bill.title,
                    "short_titles": bill.short_titles,
                    "date": bill.date,
                    "congress": bill.congress,
                    "session": bill.session,
                    "legislation_number": bill.legis_num,
                    "current_chamber": bill.current_chamber,
                    "is_appropriation": bill.is_appropriation,
                    "bill_version": bill.bill_version,
                    "bill_type": bill.bill_type,
                },
                "text": bill.markdown,
                "sections": [
                    {
                        "enum": section.enum,
                        "header": section.header,
                        "money_sentences": section.money_sentences,
                    }
                    for section in bill.sections
                ],
                "summary": bill.summary,
                "issues": bill.issues,
                "instructions": format_instructions(instructions),
            }
        )

    commentary = llm_model.chat(prompt)
    return commentary.text


def generate_bill_eli5(bill: Bill, llm_model: BaseAIModel) -> str:
    """
    Generate an ELI5 (Explain Like I'm 5) explanation of a bill.

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        ELI5 explanation.
    """
    # set up basic prompt
    instructions = [
        "You are an expert attorney explaining a bill from the United States Congress in simple terms.",
        "Carefully review the bill metadata above in METADATA.",
        "Carefully review the SUMMARY, ISSUES, and MONEY COMMENTARY above.",
        "Write a simple ELI5 (explain like I'm 5) summary of the bill that is:\n"
        "  - One to two sentences\n"
        "  - Written in simple language that a child could understand\n"
        "  - Written in the third person with a neutral style\n"
        "  - Richly formatted with Markdown\n",
        "Do not include any heading or footer. Only return the explanation text.",
    ]

    prompt = format_prompt(
        {
            "metadata": {
                "title": bill.title,
                "short_titles": bill.short_titles,
                "date": bill.date,
                "congress": bill.congress,
                "session": bill.session,
                "legislation_number": bill.legis_num,
                "current_chamber": bill.current_chamber,
                "is_appropriation": bill.is_appropriation,
                "bill_version": bill.bill_version,
                "bill_type": bill.bill_type,
            },
            "summary": bill.summary,
            "issues": bill.issues,
            "money_commentary": bill.money_commentary,
            "instructions": format_instructions(instructions),
        }
    )

    # generate the summary
    eli5 = llm_model.chat(prompt)
    return eli5.text


def filter_named_entities(bill: Bill, llm_model: BaseAIModel) -> list[str]:
    """
    Filter named entities from a bill with an LLM.

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        Named entities.
    """
    # set up basic prompt
    instructions = [
        "You are an expert attorney reviewing a bill from the United States Congress.",
        "Carefully review the bill metadata above in METADATA.",
        "Carefully read the bill text above in TEXT.",
        "Filter the named entities in ENTITIES above for relevance to the bill. Only include entities that are directly relevant to the bill.",
        "Return the list of relevant named entities as a JSON list of strings.",
        "Respond in JSON using the SCHEMA below.",
    ]

    prompt = format_prompt(
        {
            "entities": bill.entities,
            "metadata": {
                "title": bill.title,
                "short_titles": bill.short_titles,
                "date": bill.date,
                "congress": bill.congress,
                "session": bill.session,
                "legislation_number": bill.legis_num,
                "current_chamber": bill.current_chamber,
                "is_appropriation": bill.is_appropriation,
                "bill_version": bill.bill_version,
                "bill_type": bill.bill_type,
            },
            "summary": bill.summary,
            "issues": bill.issues,
            "instructions": format_instructions(instructions),
            "schema": """{"entities": list[str]}""",
        }
    )

    # generate the summary
    response = llm_model.json(prompt)
    entity_list = response.data.get("entities", [])

    # confirm we only return ones that originally existed
    original_entity_list = [entity.lower().strip() for entity in bill.entities]
    return [
        entity
        for entity in entity_list
        if entity.lower().strip() in original_entity_list
    ]


def extract_bill_keywords(bill: Bill, llm_model: BaseAIModel) -> list[str]:
    """
    Extract keywords from a bill with an LLM.

    Args:
        bill: Bill.
        llm_model: LLM model.

    Returns:
        Keywords.
    """
    # set up basic prompt
    instructions = [
        "You are an expert attorney tagging a bill from the United States Congress for search and indexing.",
        "Carefully review the bill metadata above in METADATA.",
        "Carefully review the SUMMARY, ISSUES, and SECTIONS above.",
        "List up to 10 keywords that would be relevant for search and indexing of this bill.",
        "Rank order the keywords by importance, starting from the most important keywords first."
        "Return the list of keywords as a JSON list of strings.",
        "Respond in JSON using the SCHEMA below.",
    ]

    prompt = format_prompt(
        {
            "metadata": {
                "title": bill.title,
                "short_titles": bill.short_titles,
                "date": bill.date,
                "congress": bill.congress,
                "session": bill.session,
                "legislation_number": bill.legis_num,
                "current_chamber": bill.current_chamber,
                "is_appropriation": bill.is_appropriation,
                "bill_version": bill.bill_version,
                "bill_type": bill.bill_type,
            },
            "summary": bill.summary,
            "issues": bill.issues,
            "sections": [
                {
                    "enum": section.enum,
                    "header": section.header,
                    "summary": section.summary,
                    "issues": section.issues,
                }
                for section in bill.sections
            ],
            "instructions": format_instructions(instructions),
            "schema": """{"keywords": list[str]}""",
        }
    )

    # generate the summary
    response = llm_model.json(prompt)
    keywords = response.data.get("keywords", [])

    # normalize before returning
    return [keyword.lower().strip() for keyword in keywords]
