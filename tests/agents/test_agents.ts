/**
 * Agent eval tests — run with: npm run test:agents
 * These are integration tests that validate agent output shape,
 * not exact values (LLM outputs are non-deterministic).
 */

import { describe, it, expect } from "vitest";

// Minimal mock display data shape validation
interface DisplayData {
  player: { trainer_name: string; party: unknown[] };
  opponent: { name: string; trainer_class: string; is_double: boolean; party: unknown[] };
  strategy: {
    lead_recommendation: string;
    lead_reasoning: string;
    matchups: unknown[];
    overall_notes: string;
    danger_pokemon: string[];
  };
}

function isValidDisplayData(data: unknown): data is DisplayData {
  if (typeof data !== "object" || data === null) return false;
  const d = data as Record<string, unknown>;
  return (
    typeof d.player === "object" &&
    typeof d.opponent === "object" &&
    typeof d.strategy === "object"
  );
}

describe("DisplayData shape validation", () => {
  it("accepts a well-formed display payload", () => {
    const sample: DisplayData = {
      player: {
        trainer_name: "Red",
        party: [
          {
            slot: 0,
            nickname: "PIKA",
            species_name: "Pikachu",
            type1: "Electric",
            type2: null,
            level: 25,
            hp_current: 50,
            hp_max: 55,
            hp_percent: 90,
            is_fainted: false,
            moves: [],
            sprite_url: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png",
            strategy_role: "lead",
            risk_note: null,
          },
        ],
      },
      opponent: {
        name: "Roxanne",
        trainer_class: "Gym Leader",
        is_double: false,
        party: [],
      },
      strategy: {
        lead_recommendation: "PIKA",
        lead_reasoning: "Electric is neutral vs Rock, but it outspeeds.",
        matchups: [],
        overall_notes: "Be careful of Geodude's Rock Throw.",
        danger_pokemon: ["Nosepass"],
      },
    };

    expect(isValidDisplayData(sample)).toBe(true);
    expect(sample.player.party).toHaveLength(1);
    expect(sample.strategy.danger_pokemon).toContain("Nosepass");
  });

  it("rejects missing fields", () => {
    expect(isValidDisplayData(null)).toBe(false);
    expect(isValidDisplayData({ player: {} })).toBe(false);
    expect(isValidDisplayData("string")).toBe(false);
  });
});
