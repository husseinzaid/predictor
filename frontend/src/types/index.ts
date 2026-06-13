// Mirrors API_CONTRACT.md. Keep in sync with backend/app/schemas.py.

export interface Factor {
  id: string;
  label: string;
  description: string;
  category: "form" | "ranking" | "squad" | "market" | "history" | "fun" | string;
  default_weight: number;
}

export interface Team {
  id: string;
  name: string;
  flag: string;
  confederation: string;
  group: string;
  factors: Record<string, number>;
  raw: Record<string, number | string>;
}

export interface TeamScore {
  id: string;
  name: string;
  power_score: number;
  rank: number;
}

export interface ChampionProbability {
  id: string;
  name: string;
  probability: number;
}

export interface GroupMatch {
  matchday: number;
  home: string;
  away: string;
  home_goals: number;
  away_goals: number;
}

export interface GroupStanding {
  id: string;
  name: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  qualified: boolean;
}

export interface GroupResult {
  group: string;
  matches: GroupMatch[];
  standings: GroupStanding[];
}

export interface Penalties {
  home: number;
  away: number;
}

export interface BracketMatch {
  home: string;
  away: string;
  home_goals: number;
  away_goals: number;
  winner: string;
  penalties: Penalties | null;
}

export interface BracketRound {
  name: string;
  matches: BracketMatch[];
}

export interface Bracket {
  rounds: BracketRound[];
  champion: string;
}

export interface SimulateResponse {
  weights_used: Record<string, number>;
  team_scores: TeamScore[];
  champion_probabilities: ChampionProbability[];
  group_stage: GroupResult[];
  bracket: Bracket;
  explanation: string;
}

export type WeightsMap = Record<string, number>;
