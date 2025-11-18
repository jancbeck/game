---
id: rescue_prisoner
act: 2
prerequisites: [{"completed": "join_rebels"}]
approaches:
  violent:
    requires:
      violence_thoughts: 3
    degrades:
      flexibility_charisma: -3
      flexibility_cunning: -5
    rewards:
        convictions:
            violence_thoughts: 2
        memory_flags: ["guard_captain_hostile", "reputation_brutal"]
  stealthy:
    requires:
      flexibility_cunning: 5
    degrades:
      flexibility_cunning: -1
    rewards:
        convictions:
            deceptive_acts: 2
        memory_flags: ["guard_captain_unaware"]
outcomes:
  all: [{"advance_to": "report_to_rebel_leader"}, {"unlock_location": "rebel_hideout_innere"}]
---

# Quest: Rescue the Prisoner

The local rebel leader has a man on the inside, but he's been caught.

## Approaches

### Violent
Fight your way through the front gate.

### Stealthy
Sneak in through the sewers.
