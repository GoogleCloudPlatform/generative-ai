# @title Helper Functions

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_comprehensive_city_analysis(data):
    """
    Creates comprehensive visualizations combining EV infrastructure and city data
    Args:
        data: Raw data containing city and infrastructure information
    Returns:
        dict: Dictionary of plotly figures
    """
    figures = {}

    # Extract city data for the first city
    city_data = data.cities_data[0]
    city_name = f"{city_data.city}, {city_data.state}"

    # 1. EV Infrastructure Overview Dashboard
    # Create separate figures for different chart types

    # Charging Types
    charging_data = pd.DataFrame(
        [
            {
                "type": "DC Fast",
                "count": city_data.ev_data.charging_capabilities.by_type[
                    "dc_fast"
                ].count,
            },
            {
                "type": "Level 2",
                "count": city_data.ev_data.charging_capabilities.by_type[
                    "level2"
                ].count,
            },
            {
                "type": "Level 1",
                "count": city_data.ev_data.charging_capabilities.by_type[
                    "level1"
                ].count,
            },
        ]
    )

    charging_fig = px.bar(
        charging_data,
        x="type",
        y="count",
        title=f"Charging Station Types - {city_name}",
    )
    figures["charging_types"] = charging_fig

    # Connector Distribution (Pie Chart)
    connector_data = pd.DataFrame(
        [
            {"type": c.connector_type, "count": c.count}
            for c in city_data.ev_data.charging_capabilities.connector_distribution
        ]
    )
    connector_fig = px.pie(
        connector_data,
        values="count",
        names="type",
        title=f"Connector Distribution - {city_name}",
    )
    figures["connector_distribution"] = connector_fig

    # Network Distribution
    network_data = pd.DataFrame(
        [
            {"network": n.name, "count": n.station_count}
            for n in city_data.ev_data.network_analysis.networks
        ]
    )
    network_fig = px.bar(
        network_data,
        x="network",
        y="count",
        title=f"Network Distribution - {city_name}",
    )
    figures["network_distribution"] = network_fig

    # Access & Payment Methods
    access_data = pd.DataFrame(
        [
            {
                "method": "Credit Card",
                "percentage": city_data.ev_data.accessibility.payment_methods[
                    "credit_card"
                ]["percentage"],
            },
            {
                "method": "Mobile Pay",
                "percentage": city_data.ev_data.accessibility.payment_methods[
                    "mobile_pay"
                ]["percentage"],
            },
            {
                "method": "Network Card",
                "percentage": city_data.ev_data.accessibility.payment_methods[
                    "network_card"
                ]["percentage"],
            },
            {
                "method": "24/7 Access",
                "percentage": city_data.ev_data.accessibility.access_type[
                    "24_7_access"
                ]["percentage"],
            },
        ]
    )
    access_fig = px.bar(
        access_data,
        x="method",
        y="percentage",
        title=f"Access & Payment Methods - {city_name}",
    )
    figures["access_methods"] = access_fig

    # 2. Transportation Infrastructure Analysis
    transport_fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Public Transport Facilities",
            "Road Network Distribution",
            "Parking Facilities",
            "EV vs Traditional Infrastructure",
        ),
    )

    # Public Transport
    transport_data = pd.DataFrame(
        [
            {"type": "Bus Stops", "count": city_data.summary.transport.bus_stops},
            {
                "type": "Train Stations",
                "count": city_data.summary.transport.train_stations,
            },
            {"type": "Bus Stations", "count": city_data.summary.transport.bus_stations},
            {"type": "Bike Rental", "count": city_data.summary.transport.bike_rental},
        ]
    )
    transport_fig.add_trace(
        go.Bar(x=transport_data["type"], y=transport_data["count"]), row=1, col=1
    )

    # Road Network
    road_data = pd.DataFrame(
        [
            {"type": "Motorways", "count": city_data.summary.roads.motorways},
            {"type": "Primary", "count": city_data.summary.roads.primary_roads},
            {"type": "Secondary", "count": city_data.summary.roads.secondary_roads},
            {"type": "Residential", "count": city_data.summary.roads.residential_roads},
        ]
    )
    transport_fig.add_trace(
        go.Bar(x=road_data["type"], y=road_data["count"]), row=1, col=2
    )

    # Parking Facilities
    parking_data = pd.DataFrame(
        [
            {
                "type": "Surface Parking",
                "count": city_data.summary.parking.surface_parking,
            },
            {
                "type": "Parking Structures",
                "count": city_data.summary.parking.parking_structures,
            },
            {
                "type": "Street Parking",
                "count": city_data.summary.parking.street_parking,
            },
            {"type": "EV Charging", "count": city_data.summary.parking.ev_charging},
        ]
    )
    transport_fig.add_trace(
        go.Bar(x=parking_data["type"], y=parking_data["count"]), row=2, col=1
    )

    # EV vs Traditional Infrastructure
    infra_comparison = pd.DataFrame(
        [
            {
                "type": "EV Charging Stations",
                "count": city_data.summary.automotive.ev_charging_stations,
            },
            {
                "type": "Fuel Stations",
                "count": city_data.summary.automotive.fuel_stations,
            },
            {
                "type": "Car Dealerships",
                "count": city_data.summary.automotive.car_dealerships,
            },
            {"type": "Car Repair", "count": city_data.summary.automotive.car_repair},
        ]
    )
    transport_fig.add_trace(
        go.Bar(x=infra_comparison["type"], y=infra_comparison["count"]), row=2, col=2
    )

    transport_fig.update_layout(
        height=800, title_text=f"Transportation Infrastructure - {city_name}"
    )
    figures["transport"] = transport_fig

    # 3. Urban Amenities and Services
    amenities_fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Retail and Shopping",
            "Food and Entertainment",
            "Emergency Services",
            "Public Amenities",
        ),
    )

    # Retail
    retail_data = pd.DataFrame(
        [
            {
                "type": "Shopping Centers",
                "count": city_data.summary.retail.shopping_centres,
            },
            {"type": "Supermarkets", "count": city_data.summary.retail.supermarkets},
            {
                "type": "Department Stores",
                "count": city_data.summary.retail.department_stores,
            },
            {
                "type": "Convenience Stores",
                "count": city_data.summary.retail.convenience_stores,
            },
        ]
    )
    amenities_fig.add_trace(
        go.Bar(x=retail_data["type"], y=retail_data["count"]), row=1, col=1
    )

    # Food and Entertainment
    food_ent_data = pd.DataFrame(
        [
            {"type": "Restaurants", "count": city_data.summary.food.restaurants},
            {"type": "Cafes", "count": city_data.summary.food.cafes},
            {"type": "Bars", "count": city_data.summary.food.bars},
            {"type": "Fast Food", "count": city_data.summary.food.fast_food},
        ]
    )
    amenities_fig.add_trace(
        go.Bar(x=food_ent_data["type"], y=food_ent_data["count"]), row=1, col=2
    )

    # Emergency Services
    emergency_data = pd.DataFrame(
        [
            {
                "type": "Police Stations",
                "count": city_data.summary.emergency.police_stations,
            },
            {
                "type": "Fire Stations",
                "count": city_data.summary.emergency.fire_stations,
            },
            {"type": "Hospitals", "count": city_data.summary.healthcare.hospitals},
            {"type": "Clinics", "count": city_data.summary.healthcare.clinics},
        ]
    )
    amenities_fig.add_trace(
        go.Bar(x=emergency_data["type"], y=emergency_data["count"]), row=2, col=1
    )

    # Public Amenities
    public_data = pd.DataFrame(
        [
            {"type": "Post Offices", "count": city_data.summary.amenities.post_offices},
            {"type": "Banks", "count": city_data.summary.amenities.banks},
            {"type": "ATMs", "count": city_data.summary.amenities.atms},
            {"type": "Public Toilets", "count": city_data.summary.amenities.toilets},
        ]
    )
    amenities_fig.add_trace(
        go.Bar(x=public_data["type"], y=public_data["count"]), row=2, col=2
    )

    amenities_fig.update_layout(
        height=800, title_text=f"Urban Amenities and Services - {city_name}"
    )
    figures["amenities"] = amenities_fig

    # 4. Area Analysis (Pie Chart)
    area_data = pd.DataFrame(
        [
            {
                "type": "Total Area",
                "area": city_data.summary.area_metrics.total_area_sqkm,
            },
            {
                "type": "Water Area",
                "area": city_data.summary.area_metrics.water_area_sqkm,
            },
            {
                "type": "Green Area",
                "area": city_data.summary.area_metrics.green_area_sqkm,
            },
            {
                "type": "Built Area",
                "area": city_data.summary.area_metrics.built_area_sqkm,
            },
        ]
    )

    area_fig = px.pie(
        area_data,
        values="area",
        names="type",
        title=f"Area Distribution (sq km) - {city_name}",
    )
    figures["area"] = area_fig

    return figures


