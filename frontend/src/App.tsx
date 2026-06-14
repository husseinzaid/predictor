import { useEffect, useMemo, useState, type CSSProperties } from "react";
import confetti from "canvas-confetti";
import clsx from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import { Activity, CheckCircle2, DollarSign, Goal, History, Info, ListOrdered, Loader2, Medal, Moon, Sparkles, Sun, Trophy, TrendingUp, Users } from "lucide-react";
import { getFactors, getTeams, simulate } from "./api/client";
import type { Factor, GroupMatch, SimulateResponse, Team, WeightsMap } from "./types";
import "./App.css";

const PERCENT_FORMATTER = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

const SCORE_FORMATTER = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});


function App() {
  const [factors, setFactors] = useState<Factor[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [weights, setWeights] = useState<WeightsMap>({});
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    return window.localStorage.getItem("wc-theme") === "light" ? "light" : "dark";
  });
  const [simulationRun, setSimulationRun] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("wc-theme", theme);
  }, [theme]);
  const [openInfo, setOpenInfo] = useState<Set<string>>(new Set());

  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        const [factorData, teamData] = await Promise.all([getFactors(), getTeams()]);
        if (!active) return;
        setFactors(factorData);
        setTeams(teamData);
        setWeights(defaultWeights(factorData));
        setEnabled(defaultEnabled(factorData));
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Could not load predictor data.");
      } finally {
        if (active) setInitializing(false);
      }
    }

    loadData();
    return () => {
      active = false;
    };
  }, []);

  const totalWeight = useMemo(
    () =>
      factors.reduce((sum, factor) => {
        if (!isFactorEnabled(factor.id, enabled)) return sum;
        return sum + (weights[factor.id] ?? factor.default_weight);
      }, 0),
    [enabled, factors, weights],
  );

  const factorsByCategory = useMemo(() => {
    return factors.reduce<Record<string, Factor[]>>((groups, factor) => {
      groups[factor.category] = [...(groups[factor.category] ?? []), factor];
      return groups;
    }, {});
  }, [factors]);

  const teamsById = useMemo(() => {
    return new Map(teams.map((team) => [team.id, team]));
  }, [teams]);

  const champion = useMemo(
    () => (result ? getTeamDisplay(result.bracket.champion, teamsById) : null),
    [result, teamsById],
  );

  function updateWeight(factorId: string, value: number) {
    setWeights((current) => ({ ...current, [factorId]: value }));
  }

  function toggleFactor(factorId: string) {
    setEnabled((current) => ({ ...current, [factorId]: !isFactorEnabled(factorId, current) }));
  }

  function soloFactor(factorId: string) {
    setEnabled(Object.fromEntries(factors.map((factor) => [factor.id, factor.id === factorId])));
  }

  function toggleInfo(factorId: string) {
    setOpenInfo((current) => {
      const next = new Set(current);
      if (next.has(factorId)) {
        next.delete(factorId);
      } else {
        next.add(factorId);
      }
      return next;
    });
  }

  function handleReset() {
    setWeights(defaultWeights(factors));
    setEnabled(defaultEnabled(factors));
    setResult(null);
  }

  async function handleSimulate() {
    setLoading(true);
    setError(null);
    try {
      setResult(await simulate(simulationWeights(factors, weights, enabled)));
      setSimulationRun((current) => current + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div className="brand-mark">
          <span className="brand-icon"><Trophy size={18} /></span>
          <span>WC2026 Predictor</span>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
          type="button"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </header>

      <motion.section
        animate={{ opacity: 1, y: 0 }}
        className="hero"
        initial={{ opacity: 0, y: 16 }}
        transition={{ duration: 0.45 }}
      >
        <p className="eyebrow">Night Match Simulator</p>
        <h1>Your formula. Your World Cup champion.</h1>
        <p className="hero-copy">
          Tune the football factors you believe in, run the bracket, and see who your model sends
          lifting the trophy.
        </p>
      </motion.section>

      {error && <div className="notice error">{error}</div>}

      <section className="workspace" aria-label="Prediction controls and results">
        <motion.aside animate={{ opacity: 1, x: 0 }} className="panel controls-panel" initial={{ opacity: 0, x: -16 }} transition={{ delay: 0.08, duration: 0.35 }}>
          <div className="section-heading">
            <div>
              <p className="eyebrow">Your formula</p>
              <h2>Factor weights</h2>
            </div>
            <span className="team-count">{teams.length || "-"} teams</span>
          </div>

          {initializing ? (
            <p className="empty-state">Loading factors...</p>
          ) : (
            <>
              <div className="action-row controls-actions">
                <button className="secondary-button ai-button" onClick={handleReset} type="button">
                  <span className="ai-badge">AI</span>
                  Recommended defaults
                </button>
                <button
                  className="primary-button"
                  disabled={loading || factors.length === 0 || totalWeight === 0}
                  onClick={handleSimulate}
                  type="button"
                >
                  {loading ? <><Loader2 className="spin-icon" size={16} /> Simulating...</> : <><Goal size={16} /> Simulate World Cup</>}
                </button>
              </div>

              <div className="slider-groups">
                {Object.entries(factorsByCategory).map(([category, categoryFactors]) => (
                  <div className="factor-category" key={category}>
                    <h3><CategoryIcon category={category} /> {formatCategory(category)}</h3>
                    {categoryFactors.map((factor) => {
                      const value = weights[factor.id] ?? factor.default_weight;
                      const factorEnabled = isFactorEnabled(factor.id, enabled);
                      const normalized = factorEnabled && totalWeight > 0 ? (value / totalWeight) * 100 : 0;

                      return (
                        <div className={clsx("factor-control", !factorEnabled && "disabled", isSoloFactor(factor.id, enabled) && "solo-active")} key={factor.id}>
                          <div className="factor-topline">
                            <div className="factor-heading">
                              <label className="factor-toggle">
                                <input
                                  checked={factorEnabled}
                                  onChange={() => toggleFactor(factor.id)}
                                  type="checkbox"
                                />
                                <span>{factor.label}</span>
                              </label>
                              <span className="factor-info">
                                <button
                                  aria-expanded={openInfo.has(factor.id)}
                                  aria-label={`About ${factor.label}`}
                                  className="info-dot"
                                  onClick={() => toggleInfo(factor.id)}
                                  type="button"
                                >
                                  i
                                </button>
                                <span
                                  className={openInfo.has(factor.id) ? "factor-tooltip open" : "factor-tooltip"}
                                  role="tooltip"
                                >
                                  {factor.description}
                                </span>
                              </span>
                            </div>
                            <div className="factor-actions">
                              <button className="solo-button" onClick={() => soloFactor(factor.id)} type="button">
                                <Sparkles size={12} /> Solo
                              </button>
                              <strong>{PERCENT_FORMATTER.format(normalized)}%</strong>
                            </div>
                          </div>
                          <span className="slider-row">
                            <input
                              aria-label={`${factor.label} weight`}
                              disabled={!factorEnabled}
                              max="100"
                              min="0"
                              onChange={(event) => updateWeight(factor.id, Number(event.target.value))}
                              style={{ "--slider-fill": `${value}%` } as SliderStyle}
                              type="range"
                              value={value}
                            />
                            <span className="raw-weight">{value}</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </>
          )}
        </motion.aside>

        <section className="results-panel">
          {result ? (
            <Results champion={champion} result={result} runId={simulationRun} teamsById={teamsById} />
          ) : (
            <div className="panel empty-results">
              <p className="eyebrow">Ready when you are</p>
              <h2>Build your bracket</h2>
              <p>
                Adjust the sliders, hit simulate, and your champion probabilities, groups, and
                knockout path will appear here.
              </p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function Results({
  result,
  teamsById,
  champion,
  runId,
}: {
  result: SimulateResponse;
  teamsById: Map<string, Team>;
  champion: TeamDisplay | null;
  runId: number;
}) {
  const reduceMotion = useReducedMotion();
  const [showAllRankings, setShowAllRankings] = useState(false);
  const probabilityByTeam = useMemo(
    () => new Map(result.champion_probabilities.map((item) => [item.id, item.probability])),
    [result.champion_probabilities],
  );
  const visibleScores = showAllRankings ? result.team_scores : result.team_scores.slice(0, 12);

  useEffect(() => {
    if (!champion || reduceMotion) return;
    const colors = ["#2dbe4e", "#2a4bd7", "#e52a39", "#ffc72c"];
    confetti({ particleCount: 110, spread: 85, origin: { y: 0.28 }, colors });
    confetti({ particleCount: 28, spread: 55, origin: { y: 0.28 }, shapes: [confetti.shapeFromText({ text: "*", scalar: 1.6 })], colors: ["#ffc72c"] });
  }, [champion, reduceMotion, runId]);

  return (
    <motion.div animate={{ opacity: 1, y: 0 }} className="results-stack" initial={{ opacity: 0, y: 18 }} transition={{ duration: reduceMotion ? 0 : 0.35 }}>
      {champion && <ChampionReveal champion={champion} />}

      <section className="panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Model table</p>
            <h2>Power rankings</h2>
          </div>
          {champion && <div className="champion-pill">Your Champion: {champion.flag} {champion.name}</div>}
        </div>
        <p className="explanation compact-explanation">{result.explanation}</p>
        <div className="table-wrap rankings-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>
                  <span
                    className="info-header"
                    title="Power Score is the weighted team strength from your enabled factors and slider values. It is the model's base rating before the tournament path is simulated."
                  >
                    Power Score
                    <span aria-hidden="true" className="info-dot"><Info size={10} /></span>
                  </span>
                </th>
                <th>
                  <span
                    className="info-header"
                    title="Champion % is the team's chance to win the tournament in the simulation, including group results, knockout matchups, scorelines, and penalty shootouts."
                  >
                    Champion %
                    <span aria-hidden="true" className="info-dot"><Info size={10} /></span>
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleScores.map((score) => {
                const team = getTeamDisplay(score.id, teamsById, score.name);
                const scorePercent = score.power_score * 100;
                const championPercent = (probabilityByTeam.get(score.id) ?? 0) * 100;
                return (
                  <tr key={score.id}>
                    <td><RankBadge rank={score.rank} /></td>
                    <td>
                      <TeamName flag={team.flag} name={team.name} />
                    </td>
                    <td>
                      <div className="score-cell">
                        <span className="score-track"><span style={{ width: `${scorePercent}%` }} /></span>
                        <strong>{SCORE_FORMATTER.format(scorePercent)}</strong>
                      </div>
                    </td>
                    <td>
                      <div className="score-cell probability-cell">
                        <span className="score-track probability-track">
                          <span style={{ width: `${Math.min(championPercent, 100)}%` }} />
                        </span>
                        <strong>{championPercent > 0 ? `${PERCENT_FORMATTER.format(championPercent)}%` : "0%"}</strong>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {result.team_scores.length > 12 && (
          <button className="expand-button" onClick={() => setShowAllRankings((current) => !current)} type="button">
            {showAllRankings ? "Show top 12" : `Show all ${result.team_scores.length} teams`}
          </button>
        )}
      </section>

      <section className="panel group-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Representative simulation</p>
            <h2>Group stage</h2>
          </div>
        </div>
        <div className="group-grid">
          {result.group_stage.map((group) => (
            <article className="group-card" data-group={group.group} key={group.group}>
              <h3>Group {group.group}</h3>
              <GroupFixtures matches={group.matches} teamsById={teamsById} />
              <div className="table-wrap compact-table-wrap">
                <table className="standings-table">
                  <thead>
                    <tr>
                      <th>Team</th>
                      <th>P</th>
                      <th>W</th>
                      <th>D</th>
                      <th>L</th>
                      <th>GF</th>
                      <th>GA</th>
                      <th>GD</th>
                      <th>Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.standings.map((standing) => {
                      const team = getTeamDisplay(standing.id, teamsById, standing.name);
                      return (
                        <tr className={standing.qualified ? "qualified" : undefined} key={standing.id}>
                          <td className="standings-team">{standing.qualified && <CheckCircle2 className="qualified-icon" size={14} />}<TeamName flag={team.flag} name={team.name} /></td>
                          <td>{standing.played}</td>
                          <td>{standing.won}</td>
                          <td>{standing.drawn}</td>
                          <td>{standing.lost}</td>
                          <td>{standing.goals_for}</td>
                          <td>{standing.goals_against}</td>
                          <td>{formatGoalDifference(standing.goal_difference)}</td>
                          <td>{standing.points}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Knockout path</p>
            <h2>Bracket</h2>
          </div>
          {champion && <div className="champion-pill compact-pill">{champion.flag} {champion.name}</div>}
        </div>
        <div className="bracket-rounds">
          {result.bracket.rounds.map((round) => (
            <article className="round-card" key={round.name}>
              <h3>{round.name}</h3>
              <div className="match-list">
                {round.matches.map((match, index) => (
                  <div className="match-card" key={`${round.name}-${match.home}-${match.away}-${index}`}>
                    <TeamSlot
                      goals={match.home_goals}
                      id={match.home}
                      teamsById={teamsById}
                      winner={match.winner === match.home}
                    />
                    <TeamSlot
                      goals={match.away_goals}
                      id={match.away}
                      teamsById={teamsById}
                      winner={match.winner === match.away}
                    />
                    {match.penalties && (
                      <div className="penalty-note">
                        pen. {match.penalties.home}-{match.penalties.away}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </motion.div>
  );
}

function ChampionReveal({ champion }: { champion: TeamDisplay }) {
  return (
    <motion.section animate={{ opacity: 1, scale: 1 }} className="champion-reveal" initial={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.35 }}>
      <div className="champion-trophy"><Trophy size={30} /></div>
      <div>
        <p className="eyebrow">Champion Reveal</p>
        <h2>{champion.flag} {champion.name}</h2>
      </div>
    </motion.section>
  );
}

function GroupFixtures({ matches, teamsById }: { matches: GroupMatch[]; teamsById: Map<string, Team> }) {
  const matchesByDay = groupMatchesByMatchday(matches);

  return (
    <div className="fixtures-list">
      {matchesByDay.map(([matchday, dayMatches]) => (
        <div className="matchday-block" key={matchday}>
          <h4>Matchday {matchday}</h4>
          {dayMatches.map((match, index) => {
            const home = getTeamDisplay(match.home, teamsById);
            const away = getTeamDisplay(match.away, teamsById);

            return (
              <div className="fixture-line" key={`${match.matchday}-${match.home}-${match.away}-${index}`}>
                <TeamName className="fixture-team home-team" flag={home.flag} name={home.name} />
                <strong>{match.home_goals} - {match.away_goals}</strong>
                <TeamName className="fixture-team" flag={away.flag} name={away.name} />
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function CategoryIcon({ category }: { category: string }) {
  const iconProps = { size: 15, strokeWidth: 2.4 };
  if (category === "form") return <Activity {...iconProps} />;
  if (category === "ranking") return <ListOrdered {...iconProps} />;
  if (category === "squad") return <Users {...iconProps} />;
  if (category === "market") return <TrendingUp {...iconProps} />;
  if (category === "history") return <History {...iconProps} />;
  if (category === "fun") return <DollarSign {...iconProps} />;
  return <Sparkles {...iconProps} />;
}

function RankBadge({ rank }: { rank: number }) {
  const medalClass = rank === 1 ? "gold" : rank === 2 ? "silver" : rank === 3 ? "bronze" : undefined;
  return (
    <span className={clsx("rank-badge", medalClass)}>
      {rank <= 3 && <Medal size={14} />}
      #{rank}
    </span>
  );
}

function TeamName({ className, flag, name }: { className?: string; flag: string; name: string }) {
  return (
    <span className={className ? `team-label ${className}` : "team-label"}>
      <span aria-hidden="true" className="team-flag">{flag}</span>
      <span className="team-label-name">{name}</span>
    </span>
  );
}

function TeamSlot({
  goals,
  id,
  teamsById,
  winner,
}: {
  goals: number;
  id: string;
  teamsById: Map<string, Team>;
  winner: boolean;
}) {
  const team = getTeamDisplay(id, teamsById);
  return (
    <div className={winner ? "team-slot winner" : "team-slot"}>
      <TeamName flag={team.flag} name={team.name} />
      <span className="knockout-score">
        <strong>{goals}</strong>
        {winner && <em>Winner</em>}
      </span>
    </div>
  );
}

type SliderStyle = CSSProperties & {
  "--slider-fill": string;
};

type TeamDisplay = {
  flag: string;
  name: string;
};

function getTeamDisplay(id: string, teamsById: Map<string, Team>, fallbackName?: string): TeamDisplay {
  const team = teamsById.get(id);
  return {
    flag: team?.flag ?? "",
    name: team?.name ?? fallbackName ?? id,
  };
}

function defaultWeights(factors: Factor[]): WeightsMap {
  return Object.fromEntries(factors.map((factor) => [factor.id, factor.default_weight]));
}

function defaultEnabled(factors: Factor[]) {
  return Object.fromEntries(factors.map((factor) => [factor.id, true]));
}

function isFactorEnabled(factorId: string, enabled: Record<string, boolean>) {
  return enabled[factorId] ?? true;
}

function isSoloFactor(factorId: string, enabled: Record<string, boolean>) {
  const enabledIds = Object.entries(enabled).filter(([, value]) => value).map(([id]) => id);
  return enabledIds.length === 1 && enabledIds[0] === factorId;
}

function simulationWeights(factors: Factor[], weights: WeightsMap, enabled: Record<string, boolean>): WeightsMap {
  return Object.fromEntries(
    factors.map((factor) => [
      factor.id,
      isFactorEnabled(factor.id, enabled) ? weights[factor.id] ?? factor.default_weight : 0,
    ]),
  );
}
function groupMatchesByMatchday(matches: GroupMatch[]) {
  const grouped = matches.reduce<Map<number, GroupMatch[]>>((groups, match) => {
    groups.set(match.matchday, [...(groups.get(match.matchday) ?? []), match]);
    return groups;
  }, new Map());

  return [...grouped.entries()].sort(([a], [b]) => a - b);
}

function formatGoalDifference(goalDifference: number) {
  return goalDifference > 0 ? `+${goalDifference}` : String(goalDifference);
}


function formatCategory(category: string) {
  return category.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default App;
