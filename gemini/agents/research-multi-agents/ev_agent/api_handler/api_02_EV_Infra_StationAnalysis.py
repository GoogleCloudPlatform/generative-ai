# @title Helper Functions

from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
import requests

# Constants
DEFAULT_TIMEOUT = 30
DEFAULT_RADIUS = 25.0
DEFAULT_STATIONS_PER_PAGE = 200
EARTH_RADIUS_MILES = 3956


# Data Models
class ChargingSpeed(BaseModel):
    count: int = 0
    total_ports: int = 0
    max_power: float = 0.0
    percentage: float = 0.0


class ConnectorDistribution(BaseModel):
    connector_type: str
    count: int
    percentage: float
    ports_per_station: float


class NetworkInfo(BaseModel):
    name: str
    station_count: int
    percentage: float


class FacilityTypeCount(BaseModel):
    parking_garage: int = 0
    retail: int = 0
    workplace: int = 0
    other: int = 0


class GeographicAnalysis(BaseModel):
    total_stations_per_square_mile: float
    stations_by_facility_type: FacilityTypeCount
    highway_proximity: Dict[str, int] = {"near_highway": 0, "city_center": 0}


class ChargingCapabilities(BaseModel):
    by_type: Dict[str, ChargingSpeed]
    connector_distribution: List[ConnectorDistribution]
    total_ports: int = 0


class AccessibilityMetrics(BaseModel):
    access_type: Dict[str, Dict[str, Union[int, float]]] = {
        "24_7_access": {"count": 0, "percentage": 0.0},
        "restricted": {"count": 0, "percentage": 0.0},
        "public": {"count": 0, "percentage": 0.0},
    }
    payment_methods: Dict[str, Dict[str, Union[int, float]]] = {
        "credit_card": {"count": 0, "percentage": 0.0},
        "mobile_pay": {"count": 0, "percentage": 0.0},
        "network_card": {"count": 0, "percentage": 0.0},
    }
    operational_status: Dict[str, Dict[str, Union[int, float]]] = {
        "operational": {"count": 0, "percentage": 0.0},
        "non_operational": {"count": 0, "percentage": 0.0},
    }


class NetworkAnalysis(BaseModel):
    networks: List[NetworkInfo]
    pricing_types: Dict[str, Dict[str, Union[int, float]]] = {
        "free": {"count": 0, "percentage": 0.0},
        "paid": {"count": 0, "percentage": 0.0},
        "variable": {"count": 0, "percentage": 0.0},
    }


class StationAge(BaseModel):
    age_distribution: Dict[str, Dict[str, Union[int, float]]] = {
        "less_than_1_year": {"count": 0, "percentage": 0.0},
        "1_to_3_years": {"count": 0, "percentage": 0.0},
        "more_than_3_years": {"count": 0, "percentage": 0.0},
    }
    last_verified: Dict[str, Dict[str, Union[int, float]]] = {
        "last_30_days": {"count": 0, "percentage": 0.0},
        "last_90_days": {"count": 0, "percentage": 0.0},
        "older": {"count": 0, "percentage": 0.0},
    }


class StationAnalysis(BaseModel):
    metadata: Dict[str, Any]
    geographic_analysis: GeographicAnalysis
    charging_capabilities: ChargingCapabilities
    accessibility: AccessibilityMetrics
    network_analysis: NetworkAnalysis
    station_age: StationAge


def analyze_facility_types(stations: List[Dict]) -> FacilityTypeCount:
    """Analyze facility types from station data"""
    counts = FacilityTypeCount()

    for station in stations:
        # Handle potential None values properly
        facility_type = (station.get("facility_type") or "").lower()

        if "parking" in facility_type or "garage" in facility_type:
            counts.parking_garage += 1
        elif "retail" in facility_type or "shopping" in facility_type:
            counts.retail += 1
        elif "workplace" in facility_type or "office" in facility_type:
            counts.workplace += 1
        else:
            counts.other += 1

    return counts


