import httpx

from app.config import settings


async def get_weather(lat: float, lng: float) -> dict | None:
    if not settings.openweather_api_key:
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lng,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()

        weather_main = data.get("weather", [{}])[0].get("main", "Clear")
        temp = data.get("main", {}).get("temp", 20)

        is_outdoor_ok = (
            weather_main not in ("Thunderstorm", "Snow", "Extreme")
            and temp > 0
            and temp < 38
        )

        return {
            "description": weather_main,
            "temperature": temp,
            "is_outdoor_ok": is_outdoor_ok,
        }
    except Exception:
        return None
