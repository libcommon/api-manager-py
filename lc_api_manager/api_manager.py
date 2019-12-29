## -*- coding: UTF-8 -*-
## api_manager.py
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


from datetime import datetime
import time

from .api_client import APIClient, RateLimitReachedError
from .lib.cache import Cache


__author__ = "libcommon"


class APIManager:
    """Manage requests to an API to transparently respect rate limits and cache
    requests to reduce duplicative requests."""
    __slots__ = (
        "cache",
        "interval",
        "interval_buffer",
        "threshold",
        "_cache_on_failure",
        "_client",
        "_count",
        "_start_time")

    def __init__(self,
                 interval: int,
                 threshold: int,
                 client: APIClient,
                 cache: Cache,
                 interval_buffer: int = 3,
                 cache_on_failure: bool = True) -> None:
        if interval <= 0: raise ValueError("Interval must be greater than 0")
        if threshold <= 0: raise ValueError("Threshold must be greater than 0")
        if interval_buffer < 0: raise ValueError("Interval buffer must be greater than or equal to 0")

        self.interval = interval + interval_buffer
        self.threshold = threshold
        self._client = client
        self.cache = cache
        self._cache_on_failure = cache_on_failure
        self._count, self._start_time = self.gen_initial_state()

    def gen_initial_state(self) -> Tuple[int, Optional[float]]:
        """
        Args:
            N/A
        Returns:
            Initial count and start time.  Default implementation sets state
            as if no API requests have been made.  In situations where multiple
            programs, or multiple runs of the same program, are using the same API,
            child classes may override this function to set the actual count and start time.
            For example, suppose an API has a rate limit of 5,000 requests/hour, and provides
            an endpoint "/api/v1/rate_limit" that returns the number of requests made toward
            the rate limit.  A child class could make a request to that API when the APIManager
            is instantiated to properly set count and start time, otherwise the API manager
            would be ineffective.
            NOTE:
                When setting start time from an API response, ensure the timezone is UTC to
                avoid any incongruence with reset_state.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        return 0, None

    def reset_state(self) -> None:
        """
        Args:
            N/A
        Procedure:
            Reset count and start time.  Used to reset state once the rate limit interval has been reached.
            Even though this method is public, you should not use it unless you know what you're doing.
        Preconditions:
            N/A
        Raises:
            ValueError: if start time is set to be ahead of the time at which this method is called
        """
        self._count = 0
        self._start_time = datetime.utcnow().timestamp()

    def gen_remaining_time(self) -> float:
        """
        Args:
            N/A
        Returns:
            Amount of time in seconds remaining in the current interval.  If amount of time
            passed is greater than the interval (plus the interval buffer), resets count
            and start time.
        Preconditions:
            N/A
        Raises:
            ValueError: if start time is ahead of current timestamp
        """
        # If timer hasn't been set, return interval
        if self._start_time is None:
            return self.interval
        # Get current timestamp
        current_ts = datetime.utcnow().timestamp()
        # Start time can't be after current timestamp
        if self._start_time > current_ts:
            raise ValueError("Start time is ahead of current timestamp ({} > {})".format(self._start_time, current_ts))
        # Time remaining is length of the interval minus time passed in current interval
        return float(self.interval) - (current_ts - self._start_time)

    def gen_remaining_requests(self) -> int:
        """
        Args:
            N/A
        Returns:
            Number of remaining requests.  If start time hasn't been set, returns threshold.
            If the amount of time passed is greater than the interval (plus the interval buffer),
            resets count and start time.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        # If the time remaining is greater than the interval
        # (AKA passed into new interval), reset state
        if self.gen_remaining_time() > self.interval:
            self.reset_state()
        return self.threshold - self._count
    
    def _defer_until_next_interval(self) -> None:
        """
        Args:
            N/A
        Procedure:
            Calculate remaining time in interval and sleep.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        # Generate time remaining in interval
        # NOTE: It's possble that the rate limit was reached before this block,
        # but entered a new interval within this block. In this case,
        # the API manager will simply sleep for the remainder of the interval.
        # This implementation may change in the future to handle this (edge) case
        # depending on how often it occurs.
        remaining_time = self.gen_remaining_time()
        # Sleep for remainder of interval
        time.sleep(remaining_time)
        # Reset state
        self.reset_state()

    def _make_request(self, rate_limit_reached: bool, *args, **kwargs) -> Optional[Any]:
        """
        Args:
            rate_limit_reached  => signal of whether rate limit has been reached
                                   to be passed back to caller
        Returns:
            Attempt API request and, if successful, add response to cache and return it.
            If rate limit is reached, returns None.
        Preconditions:
            N/A
        Raises:
            Exception: if API request fails (other than a RateLimitReachedError)
        """
        try:
            # Submit request to API and get response
            response = self._client.request(*args, **kwargs)
            # Signal that response was successful
            response_was_successful = True
            # Process response and insert into cache
            self.cache.insert(self._client.process_response_for_cache(response))
            return response
        except RateLimitReachedError:
            # Signal that API response stated the API rate limit was reached.
            # This will cause the API manager to sleep for the remainder of the
            # interval.  See api_client.RateLimitReachedError.
            rate_limit_reached = True
            return None
        except Exception as exc:
            # If caching failed requests, process and insert into cache
            if self._cache_on_failure:
                self.cache.insert(self._client.process_response_for_cache(None))
            raise
        finally:
            # NOTE: Increment count on successful and failed API requests, because
            # some APIs may count unsuccessful requests toward rate limit.
            self._count += 1

    def request(self, *args, request_hash: Any = None, **kwargs) -> Any:
        """
        Args:
            Takes any positional or keyword arguments
        Returns:
            If the result of this request has already been cached, return cached response.
            Otherwise, submit API request pursuant to rate limit, and cache response.
            If rate limit reached, will sleep for remainder of interval then
            retry the API request.
        Preconditions:
            N/A
        Raises:
            
        """
        # Generate request hash if not provided
        if request_hash is None:
            try:
                request_hash = self._client.gen_request_hash(*args, **kwargs)
            except Exception as exc:
                err_type = type(exc)
                raise err_type("Failed to generate request hash: {}".format(exc.message))
        # If request hash in cache, return cached response
        # NOTE: Must use `check` here instead of `get` -> check for None value, because
        # in certain cases None may be a valid cached value for a request hash.
        if self.cache.check(request_hash):
            return self.cache.get(request_hash)
        # Generate remaining requests in interval
        remaining_requests = self.gen_remaining_requests()
        rate_limit_reached = False
        # If requests remaining in interval
        if remaining_requests > 0:
            # Attempt API request
            response = self._make_request(rate_limit_reached, *args, **kwargs)
        # If ran out of API requests or API client signalled the rate limit was reached
        if remaining_requests == 0 or rate_limit_reached:
            # Sleep until the next interval
            self._defer_until_next_interval()
            # Re-submit API request
            return self.request(*args, request_hash=request_hash, **kwargs)
        # Otherwise, return response
        else:
            return response
