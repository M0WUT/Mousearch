import json
import logging
from typing import Optional

import requests


class MouserBaseRequest:
    VERSION = "2"
    BASE_URL = f"https://api.mouser.com/api/v{VERSION}"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def post(self, url, data):
        post_headers = {
            "Content-Type": "application/json",
        }
        return requests.post(
            url=f"{self.BASE_URL}/{url}?apiKey={self.api_key}",
            data=json.dumps(data),
            headers=post_headers,
        )


class MouserAPI:
    def __init__(self, api_key: str, logger: Optional[logging.Logger] = None):

        self.api_key = api_key
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.WARNING)
            logger_handler = logging.StreamHandler()
            logger_handler.setLevel(logging.WARNING)
            self.logger.addHandler(logger_handler)

    def search_by_keyword(self, keyword):

        self.logger.debug(f"Searching for {keyword}")
        x = MouserBaseRequest(self.api_key)
        result = x.post(
            url="search/keyword",
            data={
                "SearchByKeywordRequest": {
                    "keyword": f"{keyword}",
                }
            },
        ).json()

        errors = result["Errors"]
        search_results = result["SearchResults"]
        assert not errors, f"Query for {keyword} return errors: {errors}"
        if len(search_results["Parts"]) != 1:
            print(search_results["Parts"])


if __name__ == "__main__":
    logger = logging.getLogger("Mousearch Debug")
    logger.setLevel(logging.DEBUG)
    logger_handler = logging.StreamHandler()
    logger_handler.setLevel(logging.DEBUG)
    logger.addHandler(logger_handler)
    with open("api_key.txt", "r") as file:
        api_key = file.readline()
    x = MouserAPI(api_key, logger)
    x.search_by_keyword("RK73H1ETTP6R80F")
