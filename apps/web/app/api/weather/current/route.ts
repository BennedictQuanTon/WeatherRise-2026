import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const weatherData = {
    "Da Nang": {
      temp: 31,
      condition: "Partly Cloudy",
      risk: "Low",
      humidity: 72,
      wind_speed: 18.5,
      precipitation: 0.0,
      feels_like: 34,
      uv_index: 8,
      visibility_km: 10,
    },
    "Hanoi": {
      temp: 28,
      condition: "Light rain",
      risk: "Moderate",
      humidity: 84,
      wind_speed: 12.0,
      precipitation: 3.5,
      feels_like: 31,
      uv_index: 4,
      visibility_km: 7,
    },
    "Ho Chi Minh": {
      temp: 33,
      condition: "Sunny & Humid",
      risk: "Low",
      humidity: 68,
      wind_speed: 14.0,
      precipitation: 0.0,
      feels_like: 37,
      uv_index: 9,
      visibility_km: 10,
    }
  };

  return NextResponse.json(weatherData);
}
