import { PlayerCard } from "./PokemonCard";
import type { DisplayData } from "../types";

interface Props {
  data: DisplayData["player"];
  leadName: string;
}

export default function PartyDisplay({ data, leadName }: Props) {
  return (
    <section>
      <h2 className="font-pixel text-sm text-pokegold mb-3">
        {data.trainer_name}'s Party
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {data.party.map((p) => (
          <PlayerCard
            key={p.slot}
            pokemon={p}
            highlight={p.species_name === leadName || p.nickname === leadName}
          />
        ))}
      </div>
    </section>
  );
}
