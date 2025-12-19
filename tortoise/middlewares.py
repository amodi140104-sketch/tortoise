import random


class RandomUserAgentMiddleware:
    """
    Rotate between realistic desktop Chrome UAs.
    Low entropy, low risk.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",

        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36",

        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36",
    ]

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(self.USER_AGENTS)


class FlipkartRetryMiddleware:
    """
    Gentle retry for soft blocks / transient failures.
    """

    MAX_RETRIES = 2

    def process_response(self, request, response, spider):
        if response.status in (429, 503):
            retries = request.meta.get("retry_times", 0)
            if retries < self.MAX_RETRIES:
                spider.logger.warning(
                    f"Retrying {request.url} ({response.status})"
                )
                new_request = request.copy()
                new_request.meta["retry_times"] = retries + 1
                new_request.dont_filter = True
                return new_request
        return response
