import { Swords } from "lucide-react";
import { OpponentCard } from "./PokemonCard";
import type { DisplayData } from "../types";

interface Props {
  data: DisplayData["opponent"];
}

export default function TrainerDisplay({ data }: Props) {
  return (
    <section>
      <h2 className="font-pixel text-sm text-pokered mb-1 flex items-center gap-2">
        <Swords className="w-4 h-4" />
        {data.trainer_class} {data.name}
      </h2>
      {data.is_double && (
        <span className="text-[9px] font-pixel text-yellow-400 mb-3 block">
          ⚡ DOUBLE BATTLE
        </span>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
        {data.party.map((p, i) => (
          <OpponentCard key={i} pokemon={p} />
        ))}
      </div>
    </section>
  );
}
