import { AlertTriangle, Shield, Zap } from "lucide-react";
import type { Strategy, Matchup } from "../types";

const RISK_ICON = {
  safe:      <Shield className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />,
  caution:   <Zap className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />,
  dangerous: <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />,
};

function MatchupRow({ m }: { m: Matchup }) {
  return (
    <div className={`card flex gap-3 items-start border-l-4
      ${m.risk_level === "safe" ? "border-l-green-500"
        : m.risk_level === "caution" ? "border-l-yellow-400"
        : "border-l-red-500"}`}
    >
      <div className="mt-0.5">{RISK_ICON[m.risk_level]}</div>
      <div className="flex-1 text-xs">
        <p className="font-semibold text-white">
          {m.player_pokemon}{" "}
          <span className="text-gray-400">vs</span>{" "}
          {m.opponent_pokemon}
        </p>
        <p className="text-pokegold mt-0.5">
          Use: <span className="font-semibold">{m.recommended_move}</span>
        </p>
        {m.notes && <p className="text-gray-400 mt-0.5 text-[11px]">{m.notes}</p>}
      </div>
    </div>
  );
}

interface Props {
  strategy: Strategy;
}

export default function StrategyDisplay({ strategy }: Props) {
  return (
    <section className="space-y-4">
      <h2 className="font-pixel text-sm text-pokegold">Battle Strategy</h2>

      {/* Lead recommendation */}
      <div className="card border border-pokegold/40 bg-pokegold/5">
        <p className="font-pixel text-[10px] text-pokegold mb-1">Recommended Lead</p>
        <p className="text-lg font-semibold text-white">{strategy.lead_recommendation}</p>
        <p className="text-xs text-gray-400 mt-1">{strategy.lead_reasoning}</p>
      </div>

      {/* Danger mons */}
      {strategy.danger_pokemon.length > 0 && (
        <div className="card border border-red-800 bg-red-900/10">
          <p className="font-pixel text-[10px] text-red-400 mb-1.5 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Danger Threats
          </p>
          <div className="flex flex-wrap gap-1.5">
            {strategy.danger_pokemon.map((name) => (
              <span key={name} className="text-[10px] font-pixel bg-red-900 text-red-300 px-2 py-0.5 rounded">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Matchups */}
      <div>
        <p className="font-pixel text-[10px] text-gray-400 mb-2">Matchup Breakdown</p>
        <div className="space-y-2">
          {strategy.matchups.map((m, i) => (
            <MatchupRow key={i} m={m} />
          ))}
        </div>
      </div>

      {/* Overall notes */}
      {strategy.overall_notes && (
        <div className="card bg-pokeborder/30">
          <p className="font-pixel text-[10px] text-gray-400 mb-1">Overall Notes</p>
          <p className="text-xs text-gray-300 leading-relaxed">{strategy.overall_notes}</p>
        </div>
      )}
    </section>
  );
}