def analyze_charging_capabilities(stations: List[Dict]) -> ChargingCapabilities:
    """Analyze charging capabilities from station data"""
    speeds = {
        "dc_fast": ChargingSpeed(),
        "level2": ChargingSpeed(),
        "level1": ChargingSpeed(),
    }

    connector_types = {}
    total_ports = 0

    for station in stations:
        # Count ports and analyze charging speeds
        dc_ports = int(station.get("ev_dc_fast_num") or 0)
        l2_ports = int(station.get("ev_level2_evse_num") or 0)
        l1_ports = int(station.get("ev_level1_evse_num") or 0)

        total_ports += dc_ports + l2_ports + l1_ports

        if dc_ports:
            speeds["dc_fast"].count += 1
            speeds["dc_fast"].total_ports += dc_ports
            speeds["dc_fast"].max_power = max(
                speeds["dc_fast"].max_power,
                float(station.get("ev_power_level_dc_max") or 0),
            )

        if l2_ports:
            speeds["level2"].count += 1
            speeds["level2"].total_ports += l2_ports
            speeds["level2"].max_power = max(
                speeds["level2"].max_power,
                float(station.get("ev_power_level_l2_max") or 0),
            )

        if l1_ports:
            speeds["level1"].count += 1
            speeds["level1"].total_ports += l1_ports
            speeds["level1"].max_power = max(
                speeds["level1"].max_power,
                float(station.get("ev_power_level_l1_max") or 0),
            )

        # Analyze connector types
        connectors = station.get("ev_connector_types", []) or []
        for connector in connectors:
            if connector:
                connector_types[connector] = connector_types.get(connector, 0) + 1

    # Calculate percentages
    total_stations = len(stations)
    for speed in speeds.values():
        speed.percentage = (
            round((speed.count / total_stations * 100), 2) if total_stations > 0 else 0
        )

    # Create connector distribution list
    connector_distribution = [
        ConnectorDistribution(
            connector_type=c_type,
            count=count,
            percentage=(
                round((count / total_stations * 100), 2) if total_stations > 0 else 0
            ),
            ports_per_station=(
                round(count / total_stations, 2) if total_stations > 0 else 0
            ),
        )
        for c_type, count in connector_types.items()
    ]

    return ChargingCapabilities(
        by_type=speeds,
        connector_distribution=connector_distribution,
        total_ports=total_ports,
    )


def analyze_accessibility(stations: List[Dict]) -> AccessibilityMetrics:
    """Analyze accessibility metrics from station data"""
    metrics = AccessibilityMetrics()
    total_stations = len(stations)

    for station in stations:
        # Access type analysis
        access_time = (station.get("access_days_time") or "").lower()
        access_code = (station.get("access_code") or "").lower()

        if "24 hours" in access_time:
            metrics.access_type["24_7_access"]["count"] += 1
        if "restricted" in access_time:
            metrics.access_type["restricted"]["count"] += 1
        if access_code == "public":
            metrics.access_type["public"]["count"] += 1

        # print(station)

        # Payment methods analysis based on network and other indicators
        network = station.get("ev_network", "").lower()
        # If it's a networked station (not Tesla and not Non-Networked)
        if network and network not in ["tesla", "non-networked"]:
            # Most charging networks support multiple payment methods
            metrics.payment_methods["credit_card"]["count"] += 1
            metrics.payment_methods["mobile_pay"]["count"] += 1
            metrics.payment_methods["network_card"]["count"] += 1
        elif "tesla" in network.lower():
            # Tesla specific payment methods
            metrics.payment_methods["mobile_pay"]["count"] += 1
        elif any(keyword in access_time.lower() for keyword in ["pay", "fee", "paid"]):
            # For non-networked stations that mention payment
            metrics.payment_methods["credit_card"]["count"] += 1

        # Operational status
        if station.get("status_code") == "E":
            metrics.operational_status["operational"]["count"] += 1
        else:
            metrics.operational_status["non_operational"]["count"] += 1

    # Calculate percentages
    if total_stations > 0:
        for category in [
            metrics.access_type,
            metrics.payment_methods,
            metrics.operational_status,
        ]:
            for metric in category.values():
                metric["percentage"] = round(
                    (metric["count"] / total_stations * 100), 2
                )

    return metrics


