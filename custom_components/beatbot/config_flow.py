"""Config flow for the Beatbot custom integration."""

from collections.abc import Mapping
import logging
from typing import Any, override

from beatbot_cloud import (
    BeatbotAuthenticationError,
    BeatbotClient,
    BeatbotConnectionError,
    decode_access_token,
)
from beatbot_cloud.const import OAUTH2_CLIENT_ID, REGION_API_BASE_URL

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BeatbotConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle an OAuth2 PKCE config flow for Beatbot."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    @override
    def logger(self) -> logging.Logger:
        """Return the flow logger."""
        return _LOGGER

    async def _async_ensure_public_credential(self) -> None:
        """Register Beatbot's public OAuth2 PKCE client ID."""
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(OAUTH2_CLIENT_ID, "", name="Beatbot"),
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start a flow using Beatbot's public OAuth client."""
        await self._async_ensure_public_credential()
        return await super().async_step_user(user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication dialog."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        await self._async_ensure_public_credential()
        return await super().async_step_user()

    @override
    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create or update the config entry using identity and region token claims."""
        access_token = (data.get("token") or {}).get("access_token")
        claims = (
            decode_access_token(access_token) if isinstance(access_token, str) else None
        )
        if claims is None or not isinstance(sub := claims.get("sub"), str) or not sub:
            return self.async_abort(reason="oauth_error")

        if region := claims.get("region"):
            data["region"] = str(region)
        if data.get("region") not in REGION_API_BASE_URL:
            return self.async_abort(reason="unknown_region")

        await self.async_set_unique_id(sub)

        if self.source == SOURCE_REAUTH:
            reauth_entry = self._get_reauth_entry()
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            if abort_result := await self._async_validate_resource_api(data):
                return abort_result
            return self.async_update_reload_and_abort(
                reauth_entry,
                data_updates=data,
            )

        self._abort_if_unique_id_configured()
        if abort_result := await self._async_validate_resource_api(data):
            return abort_result
        return self.async_create_entry(title="Beatbot", data=data)

    async def _async_validate_resource_api(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult | None:
        """Verify the token can access the regional Beatbot device API."""
        client = BeatbotClient(
            data["region"],
            async_get_clientsession(self.hass),
            data["token"]["access_token"],
        )
        try:
            await client.get_devices()
        except BeatbotAuthenticationError:
            return self.async_abort(reason="oauth_error")
        except BeatbotConnectionError:
            return self.async_abort(reason="cannot_connect")
        return None
