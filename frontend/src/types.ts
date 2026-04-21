export type PokemonType =
  | "Normal" | "Fire" | "Water" | "Electric" | "Grass" | "Ice"
  | "Fighting" | "Poison" | "Ground" | "Flying" | "Psychic" | "Bug"
  | "Rock" | "Ghost" | "Dragon" | "Dark" | "Steel";

export interface MoveInfo {
  id: number;
  name: string;
  type: PokemonType;
  power: number | null;
  accuracy: number | null;
  pp: number;
  damage_class?: string;
}

export interface PlayerPokemon {
  slot: number;
  nickname: string;
  species_name: string;
  species_id: number;
  type1: PokemonType;
  type2: PokemonType | null;
  level: number;
  hp_current: number;
  hp_max: number;
  hp_percent: number;
  is_fainted: boolean;
  moves: MoveInfo[];
  sprite_url: string;
  strategy_role: "lead" | "support" | "closer" | "bench";
  risk_note?: string;
}

export interface OpponentPokemon {
  species_name: string;
  species_id: number;
  type1: PokemonType;
  type2: PokemonType | null;
  level: number;
  moves: MoveInfo[];
  sprite_url: string;
  danger_level: "low" | "medium" | "high";
}

export interface MatchupSummary {
  opponent_pokemon: string;
  player_pokemon_used: string;
  turns_to_ko: number;
  risk_level: "safe" | "caution" | "dangerous";
}

export interface SimTurn {
  turn: number;
  matchup: string;

  player_pokemon: string;
  player_pokemon_species: string;
  player_hp_before: number;
  player_hp_max: number;

  opponent_pokemon: string;
  opponent_hp_before: number;
  opponent_hp_max: number;

  goes_first: "player" | "opponent" | "tie";

  player_action: string;
  player_action_type: PokemonType;
  player_damage_min: number;
  player_damage_max: number;
  player_damage_avg: number;
  player_effectiveness: number;

  opponent_action: string;
  opponent_action_type: PokemonType;
  opponent_damage_min: number;
  opponent_damage_max: number;
  opponent_damage_avg: number;
  opponent_effectiveness: number;

  player_hp_after: number;
  opponent_hp_after: number;

  player_fainted: boolean;
  opponent_fainted: boolean;
  is_risky: boolean;
  note: string;
}

export interface Strategy {
  lead_recommendation: string;
  lead_reasoning: string;
  overall_notes: string;
  danger_pokemon: string[];
  matchup_summary: MatchupSummary[];
  turns: SimTurn[];
  total_turns: number;
  surviving_party: string[];
}

export interface DisplayData {
  player: {
    trainer_name: string;
    party: PlayerPokemon[];
  };
  opponent: {
    name: string;
    trainer_class: string;
    is_double: boolean;
    party: OpponentPokemon[];
  };
  strategy: Strategy;
}

export type UploadStep = "idle" | "uploading_sav" | "uploading_gba" | "analyzing" | "done" | "error";
