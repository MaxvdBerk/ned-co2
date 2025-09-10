from __future__ import annotations
from datetime import datetime, timedelta, timezone
import logging
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import now as ha_now

from .const import (
    BASE_URL,
    TYPE_ELECTRICITY_MIX,
    ACTIVITY_PROVIDING,
    CLASS_CURRENT,
    CLASS_FORECAST,
    CONF_API_KEY,
    CONF_POINT,
    CONF_GRANULARITY,
    CONF_WINDOW_DAYS,
    CONF_LOCAL_TZ_FILTER,
    DEFAULT_POINT,
    DEFAULT_GRANULARITY,
    DEFAULT_WINDOW_DAYS,
    DEFAULT_LOCAL_TZ_FILTER,
)

_LOGGER = logging.getLogger(__name__)


def _dates_for_window(days: int, local_tz: bool):
    """Return (after, before) date filters for the API."""
    n = ha_now() if local_tz else datetime.now(timezone.utc)
    start = (n - timedelta(days=1)).date()
    end = (n + timedelta(days=days)).date()
    return start.isoformat(), end.isoformat()


class NedCoordinator(DataUpdateCoordinator):
    """Coordinator fetching NED CO₂ data."""

    def __init__(self, hass: HomeAssistant, data: dict, options: dict):
        self.hass = hass
        self.api_key = data.get(CONF_API_KEY)
        self.point = int(options.get(CONF_POINT, DEFAULT_POINT))
        self.granularity = int(options.get(CONF_GRANULARITY, DEFAULT_GRANULARITY))
        self.window_days = int(options.get(CONF_WINDOW_DAYS, DEFAULT_WINDOW_DAYS))
        self.local_tz_filter = bool(
            options.get(CONF_LOCAL_TZ_FILTER, DEFAULT_LOCAL_TZ_FILTER)
        )

        super().__init__(
            hass,
            _LOGGER,
            name="NED CO₂",
            update_interval=timedelta(minutes=5),
        )

    def update_options(self, options: dict) -> None:
        """Update options when entry changes."""
        self.point = int(options.get(CONF_POINT, DEFAULT_POINT))
        self.granularity = int(options.get(CONF_GRANULARITY, DEFAULT_GRANULARITY))
        self.window_days = int(options.get(CONF_WINDOW_DAYS, DEFAULT_WINDOW_DAYS))
        self.local_tz_filter = bool(
            options.get(CONF_LOCAL_TZ_FILTER, DEFAULT_LOCAL_TZ_FILTER)
        )

    async def _async_update_data(self):
        """Fetch data from NED API."""
        after, before = _dates_for_window(self.window_days, self.local_tz_filter)
        params = {
            "point": self.point,
            "type": TYPE_ELECTRICITY_MIX,
            "activity": ACTIVITY_PROVIDING,
            "granularity": self.granularity,
            "granularitytimezone": 1 if self.local_tz_filter else 0,
            "validfrom[after]": after,
            "validfrom[strictly_before]": before,
        }
        headers = {
            "accept": "application/ld+json",
            "X-AUTH-TOKEN": self.api_key,
        }

        async with aiohttp.ClientSession() as sess:

            async def fetch(classification: int):
                q = params.copy()
                q["classification"] = classification
                async with sess.get(BASE_URL, params=q, headers=headers) as r:
                    if r.status != 200:
                        text = await r.text()
                        raise UpdateFailed(
                            f"NED HTTP {r.status}: {text[:200]}"
                        )
                    return await r.json()

            current = await fetch(CLASS_CURRENT)
            forecast = await fetch(CLASS_FORECAST)

        return {
            "current": current,
            "forecast": forecast,
            "meta": {
                "after": after,
                "before": before,
                "tz": "local" if self.local_tz_filter else "utc",
            },
        }

    @staticmethod
    def _match_current_slot(rows: list[dict]) -> dict | None:
        """Find the row matching the current UTC time."""
        now_utc = datetime.now(timezone.utc)
        hit = None
        for r in rows:
            try:
                vf = datetime.fromisoformat(r["validfrom"].replace("Z", "+00:00"))
                vt = datetime.fromisoformat(r["validto"].replace("Z", "+00:00"))
                if vf <= now_utc < vt:
                    return r
                # fallback: last past slot
                if vf <= now_utc:
                    if not hit or vf > datetime.fromisoformat(
                        hit["validfrom"].replace("Z", "+00:00")
                    ):
                        hit = r
            except Exception:
                continue
        return hit

    @staticmethod
    def _min_slot(rows: list[dict]) -> dict | None:
        """Return the row with the minimum emission factor."""
        slots = [r for r in rows if r.get("emissionfactor") is not None]
        return min(slots, key=lambda r: r["emissionfactor"]) if slots else None
