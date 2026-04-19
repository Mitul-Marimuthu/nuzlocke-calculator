import TypeBadge from "./TypeBadge";
import type { PlayerPokemon, OpponentPokemon } from "../types";

interface PlayerCardProps {
  pokemon: PlayerPokemon;
  highlight?: boolean;
}

interface OpponentCardProps {
  pokemon: OpponentPokemon;
}

function HpBar({ current, max }: { current: number; max: number }) {
  const pct = max > 0 ? Math.round((current / max) * 100) : 0;
  const color =
    pct > 50 ? "bg-green-500" : pct > 25 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="mt-1">
      <div className="hp-bar-bg">
        <div className={`${color} h-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-gray-400 mt-0.5">
        {current}/{max} HP
      </p>
    </div>
  );
}

const ROLE_BADGE: Record<string, string> = {
  lead:    "bg-pokered text-white",
  support: "bg-blue-700 text-white",
  closer:  "bg-purple-700 text-white",
  bench:   "bg-gray-700 text-gray-300",
};

export function PlayerCard({ pokemon, highlight }: PlayerCardProps) {
  const ringClass = highlight ? "ring-2 ring-pokegold shadow-gold" : "";
  const faintedClass = pokemon.is_fainted ? "opacity-40 grayscale" : "";

  return (
    <div className={`card relative ${ringClass} ${faintedClass} transition-all`}>
      {highlight && (
        <span className="absolute -top-2 left-3 text-[9px] font-pixel text-pokegold">
          ★ LEAD
        </span>
      )}

      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <img
            src={pokemon.sprite_url}
            alt={pokemon.species_name}
            className="w-16 h-16 object-contain"
            style={{ imageRendering: "pixelated" }}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div>
              <p className="font-pixel text-xs text-pokegold truncate">{pokemon.nickname}</p>
              <p className="text-[10px] text-gray-400">{pokemon.species_name}</p>
            </div>
            <span className={`text-[9px] font-pixel px-1.5 py-0.5 rounded ${ROLE_BADGE[pokemon.strategy_role]}`}>
              {pokemon.strategy_role}
            </span>
          </div>

          <p className="text-[10px] text-gray-400 mt-0.5">Lv. {pokemon.level}</p>

          <div className="flex gap-1 mt-1 flex-wrap">
            <TypeBadge type={pokemon.type1} size="sm" />
            {pokemon.type2 && <TypeBadge type={pokemon.type2} size="sm" />}
          </div>

          <HpBar current={pokemon.hp_current} max={pokemon.hp_max} />

          {pokemon.risk_note && (
            <p className="text-[9px] text-yellow-400 mt-1 leading-tight">{pokemon.risk_note}</p>
          )}
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-1">
        {pokemon.moves.map((m) => (
          <div key={m.id} className="flex items-center gap-1 text-[9px] text-gray-300">
            <TypeBadge type={m.type} size="sm" />
            <span className="truncate">{m.name}</span>
            {m.power && <span className="text-gray-500 ml-auto">{m.power}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

export function OpponentCard({ pokemon }: OpponentCardProps) {
  const dangerBorder: Record<string, string> = {
    low:    "border-green-700",
    medium: "border-yellow-500",
    high:   "border-red-500",
  };
  const dangerLabel: Record<string, string> = {
    low:    "text-green-400",
    medium: "text-yellow-400",
    high:   "text-red-400",
  };

  return (
    <div className={`card border-2 ${dangerBorder[pokemon.danger_level]}`}>
      <div className="flex items-start gap-3">
        <img
          src={pokemon.sprite_url}
          alt={pokemon.species_name}
          className="w-16 h-16 object-contain"
          style={{ imageRendering: "pixelated", transform: "scaleX(-1)" }}
        />
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <p className="font-pixel text-xs text-white">{pokemon.species_name}</p>
            <span className={`text-[9px] font-pixel uppercase ${dangerLabel[pokemon.danger_level]}`}>
              {pokemon.danger_level}
            </span>
          </div>
          <p className="text-[10px] text-gray-400">Lv. {pokemon.level}</p>
          <div className="flex gap-1 mt-1 flex-wrap">
            <TypeBadge type={pokemon.type1} size="sm" />
            {pokemon.type2 && <TypeBadge type={pokemon.type2} size="sm" />}
          </div>
          {pokemon.moves.length > 0 && (
            <div className="mt-2 grid grid-cols-2 gap-1">
              {pokemon.moves.map((m) => (
                <div key={m.id} className="flex items-center gap-1 text-[9px] text-gray-300">
                  <TypeBadge type={m.type} size="sm" />
                  <span className="truncate">{m.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
