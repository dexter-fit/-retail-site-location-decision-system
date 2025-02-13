__author__ = "Oleksandr Turytsia"
__maintainer__ = "Oleksandr Turytsia"
__email__ = "xturyt00@stud.fit.vutbr.cz"

from geopy.geocoders import Nominatim
from geopy.location import Location
from typing import Optional
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point
import osmnx as ox
import networkx as nx
import json
import os

from settings import (
    GRAPH
)

CACHE_COORDINATES = {}

def get_coordinates(place: str) -> Optional[tuple[float, float]]:
    """
    Get the coordinates (latitude and longitude) of a place.

    This function uses the geopy library to geocode the specified place and retrieve 
    its coordinates. If the location is found, it returns a tuple containing the latitude 
    and longitude. If the location is not found, it returns None.

    Args:
        place (str): The name of the place to get coordinates for.

    Returns:
        Optional[Tuple[float, float]]: A tuple containing the latitude and longitude 
            of the specified place, or None if the location is not found.

    Example:
        >>> get_coordinates("New York City")
        (40.7127281, -74.0060152)
    """

    if place in CACHE_COORDINATES:
        return CACHE_COORDINATES[place]

    geolocator = Nominatim(user_agent="my_app")
    location: Location = geolocator.geocode(place) # type: ignore

    CACHE_COORDINATES[place] = (location.latitude, location.longitude)

    if location:
        return  CACHE_COORDINATES[place]
    else:
        return None
    

def get_squares(meters=500) -> gpd.GeoDataFrame:
    """
    Generate square polygons covering the area of the graph.

    This function generates square polygons covering the area of the graph. 
    Each square has a specified size in meters and is defined by its center 
    point. The function divides the bounding box of the graph into squares 
    and creates polygons for each square.

    Args:
        meters (float, optional): The size of each square in meters. 
            Defaults to 500.

    Returns:
        gpd.GeoDataFrame: A GeoDataFrame containing square polygons 
            covering the area of the graph.

    Notes:
        This function assumes the existence of a global variable GRAPH, 
        which represents the graph data.

    Example:
        >>> get_squares(1000)
        <GeoDataFrame>
            geometry    center
        0   POLYGON ((<coordinates>))  POINT (<center coordinates>)
        1   POLYGON ((<coordinates>))  POINT (<center coordinates>)
        ...
    """
    def add_meters_to_latitude(latitude: float, meters: float) -> float:
        # Approximate scaling factor: 1 degree = 111 kilometers
        # meters = meters / 111000 degrees
        delta_lat = meters / 111000
        new_latitude = latitude + delta_lat
        return new_latitude

    def add_meters_to_longitude(longitude: float, latitude: float, meters: float) -> float:
        # Approximate scaling factor for longitude at equator: 1 degree = 111 kilometers
        # Scaling factor varies with latitude
        # Calculate the scaling factor for longitude at the given latitude
        scaling_factor = math.cos(math.radians(latitude))

        # meters meters = meters / (scaling_factor * 111000) degrees
        delta_lon = meters / (scaling_factor * 111000)
        new_longitude = longitude + delta_lon
        return new_longitude
    
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(GRAPH)

    # Get the bounding box coordinates
    minx, miny, maxx, maxy = gdf_nodes.geometry.total_bounds # type: ignore

    geometry: list[Polygon] = []
    center: list[Point] = []

    x1 = minx
    while x1 < maxx:

        y1 = miny
        x2 = add_meters_to_longitude(x1, miny, meters)

        while y1 < maxy:

            x2 = add_meters_to_longitude(x1, y1, meters)
            y2 = add_meters_to_latitude(y1, meters)

            center.append(Point(x2 - (x2 - x1) / 2, y2 - (y2 - y1) / 2))
            geometry.append(Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)]))

            y1 = y2
        x1 = x2

    return gpd.GeoDataFrame({"center": center, "geometry": geometry})

def get_squares_list() -> list[list[float]]:
    """
    Get the list of square coordinates.

    This function retrieves the list of coordinates for the exterior of each square polygon 
    generated by the get_squares function. It extracts the exterior coordinates of each 
    square polygon and returns them as a list of lists of floats.

    Returns:
        list[list[float]]: A list of lists of floats representing the exterior coordinates 
            of each square polygon.

    Notes:
        This function relies on the get_squares function to generate square polygons.

    Example:
        >>> get_squares_list()
        [
            [[<coordinates>], [<coordinates>], ...],  # Square 1 exterior coordinates
            [[<coordinates>], [<coordinates>], ...],  # Square 2 exterior coordinates
            ...
        ]
    """
    return [list(geometry.exterior.coords) for geometry in get_squares()["geometry"]] # type: ignore

def read_json_file(path_to_file: str, is_relative: bool = False) -> dict | list:
    """
    Read data from a JSON file.

    This function reads data from a JSON file located at the specified path. It can 
    optionally handle relative paths. The function returns the content of the JSON file 
    as either a dictionary or a list, depending on the structure of the JSON data.

    Args:
        path_to_file (str): The path to the JSON file.
        is_relative (bool, optional): Whether the provided path is relative to the 
            current working directory. Defaults to False.

    Returns:
        Union[dict, list]: The content of the JSON file as either a dictionary or a list.

    Raises:
        FileNotFoundError: If the specified file does not exist.

    Example:
        >>> read_json_file("data.json")
        {'key': 'value'}

        >>> read_json_file("data.json", is_relative=True)
        [{'key': 'value'}, {'key': 'value'}, ...]
    """
    path = os.path.join(os.getcwd(), path_to_file) if is_relative else path_to_file

    try:
        with open(path, "r", encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError as e:
        exit(str(e))

def read_dataset(path_to_file: str, is_relative: bool = False) -> list[tuple[float, float, float]]:

    dataset = read_json_file(path_to_file, is_relative)

    # TODO validation

    return dataset # type: ignore