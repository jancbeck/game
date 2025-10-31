# Gothic Aftermath Prototype

A Godot 4 prototype that blends Gothic II's aftermath with narrative mechanics inspired by Disco Elysium. This project provides a graybox slice that demonstrates core systems for dialog-driven progression, character stats, faction reputation, and investigative note tracking.

## Features

- **Exploration Hub** – Move around a compact harbor scene using WASD controls and collide with simple level geometry.
- **Conversation Engine** – Engage Sergeant Bran with branching dialog, internal voice call-outs, and stat-based skill checks.
- **Character Sheet** – Press `Q` to view core attributes, morale, health, and the current time phase along with faction standing summaries.
- **Notebook System** – Press `T` to review automatically curated investigation notes gathered during conversations.
- **Faction Reputation** – Choices influence faction meters for the Myrtanian Legion, Harbor Commons, Old Camp Remnants, and the Circle of Water.
- **Time Progression** – Certain dialog options advance a lightweight time counter reflected in the HUD and character sheet.

## Getting Started

1. Install [Godot 4.2](https://godotengine.org/). The project was authored against the 4.x branch.
2. Open the project folder (`/workspace/game`) in the Godot editor.
3. Run the project to enter the harbor scene.
4. Use the controls listed in the HUD to explore interactions and inspect UI overlays.

## Extending the Prototype

- Add more NPC scenes that reuse the existing conversation manager API.
- Author additional dialog resources or external data files to decouple narrative content.
- Expand the world geometry with tile sets, lighting, and interactable props.
- Wire up save/load support by serializing `WorldState` data into user files.

Contributions and further iteration can build on this foundation to realize the full post-Gothic II investigative RPG experience.
