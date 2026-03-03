import json
from typing import Any, Unpack

import aiohttp

from superset_client.config import SupersetConfig
from superset_client.models import Chart, ChartDataResponse, Dashboard


class AuthError(Exception):
    pass


class APIError(Exception):
    pass


class NotFoundError(Exception):
    pass


class SupersetClient:
    def __init__(self, config: SupersetConfig):
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._csrf_token: str | None = None

    async def __aenter__(self) -> "SupersetClient":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        self.config.validate_for_connection()
        assert self.config.base_url is not None
        self._session = aiohttp.ClientSession(base_url=self.config.base_url)
        await self._authenticate()

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _authenticate(self) -> None:
        assert self._session is not None

        if self.config.uses_token_auth:
            self._access_token = self.config.api_token
            return

        if not self.config.uses_password_auth:
            raise AuthError("No valid authentication method configured")

        async with self._session.post(
            "/api/v1/security/login",
            json={
                "username": self.config.username,
                "password": self.config.password,
                "provider": "db",
                "refresh": True,
            },
        ) as resp:
            if resp.status != 200:
                raise AuthError(f"Authentication failed: {await resp.text()}")
            data = await resp.json()
            self._access_token = data["access_token"]

        async with self._session.get(
            "/api/v1/security/csrf_token/",
            headers=self._auth_headers(),
        ) as resp:
            if resp.status != 200:
                raise AuthError(f"CSRF token fetch failed: {await resp.text()}")
            data = await resp.json()
            self._csrf_token = data["result"]

    def _auth_headers(self) -> dict[str, str]:
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _headers(self) -> dict[str, str]:
        headers = self._auth_headers()
        if self._csrf_token:
            headers["X-CSRFToken"] = self._csrf_token
        headers["Content-Type"] = "application/json"
        return headers

    async def _request(
        self, method: str, path: str, **kwargs: Unpack[aiohttp.client._RequestOptions]
    ) -> dict:
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")

        kwargs.setdefault("headers", {}).update(self._headers())

        async with self._session.request(method, path, **kwargs) as resp:
            if resp.status >= 400:
                raise APIError(f"API error {resp.status}: {await resp.text()}")
            return await resp.json()

    async def get_dashboard(self, dashboard_id: int) -> Dashboard:
        data = await self._request("GET", f"/api/v1/dashboard/{dashboard_id}")
        return Dashboard(**data["result"])

    async def list_charts(
        self,
        page: int = 0,
        page_size: int = 100,
        filters: list[dict[str, Any]] | None = None,
        order_column: str | None = None,
        order_direction: str | None = None,
    ) -> tuple[list[Chart], int]:
        query_params: dict[str, Any] = {"page": page, "page_size": page_size}

        q: dict[str, Any] = {}
        if filters:
            q["filters"] = filters
        if order_column:
            q["order_column"] = order_column
        if order_direction:
            q["order_direction"] = order_direction

        if q:
            query_params["q"] = json.dumps(q)

        data = await self._request("GET", "/api/v1/chart/", params=query_params)
        charts = [Chart(**item) for item in data.get("result", [])]
        count = data.get("count", 0)
        return charts, count

    async def find_chart_by_name(self, name: str) -> Chart:
        charts, _ = await self.list_charts(
            filters=[{"col": "slice_name", "opr": "eq", "value": name}]
        )
        if not charts:
            raise NotFoundError(f"Chart not found: {name}")
        return charts[0]

    async def get_chart(self, chart_id: int) -> Chart:
        data = await self._request("GET", f"/api/v1/chart/{chart_id}")
        return Chart(**data["result"])

    async def get_chart_data(
        self,
        chart_id: int,
        format: str | None = None,
        type: str | None = None,
        force: bool | None = None,
    ) -> ChartDataResponse:
        params = {}
        if format is not None:
            params["format"] = format
        if type is not None:
            params["type"] = type
        if force is not None:
            params["force"] = force

        data = await self._request("GET", f"/api/v1/chart/{chart_id}/data/", params=params)
        return ChartDataResponse(**data)

    async def render_chart(self, form_data: dict[str, Any], queries: list[dict[str, Any]]) -> dict:
        return await self._request(
            "POST", "/api/v1/chart/data", json={"form_data": form_data, "queries": queries}
        )
