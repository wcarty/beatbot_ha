"""Beatbot cloud WebSocket event stream supervisor."""

import asyncio
from contextlib import suppress
import logging

from beatbot_cloud import (
    BeatbotAuthenticationError,
    BeatbotClient,
    BeatbotConnectionError,
    BeatbotEventClient as BeatbotCloudEventClient,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, OAuth2TokenRequestBaseError
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import BeatbotCoordinator

_LOGGER = logging.getLogger(__name__)


class BeatbotEventClient:
    """Connect Beatbot cloud WebSocket events to the Home Assistant coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
        api: BeatbotClient,
        coordinator: BeatbotCoordinator,
    ) -> None:
        """Initialize the Beatbot event client."""
        self._coordinator = coordinator
        self._hass = hass
        self._entry = entry
        self._oauth_session = oauth_session
        self._task: asyncio.Task[None] | None = None
        self._client = BeatbotCloudEventClient(
            async_get_clientsession(hass),
            api.event_stream_url,
            api.async_get_access_token,
            state_callback=coordinator.async_apply_device_event,
            device_added_callback=self._async_handle_device_added,
            reconnect_callback=coordinator.async_request_refresh,
            token_refresh_callback=self._async_refresh_token,
        )

    def async_start(self) -> None:
        """Start the WebSocket supervisor task."""
        if self._task is None or self._task.done():
            self._task = self._entry.async_create_background_task(
                self._hass,
                self._run(),
                f"beatbot_event_stream_{self._entry.entry_id}",
            )

    async def async_stop(self) -> None:
        """Stop and close the WebSocket stream."""
        await self._client.async_close()
        task, self._task = self._task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def _run(self) -> None:
        """Run the cloud event client with auth recovery."""
        while True:
            try:
                await self._client.async_run()
            except BeatbotAuthenticationError:
                _LOGGER.warning("Beatbot event stream authorization failed")
                await self._coordinator.async_request_refresh()
            else:
                return

            await self._async_wait_for_recovery()

    async def _async_wait_for_recovery(self) -> None:
        """Wait for a later successful refresh before retrying stream auth."""
        recovered = asyncio.Event()

        @callback
        def async_handle_update() -> None:
            if self._coordinator.last_update_success:
                recovered.set()

        unsub = self._coordinator.async_add_listener(async_handle_update)
        try:
            await recovered.wait()
        finally:
            unsub()

    async def _async_refresh_token(self, rejected_access_token: str) -> str:
        """Force-refresh a rejected access token via Home Assistant's OAuth session."""
        current_token = self._oauth_session.token
        if current_token.get("access_token") == rejected_access_token:
            self._hass.config_entries.async_update_entry(
                self._entry,
                data={
                    **self._entry.data,
                    "token": {**current_token, "expires_at": 0},
                },
            )

        try:
            await self._oauth_session.async_ensure_token_valid()
        except ConfigEntryAuthFailed as err:
            raise BeatbotAuthenticationError from err
        except OAuth2TokenRequestBaseError as err:
            raise BeatbotConnectionError("OAuth token refresh failed") from err

        access_token = self._oauth_session.token.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise BeatbotAuthenticationError
        return access_token

    async def _async_handle_device_added(self, device_id: str) -> None:
        """Refresh discovery when a new device appears on the account."""
        await self._coordinator.async_request_refresh()
