import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol


def _get_geo_user_agent() -> str:
    """Return compliant User-Agent for OSM/Photon, configurable via environment."""
    explicit_agent = os.environ.get("GEOLOCATION_USER_AGENT", "").strip()
    if explicit_agent:
        return explicit_agent
    contact = os.environ.get("GEOLOCATION_CONTACT_EMAIL", "").strip()
    if contact:
        return f"VinFast-Booking-Agent/1.0 (contact: {contact})"
    return "VinFast-Booking-Agent/1.0 (https://github.com/AI20K-Build-Phase-Cohort-3/P-053)"


def _parse_retry_after(error: urllib.error.HTTPError, default_seconds: float = 60.0) -> float:
    """Extract Retry-After header duration in seconds if present."""
    try:
        if error.headers:
            header_val = error.headers.get("Retry-After")
            if header_val:
                return max(1.0, float(header_val))
    except (ValueError, TypeError):
        pass
    return default_seconds


class _CircuitBreaker:
    """Thread-safe circuit breaker with synchronized cooldown tracking and Retry-After support."""

    def __init__(self, default_cooldown_seconds: float = 60.0) -> None:
        self._default_cooldown = default_cooldown_seconds
        self._cooldown_until: float = 0.0
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        with self._lock:
            return time.time() >= self._cooldown_until

    def trip(self, cooldown_seconds: float | None = None) -> None:
        cooldown = cooldown_seconds if cooldown_seconds is not None else self._default_cooldown
        with self._lock:
            self._cooldown_until = time.time() + cooldown


_photon_breaker = _CircuitBreaker(default_cooldown_seconds=60.0)
_nominatim_breaker = _CircuitBreaker(default_cooldown_seconds=60.0)


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


class MapProvider(Protocol):
    def distances_km(self, origin: Coordinates, destinations: list[Coordinates]) -> list[float]: ...


class HaversineMapProvider:
    """Offline fallback that calculates straight-line distance."""

    @staticmethod
    def distance_km(origin: Coordinates, destination: Coordinates) -> float:
        lat1 = math.radians(origin.latitude)
        lat2 = math.radians(destination.latitude)
        longitude_delta = math.radians(destination.longitude - origin.longitude)
        value = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(longitude_delta / 2) ** 2
        return 6371 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))

    def distances_km(self, origin: Coordinates, destinations: list[Coordinates]) -> list[float]:
        return [self.distance_km(origin, destination) for destination in destinations]


def _fetch_nominatim_coordinates(query_str: str) -> Coordinates | None:
    user_agent = _get_geo_user_agent()

    # 1. Thử qua Photon Geocoder (với 429 rate-limiting check và thread-safe Circuit Breaker cooldown)
    if _photon_breaker.is_available():
        photon_url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(query_str)}&limit=1"
        req_photon = urllib.request.Request(
            photon_url,
            headers={"User-Agent": user_agent},
        )
        try:
            with urllib.request.urlopen(req_photon, timeout=6) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                features = data.get("features", [])
                if features and len(features) > 0:
                    coords = features[0]["geometry"]["coordinates"]
                    return Coordinates(latitude=float(coords[1]), longitude=float(coords[0]))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                _photon_breaker.trip(_parse_retry_after(e, 60.0))
        except Exception:
            pass

    # 2. Dự phòng qua Nominatim OSM server (với 429 rate-limiting check và thread-safe Circuit Breaker cooldown)
    if _nominatim_breaker.is_available():
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_str)}&countrycodes=vn&format=json&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": user_agent},
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    return Coordinates(latitude=float(data[0]["lat"]), longitude=float(data[0]["lon"]))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                _nominatim_breaker.trip(_parse_retry_after(e, 60.0))
        except Exception:
            pass
    return None


