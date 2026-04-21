import { useState } from "react";
import { AlertTriangle, Shield, Zap, ChevronDown, ChevronRight, Swords, ArrowLeftRight } from "lucide-react";
import TypeBadge from "./TypeBadge";
import type { Strategy, SimTurn, MatchupSummary, PokemonType } from "../types";

// ── Helpers ────────────────────────────────────────────────────────────────

function EffLabel({ mult }: { mult: number }) {
  if (mult === 0)   return <span className="text-gray-500 text-[9px]">immune</span>;
  if (mult >= 4)    return <span className="text-red-400 text-[9px] font-pixel">4×</span>;
  if (mult >= 2)    return <span className="text-green-400 text-[9px] font-pixel">2×</span>;
  if (mult <= 0.25) return <span className="text-blue-400 text-[9px] font-pixel">¼×</span>;
  if (mult <= 0.5)  return <span className="text-blue-400 text-[9px] font-pixel">½×</span>;
  return null;
}

function MiniHpBar({ before, after, max, side }: { before: number; after: number; max: number; side: "player" | "opponent" }) {
  const pctBefore = max > 0 ? (before / max) * 100 : 0;
  const pctAfter  = max > 0 ? (after  / max) * 100 : 0;
  const color = pctAfter > 50 ? "bg-green-500" : pctAfter > 25 ? "bg-yellow-400" : "bg-red-500";
  const lostColor = side === "player" ? "bg-red-900" : "bg-green-900";

  return (
    <div className="w-full">
      <div className="h-1.5 rounded bg-gray-700 overflow-hidden relative">
        {/* lost HP shown as darker segment */}
        <div className={`absolute inset-0 ${lostColor}`} style={{ width: `${pctBefore}%` }} />
        <div className={`absolute inset-0 ${color} transition-all`} style={{ width: `${pctAfter}%` }} />
      </div>
      <div className="flex justify-between text-[9px] text-gray-500 mt-0.5">
        <span>{after}/{max}</span>
        {after < before && <span className="text-red-400">-{before - after}</span>}
      </div>
    </div>
  );
}

// ── Turn row ───────────────────────────────────────────────────────────────

