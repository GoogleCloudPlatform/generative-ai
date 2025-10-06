/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use strict";

import axios from "axios";
import { config as dotenvConfig } from "dotenv";
import simplify from "simplify-js";
import { decode, encode, LatLngTuple } from "@googlemaps/polyline-codec";

const maxPolylineSize = 10000;

// Init required environment variables, see .env.example for required entries
dotenvConfig({
  path: process.env.ENV_FILE_LOCATION ? process.env.ENV_FILE_LOCATION : ".env",
});

// This will be intialised by dotenv
const GOOGLE_MAPS_API_KEY = process.env.GOOGLE_MAPS_API_SERVER_KEY!;

if (!GOOGLE_MAPS_API_KEY) {
  throw new Error("GOOGLE_MAPS_API_SERVER_KEY is not defined");
}

// Route request as sent to the maps routing API
interface RouteRequest {
  origin: {
    address: string;
  };
  destination: {
    address: string;
  };
  intermediates: [
    {
      address: string;
    },
  ];
  travelMode: string;
}

// Route response from the maps routing API
interface RouteReponse {
  routes: [
    {
      polyline: {
        encodedPolyline: string;
      };
    },
  ];
}

// Series of points for the simplification API
interface Point {
  x: number;
  y: number;
}

/**
 * Return an image showing a route between two addresses and optionally intermediate addresses
 * @param start The start address (e.g. Battersea Power Station)
 * @param stops An optional list of intermediate stops
 * @param end The end address (e.g. Tobacco Docks)
 */
export async function renderMap(
  start: string,
  end: string,
  stops?: string[],
): Promise<string> {
  // Obtain polyline for route between two points
  let polyline = await route(start, end, stops);

  // Maps API cannot draw a polyline greater than a certain size, if that happens simplify it
  if (polyline.length > maxPolylineSize) {
    const points = polylineToPoints(polyline);

    // We don't know the precision ahead of time, so iterate until we find it
    for (let i = 0.05; i <= 2; i += 0.05) {
      const s = simplify(points, i, false);
      // If we have fewer than 3000 points attempt an encoding
      if (s.length < 3000) {
        polyline = pointsToPolyline(s);
        if (polyline.length <= maxPolylineSize) {
          break;
        }
      }
    }
    // If we got this far then we cannot draw a polyline, even after simplification - error out
    if (polyline.length > maxPolylineSize) {
      throw new Error("Cannot render map between these two points");
    }
  }

  // Construct Google Maps API request
  const mapURL = new URL("https://maps.googleapis.com/maps/api/staticmap");
  mapURL.searchParams.set("size", "640x640");
  mapURL.searchParams.set("path", `enc:${polyline}`);
  mapURL.searchParams.set("key", GOOGLE_MAPS_API_KEY!);

  // Render a static image from the polyline
  try {
    const response = await fetch(mapURL);
    if (response.status != 200) {
      throw new Error(
        `Error fetching map image. Status code: ${response.status}`,
      );
    }
    const mapImageBuffer = await response.arrayBuffer();
    // Convert the buffer to a data URL
    return Buffer.from(mapImageBuffer).toString("base64");
  } catch (error) {
    console.error("Error fetching map image:", error);
    throw error;
  }
}
// Calculate distance between two points. Will ultimately return a polyline
async function route(
  start: string,
  end: string,
  stops?: string[],
): Promise<string> {
  const intermediates: { address: string }[] = [];
  // Populate intermediate stops
  if (stops) {
    stops.forEach((stop) => {
      if (stop !== "") {
        intermediates.push({
          address: stop,
        });
      }
    });
  }
  const request = {
    destination: {
      address: end,
    },
    origin: {
      address: start,
    },
    intermediates: intermediates,
    travelMode: "TRAVEL_MODE_UNSPECIFIED",
  } as RouteRequest;

  try {
    const response = await axios.post(
      "https://routes.googleapis.com/directions/v2:computeRoutes",
      request,
      {
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
          "X-Goog-FieldMask": "routes.polyline",
        },
      },
    );
    const mapsResponse = response.data as RouteReponse;
    return mapsResponse.routes[0].polyline.encodedPolyline;
  } catch (error) {
    console.error("Error fetching route data:", error);
    // console.error(error.response.data);
    throw error;
  }
}

// Converts a polyline into a series of points that can be simplified
function polylineToPoints(polyline: string): Point[] {
  const decodedPoints = decode(polyline, 5);
  const newPoints: Point[] = [];
  decodedPoints.forEach((p) => {
    newPoints.push({ x: p[0], y: p[1] });
  });
  return newPoints;
}

// Converts a series of points into a polyline
function pointsToPolyline(points: Point[]): string {
  const tuple: LatLngTuple[] = [];
  points.forEach((p) => {
    tuple.push([p.x, p.y]);
  });
  return encode(tuple);
}
