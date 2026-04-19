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

export interface Matchup {
  player_pokemon: string;
  opponent_pokemon: string;
  recommended_move: string;
  risk_level: "safe" | "caution" | "dangerous";
  notes: string;
}

export interface Strategy {
  lead_recommendation: string;
  lead_reasoning: string;
  matchups: Matchup[];
  overall_notes: string;
  danger_pokemon: string[];
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
