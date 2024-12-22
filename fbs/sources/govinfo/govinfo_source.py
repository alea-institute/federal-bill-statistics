"""
GovInfo source classes
"""

# conform to upstream API naming, which is not snake case
# pylint: disable=invalid-name

# future
from __future__ import annotations

# imports
import datetime
import gzip
import hashlib
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Any

# packages
import httpx
import lxml.etree
from alea_llm_client import BaseAIModel

# project
from fbs.logger import LOGGER
from fbs.sources.govinfo.govinfo_parser import parse_xml_bill
from fbs.sources.govinfo.govinfo_types import (
    CollectionSummary,
    SearchResponse,
    SearchResult,
    SummaryItem,
    Bill,
)

# set up default sorts parameters
DEFAULT_SORTS = [
    {"field": "publishdate", "sortOrder": "ASC"},
]


class GovInfoSource:
    """
    Represents a source of data from the GovInfo API.
    """

    def __init__(self, **kwargs):
        """
        Initialize the source.

        Args:
            **kwargs:
        """
        # set the client key
        self.api_key = kwargs.get("api_key", os.getenv("GOVINFO_API_KEY", None))
        if not self.api_key:
            raise ValueError(
                "A key is required for govinfo API: https://www.govinfo.gov/api-signup"
            )

        # set the base url
        self.base_url = "https://api.govinfo.gov"

        # get the client
        self.client: httpx.Client = self._init_httpx_client()

        # set up the cache paths
        self.govinfo_cache_path = Path.home() / ".cache" / "fbs" / "govinfo"
        self.govinfo_cache_path.mkdir(parents=True, exist_ok=True)
        self.bill_cache_path = Path.home() / ".cache" / "fbs" / "bills"
        self.bill_cache_path.mkdir(parents=True, exist_ok=True)

        # cache collection info at startup
        self.collections = self.get_collections().collections

    @staticmethod
    def _init_httpx_client() -> httpx.Client:
        """
        Initialize the httpx Client with default values.

        Returns:
            httpx.Client: An httpx Client object.
        """
        # init
        client = httpx.Client(
            http1=True, http2=True, verify=False, follow_redirects=True
        )

        # set default headers
        client.headers.update(
            {
                "User-Agent": "federal-bill-statistics/0.1 (https://github.com/alea-institute/federal-bill-statistics)",
            }
        )

        # log initialization
        LOGGER.info("Initialized httpx client")

        return client

    def close(self):
        """
        Close the httpx clients.
        """
        self.client.close()

    def __del__(self):
        """
        Close the httpx clients when the object is deleted.
        """
        try:
            self.close()
        except Exception as e:
            LOGGER.error("Error closing httpx client: %s", e)

    def __enter__(self):
        """
        Return the source object.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the source object.
        """
        self.close()

    def get_url(self, path: str) -> str:
        """
        Get the full URL for the path.

        Args:
            path (str): Path to the resource

        Returns:
            str: Full URL for the resource
        """
        return f"{self.base_url}{path}"

    def _get_response(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Perform a GET request to the specified URL.

        Args:
            url (str): URL to GET.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            httpx.Response: Response object.
        """
        # merge headers
        request_headers = self.client.headers.copy()
        if headers:
            request_headers.update(headers)

        # get the response
        try:
            LOGGER.info("GET %s", url)
            response = self.client.get(url, headers=request_headers, params=params)
            # check the response for the x-rate-limit headers
            for key, value in response.headers.items():
                if key.lower() == "x-ratelimit-limit":
                    self.rate_limit_limit = int(value)
                elif key.lower() == "x-ratelimit-remaining":
                    self.rate_limit_remaining = int(value)

            # check the response
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            LOGGER.error("HTTP Status Error: %s", e)
            raise e

        return response

    def _post_response(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Perform a POST request to the specified URL.

        Args:
            url (str): URL to POST.
            data (str | bytes | Optional[dict[str, Any]]): Data to include in the request.
            json_data (Optional[dict[str, Any]]): Data to include in the request as JSON.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            httpx.Response: Response object.
        """
        # merge headers
        request_headers = self.client.headers.copy()
        if headers:
            request_headers.update(headers)

        # get the response
        try:
            LOGGER.info("POST %s", url)
            response = self.client.post(
                url, data=data, json=json_data, params=params, headers=request_headers
            )

            # check the response
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            LOGGER.error("HTTP Status Error: %s", e)
            raise e

        return response

    def _get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> bytes:
        """
        Perform a GET request to the specified URL.

        Args:
            url (str): URL to GET.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            bytes: Response content.
        """
        # check for cached path
        url_hash = hashlib.blake2b(url.encode()).hexdigest()
        url_cache_path = self.govinfo_cache_path / url_hash
        if url_cache_path.exists():
            with gzip.open(url_cache_path, "rb") as input_file:
                LOGGER.info("Using cached response for %s", url)
                return input_file.read()

        request_headers = dict(self.client.headers.copy())
        if headers:
            request_headers.update(headers)

        content = self._get_response(
            url=url, params=params, headers=request_headers
        ).content

        # cache the response
        with gzip.open(url_cache_path, "wb") as output_file:
            LOGGER.info("Caching response for %s", url)
            output_file.write(content)

        return content

    def _post(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> bytes:
        """
        Perform a POST request to the specified URL.

        Args:
            url (str): URL to POST.
            data (Optional[dict[str, Any]]): Data to include in the request.
            json_data (Optional[dict[str, Any]]): Data to include in the request as JSON.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            bytes: Response content.
        """
        request_headers = dict(self.client.headers.copy())
        if headers:
            request_headers.update(headers)

        return self._post_response(
            url=url,
            data=data,
            json_data=json_data,
            params=params,
            headers=request_headers,
        ).content

    def _get_json(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Perform a GET request to the specified URL and return the JSON response.

        Args:
            url (str): URL to GET.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            dict[str, Any]: JSON response content.
        """
        request_headers = dict(self.client.headers.copy())
        if headers:
            request_headers.update(headers)
        return json.loads(self._get(url=url, params=params, headers=request_headers))

    def _get_json_list(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform a GET request to the specified URL and return the JSON response as a list.

        Args:
            url (str): URL to GET.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            list[dict[str, Any]]: JSON response content as a list.
        """
        json_data = self._get_json(url=url, params=params, headers=headers)
        if isinstance(json_data, list):
            return json_data
        return [json_data]

    def _post_json(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Perform a POST request to the specified URL and return the JSON response.

        Args:
            url (str): URL to POST.
            data (Optional[dict[str, Any]]): Data to include in the request.
            json_data (Optional[dict[str, Any]]): Data to include in the request as JSON.
            params (Optional[dict[str, Any]]): Parameters to include in the request.
            headers (Optional[dict[str, Any]]): Headers to include in the request.

        Returns:
            dict[str, Any]: JSON response content.
        """
        request_headers = dict(self.client.headers.copy())
        if headers:
            request_headers.update(headers)
        return json.loads(
            self._post(
                url=url,
                data=data,
                json_data=json_data,
                params=params,
                headers=request_headers,
            )
        )

    def get_response_retry(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        max_retry: int = 3,
    ) -> httpx.Response:
        """
        Wrap GET requests with a 503 retry handled to simplify code related to the
        on-the-fly package/granule service generation.

        Args:
            url (str): The URL to get.
            headers (Optional[dict[str, str]]): The headers.
            params (Optional[dict[str, Any]]): The parameters.
            max_retry (int): The maximum number of retries.

        Returns:
            httpx.Response: The response.
        """
        # retry the request
        for _ in range(max_retry):
            try:
                # make the upstream call
                document_response = self._get_response(
                    url=url, headers=headers, params=params
                )

                # return directly if no 503
                if document_response.status_code not in (503,):
                    return document_response
            except httpx.HTTPStatusError as e:
                # NOTE: 503 really means "sleep for Retry-After" and try again
                # https://github.com/usgpo/api/blob/main/README.md#packages-service
                if e.response.status_code == 503:
                    LOGGER.info("Waiting for package service to generate...")
                    try:
                        retry_delay = int(e.response.headers.get("Retry-After", 30))
                    except ValueError:
                        retry_delay = 30

                    # sleep for the retry delay
                    time.sleep(retry_delay)
                    continue

                # raise directly if not 503
                raise e
            except Exception as e:
                # raise directly if not an httpx error
                LOGGER.error("Error downloading %s: %s", url, e)
                raise e

        # raise an error if we've exhausted retries
        raise RuntimeError(f"Exhausted retries for {url}")

    def get_collections(self) -> CollectionSummary:
        """
        Get the collections.

        Returns:
            CollectionSummary: The collection summary.
        """
        # set path
        path = "/collections"

        # get the response
        response_json = self._get_json(
            url=self.get_url(path),
            headers={"X-Api-Key": self.api_key},
        )

        # parse args
        summary_args = {k: v for k, v in response_json.items() if k != "collections"}
        summary_args["collections"] = [
            SummaryItem(**collection)
            for collection in response_json.get("collections", [])
        ]
        return CollectionSummary(**summary_args)

    def search(
        self,
        query: str,
        page_size: int = 100,
        offset_mark: str = "*",
        result_level: str = "default",
        historical: bool = True,
        sorts: Optional[List[Dict[str, str]]] = None,
    ) -> SearchResponse:
        """
        Search the GovInfo API.

        Args:
            query (str): The search query.
            page_size (int): The number of results per page.
            offset_mark (str): The offset mark.
            result_level (str): The result level.
            historical (bool): Whether to include historical content.
            sorts (List[Dict[str, str]]): Sorts for the search.

        Returns:
            SearchResponse: The search response.
        """
        # set the path
        path = "/search"

        # set the params
        post_data = {
            "query": query,
            "pageSize": page_size,
            "offsetMark": offset_mark,
            "resultLevel": result_level,
            "historical": historical,
            "sorts": sorts or DEFAULT_SORTS,
        }

        # get the response
        LOGGER.info("Searching GovInfo with query: %s", query)
        response = self._post_json(
            url=self.get_url(path),
            headers={"X-Api-Key": self.api_key},
            json_data=post_data,
        )

        # log result count
        LOGGER.info("Search returned %s results", response.get("count", 0))

        # set the results
        results = []
        for result in response.get("results", []):
            # set the result
            results.append(
                SearchResult(
                    title=result.get("title"),
                    packageId=result.get("packageId"),
                    granuleId=result.get("granuleId"),
                    collectionCode=result.get("collectionCode"),
                    resultLink=result.get("resultLink"),
                    relatedLink=result.get("relatedLink"),
                    lastModified=result.get("lastModified"),
                    dateIssued=result.get("dateIssued"),
                    dateIngested=result.get("dateIngested"),
                    governmentAuthor=result.get("governmentAuthor", []),
                    download=result.get("download", {}),
                )
            )

        # set the search response
        search_response = SearchResponse(
            count=response.get("count", 0),
            offsetMark=response.get("offsetMark", "*"),
            results=results,
        )

        # return the search response
        return search_response

    def get_result_link(self, url: str) -> bytes:
        """
        Get the result link.

        Args:
            url (str): The URL.

        Returns:
            bytes: The result link.
        """
        # add api_key
        url += f"?api_key={self.api_key}"

        # get the response
        return self._get(url)

    def get_bill(self, bill_result: SearchResult, llm_model: BaseAIModel) -> Bill:
        """
        Get the bill.

        Args:
            bill_result (SearchResult): The search result.
            llm_model (BaseAIModel): The LLM model.

        Returns:
            Bill: The bill.
        """
        # check if we have the package id in cache
        package_id_hash = hashlib.blake2b(bill_result.packageId.encode()).hexdigest()
        package_id_cache_path = self.bill_cache_path / package_id_hash
        if package_id_cache_path.exists():
            with gzip.open(package_id_cache_path, "rt", encoding="utf-8") as input_file:
                bill_data = json.loads(input_file.read())
                bill_data["date"] = datetime.datetime.fromisoformat(bill_data["date"])
                return Bill(**bill_data)

        # get relevant links and retrieve
        result_summary_link = bill_result.resultLink
        result_xml_link = bill_result.download.get("xmlLink")
        summary_data = json.loads(self.get_result_link(result_summary_link))
        xml_doc = lxml.etree.fromstring(self.get_result_link(result_xml_link))

        # parse the bill data
        bill_data = parse_xml_bill(
            xml_doc=xml_doc, summary_data=summary_data, llm_model=llm_model
        )
        bill_data.package_id = bill_result.packageId

        # cache the bill data
        with gzip.open(package_id_cache_path, "wt", encoding="utf-8") as output_file:
            output_file.write(json.dumps(bill_data.to_dict()))

        return bill_data
