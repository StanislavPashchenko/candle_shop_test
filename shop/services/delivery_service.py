import json
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def get_nova_poshta_warehouses(city: str):
    city = (city or "").strip()
    if not city:
        return []

    api_key = getattr(settings, "NOVA_POSHTA_API_KEY", "")
    if not api_key:
        logger.warning("Nova Poshta API key not configured")
        return []

    try:
        url = "https://api.novaposhta.ua/v2.0/json/"
        payload = {
            "apiKey": api_key,
            "modelName": "AddressGeneral",
            "calledMethod": "searchSettlements",
            "methodProperties": {"CityName": city, "Limit": 50},
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        if data.get("success") and data.get("data"):
            settlements = data["data"][0].get("Addresses", [])

            if settlements:
                settlement_ref = settlements[0]["DeliveryCity"]

                payload2 = {
                    "apiKey": api_key,
                    "modelName": "AddressGeneral",
                    "calledMethod": "getWarehouses",
                    "methodProperties": {"CityRef": settlement_ref, "Limit": 200},
                }

                req2 = urllib.request.Request(
                    url,
                    data=json.dumps(payload2).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    data2 = json.loads(resp2.read().decode("utf-8", errors="replace"))

                if data2.get("success") and data2.get("data"):
                    return [
                        {"id": w["Ref"], "name": w["Description"]}
                        for w in data2["data"]
                    ]
    except Exception as e:
        logger.error(f"Nova Poshta API error: {e}")

    return []
