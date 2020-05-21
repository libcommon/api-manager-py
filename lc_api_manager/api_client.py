## -*- coding: UTF-8 -*-
## api_client.py
##
## Copyright (c) 2019 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.


from typing import Any, Optional

from lc_cache import gen_python_hash


__author__ = "libcommon"


class RateLimitReachedError(ConnectionError):
    """Signals that an API response was received
    that stated the rate limit has been reached. This lets
    the API manager know its accounting system has
    failed and _should_ trigger an appropriate action from
    the manager.
    """


class APIClient:
    """Interface for API clients to use with an APIManager."""
    __slots__ = ()

    def gen_request_hash(self, *args, **kwargs) -> Any: # pylint: disable=R0201
        """
        Args:
            Takes any positional or keyword arguments
        Returns:
            Unique hash of positional and keyword arguments.  Default implementation uses
            Python's native hashing function to produce an int (see: cache.gen_python_hash).
            Child classes may override this method, though the parameters should match the
            query method signature.
        Preconditions:
            All positional and keyword arguments are hashable
        Raises:
            TypeError: if any positional or keyword argument is not hashable
        """
        return hash((gen_python_hash(args), gen_python_hash(kwargs)))

    def process_response_for_cache(self, response: Optional[Any]) -> Any:   # pylint: disable=R0201
        """
        Args:
            response    => API response
        Returnes:
            Response data processed for the cache maintained in APIManager.  Default
            implementation simply returns the response.  This method _should not_ raise
            an exception.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        return response

    def request(self, *args, **kwargs) -> Any:
        """
        Args:
            Takes any positional or keyword arguments
        Returns:
            Response from API request.
        Preconditions:
            N/A
        Raises:
            RateLimitReachedError: if API signals that rate limit has been reached
