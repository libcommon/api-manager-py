# api-manager-py

## Overview

Many APIs with rate limits push responsibility on API users to manage rate limiting, including those with SDKs.
`api-manager-py` is a Python library that aims to abstract away the complexity of managing rate limits,
allowing developers to focus on retrieving desired data without hacking together buggy, case-by-case solutions.
The API management functionality does not require using a specific library for interacting with an API, and will
automatically cache responses based on input parameters to reduce network IO. Simply implement a small API client
interface and start making requests.

## Installation

### Install from PyPi (preferred method)

```bash
pip install lc-api-manager
```

### Install from GitHub with Pip

```bash
pip install git+https://github.com/libcommon/api-manager-py.git@vx.x.x#egg=lc_api_manager
```

where `x.x.x` is the version you want to download.

## Install by Manual Download

To download the source distribution and/or wheel files, navigate to
`https://github.com/libcommon/api-manager-py/tree/releases/vx.x.x/dist`, where `x.x.x` is the version you want to install,
and download either via the UI or with a tool like wget. Then to install run:

```bash
pip install <downloaded file>
```

Do _not_ change the name of the file after downloading, as Pip requires a specific naming convention for installation files.

## Dependencies

`api-manager-py` depends on the [lc-cache](https://pypi.org/project/lc-cache/) library for caching API responses. Only
Python versions >= 3.6 are officially supported.

## Getting Started

The first step is to implement an `APIClient` and choose a library to make HTTP requests. One common choice is the
[Requests](https://2.python-requests.org/en/master/) library, which we'll use to implement a client for the [GitHub REST API
v3](https://developer.github.com/v3/). The domain for GitHub's API is `https://api.github.com`, so the client's `request` method
only needs the HTTP method (`GET`, `POST`, etc.), API endpoint (i.e., `/repos/<username>/<repo_name>`), and optional `headers`,
`params`, and `data` dictionaries (see: [Requests documentation](https://2.python-requests.org/en/master/user/quickstart/#make-a-request)).

```python
from hashlib import sha256
from typing import Any, Dict, Optional

import requests
from requests import Response

from lc_api_manager import APIClient

class GitHubAPIClient(APIClient):
    """API client for GitHub Rest API v3."""
    __slots__ = ("_headers",)

    def __init__(self, auth_token: Optional[str] = None) -> None:
        """Initialize API client with optional GitHub API oauth token
        see: https://developer.github.com/v3/#authentication.
        """
        if auth_token:
            self._headers = {"Authorization": "token {}".format(auth_token)}
        else:
            self._headers = dict()

    def process_response_for_cache(self, response: Optional[Response]) -> Optional[str]:
        """Return the SHA-256 hash of the API response if not None."""
        if response:
            return sha256(response.text.encode("utf8")).hexdigest()
        return None

    def request(http_method: str,
                api_endpoint: str,
                headers: Optional[Dict[str, Any]],
                params: Optional[Dict[str, Any]],
                data: Optional[Dict[Any, Any]]) -> Response:
        """Make request to GitHub REST API endpoint with provided
        headers, URL parameters, and data and return response."""
        # Merge authorization header with provided headers
        merged_headers = self._headers
        if headers:
            merged_headers.update(headers)

        # Construct full URL and make request
        url = "https://api.github.com/{}".format(api_endpoint.lstrip("/"))
        response = requests.request(http_method.upper(), url, params=params, data=data, headers=merged_headers)

        # Raise error if status code is 4XX or 5XX
        response.raise_for_status()
        return response
```

With a functional `APIClient`, we can start making requests and caching them using the built-in `APIManager` class:

```python
from lc_api_manager import APIManager
from lc_cache import HashmapCache

def main() -> int:
    """Make 60 unauthenticated requests to an API endpoint in rapid succession."""
    api_manager = APIManager(3600, # GitHub API allows 60 unauthenticated requests per hour
                             60,
                             GitHubAPIClient(),
                             HashmapCache())

    # Make 60 requests to the same API endpoint
    for _ in range(60):
        # The API manager will make the request on first iteration,
        # but will return cached response on the other 59
        response = api_manager.request("GET", "repos/libcommon/api-manager-py", params=dict(per_page=100))

    # Check rate limit status, should be 59 requests remaining
    # See: https://developer.github.com/v3/rate_limit/
    response = api_manager.request("GET", "rate_limit")
    requests_remaining = response.json().get("resources").get("core").get("remaining")
    assert(requests_remaining == 59)

    return 0

if __name__ == "__main__":
    main()
```

If you are running multiple Python processes requesting data from the same API, and want to ensure that all of them
respect the rate limit requirements, you could override the `APIManager.update_state` method. The `APIManager` constructor
has a parameter called `updated_state_before_request`, which defaults to False. If you set this to `True`, the `update_state`
method will be called before every API request, and thus can be used to sync rate limiting state across multiple processes.
For example, you could use the `/rate_limit` GitHub API endpoint to implement this method:

```python
from lc_api_manager import APIManager


def GitHubAPIManager(APIManager):
    """API manager for GitHub REST API v3 that syncs rate limiting state."""
    __slots__ = ()

    def __init__(self, *args, **kwargs) -> None:
        if not kwargs.get("update_state_before_request"):
            kwargs["update_state_before_request"] = True
        super().__init__(*args, **kwargs)

    def update_state(self) -> None:
        """Make request to /rate_limit endpoint and update rate limit status."""
        response = self._client.request("GET", "rate_limit")
        requests_remaining = response.json().get("resources").get("core").get("remaining")
        self._count = self._threshold - requests_remaining
```

## Contributing/Suggestions

Contributions and suggestions are welcome! To make a feature request, report a bug, or otherwise comment on existing
functionality, please file an issue. For contributions please submit a PR, but make sure to lint, type-check, and test
your code before doing so. Thanks in advance!