def process_station_data(
    data: Dict, city_area: float, debug: bool = False
) -> StationAnalysis:
    """Process station data with enhanced metrics"""
    try:
        stations = data["stations"]
        if not stations:
            if debug:
                print("Debug: No stations found in data")
            return StationAnalysis()

        total_stations = len(stations)

        # Geographic Analysis
        facility_counts = analyze_facility_types(stations)
        geographic = GeographicAnalysis(
            total_stations_per_square_mile=(
                round(total_stations / city_area, 2) if city_area > 0 else 0
            ),
            stations_by_facility_type=facility_counts,
            highway_proximity={
                "near_highway": sum(
                    1 for s in stations if s.get("intersection_directions")
                ),
                "city_center": sum(
                    1
                    for s in stations
                    if "downtown" in (s.get("city_center", "") or "").lower()
                ),
            },
        )

        # Charging Capabilities
        charging = analyze_charging_capabilities(stations)

        # Accessibility Metrics
        accessibility = analyze_accessibility(stations)

        # Network Analysis
        networks = {}
        pricing_types = {"free": 0, "paid": 0, "variable": 0}

        for station in stations:
            # Network analysis
            network = station.get("ev_network") or "Unknown"
            networks[network] = networks.get(network, 0) + 1

            # Pricing analysis
            pricing = station.get("ev_pricing", "") or ""
            if not pricing or pricing.lower() in ["free", "no fee", "no charge"]:
                pricing_types["free"] += 1
            elif "variable" in pricing.lower():
                pricing_types["variable"] += 1
            else:
                pricing_types["paid"] += 1

        network_info = [
            NetworkInfo(
                name=name,
                station_count=count,
                percentage=round((count / total_stations * 100), 2),
            )
            for name, count in sorted(
                networks.items(), key=lambda x: x[1], reverse=True
            )
        ]

        network_analysis = NetworkAnalysis(
            networks=network_info,
            pricing_types={
                k: {"count": v, "percentage": round((v / total_stations * 100), 2)}
                for k, v in pricing_types.items()
            },
        )

        now = datetime.now()
        age_distribution = {
            "less_than_1_year": 0,
            "1_to_3_years": 0,
            "more_than_3_years": 0,
        }
        last_verified = {"last_30_days": 0, "last_90_days": 0, "older": 0}

        for station in stations:
            # Age distribution
            open_date = station.get("open_date")
            if open_date:
                try:
                    date_opened = datetime.strptime(open_date, "%Y-%m-%d")
                    age_days = (now - date_opened).days
                    if age_days <= 365:
                        age_distribution["less_than_1_year"] += 1
                    elif age_days <= 1095:
                        age_distribution["1_to_3_years"] += 1
                    else:
                        age_distribution["more_than_3_years"] += 1
                except:
                    if debug:
                        print(f"Debug: Could not parse open date: {open_date}")
                    age_distribution["more_than_3_years"] += 1

            # Last verified - Fixed to handle date_last_confirmed field
            date_last_verified = station.get(
                "date_last_confirmed"
            )  # Changed from date_last_verified
            if date_last_verified:
                try:
                    verified_date = datetime.strptime(date_last_verified, "%Y-%m-%d")
                    days_since_verified = (now - verified_date).days
                    if days_since_verified <= 30:
                        last_verified["last_30_days"] += 1
                    elif days_since_verified <= 90:
                        last_verified["last_90_days"] += 1
                    else:
                        last_verified["older"] += 1
                except:
                    if debug:
                        print(
                            f"Debug: Could not parse verification date: {date_last_verified}"
                        )
                    last_verified["older"] += 1
            else:
                last_verified["older"] += 1

        station_age = StationAge(
            age_distribution={
                k: {"count": v, "percentage": round((v / total_stations * 100), 2)}
                for k, v in age_distribution.items()
            },
            last_verified={
                k: {"count": v, "percentage": round((v / total_stations * 100), 2)}
                for k, v in last_verified.items()
            },
        )

        return StationAnalysis(
            metadata={
                "total_stations": total_stations,
                "city_area_square_miles": city_area,
                "analysis_timestamp": datetime.now().isoformat(),
            },
            geographic_analysis=geographic,
            charging_capabilities=charging,
            accessibility=accessibility,
            network_analysis=network_analysis,
            station_age=station_age,
        )

    except Exception as e:
        if debug:
            print(f"Debug: Error processing station data: {str(e)}")
        raise