function TurnRow({ turn }: { turn: SimTurn }) {
  const riskBorder = turn.is_risky ? "border-l-red-500" : turn.player_fainted ? "border-l-red-700" : "border-l-transparent";
  const faintBg    = (turn.player_fainted || turn.opponent_fainted) ? "bg-gray-800/60" : "";

  return (
    <div className={`border-l-2 ${riskBorder} pl-3 py-2 ${faintBg}`}>
      {/* Turn header */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[9px] font-pixel text-gray-500 w-8 flex-shrink-0">T{turn.turn}</span>

        {/* Speed indicator */}
        <span className={`text-[9px] font-pixel flex-shrink-0 ${turn.goes_first === "player" ? "text-green-400" : turn.goes_first === "tie" ? "text-yellow-400" : "text-red-400"}`}>
          {turn.goes_first === "player" ? "▶ you first" : turn.goes_first === "tie" ? "= tie" : "◀ opp first"}
        </span>

        {turn.is_risky && (
          <span className="text-[9px] font-pixel text-red-400 flex items-center gap-0.5">
            <AlertTriangle className="w-2.5 h-2.5" /> risky
          </span>
        )}
        {turn.opponent_fainted && <span className="text-[9px] font-pixel text-green-400">✓ KO</span>}
        {turn.player_fainted   && <span className="text-[9px] font-pixel text-red-400">✗ fainted</span>}
      </div>

      {/* Two-column: player side | opponent side */}
      <div className="grid grid-cols-2 gap-3">
        {/* Player */}
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 font-semibold truncate">{turn.player_pokemon}</p>
          <MiniHpBar before={turn.player_hp_before} after={turn.player_hp_after} max={turn.player_hp_max} side="player" />
          <div className="flex items-center gap-1 flex-wrap">
            <TypeBadge type={turn.player_action_type as PokemonType} size="sm" />
            <span className="text-[10px] text-white truncate">{turn.player_action}</span>
            <EffLabel mult={turn.player_effectiveness} />
          </div>
          <p className="text-[9px] text-green-400">
            {turn.player_damage_avg} dmg
            <span className="text-gray-500 ml-1">({turn.player_damage_min}–{turn.player_damage_max})</span>
          </p>
        </div>

        {/* Opponent */}
        <div className="space-y-1">
          <p className="text-[10px] text-gray-400 font-semibold truncate">{turn.opponent_pokemon}</p>
          <MiniHpBar before={turn.opponent_hp_before} after={turn.opponent_hp_after} max={turn.opponent_hp_max} side="opponent" />
          <div className="flex items-center gap-1 flex-wrap">
            <TypeBadge type={turn.opponent_action_type as PokemonType} size="sm" />
            <span className="text-[10px] text-gray-300 truncate">{turn.opponent_action}</span>
            <EffLabel mult={turn.opponent_effectiveness} />
          </div>
          <p className="text-[9px] text-red-400">
            {turn.opponent_damage_avg} dmg
            <span className="text-gray-500 ml-1">({turn.opponent_damage_min}–{turn.opponent_damage_max})</span>
          </p>
        </div>
      </div>

      {/* LLM note */}
      {turn.note && (
        <p className="text-[10px] text-yellow-300/80 mt-1.5 leading-relaxed italic">{turn.note}</p>
      )}
    </div>
  );
}

// ── Matchup group ──────────────────────────────────────────────────────────

function MatchupGroup({ label, turns, summary }: {
  label: string;
  turns: SimTurn[];
  summary?: MatchupSummary;
}) {
  const [open, setOpen] = useState(true);
  const riskColor = summary?.risk_level === "dangerous" ? "text-red-400" :
                    summary?.risk_level === "caution"   ? "text-yellow-400" : "text-green-400";

  return (
    <div className="card border border-pokeborder/60">
      <button
        className="w-full flex items-center justify-between gap-2 text-left"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-2">
          <Swords className="w-3.5 h-3.5 text-pokered flex-shrink-0" />
          <span className="font-pixel text-[10px] text-white">{label}</span>
          {summary && (
            <>
              <span className={`text-[9px] font-pixel ${riskColor}`}>{summary.risk_level}</span>
              <span className="text-[9px] text-gray-500">{turns.length} turn{turns.length !== 1 ? "s" : ""}</span>
            </>
          )}
        </div>
        {open ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
      </button>

      {open && (
        <div className="mt-3 space-y-2 divide-y divide-pokeborder/30">
          {turns.map(t => (
            <div key={t.turn} className="pt-2 first:pt-0">
              <TurnRow turn={t} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface Props { strategy: Strategy }

export default function StrategyDisplay({ strategy }: Props) {
  // Group turns by matchup label
  const groups: Record<string, SimTurn[]> = {};
  for (const turn of strategy.turns ?? []) {
    if (!groups[turn.matchup]) groups[turn.matchup] = [];
    groups[turn.matchup].push(turn);
  }

  const summaryByOpp: Record<string, MatchupSummary> = {};
  for (const s of strategy.matchup_summary ?? []) {
    summaryByOpp[s.opponent_pokemon] = s;
  }

  return (
    <section className="space-y-4">
      <h2 className="font-pixel text-sm text-pokegold">Battle Plan</h2>

      {/* Lead card */}
      <div className="card border border-pokegold/40 bg-pokegold/5">
        <p className="font-pixel text-[9px] text-pokegold mb-1">Recommended Lead</p>
        <p className="text-base font-semibold text-white">{strategy.lead_recommendation}</p>
        {strategy.lead_reasoning && (
          <p className="text-xs text-gray-400 mt-1">{strategy.lead_reasoning}</p>
        )}
      </div>

      {/* Danger list */}
      {strategy.danger_pokemon?.length > 0 && (
        <div className="card border border-red-800 bg-red-900/10">
          <p className="font-pixel text-[9px] text-red-400 mb-1.5 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Danger Threats
          </p>
          <div className="flex flex-wrap gap-1.5">
            {strategy.danger_pokemon.map(name => (
              <span key={name} className="text-[9px] font-pixel bg-red-900 text-red-300 px-2 py-0.5 rounded">{name}</span>
            ))}
          </div>
        </div>
      )}

      {/* Turn-by-turn */}
      {Object.keys(groups).length > 0 && (
        <div className="space-y-2">
          <p className="font-pixel text-[9px] text-gray-400 flex items-center gap-1.5">
            <ArrowLeftRight className="w-3 h-3" />
            Turn-by-Turn ({strategy.total_turns} total)
          </p>
          {Object.entries(groups).map(([label, turns]) => {
            const oppName = turns[0]?.opponent_pokemon;
            return (
              <MatchupGroup
                key={label}
                label={label}
                turns={turns}
                summary={summaryByOpp[oppName]}
              />
            );
          })}
        </div>
      )}

      {/* Overall notes */}
      {strategy.overall_notes && (
        <div className="card bg-pokeborder/20">
          <p className="font-pixel text-[9px] text-gray-400 mb-1 flex items-center gap-1">
            <Shield className="w-3 h-3" /> Overall Notes
          </p>
          <p className="text-xs text-gray-300 leading-relaxed">{strategy.overall_notes}</p>
        </div>
      )}

      {/* Surviving party */}
      {strategy.surviving_party?.length > 0 && (
        <div className="card border border-green-800 bg-green-900/10">
          <p className="font-pixel text-[9px] text-green-400 mb-1">Projected Survivors</p>
          <div className="flex flex-wrap gap-1.5">
            {strategy.surviving_party.map(name => (
              <span key={name} className="text-[9px] font-pixel bg-green-900 text-green-300 px-2 py-0.5 rounded">{name}</span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
