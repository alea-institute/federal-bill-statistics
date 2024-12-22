# Federal Bill Statistics

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)

This is the [ALEA Institute](https://aleainstitute.ai) project behind the https://usbills.ai website.  Everything you see
on the website is generated from the source and data in this repository.

## Overview

This project provides automated analysis of US federal legislation using a combination of traditional natural language processing and large language models.

Key features include:

- Collection of bill data from govinfo.gov API
- Text analysis using NLP and LLMs
- Plain language summaries and ELI5 explanations
- Key issue identification
- Readability metrics and statistics
- Money/funding analysis

## Data Collection

Bills are retrieved directly from the govinfo.gov API and updated daily. For each bill we:

- Download official metadata and XML version
- Parse and extract content, structure and key information
- Store in standardized format for analysis

## Analysis

The analysis process includes:

### Traditional NLP
- Tokenization
- Syntactic parsing and POS tagging
- Named entity recognition

### LLM Analysis
- Plain language summaries
- Key issue identification
- ELI5 descriptions
- Commentary on implications
- Named entity filtering

## Metrics

The project calculates various metrics including:

### Basic Stats
- Section count
- Word/token count
- Character count
- Sentence count

### Language Statistics
- Parts of speech distribution
- Key phrases
- Entity counts

### Complexity Metrics
- Average word length
- Average sentence length
- Token entropy
- Automated Readability Index (ARI)

## Data Access

You can download complete metadata, statistics and commentary for all bills in JSON format:

- All bills index: `https://usbills.ai/index.json`

## Important Notes

- AI-generated content is marked with an AI tag
- Analysis is meant to supplement, not replace human review
- Always refer to original bill text and consult legal professionals

## License

This project is licensed under a Creative Commons Attribution 4.0 International License.

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## Learn More

Visit [usbills.ai](https://usbills.ai) to explore the project.

An [ALEA Institute](https://aleainstitute.ai) project.
