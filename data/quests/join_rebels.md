---
id: join_rebels
act: 1
location: rebel_camp
prerequisites: []
approaches:
  diplomatic:
    label: "Offer your services"
    requires: {}
    degrades:
      flexibility_charisma: -5
      flexibility_empathy: -2
    rewards:
      memory_flags: ["joined_rebels"]
outcomes:
  all: [{"advance_to": "rescue_prisoner"}]
---

# Join the Rebels

You found the camp. Now you must convince them you are useful.

## Diplomatic Approach

Just talk to the leader.
