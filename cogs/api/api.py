import asyncio
import logging
import os
import re
import time
from functools import wraps
from typing import Any, ClassVar, TypeVar

import aiohttp

from config import ConfigManager

T = TypeVar("T", bound="API")
ResponseType = tuple[Any, int]


class API:
    # Base configuration
    url: ClassVar[str] = ""
    headers: ClassVar[dict[str, str]] = {}
    cookies: ClassVar[dict[str, str]] = {}

    # Session management
    _session: ClassVar[aiohttp.ClientSession | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _last_used: ClassVar[float] = 0
    _session_ttl: ClassVar[float] = 300  # 5 minutes

    # Error handling and retry configuration
    _max_retries: ClassVar[int] = 3
    _retry_delay: ClassVar[float] = 1.0
    _timeout: ClassVar[aiohttp.ClientTimeout] = aiohttp.ClientTimeout(total=30)
    _logger: ClassVar[logging.Logger] = logging.getLogger("API")

    @classmethod
    def configure(
        cls: type[T],
        *,
        url: str | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        session_ttl: float | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
        timeout: float | None = None,
    ) -> type[T]:
        """Configure API parameters."""
        if url is not None:
            cls.url = url.rstrip("/")
        if headers is not None:
            cls.headers = headers
        if cookies is not None:
            cls.cookies = cookies
        if session_ttl is not None:
            cls._session_ttl = session_ttl
        if max_retries is not None:
            cls._max_retries = max_retries
        if retry_delay is not None:
            cls._retry_delay = retry_delay
        if timeout is not None:
            cls._timeout = aiohttp.ClientTimeout(total=timeout)
        return cls

    @classmethod
    async def _ensure_session(cls: type[T]) -> None:
        """Ensure an active session exists or create a new one."""
        current_time = time.time()

        # If the session exists but is expired, close it
        if (
            cls._session
            and not cls._session.closed
            and current_time - cls._last_used > cls._session_ttl
        ):
            cls._logger.debug("Session expired, closing...")
            await cls.close()

        # If no session or session is closed, create a new one
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    cls._logger.debug("Creating a new session...")
                    cls._session = aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(limit=10, ssl=False),
                        headers=cls.headers,
                        cookies=cls.cookies,
                        timeout=cls._timeout,
                    )

        cls._last_used = current_time

    @classmethod
    async def close(cls: type[T]) -> None:
        """Close the HTTP session if it exists."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
            cls._logger.debug("Session closed")

    @classmethod
    async def _request(
        cls: type[T], method: str, route: str, *args, retry_count: int = 0, **kwargs
    ) -> ResponseType:
        """Execute an HTTP request with error handling and retries."""
        await cls._ensure_session()
        url = f"{cls.url}/{route.strip('/')}"
        if args:
            url = f"{url}/{'/'.join(str(arg) for arg in args)}"

        cls._logger.debug(f"Sending {method} to {url}")

        try:
            async with cls._session.request(method, url, **kwargs) as response:
                cls._last_used = time.time()

                # Handle rate limiting and server errors with retries
                if response.status in {429, 500, 502, 503, 504} and retry_count < cls._max_retries:
                    retry_after = int(response.headers.get("Retry-After", cls._retry_delay))
                    cls._logger.warning(
                        f"Error {response.status}, retrying in {retry_after}s "
                        f"({retry_count + 1}/{cls._max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                    return await cls._request(
                        method, route, *args, retry_count=retry_count + 1, **kwargs
                    )

                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    # Fallback if the response is not JSON
                    data = await response.text()

                return data, response.status

        except (TimeoutError, aiohttp.ClientError) as e:
            cls._logger.error(f"Connection error: {str(e)}")

            # Retry with exponential backoff
            if retry_count < cls._max_retries:
                # Reset the session in case of an error
                await cls.close()
                await asyncio.sleep(cls._retry_delay * (2**retry_count))
                return await cls._request(
                    method, route, *args, retry_count=retry_count + 1, **kwargs
                )

            raise ConnectionError(
                f"Connection failed after {cls._max_retries} attempts: {str(e)}"
            ) from e

    @classmethod
    async def __aenter__(cls: type[T]) -> type[T]:
        """Class context manager for use with 'async with'."""
        await cls._ensure_session()
        return cls

    @classmethod
    async def __aexit__(cls: type[T], *exc_details) -> None:
        """Close the session when exiting the context manager."""
        await cls.close()

    @staticmethod
    def endpoint(route: str, method: str = "GET") -> callable:
        """
        Decorator to easily create API endpoints.

        Args:
            route: The API route with optional format placeholders like {param_name}
            method: The HTTP method (GET, POST, etc.)

        Usage:
            @API.endpoint('/auteurs/{id_author}')
            def get_author(cls, data, status, id_author, **kwargs):
                # Function implementation
        """

        def decorator(func: callable):
            @wraps(func)
            def wrapped(cls, data, status, *args, **kwargs):
                return func(cls, data, status, *args, **kwargs)

            async def wrapper(cls: type[T], *args, **kwargs) -> Any:
                # Extract request-specific parameters
                request_kwargs = {}
                request_keys = {"params", "json", "data", "headers", "cookies", "allow_redirects"}

                # Format the route with args - replace {placeholders} with values
                formatted_route = route
                route_params = {}
                param_names = re.findall(r"{([^}]+)}", route)

                # If args are provided, use them to replace route parameters in order
                if param_names and args:
                    for i, param_name in enumerate(param_names):
                        if i < len(args):
                            route_params[param_name] = args[i]

                    # Replace the parameters in the route
                    for param_name, param_value in route_params.items():
                        formatted_route = formatted_route.replace(
                            f"{{{param_name}}}", str(param_value)
                        )

                # Extract special request parameters from kwargs
                for key in list(kwargs.keys()):
                    if key in request_keys:
                        request_kwargs[key] = kwargs.pop(key)

                # Add any remaining kwargs to the request params
                if kwargs:
                    if "params" not in request_kwargs:
                        request_kwargs["params"] = {}
                    request_kwargs["params"].update(kwargs)

                # Special case for POST/PUT/PATCH with json payload
                if (
                    "json" not in request_kwargs
                    and method in {"POST", "PUT", "PATCH"}
                    and "data" not in request_kwargs
                ) and "json_data" in kwargs:
                    request_kwargs["json"] = kwargs.pop("json_data")

                # Make the request with formatted route
                data, status = await cls._request(method, formatted_route, **request_kwargs)

                # Pass the original args and kwargs to the wrapped function
                return wrapped(cls, data, status, *args, **kwargs)

            return classmethod(wrapper)

        return decorator


class MistralAI(API):
    url = "https://api.mistral.ai"
    api_key = os.getenv("MISTRAL_API_KEY", ConfigManager.get("mistral_key"))
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    @API.endpoint("/v1/chat/completions", method="POST")
    def chat_completion(cls, data, status, **kwargs):
        if status == 200:
            content = data["choices"][0]["message"]["content"]
            return re.sub(r"<@&?\d+>|@everyone|@here", "X", content)
        elif status == 422:
            raise ValueError(data["detail"][-1]["msg"])
        else:
            raise RuntimeError(f"API Error {status}: {data.get('message', 'Unknown error')}")


class RootMe(API):
    url = "https://api.www.root-me.org"

    @classmethod
    def setup(cls, api_key: str = None):
        """Configure the RootMe API with an API key."""
        if api_key:
            cls.cookies = {"api_key": api_key}
        else:
            if os.getenv("ROOTME_API_KEY"):
                cls.cookies = {"api_key": os.getenv("ROOTME_API_KEY")}
            else:
                # If no API key provided, check configuration
                from utils import ConfigManager

                if not ConfigManager.get("rootme_key"):
                    raise ValueError("API key is required for RootMe API")

                cls.cookies = {"api_key": ConfigManager.get("rootme_key")}

        return cls

    @API.endpoint("/challenges")
    def get_challenges(cls, data, status, **kwargs):
        """
        Get challenges data with optional filtering.

        Parameters:
        - titre: Filter by title
        - soustitre: Filter by subtitle
        - lang: Filter by language
        - score: Filter by score
        - id_auteur[]: List of author IDs
        """
        if status != 200:
            raise Exception(f"Failed to fetch challenges: Status {status}")
        return data

    @API.endpoint("/challenges/{id_challenge}")
    def get_challenge(cls, data, status, id_challenge):
        """
        Get details for a specific challenge by ID.

        Parameters:
        - id_challenge: The challenge ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch challenge {id_challenge}: Status {status}")
        return data

    @API.endpoint("/auteurs")
    def get_authors(cls, data, status, **kwargs):
        """
        Get authors data with optional filtering.

        Parameters:
        - nom: Filter by name
        - statut: Filter by status
        - lang: Filter by language
        """
        if status != 200:
            raise Exception(f"Failed to fetch authors: Status {status}")
        return data

    @API.endpoint("/auteurs/{id_author}")
    def get_author(cls, data, status, id_author):
        """
        Get details for a specific author by ID.

        Parameters:
        - id_author: The author ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch author {id_author}: Status {status}")
        return data

    @API.endpoint("/classement")
    def get_leaderboard(cls, data, status, **kwargs):
        """
        Get leaderboard data.

        Parameters:
        - debut_classement: Starting position for pagination
        """
        if status != 200:
            raise Exception(f"Failed to fetch leaderboard: Status {status}")
        return data

    @API.endpoint("/environnements_virtuels")
    def get_virtual_environments(cls, data, status, **kwargs):
        """
        Get virtual environments data with optional filtering.

        Parameters:
        - nom: Filter by name
        - os: Filter by operating system
        """
        if status != 200:
            raise Exception(f"Failed to fetch virtual environments: Status {status}")
        return data

    @API.endpoint("/environnements_virtuels/{id_env}")
    def get_virtual_environment(cls, data, status, id_env):
        """
        Get details for a specific virtual environment by ID.

        Parameters:
        - id_env: The environment ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch virtual environment {id_env}: Status {status}")
        return data
