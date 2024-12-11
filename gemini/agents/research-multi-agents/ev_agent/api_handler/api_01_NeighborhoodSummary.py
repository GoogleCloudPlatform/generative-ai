# @title Helper Functions

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class HealthcareFacilities:
    """Raw healthcare facility counts from OSM"""

    hospitals: int = 0
    clinics: int = 0
    doctors: int = 0
    dentists: int = 0
    pharmacies: int = 0
    healthcare_centres: int = 0
    veterinary: int = 0


@dataclass
class EducationalFacilities:
    """Raw educational facility counts from OSM"""

    schools: int = 0
    kindergartens: int = 0
    colleges: int = 0
    universities: int = 0
    libraries: int = 0
    training_centers: int = 0
    language_schools: int = 0
    music_schools: int = 0


@dataclass
class TransportFacilities:
    """Raw transportation facility counts from OSM"""

    bus_stops: int = 0
    tram_stops: int = 0
    subway_stations: int = 0
    train_stations: int = 0
    taxi_stands: int = 0
    bike_rental: int = 0
    ferry_terminals: int = 0
    bus_stations: int = 0
    transport_platforms: int = 0


@dataclass
class RoadNetwork:
    """Raw road network counts from OSM"""

    motorways: int = 0
    trunks: int = 0
    primary_roads: int = 0
    secondary_roads: int = 0
    tertiary_roads: int = 0
    residential_roads: int = 0
    service_roads: int = 0
    cycleways: int = 0
    footways: int = 0
    bridges: int = 0
    tunnels: int = 0


@dataclass
class Retail:
    """Raw retail facility counts from OSM"""

    malls: int = 0
    supermarkets: int = 0
    department_stores: int = 0
    convenience_stores: int = 0
    grocery_stores: int = 0
    markets: int = 0
    retail_parks: int = 0
    shopping_centres: int = 0


@dataclass
class FoodAndDrink:
    """Raw food and drink establishment counts from OSM"""

    restaurants: int = 0
    cafes: int = 0
    fast_food: int = 0
    pubs: int = 0
    bars: int = 0
    food_courts: int = 0
    ice_cream: int = 0
    bistros: int = 0


@dataclass
class LeisureFacilities:
    """Raw leisure facility counts from OSM"""

    parks: int = 0
    sports_centres: int = 0
    fitness_centers: int = 0
    swimming_pools: int = 0
    stadiums: int = 0
    playgrounds: int = 0
    recreation_grounds: int = 0
    golf_courses: int = 0


@dataclass
class Buildings:
    """Raw building counts from OSM"""

    residential: int = 0
    apartments: int = 0
    commercial: int = 0
    retail: int = 0
    industrial: int = 0
    warehouse: int = 0
    office: int = 0
    government: int = 0
    hospital: int = 0
    school: int = 0
    university: int = 0
    hotel: int = 0
    parking: int = 0


@dataclass
class Parking:
    """Raw parking facility counts from OSM"""

    surface_parking: int = 0
    parking_structures: int = 0
    street_parking: int = 0
    bike_parking: int = 0
    parking_spaces: int = 0
    disabled_parking: int = 0
    ev_charging: int = 0


@dataclass
class EmergencyServices:
    """Raw emergency service facility counts from OSM"""

    police_stations: int = 0
    fire_stations: int = 0
    ambulance_stations: int = 0
    emergency_posts: int = 0
    rescue_stations: int = 0
    disaster_response: int = 0


@dataclass
class Entertainment:
    """Raw entertainment facility counts from OSM"""

    cinemas: int = 0
    theatres: int = 0
    arts_centres: int = 0
    nightclubs: int = 0
    community_centres: int = 0
    event_venues: int = 0
    museums: int = 0
    galleries: int = 0


@dataclass
class Automotive:
    """Raw automotive facility counts from OSM"""

    car_dealerships: int = 0
    car_repair: int = 0
    car_wash: int = 0
    car_rental: int = 0
    car_sharing: int = 0
    fuel_stations: int = 0
    ev_charging_stations: int = 0


@dataclass
class PublicAmenities:
    """Raw public amenity counts from OSM"""

    post_offices: int = 0
    banks: int = 0
    atms: int = 0
    toilets: int = 0
    recycling: int = 0
    waste_disposal: int = 0
    water_points: int = 0
    benches: int = 0


