import type { PokemonType } from "../types";

const TYPE_COLORS: Record<PokemonType, string> = {
  Normal:   "bg-[#A8A878] text-black",
  Fire:     "bg-[#F08030] text-black",
  Water:    "bg-[#6890F0] text-white",
  Electric: "bg-[#F8D030] text-black",
  Grass:    "bg-[#78C850] text-black",
  Ice:      "bg-[#98D8D8] text-black",
  Fighting: "bg-[#C03028] text-white",
  Poison:   "bg-[#A040A0] text-white",
  Ground:   "bg-[#E0C068] text-black",
  Flying:   "bg-[#A890F0] text-black",
  Psychic:  "bg-[#F85888] text-white",
  Bug:      "bg-[#A8B820] text-black",
  Rock:     "bg-[#B8A038] text-black",
  Ghost:    "bg-[#705898] text-white",
  Dragon:   "bg-[#7038F8] text-white",
  Dark:     "bg-[#705848] text-white",
  Steel:    "bg-[#B8B8D0] text-black",
};

interface Props {
  type: PokemonType;
  size?: "sm" | "md";
}

export default function TypeBadge({ type, size = "md" }: Props) {
  const color = TYPE_COLORS[type] ?? "bg-gray-500 text-white";
  const cls = size === "sm" ? "text-[9px] px-1.5 py-0.5" : "text-[10px] px-2 py-1";
  return (
    <span className={`${color} ${cls} rounded font-pixel uppercase tracking-wide`}>
      {type}
    </span>
  );
}