def get_city_coordinates(
    city: str, state: str, debug: bool = False
) -> Dict[str, float]:
    """Get city coordinates and metadata"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "city": city,
            "state": state,
            "country": "USA",
            "format": "json",
            "limit": 1,
        }
        headers = {"User-Agent": "EVChargingStationFinder/1.0"}

        if debug:
            print(f"\nDebug: Getting coordinates for {city}, {state}")

        response = requests.get(
            url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()
        if not data:
            raise LocationError(f"Location not found: {city}, {state}")

        location = data[0]
        if debug:
            print(f"Debug: Found location data: {location}")

        bbox = location.get("boundingbox")
        area = 0.0
        if bbox:
            lat_diff = abs(float(bbox[1]) - float(bbox[0]))
            lon_diff = abs(float(bbox[3]) - float(bbox[2]))
            area = lat_diff * lon_diff * 69 * 54  # Approximate square miles

        return {
            "lat": float(location["lat"]),
            "lon": float(location["lon"]),
            "city_area": area if area > 0 else 100.0,
            "bbox": bbox,
            "display_name": location.get("display_name", f"{city}, {state}"),
        }

    except Exception as e:
        if debug:
            print(f"Debug: Error getting coordinates: {str(e)}")
        raise


def get_station_data_filtered(
    lat: float,
    lon: float,
    radius: float,
    state: str,
    api_key: str,
    max_stations: Optional[int] = None,
    stations_per_page: int = DEFAULT_STATIONS_PER_PAGE,
    debug: bool = False,
) -> Dict:
    """Get charging station data with proper location filtering"""
    url = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"

    base_params = {
        "api_key": api_key,
        "fuel_type": "ELEC",
        "latitude": lat,
        "longitude": lon,
        "radius": radius,
        "state": state,
        "country": "US",
        "status": "E",
        "access": "public",
        "limit": stations_per_page,
    }

    try:
        response = requests.get(url, params=base_params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        total_available = data.get("total_results", 0)
        if debug:
            print(f"Debug: Found {total_available} stations in {state}")

        # Validate and collect stations
        stations = []
        for station in data.get("fuel_stations", []):
            if validate_station_location(station, lat, lon, radius):
                stations.append(station)

        if debug:
            print(f"Debug: Validated {len(stations)} stations within {radius} miles")

        # Limit stations if max_stations is specified
        if max_stations:
            stations = stations[:max_stations]
            if debug:
                print(
                    f"Debug: Limited to {len(stations)} stations due to max_stations setting"
                )

        return {
            "stations": stations,
            "total_available": len(stations),
            "stations_processed": len(stations),
        }

    except Exception as e:
        if debug:
            print(f"Debug: Error fetching station data: {str(e)}")
        raise


def validate_station_location(
    station: Dict, center_lat: float, center_lon: float, radius_miles: float
) -> bool:
    """Validate if a station is within the specified radius"""
    station_lat = station.get("latitude")
    station_lon = station.get("longitude")

    if not station_lat or not station_lon:
        return False

    distance = calculate_distance(center_lat, center_lon, station_lat, station_lon)
    return distance <= radius_miles


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles using Haversine formula"""
    lat1, lon1 = radians(float(lat1)), radians(float(lon1))
    lat2, lon2 = radians(float(lat2)), radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_MILES * c


def get_charging_stations(config: Dict) -> Dict:
    """Main function to get and analyze charging station data"""
    debug = config.get("debug", False)
    radius_miles = config.get("radius_miles", DEFAULT_RADIUS)
    api_key = config.get("api_key", "DEMO_KEY")

    if api_key == "YOUR_API_KEY":
        api_key = "DEMO_KEY"
        if debug:
            print("Debug: Using DEMO_KEY for API access")

    try:
        if not config.get("city") or not config.get("state"):
            raise ValueError("City and state are required")

        # Get coordinates
        coords = get_city_coordinates(config["city"], config["state"], debug)

        # Get station data
        station_data = get_station_data_filtered(
            coords["lat"],
            coords["lon"],
            radius_miles,
            config["state"],
            api_key,
            config.get("max_total_stations"),
            config.get("stations_per_page", DEFAULT_STATIONS_PER_PAGE),
            debug,
        )

        # Process and analyze the data
        result = process_station_data(station_data, coords["city_area"], debug)

        # Add location metadata
        result.metadata.update(
            {
                "city": config["city"],
                "state": config["state"],
                "radius_miles": radius_miles,
                "coordinates": {"latitude": coords["lat"], "longitude": coords["lon"]},
                "display_name": coords.get("display_name"),
            }
        )

        return result

    except Exception as e:
        if debug:
            print(f"Error: {str(e)}")
        raise


class LocationError(Exception):
    """Custom exception for location-related errors"""


class ChargingError(Exception):
    """Custom exception for charging station-related errors"""
