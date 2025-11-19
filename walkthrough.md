# Game Walkthrough (Act 1)

This document outlines the current playable content for Act 1: The Descent. It details the quest chain, available approaches, and the systemic consequences of your choices.

## Quest 1: Join the Rebels (`join_rebels`)

**Summary:** You found the camp. To earn their trust, you must offer something they cannot refuse.

*   **Prerequisites:** None (Starting Quest)
*   **Location:** Rebel Camp

### Approaches

1.  **Diplomatic**
    *   **Action:** Offer your services.
    *   **Requirements:** None.
    *   **Degradation:**
        *   -5 Flexibility (Charisma)
        *   -2 Flexibility (Empathy)
    *   **Rewards:**
        *   Memory Flag: `joined_rebels`

### Outcome
*   Unlocks Quest: `rescue_prisoner`

---

## Quest 2: Rescue the Prisoner (`rescue_prisoner`)

**Summary:** A rebel is held captive. You must break them out before they talk.

*   **Prerequisites:** Complete `join_rebels`
*   **Location:** King's Dungeon (implied)

### Approaches

1.  **Violent**
    *   **Action:** Storm the dungeon.
    *   **Requirements:** `violence_thoughts` >= 3
    *   **Degradation:**
        *   -3 Flexibility (Charisma)
        *   -5 Flexibility (Cunning)
    *   **Rewards:**
        *   +2 Conviction (Violence Thoughts)
        *   Memory Flags: `guard_captain_hostile`, `reputation_brutal`

2.  **Stealthy**
    *   **Action:** Sneak past the guards.
    *   **Requirements:** `flexibility_cunning` >= 5
    *   **Degradation:**
        *   -1 Flexibility (Cunning)
    *   **Rewards:**
        *   +2 Conviction (Deceptive Acts)
        *   Memory Flags: `guard_captain_unaware`

### Outcome
*   Unlocks Quest: `investigate_ruins`
*   Unlocks Location: `rebel_hideout_innere`

---

## Quest 3: Investigate Ruins (`investigate_ruins`)

**Summary:** Elira sent you to the ruins. A sealed door blocks the way, pulsing with dark energy. You must find a way inside.

*   **Prerequisites:** Complete `rescue_prisoner`
*   **Location:** Ancient Ruins

### Approaches

1.  **Analyze**
    *   **Action:** Decipher the warnings.
    *   **Requirements:** `flexibility_cunning` >= 3
    *   **Degradation:**
        *   -2 Flexibility (Empathy)
    *   **Rewards:**
        *   Memory Flag: `knows_corruption_origin`

2.  **Force**
    *   **Action:** Smash the sealed door.
    *   **Requirements:** `violence_thoughts` >= 5
    *   **Degradation:**
        *   -3 Flexibility (Cunning)
    *   **Rewards:**
        *   Memory Flag: `ruins_damaged`

3.  **Ritual**
    *   **Action:** Offer blood to the seal.
    *   **Requirements:** `flexibility_empathy` >= 4
    *   **Degradation:**
        *   -4 Flexibility (Charisma)
    *   **Rewards:**
        *   Memory Flag: `marked_by_corruption`

### Outcome
*   Unlocks Quest: `secure_camp_defenses` (Not yet implemented)

---

## System Notes

*   **Degradation:** Every major choice permanently reduces your "Flexibility" stats (Charisma, Cunning, Empathy), representing the toll of your actions.
*   **Convictions:** Some choices increase your "Convictions" (Violence, Deception, Compassion), unlocking new paths but potentially locking others.
*   **Memory Flags:** NPCs will remember your methods (e.g., if you were brutal or stealthy), affecting future dialogue and options.