PROVINCE_COORDINATES: dict[str, tuple[float, float]] = {
    "bắc giang": (21.2731, 106.1946),
    "bac giang": (21.2731, 106.1946),
    "bắc ninh": (21.1861, 106.0763),
    "bac ninh": (21.1861, 106.0763),
    "hà nội": (21.0285, 105.8542),
    "ha noi": (21.0285, 105.8542),
    "hồ chí minh": (10.7769, 106.7009),
    "ho chi minh": (10.7769, 106.7009),
    "hải phòng": (20.8449, 106.6881),
    "hai phong": (20.8449, 106.6881),
    "đà nẵng": (16.0544, 108.2022),
    "da nang": (16.0544, 108.2022),
    "cần thơ": (10.0452, 105.7469),
    "can tho": (10.0452, 105.7469),
    "quảng ninh": (20.9599, 107.0425),
    "thanh hóa": (19.8067, 105.7851),
    "nghệ an": (18.6734, 105.6813),
    "thừa thiên huế": (16.4637, 107.5909),
    "huế": (16.4637, 107.5909),
    "lạng sơn": (21.8474, 106.7583),
    "thái nguyên": (21.5928, 105.8442),
    "phú thọ": (21.3228, 105.4019),
    "vĩnh phúc": (21.3089, 105.6049),
    "hải dương": (20.9373, 106.3146),
    "hưng yên": (20.6464, 106.0511),
    "thái bình": (20.4463, 106.3365),
    "nam định": (20.4200, 106.1683),
    "ninh bình": (20.2506, 105.9744),
    "hà nam": (20.5452, 105.9126),
    "hoà bình": (20.8172, 105.3378),
    "sơn la": (21.3257, 103.9188),
    "lai châu": (22.3963, 103.4588),
    "điện biên": (21.3860, 103.0230),
    "lào cai": (22.4854, 103.9707),
    "yên bái": (21.7051, 104.8753),
    "hà giang": (22.8233, 104.9839),
    "tuyên quang": (21.8236, 105.2158),
    "cao bằng": (22.6658, 106.2573),
    "bắc kạn": (22.1481, 105.8347),
    "quảng bình": (17.4764, 106.5985),
    "quảng trị": (16.7454, 107.1853),
    "quảng nam": (15.5736, 108.4740),
    "quảng ngãi": (15.1205, 108.7924),
    "bình định": (13.7830, 109.2197),
    "phú yên": (13.0882, 109.0924),
    "khánh hòa": (12.2388, 109.1967),
    "ninh thuận": (11.5653, 108.9882),
    "bình thuận": (10.9333, 108.1000),
    "kon tum": (14.3497, 108.0004),
    "gia lai": (13.9833, 108.0000),
    "đắk lắk": (12.6667, 108.0500),
    "đắk nông": (12.0000, 107.6833),
    "lâm đồng": (11.9404, 108.4583),
    "bình phước": (11.5333, 106.8833),
    "tây ninh": (11.3000, 106.1000),
    "bình dương": (11.1667, 106.6500),
    "đồng nai": (10.9500, 106.8167),
    "bà rịa vũng tàu": (10.5000, 107.1667),
    "vũng tàu": (10.3460, 107.0843),
    "long an": (10.5333, 106.4000),
    "tiền giang": (10.4167, 106.3667),
    "bến tre": (10.2333, 106.3833),
    "trà vinh": (9.9333, 106.3333),
    "vĩnh long": (10.2500, 105.9667),
    "đồng tháp": (10.4667, 105.6333),
    "an giang": (10.3833, 105.4333),
    "kiên giang": (10.0167, 105.0833),
    "hậu giang": (9.7833, 105.4667),
    "sóc trăng": (9.6000, 105.9833),
    "bạc liêu": (9.2833, 105.7167),
    "cà mau": (9.1769, 105.1500),
}

LOCALITY_COORDINATES: dict[str, tuple[float, float]] = {
    # Deterministic fallback for common booking localities. This also keeps
    # local/test behavior useful when the external geocoder is unavailable.
    "quận 7": (10.7340, 106.7210),
    "quan 7": (10.7340, 106.7210),
}


class _GeocodeCache:
    """Thread-safe LRU cache that stores only successful (non-None) geocoding results."""

    def __init__(self, maxsize: int = 1024) -> None:
        self._maxsize = maxsize
        self._cache: OrderedDict[str, Coordinates] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Coordinates | None:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, coords: Coordinates) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = coords


_geocode_cache = _GeocodeCache(maxsize=1024)


def resolve_address_coordinates(address: str) -> Coordinates | None:
    if not address:
        return None
    clean_addr = address.strip()
    normalized = clean_addr.lower()

    # 0. Tra cứu từ bộ nhớ đệm trước (dùng normalized key để tránh duplicate do chữ hoa/thường)
    cached = _geocode_cache.get(normalized)
    if cached is not None:
        return cached

    # 1. Nếu từ khóa tra cứu trùng khớp hoàn toàn tên Tỉnh / Thành phố chính (0ms L1 memory lookup)
    if normalized in PROVINCE_COORDINATES:
        lat, lon = PROVINCE_COORDINATES[normalized]
        exact_coords = Coordinates(latitude=lat, longitude=lon)
        _geocode_cache.set(normalized, exact_coords)
        return exact_coords
    if normalized in LOCALITY_COORDINATES:
        lat, lon = LOCALITY_COORDINATES[normalized]
        exact_coords = Coordinates(latitude=lat, longitude=lon)
        _geocode_cache.set(normalized, exact_coords)
        return exact_coords

    # 2. Ưu tiên Dynamic Geocoding (OpenStreetMap API với timeout 10s)
    resolved_coords: Coordinates | None = _fetch_nominatim_coordinates(clean_addr)
    if resolved_coords is not None:
        _geocode_cache.set(normalized, resolved_coords)
        return resolved_coords

    if "," in clean_addr:
        space_addr = clean_addr.replace(",", " ")
        resolved_coords = _fetch_nominatim_coordinates(space_addr)
        if resolved_coords is not None:
            _geocode_cache.set(normalized, resolved_coords)
            return resolved_coords
        parts = [p.strip() for p in clean_addr.split(",") if p.strip()]
        for part in parts:
            resolved_coords = _fetch_nominatim_coordinates(part)
            if resolved_coords is not None:
                _geocode_cache.set(normalized, resolved_coords)
                return resolved_coords

    # 3. Fallback L1: Nếu API không trả về kết quả, mới quét tên Tỉnh / Thành phố lân cận
    for key, (lat, lon) in PROVINCE_COORDINATES.items():
        if key in normalized:
            fallback_coords = Coordinates(latitude=lat, longitude=lon)
            _geocode_cache.set(normalized, fallback_coords)
            return fallback_coords

    return None
