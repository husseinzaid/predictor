import type { Factor, SimulateResponse, Team, WeightsMap } from "../types";
import mockFactors from "../mocks/factors.json";
import mockTeams from "../mocks/teams.json";
import mockSimulateResponse from "../mocks/simulate_response.json";

// Set VITE_USE_MOCKS=false (in .env.local) once the FastAPI backend is
// running at VITE_API_BASE_URL to hit the real API instead of fixtures.
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getFactors(): Promise<Factor[]> {
  if (USE_MOCKS) return mockFactors as Factor[];
  const res = await fetch(`${API_BASE_URL}/api/factors`);
  if (!res.ok) throw new Error(`GET /api/factors failed: ${res.status}`);
  return res.json();
}

export async function getTeams(): Promise<Team[]> {
  if (USE_MOCKS) return mockTeams as Team[];
  const res = await fetch(`${API_BASE_URL}/api/teams`);
  if (!res.ok) throw new Error(`GET /api/teams failed: ${res.status}`);
  return res.json();
}

export async function simulate(weights: WeightsMap): Promise<SimulateResponse> {
  if (USE_MOCKS) return mockSimulateResponse as SimulateResponse;
  const res = await fetch(`${API_BASE_URL}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weights }),
  });
  if (!res.ok) throw new Error(`POST /api/simulate failed: ${res.status}`);
  return res.json();
}