@dataclass
class AreaMetrics:
    """Raw area and density metrics"""

    total_area_sqkm: float = 0.0
    water_area_sqkm: float = 0.0
    green_area_sqkm: float = 0.0
    built_area_sqkm: float = 0.0
    bounds_north: float = 0.0
    bounds_south: float = 0.0
    bounds_east: float = 0.0
    bounds_west: float = 0.0


@dataclass
class DataQuality:
    """Data quality and metadata"""

    total_elements: int = 0
    node_count: int = 0
    way_count: int = 0
    relation_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    query_time_seconds: float = 0.0
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class NeighborhoodSummary:
    """Complete raw neighborhood summary"""

    # Location identifiers
    city: str
    state: str
    osm_id: Optional[str] = None

    # Raw counts by category
    healthcare: HealthcareFacilities = field(default_factory=HealthcareFacilities)
    education: EducationalFacilities = field(default_factory=EducationalFacilities)
    transport: TransportFacilities = field(default_factory=TransportFacilities)
    roads: RoadNetwork = field(default_factory=RoadNetwork)
    retail: Retail = field(default_factory=Retail)
    food: FoodAndDrink = field(default_factory=FoodAndDrink)
    leisure: LeisureFacilities = field(default_factory=LeisureFacilities)
    buildings: Buildings = field(default_factory=Buildings)
    parking: Parking = field(default_factory=Parking)
    emergency: EmergencyServices = field(default_factory=EmergencyServices)
    entertainment: Entertainment = field(default_factory=Entertainment)
    automotive: Automotive = field(default_factory=Automotive)
    amenities: PublicAmenities = field(default_factory=PublicAmenities)

    # Area and quality metrics
    area_metrics: AreaMetrics = field(default_factory=AreaMetrics)
    data_quality: DataQuality = field(default_factory=DataQuality)

    def to_dict(self) -> Dict:
        """Convert all non-None values to dictionary"""

        def dataclass_to_dict(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return {k: v for k, v in obj.__dict__.items() if v is not None}
            return obj

        return {
            k: dataclass_to_dict(v) for k, v in self.__dict__.items() if v is not None
        }


from datetime import datetime
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import requests


class APIConfig:
    """API configuration and constants"""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    USER_AGENT = "EV-Planning-Tool/1.0"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    TIMEOUT = 180  # seconds


class LocationAPI:
    """Handles Nominatim API interactions"""

    @staticmethod
    def get_city_coordinates(
        city: str, state: str, debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get city coordinates and boundary information"""
        try:
            headers = {"User-Agent": APIConfig.USER_AGENT}
            params = {
                "city": city,
                "state": state,
                "country": "USA",
                "format": "json",
                "limit": 1,
            }

            if debug:
                print(f"\nDebug: Querying Nominatim API for {city}, {state}")
                print(f"Debug: Parameters: {params}")

            for attempt in range(APIConfig.MAX_RETRIES):
                try:
                    response = requests.get(
                        APIConfig.NOMINATIM_URL,
                        params=params,
                        headers=headers,
                        timeout=APIConfig.TIMEOUT,
                    )

                    if debug:
                        print(
                            f"Debug: Attempt {attempt + 1} - Status: {response.status_code}"
                        )

                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            return {
                                "bbox": data[0]["boundingbox"],
                                "osm_id": data[0].get("osm_id"),
                                "lat": data[0]["lat"],
                                "lon": data[0]["lon"],
                                "display_name": data[0]["display_name"],
                                "timestamp": datetime.now().isoformat(),
                            }
                    elif response.status_code == 429:
                        if debug:
                            print(
                                f"Debug: Rate limited, waiting {APIConfig.RETRY_DELAY}s"
                            )
                        time.sleep(APIConfig.RETRY_DELAY)

                except requests.Timeout:
                    if debug:
                        print(f"Debug: Timeout on attempt {attempt + 1}")
                    time.sleep(APIConfig.RETRY_DELAY)

            return None

        except Exception as e:
            if debug:
                print(f"Debug: Error in get_city_coordinates: {str(e)}")
            return None


class OverpassAPI:
    """Handles Overpass API interactions"""

    @staticmethod
    def build_query(city: str, bbox: list) -> str:
        """Build comprehensive Overpass query for all raw data"""
        city_escaped = quote(city)
        south, north, west, east = map(str, bbox)

        return f"""[out:json][timeout:180][bbox:{south},{west},{north},{east}];
        area["admin_level"~"4|6|8"]["name"~"^{city_escaped}$|^{city_escaped} City$",i]->.searchArea;
        (
            // Healthcare
            node(area.searchArea)["amenity"~"hospital|clinic|doctors|dentist|pharmacy|healthcare|veterinary"];
            way(area.searchArea)["amenity"~"hospital|clinic|doctors|dentist|pharmacy|healthcare|veterinary"];

            // Education
            node(area.searchArea)["amenity"~"school|kindergarten|college|university|library|training|language_school|music_school"];
            way(area.searchArea)["amenity"~"school|kindergarten|college|university|library|training|language_school|music_school"];

            // Transportation
            node(area.searchArea)["public_transport"];
            node(area.searchArea)["highway"="bus_stop"];
            node(area.searchArea)["railway"~"station|subway_entrance|tram_stop"];
            node(area.searchArea)["amenity"="taxi"];
            node(area.searchArea)["amenity"="bicycle_rental"];
            node(area.searchArea)["amenity"="ferry_terminal"];

            // Road Network
            way(area.searchArea)["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|cycleway|footway"];
            way(area.searchArea)["bridge"];
            way(area.searchArea)["tunnel"];

            // Retail
            node(area.searchArea)["shop"~"mall|supermarket|department_store|convenience|grocery|market"];
            way(area.searchArea)["shop"~"mall|supermarket|department_store|convenience|grocery|market"];

            // Food and Drink
            node(area.searchArea)["amenity"~"restaurant|cafe|fast_food|pub|bar|food_court|ice_cream|bistro"];

            // Leisure
            way(area.searchArea)["leisure"~"park|sports_centre|fitness_center|swimming_pool|stadium|playground|recreation_ground|golf_course"];
            node(area.searchArea)["leisure"~"park|sports_centre|fitness_center|swimming_pool|stadium|playground|recreation_ground|golf_course"];

            // Buildings
            way(area.searchArea)["building"~"residential|apartments|commercial|retail|industrial|warehouse|office|government|hospital|school|university|hotel|parking"];

            // Parking
            node(area.searchArea)["amenity"="parking"];
            way(area.searchArea)["amenity"="parking"];
            node(area.searchArea)["amenity"="parking_space"];
            node(area.searchArea)["amenity"="bicycle_parking"];
            node(area.searchArea)["amenity"="charging_station"];

            // Emergency Services
            node(area.searchArea)["amenity"~"police|fire_station|ambulance_station|emergency_post|rescue"];
            way(area.searchArea)["amenity"~"police|fire_station|ambulance_station|emergency_post|rescue"];

            // Entertainment
            node(area.searchArea)["amenity"~"cinema|theatre|arts_centre|nightclub|community_centre|events_venue|museum|gallery"];
            way(area.searchArea)["amenity"~"cinema|theatre|arts_centre|nightclub|community_centre|events_venue|museum|gallery"];

            // Automotive
            node(area.searchArea)["shop"~"car|car_repair|car_parts"];
            node(area.searchArea)["amenity"~"car_wash|car_rental|car_sharing|fuel"];

            // Public Amenities
            node(area.searchArea)["amenity"~"post_office|bank|atm|toilets|recycling|waste_disposal|water_point|bench"];

            // Area Features
            way(area.searchArea)["natural"="water"];
            way(area.searchArea)["landuse"="grass"];
            way(area.searchArea)["landuse"~"residential|commercial|industrial"];
        );
        out body;
        >;
        out skel qt;"""

    @staticmethod
    def get_city_data(
        city: str, bbox: list, debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get raw city data from Overpass API"""
        try:
            start_time = time.time()
            query = OverpassAPI.build_query(city, bbox)

            if debug:
                print("\nDebug: Sending Overpass API request")
                print(f"Debug: Query length: {len(query)} characters")

            for attempt in range(APIConfig.MAX_RETRIES):
                try:
                    response = requests.post(
                        APIConfig.OVERPASS_URL,
                        data={"data": query},
                        timeout=APIConfig.TIMEOUT,
                    )

                    if debug:
                        print(
                            f"Debug: Attempt {attempt + 1} - Status: {response.status_code}"
                        )

                    if response.status_code == 200:
                        data = response.json()
                        query_time = time.time() - start_time

                        result = {
                            "elements": data.get("elements", []),
                            "timestamp": datetime.now().isoformat(),
                            "query_time_seconds": query_time,
                            "node_count": sum(
                                1
                                for e in data.get("elements", [])
                                if e.get("type") == "node"
                            ),
                            "way_count": sum(
                                1
                                for e in data.get("elements", [])
                                if e.get("type") == "way"
                            ),
                            "relation_count": sum(
                                1
                                for e in data.get("elements", [])
                                if e.get("type") == "relation"
                            ),
                        }

                        if debug:
                            print(
                                f"Debug: Retrieved {len(result['elements'])} elements"
                            )
                            print(
                                f"Debug: {result['node_count']} nodes, {result['way_count']} ways"
                            )
                            print(f"Debug: Query time: {query_time:.2f} seconds")

                        return result

                    elif response.status_code == 429:
                        if debug:
                            print(
                                f"Debug: Rate limited, waiting {APIConfig.RETRY_DELAY}s"
                            )
                        time.sleep(APIConfig.RETRY_DELAY)

                except requests.Timeout:
                    if debug:
                        print(f"Debug: Timeout on attempt {attempt + 1}")
                    if attempt < APIConfig.MAX_RETRIES - 1:
                        time.sleep(APIConfig.RETRY_DELAY)

            return None

        except Exception as e:
            if debug:
                print(f"Debug: Error in get_city_data: {str(e)}")
            return None


def fetch_city_data(
    city: str, state: str, debug: bool = False
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Fetch all raw city data from both APIs"""
    location_data = LocationAPI.get_city_coordinates(city, state, debug)
    if not location_data:
        if debug:
            print("Debug: Failed to get location data")
        return None, None

    city_data = OverpassAPI.get_city_data(city, location_data["bbox"], debug)
    if not city_data:
        if debug:
            print("Debug: Failed to get city data")
        return None, None

    return location_data, city_data


from datetime import datetime
import math
from typing import Any, Dict, List


class RawDataProcessor:
    """Process raw OSM data with minimal transformation"""

    @staticmethod
    def process_healthcare(elements: List[Dict]) -> HealthcareFacilities:
        facilities = HealthcareFacilities()
        for element in elements:
            tags = element.get("tags", {})
            if "amenity" in tags:
                if tags["amenity"] == "hospital":
                    facilities.hospitals += 1
                elif tags["amenity"] == "clinic":
                    facilities.clinics += 1
                elif tags["amenity"] == "doctors":
                    facilities.doctors += 1
                elif tags["amenity"] == "dentist":
                    facilities.dentists += 1
                elif tags["amenity"] == "pharmacy":
                    facilities.pharmacies += 1
                elif tags["amenity"] == "healthcare":
                    facilities.healthcare_centres += 1
                elif tags["amenity"] == "veterinary":
                    facilities.veterinary += 1
        return facilities

    @staticmethod
    def process_transport(elements: List[Dict]) -> TransportFacilities:
        transport = TransportFacilities()
        for element in elements:
            tags = element.get("tags", {})

            # Public transport nodes
            if "public_transport" in tags:
                if tags["public_transport"] == "platform":
                    transport.transport_platforms += 1
                elif tags["public_transport"] == "station":
                    transport.bus_stations += 1

            # Specific transport types
            if tags.get("highway") == "bus_stop":
                transport.bus_stops += 1
            elif tags.get("railway") == "station":
                transport.train_stations += 1
            elif tags.get("railway") == "subway_entrance":
                transport.subway_stations += 1
            elif tags.get("railway") == "tram_stop":
                transport.tram_stops += 1
            elif tags.get("amenity") == "ferry_terminal":
                transport.ferry_terminals += 1
            elif tags.get("amenity") == "taxi":
                transport.taxi_stands += 1
            elif tags.get("amenity") == "bicycle_rental":
                transport.bike_rental += 1
        return transport

    @staticmethod
    def process_roads(elements: List[Dict]) -> RoadNetwork:
        roads = RoadNetwork()
        for element in elements:
            if element.get("type") != "way":
                continue

            tags = element.get("tags", {})
            if "highway" in tags:
                if tags["highway"] == "motorway":
                    roads.motorways += 1
                elif tags["highway"] == "trunk":
                    roads.trunks += 1
                elif tags["highway"] == "primary":
                    roads.primary_roads += 1
                elif tags["highway"] == "secondary":
                    roads.secondary_roads += 1
                elif tags["highway"] == "tertiary":
                    roads.tertiary_roads += 1
                elif tags["highway"] == "residential":
                    roads.residential_roads += 1
                elif tags["highway"] == "service":
                    roads.service_roads += 1
                elif tags["highway"] == "cycleway":
                    roads.cycleways += 1
                elif tags["highway"] == "footway":
                    roads.footways += 1

            if tags.get("bridge") == "yes":
                roads.bridges += 1
            if tags.get("tunnel") == "yes":
                roads.tunnels += 1
        return roads

    @staticmethod
    def process_buildings(elements: List[Dict]) -> Buildings:
        buildings = Buildings()
        for element in elements:
            if element.get("type") != "way":
                continue

            tags = element.get("tags", {})
            if "building" in tags:
                if tags["building"] in ["residential", "house", "detached"]:
                    buildings.residential += 1
                elif tags["building"] == "apartments":
                    buildings.apartments += 1
                elif tags["building"] == "commercial":
                    buildings.commercial += 1
                elif tags["building"] == "retail":
                    buildings.retail += 1
                elif tags["building"] == "industrial":
                    buildings.industrial += 1
                elif tags["building"] == "warehouse":
                    buildings.warehouse += 1
                elif tags["building"] == "office":
                    buildings.office += 1
                elif tags["building"] == "government":
                    buildings.government += 1
                elif tags["building"] == "hospital":
                    buildings.hospital += 1
                elif tags["building"] == "school":
                    buildings.school += 1
                elif tags["building"] == "university":
                    buildings.university += 1
                elif tags["building"] == "hotel":
                    buildings.hotel += 1
                elif tags["building"] == "parking":
                    buildings.parking += 1
        return buildings

    @staticmethod
    def process_education(elements: List[Dict]) -> EducationalFacilities:
        education = EducationalFacilities()
        for element in elements:
            tags = element.get("tags", {})

            # Check both amenity and building tags
            if tags.get("amenity") == "school" or tags.get("building") == "school":
                education.schools += 1
            elif tags.get("amenity") == "kindergarten":
                education.kindergartens += 1
            elif tags.get("amenity") == "college":
                education.colleges += 1
            elif (
                tags.get("amenity") == "university"
                or tags.get("building") == "university"
            ):
                education.universities += 1
            elif tags.get("amenity") == "library":
                education.libraries += 1
            elif tags.get("amenity") == "training":
                education.training_centers += 1
            elif tags.get("amenity") == "language_school":
                education.language_schools += 1
            elif tags.get("amenity") == "music_school":
                education.music_schools += 1
        return education

    @staticmethod
    def process_retail(elements: List[Dict]) -> Retail:
        retail = Retail()
        for element in elements:
            tags = element.get("tags", {})

            # Process shop tags
            shop_type = tags.get("shop")
            if shop_type == "mall":
                retail.malls += 1
            elif shop_type == "supermarket":
                retail.supermarkets += 1
            elif shop_type == "department_store":
                retail.department_stores += 1
            elif shop_type == "convenience":
                retail.convenience_stores += 1
            elif shop_type in ["grocery", "greengrocer"]:
                retail.grocery_stores += 1
            elif shop_type == "marketplace" or tags.get("amenity") == "marketplace":
                retail.markets += 1

            # Check for retail parks and shopping centres in different tags
            if tags.get("landuse") == "retail":
                retail.retail_parks += 1
            if tags.get("building") == "retail" or shop_type == "shopping_centre":
                retail.shopping_centres += 1
        return retail

    @staticmethod
    def process_food_drink(elements: List[Dict]) -> FoodAndDrink:
        food = FoodAndDrink()
        for element in elements:
            tags = element.get("tags", {})

            amenity_type = tags.get("amenity")
            if amenity_type == "restaurant":
                food.restaurants += 1
            elif amenity_type == "cafe":
                food.cafes += 1
            elif amenity_type == "fast_food":
                food.fast_food += 1
            elif amenity_type == "pub":
                food.pubs += 1
            elif amenity_type == "bar":
                food.bars += 1
            elif amenity_type == "food_court":
                food.food_courts += 1
            elif amenity_type == "ice_cream":
                food.ice_cream += 1
            elif amenity_type == "bistro":
                food.bistros += 1
        return food

    @staticmethod
    def process_parking(elements: List[Dict]) -> Parking:
        parking = Parking()
        for element in elements:
            tags = element.get("tags", {})

            if tags.get("amenity") == "parking":
                if tags.get("parking") == "surface":
                    parking.surface_parking += 1
                elif tags.get("parking") == "multi-storey":
                    parking.parking_structures += 1
                elif tags.get("parking") == "street_side":
                    parking.street_parking += 1
                else:
                    # Count as surface parking by default
                    parking.surface_parking += 1

            if tags.get("amenity") == "bicycle_parking":
                parking.bike_parking += 1
            if tags.get("amenity") == "parking_space":
                parking.parking_spaces += 1
            if tags.get("amenity") == "charging_station":
                parking.ev_charging += 1

            # Check for disabled parking
            if tags.get("amenity") == "parking" and tags.get("disabled") == "yes":
                parking.disabled_parking += 1
        return parking

    @staticmethod
    def process_emergency(elements: List[Dict]) -> EmergencyServices:
        emergency = EmergencyServices()
        for element in elements:
            tags = element.get("tags", {})

            amenity_type = tags.get("amenity")
            if amenity_type == "police":
                emergency.police_stations += 1
            elif amenity_type == "fire_station":
                emergency.fire_stations += 1
            elif amenity_type == "ambulance_station":
                emergency.ambulance_stations += 1
            elif amenity_type == "emergency_post":
                emergency.emergency_posts += 1
            elif amenity_type == "rescue_station":
                emergency.rescue_stations += 1

            # Check emergency=* tags for disaster response
            if tags.get("emergency") in ["disaster_response", "emergency_ward"]:
                emergency.disaster_response += 1
        return emergency

    @staticmethod
    def process_entertainment(elements: List[Dict]) -> Entertainment:
        entertainment = Entertainment()
        for element in elements:
            tags = element.get("tags", {})

            amenity_type = tags.get("amenity")
            leisure_type = tags.get("leisure")

            if amenity_type == "cinema":
                entertainment.cinemas += 1
            elif amenity_type == "theatre":
                entertainment.theatres += 1
            elif amenity_type == "arts_centre":
                entertainment.arts_centres += 1
            elif amenity_type == "nightclub":
                entertainment.nightclubs += 1
            elif amenity_type == "community_centre":
                entertainment.community_centres += 1
            elif (
                tags.get("building") == "events_venue" or amenity_type == "events_venue"
            ):
                entertainment.event_venues += 1
            elif amenity_type == "museum":
                entertainment.museums += 1
            elif amenity_type == "gallery":
                entertainment.galleries += 1
        return entertainment

    @staticmethod
    def process_automotive(elements: List[Dict]) -> Automotive:
        automotive = Automotive()
        for element in elements:
            tags = element.get("tags", {})

            shop_type = tags.get("shop")
            amenity_type = tags.get("amenity")

            if shop_type == "car":
                automotive.car_dealerships += 1
            elif shop_type == "car_repair":
                automotive.car_repair += 1
            elif amenity_type == "car_wash":
                automotive.car_wash += 1
            elif amenity_type == "car_rental":
                automotive.car_rental += 1
            elif amenity_type == "car_sharing":
                automotive.car_sharing += 1
            elif amenity_type == "fuel":
                automotive.fuel_stations += 1
            elif amenity_type == "charging_station":
                automotive.ev_charging_stations += 1
        return automotive

    @staticmethod
    def process_amenities(elements: List[Dict]) -> PublicAmenities:
        amenities = PublicAmenities()
        for element in elements:
            tags = element.get("tags", {})

            amenity_type = tags.get("amenity")
            if amenity_type == "post_office":
                amenities.post_offices += 1
            elif amenity_type == "bank":
                amenities.banks += 1
            elif amenity_type == "atm":
                amenities.atms += 1
            elif amenity_type == "toilets":
                amenities.toilets += 1
            elif amenity_type == "recycling":
                amenities.recycling += 1
            elif amenity_type == "waste_disposal":
                amenities.waste_disposal += 1
            elif amenity_type == "water_point" or amenity_type == "drinking_water":
                amenities.water_points += 1
            elif amenity_type == "bench":
                amenities.benches += 1
        return amenities

    @staticmethod
    def process_leisure(elements: List[Dict]) -> LeisureFacilities:
        leisure = LeisureFacilities()
        for element in elements:
            tags = element.get("tags", {})

            leisure_type = tags.get("leisure")
            if leisure_type == "park":
                leisure.parks += 1
            elif leisure_type == "sports_centre":
                leisure.sports_centres += 1
            elif leisure_type == "fitness_center" or leisure_type == "fitness_centre":
                leisure.fitness_centers += 1
            elif leisure_type == "swimming_pool":
                leisure.swimming_pools += 1
            elif leisure_type == "stadium":
                leisure.stadiums += 1
            elif leisure_type == "playground":
                leisure.playgrounds += 1
            elif leisure_type == "recreation_ground":
                leisure.recreation_grounds += 1
            elif leisure_type == "golf_course":
                leisure.golf_courses += 1

            # Also check amenity tags for sports/leisure
            amenity_type = tags.get("amenity")
            if amenity_type == "swimming_pool":
                leisure.swimming_pools += 1
            elif amenity_type == "sports_centre":
                leisure.sports_centres += 1
        return leisure

    @staticmethod
    def process_area_metrics(location_data: Dict, elements: List[Dict]) -> AreaMetrics:
        metrics = AreaMetrics()

        # Get bounds
        bbox = location_data["bbox"]
        (
            metrics.bounds_south,
            metrics.bounds_north,
            metrics.bounds_west,
            metrics.bounds_east,
        ) = map(float, bbox)

        # Calculate raw areas
        lat1, lat2 = math.radians(metrics.bounds_south), math.radians(
            metrics.bounds_north
        )
        lon1, lon2 = math.radians(metrics.bounds_west), math.radians(
            metrics.bounds_east
        )

        # Simple area calculation
        R = 6371  # Earth radius in km
        width = R * abs(lon2 - lon1) * math.cos(0.5 * (lat2 + lat1))
        height = R * abs(lat2 - lat1)
        metrics.total_area_sqkm = width * height

        # Count areas by type (no processing, just raw counts converted to area)
        water_ways = sum(
            1
            for e in elements
            if e.get("type") == "way" and e.get("tags", {}).get("natural") == "water"
        )
        green_ways = sum(
            1
            for e in elements
            if e.get("type") == "way" and e.get("tags", {}).get("landuse") == "grass"
        )
        built_ways = sum(
            1
            for e in elements
            if e.get("type") == "way"
            and e.get("tags", {}).get("landuse")
            in ["residential", "commercial", "industrial"]
        )

        # Simple proportional area assignment
        total_counted_ways = water_ways + green_ways + built_ways
        if total_counted_ways > 0:
            metrics.water_area_sqkm = (
                water_ways / total_counted_ways
            ) * metrics.total_area_sqkm
            metrics.green_area_sqkm = (
                green_ways / total_counted_ways
            ) * metrics.total_area_sqkm
            metrics.built_area_sqkm = (
                built_ways / total_counted_ways
            ) * metrics.total_area_sqkm

        return metrics


from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


class CitySummaryProcessor:
    """
    Processes city data and creates summaries based on configurable payloads.
    Uses RawDataProcessor for the actual data processing.
    """

    def __init__(self):
        self.raw_processor = RawDataProcessor()
        self.category_fields = {
            "healthcare": set(HealthcareFacilities().__dict__.keys()),
            "education": set(EducationalFacilities().__dict__.keys()),
            "transport": set(TransportFacilities().__dict__.keys()),
            "roads": set(RoadNetwork().__dict__.keys()),
            "retail": set(Retail().__dict__.keys()),
            "food": set(FoodAndDrink().__dict__.keys()),
            "leisure": set(LeisureFacilities().__dict__.keys()),
            "buildings": set(Buildings().__dict__.keys()),
            "parking": set(Parking().__dict__.keys()),
            "emergency": set(EmergencyServices().__dict__.keys()),
            "entertainment": set(Entertainment().__dict__.keys()),
            "automotive": set(Automotive().__dict__.keys()),
            "amenities": set(PublicAmenities().__dict__.keys()),
            "area_metrics": set(AreaMetrics().__dict__.keys()),
        }

    @staticmethod
    def _get_selected_fields(
        category_config: Union[bool, List[str], str], available_fields: Set[str]
    ) -> Set[str]:
        """Helper to determine which fields to include for a category"""
        if isinstance(category_config, bool) and category_config:
            return available_fields
        elif isinstance(category_config, list):
            return set(category_config) & available_fields
        elif isinstance(category_config, str) and category_config.lower() == "all":
            return available_fields
        return set()

    @staticmethod
    def _filter_dataclass_fields(obj: Any, selected_fields: Set[str]) -> Any:
        """Filter dataclass fields based on selection"""
        if not selected_fields:
            return obj

        filtered = obj.__class__()
        for field in selected_fields:
            if hasattr(obj, field):
                setattr(filtered, field, getattr(obj, field))
        return filtered

    def _expand_categories_config(self, config: Union[Dict, str]) -> Dict:
        """Expands 'all' config to full category dictionary"""
        if config == "all":
            return {
                "healthcare": True,
                "education": True,
                "transport": True,
                "roads": True,
                "retail": True,
                "food": True,
                "leisure": True,
                "buildings": True,
                "parking": True,
                "emergency": True,
                "entertainment": True,
                "automotive": True,
                "amenities": True,
                "area_metrics": True,
            }
        return config

    def _process_category(
        self,
        category: str,
        category_config: Union[bool, List[str]],
        elements: List[Dict],
        location_data: Optional[Dict] = None,
    ) -> Any:
        """Process a single category based on configuration"""
        selected_fields = self._get_selected_fields(
            category_config, self.category_fields[category]
        )

        # Map categories to their processor methods
        processors = {
            "healthcare": RawDataProcessor.process_healthcare,
            "education": RawDataProcessor.process_education,
            "transport": RawDataProcessor.process_transport,
            "roads": RawDataProcessor.process_roads,
            "retail": RawDataProcessor.process_retail,
            "food": RawDataProcessor.process_food_drink,
            "leisure": RawDataProcessor.process_leisure,
            "buildings": RawDataProcessor.process_buildings,
            "parking": RawDataProcessor.process_parking,
            "emergency": RawDataProcessor.process_emergency,
            "entertainment": RawDataProcessor.process_entertainment,
            "automotive": RawDataProcessor.process_automotive,
            "amenities": RawDataProcessor.process_amenities,
        }

        if category == "area_metrics" and location_data:
            processed = RawDataProcessor.process_area_metrics(location_data, elements)
        elif category in processors:
            processed = processors[category](elements)
        else:
            return None

        return self._filter_dataclass_fields(processed, selected_fields)

    def create_city_summary(
        self, payload: Dict[str, Any]
    ) -> Optional[NeighborhoodSummary]:
        """
        Create city summary from a configuration payload.

        Args:
            payload: Dict containing city, state, and configuration options

        Returns:
            NeighborhoodSummary object or None if data fetching fails
        """
        # Extract basic parameters
        city = payload["city"]
        state = payload["state"]
        config = payload.get("config", {})
        debug = payload.get("debug", False) or config.get("debug", False)

        # Fetch raw data
        location_data, city_data = fetch_city_data(city, state, debug)
        if not location_data or not city_data:
            return None

        elements = city_data["elements"]

        # Initialize summary
        summary = NeighborhoodSummary(
            city=city, state=state, osm_id=location_data.get("osm_id")
        )

        try:
            # Get and expand category configuration
            categories_config = self._expand_categories_config(
                config.get("categories", "all")
            )

            # Process each configured category
            for category, category_config in categories_config.items():
                if debug:
                    print(f"Debug: Processing {category}")

                if not category_config:
                    continue

                # Process category and set result
                result = self._process_category(
                    category=category,
                    category_config=category_config,
                    elements=elements,
                    location_data=location_data if category == "area_metrics" else None,
                )

                if result is not None:
                    setattr(summary, category, result)

            # Update data quality information
            summary.data_quality.total_elements = len(elements)
            summary.data_quality.node_count = city_data["node_count"]
            summary.data_quality.way_count = city_data["way_count"]
            summary.data_quality.relation_count = city_data["relation_count"]
            summary.data_quality.timestamp = datetime.fromisoformat(
                city_data["timestamp"]
            )
            summary.data_quality.query_time_seconds = city_data["query_time_seconds"]

            # Calculate missing fields based on requested categories
            for category in categories_config:
                if category != "area_metrics":
                    category_data = getattr(summary, category)
                    if all(
                        value == 0
                        for value in category_data.__dict__.values()
                        if isinstance(value, (int, float))
                    ):
                        summary.data_quality.missing_fields.append(category)

            if debug:
                print("\nDebug: Processing completed")
                print(
                    f"Debug: Total elements processed: {summary.data_quality.total_elements}"
                )
                print(
                    f"Debug: Query time: {summary.data_quality.query_time_seconds:.2f} seconds"
                )
                if summary.data_quality.missing_fields:
                    print(
                        f"Debug: Empty categories: {', '.join(summary.data_quality.missing_fields)}"
                    )

            return summary

        except Exception as e:
            if debug:
                print(f"Debug: Error during processing: {str(e)}")
                import traceback

                print(traceback.format_exc())
            raise
