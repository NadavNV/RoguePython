# Rogue Python

## Table of Contents
* [Character Information](#character-information)
  * [Status Effects](#status-effects)
      * [Buffs](#buffs)
      * [Debuffs](#debuffs)
  * [Card Modifiers](#card-modifiers)

## Character Information

Each character in the game (except the vendor), be it a Player Character (PC) or a Non-Player Character (NPC/Enemy), has
several attributes in common. They each have **Health Points** (HP), and when their HP reach 0 they die. They each take
turns in combat, drawing a **hand** of cards from a **draw pile**, playing some or none of them, and then discarding them to a
**discard pile**. When the draw pile is empty the discard pile gets shuffled into the draw pile. Different enemies have
different cards, and the PC can be one of 3 different classes that each play differently and have their own unique set
of cards. The different enemies, player classes, and their cards are detailed ater on in this document, but first I'll 
explain some general terminology.

### Status Effects

Each character can be afflicted with several status effects, some beneficial (**buffs**) and some detrimental
(**debuffs**).

#### Buffs
* **Balm** - Restores 1 HP per stack at the beginning of the turn. Does not reduce at the end of the turn.
* **Block** - Absorbs 1 attack damage per stack. Does not block damage-over-time effects like bleed or poison. Removed
at the start of the turn.
* **Armor** - Adds 1 Block per stack at the end of the turn. Does not reduce at the end of the turn. 1 stack is removed
when taking attack damage that isn't blocked.
* **Evasion** - Negate the next attack that would have dealt HP damage and remove a stack. Does not reduce at the end of
the turn.
* **Strength** - Damage dealt by attacks is increased by 1 per stack. Does not reduce at the end of the turn.
* **Agility** - Block gained from cards is increased by 1 per stack. Does not reduce at the end of the turn.
* **Ward** - Negate the next debuff application and remove a stack. Does not reduce at the end of the turn.
* **Barbed** - When attacked, inflict 1 damage to the attacker per stack. Does not reduce at the end of the turn.

#### Debuffs
* **Poison** - Deals 1 damage per stack at the end of the turn. Does not reduce at the end of the turn.
* **Bleed** - Deals 1 damage per stack at the start of the turn. Reduced by 1 at the end of the turn.
* **Burning** - Deals 1 damage per stack at the start of the turn. Reduced by half (rounded down) at the end of the
turn.
* **Blight** - Deals 1 damage per stack at the end of the turn. Increased by 1 at the end of the turn.
* **Exposed** - Damage received from attacks is increased by 50%. Reduced by 1 at the end of the turn.
* **Shattered** - Block gained from cards is reduced by 50%. Reduced by 1 at the end of the turn.
* **Weakness** - Base damage dealt is reduced by 50%. Reduced by 1 at the end of the turn.

### Card Modifiers

Each card contains text that describes what that card does. The text may include certain keywords that modify the card's
behavior in some way.

* **Burn** - When played, this card does not go to the discard pile, but to a separate **burn pile** that does not get
shuffled into the draw pile.
* **Ethereal** - Must be played this turn to go to the discard pile, otherwise it goes to the burn pile when the turn
ends.