def plot_multi_city_comparison(data):
    """
    Creates comparative visualizations for multiple cities
    Args:
        data: Raw data containing multiple cities' information
    Returns:
        dict: Dictionary of comparison plotly figures
    """
    comparison_figs = {}

    if len(data.cities_data) > 1:
        # Prepare data for all cities
        cities_data = []
        for city in data.cities_data:
            cities_data.append(
                {
                    "city": f"{city.city}, {city.state}",
                    # EV Infrastructure
                    "ev_stations": city.summary.automotive.ev_charging_stations,
                    "fuel_stations": city.summary.automotive.fuel_stations,
                    "ev_station_density": city.ev_data.geographic_analysis.total_stations_per_square_mile,
                    "dc_fast_count": city.ev_data.charging_capabilities.by_type[
                        "dc_fast"
                    ].count,
                    "level2_count": city.ev_data.charging_capabilities.by_type[
                        "level2"
                    ].count,
                    "level1_count": city.ev_data.charging_capabilities.by_type[
                        "level1"
                    ].count,
                    # Transportation
                    "bus_stops": city.summary.transport.bus_stops,
                    "train_stations": city.summary.transport.train_stations,
                    "bus_stations": city.summary.transport.bus_stations,
                    "bike_rental": city.summary.transport.bike_rental,
                    # Road Network
                    "motorways": city.summary.roads.motorways,
                    "primary_roads": city.summary.roads.primary_roads,
                    "secondary_roads": city.summary.roads.secondary_roads,
                    "residential_roads": city.summary.roads.residential_roads,
                    # Parking
                    "surface_parking": city.summary.parking.surface_parking,
                    "parking_structures": city.summary.parking.parking_structures,
                    "street_parking": city.summary.parking.street_parking,
                    "ev_parking": city.summary.parking.ev_charging,
                    # Area Metrics
                    "total_area": city.summary.area_metrics.total_area_sqkm,
                    "water_area": city.summary.area_metrics.water_area_sqkm,
                    "green_area": city.summary.area_metrics.green_area_sqkm,
                    "built_area": city.summary.area_metrics.built_area_sqkm,
                    # Urban Amenities
                    "shopping_centres": city.summary.retail.shopping_centres,
                    "supermarkets": city.summary.retail.supermarkets,
                    "restaurants": city.summary.food.restaurants,
                    "cafes": city.summary.food.cafes,
                    "hospitals": city.summary.healthcare.hospitals,
                    "police_stations": city.summary.emergency.police_stations,
                }
            )

        df_comparison = pd.DataFrame(cities_data)

        # 1. EV Infrastructure Comparisons
        comparison_figs["ev_vs_fuel"] = px.bar(
            df_comparison,
            x="city",
            y=["ev_stations", "fuel_stations"],
            title="EV vs Fuel Stations by City",
            barmode="group",
        )

        comparison_figs["charging_types"] = px.bar(
            df_comparison,
            x="city",
            y=["dc_fast_count", "level2_count", "level1_count"],
            title="Charging Station Types by City",
            barmode="group",
        )

        comparison_figs["ev_density"] = px.bar(
            df_comparison,
            x="city",
            y="ev_station_density",
            title="EV Station Density by City",
        )

        # 2. Transportation Infrastructure
        comparison_figs["public_transport"] = px.bar(
            df_comparison,
            x="city",
            y=["bus_stops", "train_stations", "bus_stations", "bike_rental"],
            title="Public Transport Infrastructure by City",
            barmode="group",
        )

        comparison_figs["road_network"] = px.bar(
            df_comparison,
            x="city",
            y=["motorways", "primary_roads", "secondary_roads", "residential_roads"],
            title="Road Network Distribution by City",
            barmode="group",
        )

        comparison_figs["parking"] = px.bar(
            df_comparison,
            x="city",
            y=["surface_parking", "parking_structures", "street_parking", "ev_parking"],
            title="Parking Facilities by City",
            barmode="group",
        )

        # 3. Area Analysis
        area_metrics = ["total_area", "water_area", "green_area", "built_area"]
        comparison_figs["area_distribution"] = px.bar(
            df_comparison,
            x="city",
            y=area_metrics,
            title="Area Distribution by City",
            barmode="group",
        )

        # 4. Urban Amenities
        amenity_metrics = [
            "shopping_centres",
            "supermarkets",
            "restaurants",
            "cafes",
            "hospitals",
            "police_stations",
        ]
        comparison_figs["urban_amenities"] = px.bar(
            df_comparison,
            x="city",
            y=amenity_metrics,
            title="Urban Amenities by City",
            barmode="group",
        )

    return comparison_figs


def plot_all_visualizations(data):
    """
    Creates all visualizations for single and multi-city analysis
    Args:
        data: Raw data containing city and infrastructure information
    Returns:
        tuple: (single_city_figs, comparison_figs) - Dictionaries containing plotly figure objects
               comparison_figs will be empty if only one city is provided
    """
    # Generate single city visualizations
    single_city_figs = create_comprehensive_city_analysis(data)

    # Generate multi-city comparison visualizations if applicable
    comparison_figs = {}
    if len(data.cities_data) > 1:
        comparison_figs = plot_multi_city_comparison(data)

    return single_city_figs, comparison_figs
