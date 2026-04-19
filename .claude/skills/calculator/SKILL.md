---
name: calculator
description: Given JSON files pertaining to a player's pokemon data and next trainer's pokemon data, calculate the optimal, safeest strategy for the player to win the next battle. Return the strategy as a JSON that holds the optimal play for every turn. 
---

When calculating the optimal strategy, always:
1. Consider type advantages and disadvantages.
2. Consider the current HP and stats of all pokemon involved.
3. Consider the damage rolls of all moves of all involved pokemon.
4. Always try to minimize the risk of losing pokemon, even if it means a longer battle. The agent should prioritize survival and winning over speed. 
5. Consider the possibility of status effects and how they might impact the battle.
6. Never use items in battle, unless they are held items.