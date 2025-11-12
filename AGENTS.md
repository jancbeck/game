# Copilot Instructions for Hades Zero

## Repository Overview

Hades-inspired twin-stick shooter prototype. Godot 4.5.1 project with GDScript.

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GDScript Toolkit 4.x, Git LFS for assets.

## Project Structure

```
game/
├── project.godot       # 1280x720, canvas_items stretch, bg_color=#3F4944
├── src/
│   ├── actors/
│   │   ├── player/
│   │   │   ├── Player.tscn
│   │   │   ├── Player.gd
│   │   │   ├── PlayerState.gd      # Autoload: persistent upgrades
│   │   │   ├── player_8dir.png     # 1024x1024, 3x3 grid
│   │   │   └── sfx_shoot_01-03.wav # Shooting sound variants
│   │   └── enemy/
│   │       ├── Enemy.tscn
│   │       ├── Enemy.gd
│   │       └── enemy_blob.png      # 1024x1024
│   ├── items/
│   │   ├── boon/
│   │   │   ├── Boon.tscn
│   │   │   ├── Boon.gd
│   │   │   ├── boon.png            # 169x241 upgrade pickup
│   │   │   └── sfx_boon_pickup.mp3
│   │   └── bullet/
│   │       ├── Bullet.tscn
│   │       ├── Bullet.gd
│   │       └── BulletParticles.tscn # Yellow impact particles
│   ├── world/
│   │   └── room/
│   │       ├── Room.tscn
│   │       ├── Room.gd
│   │       ├── room_base.png       # 1024x1024 background
│   │       ├── room_bottom.png     # 1024x105 foreground overlay
│   │       ├── music_room_entered_loop.wav  # 1:20 calm music
│   │       └── music_enemies_aggro_loop.wav # 1:20 combat music
│   ├── vfx/
│   │   ├── Impact.tscn
│   │   ├── Impact.gd
│   │   ├── ExplosionParticles.tscn # Red/orange explosion particles
│   │   ├── impact_small.png        # 500x500, 3x2 grid
│   │   └── ScreenShake.gd          # Autoload: trauma-based camera shake
│   ├── ui/
│   │   ├── HUD.tscn
│   │   └── HUD.gd                  # Health bar, enemy count, fire rate
│   ├── core/
│   │   ├── main.tscn               # Root scene with Camera2D
│   │   ├── Utils.gd                # Autoload: y-sorting
│   │   ├── GameCamera.gd           # Camera group membership
│   │   ├── MusicManager.gd         # Autoload: crossfading music system
│   │   ├── SceneTransition.tscn
│   │   └── SceneTransition.gd      # Autoload: fade transitions
│   └── tests/
│       ├── BulletTest.gd           # 3 tests: damage, speed, instantiation
│       ├── EnemyTest.gd            # 4 tests: hp, speed, damage, group
│       ├── BoonTest.gd             # 3 tests: multiplier, instantiation, calculation
│       ├── PlayerTest.gd           # 4 tests: max_hp, initial hp, take_damage, group
│       ├── PlayerStateTest.gd      # 4 tests: default, apply_boon, is_max, reset
│       └── RoomIntegrationTest.gd  # 4 tests: player spawn, 3 enemies, playable_area, exit
└── addons/
    └── gdUnit4/
```

## Core Systems

### Room System (`Room.gd`)

- Scales 1024x1024 background to fit 720p viewport (min scale ~0.703)
- Centers background with letterboxing on dark green-gray (#3F4944)
- Generates wall collisions with 112px margin (scaled), 256px exit gap at bottom
- room_bottom.png overlay at z-index 1000 for depth effect
- Spawns 3 enemies in top half of room to avoid immediate aggro
- Exit trigger always active, fades to new room (keeps PlayerState)
- Spawns boon at center after clearing enemies (once per room, if not max fire rate)

**Key vars:** `playable_area` (Rect2), `bg_scale` (float ~0.703), `boon_spawned` (bool)

### Player System (`Player.gd`)

- Twin-stick: WASD movement (250 speed), mouse aiming
- 3x3 sprite grid (1024x1024): Top=NE/N/NW, Mid=E/empty/W, Bot=SE/S/SW
- Scales sprite to 128px height
- 10px mouse deadzone to prevent flicker
- Fires bullets toward mouse (default 0.18s cooldown, persistent via PlayerState)
- 100 max HP, red flash on damage (0.1s), death at hp<=0
- Death resets PlayerState and fades to new room
- Y-sorting via Utils singleton
- Shooting: Screen shake (0.15 trauma), random SFX variant (1-3)
- Damage: Screen shake (0.5 trauma), red flash

**Sprite mapping:** Sector→Index: E=3, NE=0, N=1, NW=2, W=5, SW=8, S=7, SE=6

### Enemy System (`Enemy.gd`)

- Patrol mode: 75 speed, wanders 100px radius from spawn
- Aggro mode: 150 speed, chases player, triggered by proximity (200px) or damage
- Once aggroed, always chases (no de-aggro)
- 40 HP, spawns impact on damage, red flash (0.1s)
- Contact damage: 10 HP to player, 1s cooldown
- Stuck detection: respawns at spawn if <5px movement in 1.5s
- Scales from 1024x1024 to 64px, Y-sorting
- Death: Screen shake (0.3 trauma), explosion particles, 0.05s hit-stop

### Bullet System (`Bullet.gd`)

- Procedural yellow circle (16x16, scaled from generated image)
- 900 speed, 20 damage, 1.2s lifetime
- Collision mask=6 (walls + enemies)
- Spawns Impact + BulletParticles (yellow, 8 particles) on hit, destroys on hit or timeout

### Impact Effect (`Impact.gd`)

- 3x2 animated sprite sheet (500x500 source)
- Scaled to 80px for visibility
- 0.04s per frame, auto-destroys after animation

### Boon System (`Boon.gd`)

- Pickup reduces fire_cooldown by 35% (multiplier 0.65, min 0.05s)
- Updates PlayerState.fire_cooldown and current player instance
- Spawns at room center after clearing enemies (once per room)
- Scaled from 169x241 to 48px height

### PlayerState Autoload (`PlayerState.gd`)

- Persistent singleton for upgrades across room transitions
- `fire_cooldown`: starts 0.18s, min 0.05s
- `apply_boon()`: multiply cooldown by 0.65
- `is_max_fire_rate()`: check if at minimum
- `reset()`: restore defaults on death

### SceneTransition Autoload (`SceneTransition.gd`)

- Fade-to-black overlay at layer 100
- `fade_to_black_and_reload(duration)`: 0.8s fade out, 0.5s hold, reload, 0.8s fade in
- `fade_to_black_on_death(duration)`: Reparents player to layer 101 to keep visible during fade
- Cubic easing, waits for scene initialization before fade-in
- Called on player death and room exit

### MusicManager Autoload (`MusicManager.gd`)

- Manages seamless crossfading between room and aggro music tracks
- Both tracks play simultaneously, volume controlled for smooth transitions
- `start_room_music()`: Start calm music at beginning of room
- `trigger_aggro()`: 2s crossfade to combat music, synced to current playback position
- `trigger_calm()`: 2s crossfade back to calm music (not currently used)
- Tracks are 1:20 long and loop continuously
- Syncs playback position during crossfade for seamless transition

### ScreenShake Autoload (`ScreenShake.gd`)

- Trauma-based camera shake system for visceral combat feedback
- `add_trauma(amount)`: Add 0-1 trauma to trigger shake (clamped)
- Trauma decays at 1.5/s, shake intensity = trauma²
- Max offset: 75px, max rotation: 0.15 radians
- Finds camera via "camera" group membership
- Processes during pause for hit-stop compatibility
- Different trauma amounts: shoot (0.08), player damage (0.5), enemy death (0.4)

### Visual Feedback Systems

**Screen Shake:**

- Player shooting: 0.08 trauma (very light, prevents spam accumulation)
- Player taking damage: 0.5 trauma (strong warning)
- Enemy death: 0.4 trauma (satisfying impact)

**Hit-Stop:**

- 0.05s game pause when enemy is hit by bullet for chunky impact feel
- Timer processes during pause to ensure hit-stop works correctly
- Camera and ScreenShake process during pause for continuous feedback

**Particle Systems:**

- BulletParticles: Yellow, 8 particles, 0.3s lifetime, spawns on bullet impact
- ExplosionParticles: Red/orange, 20 particles, 0.5s lifetime, gravity, spawns on enemy death
- Auto-cleanup after particle lifetime to prevent memory leaks

## Asset Specifications

All art is 1024x1024, 500x500, or custom sizes. Scripts scale down:

- Player sprite: 128px height
- Enemy: 64px
- Boon: 48px height (from 169x241 source)
- Impact: 80px
- Room: Scaled to fit 720px height (~0.703x)
- Room bottom overlay: Matches room scale, z-index 1000

## Collision Layers

- Layer 1: Player, Boon detection
- Layer 2: Walls
- Layer 4: Enemies
- Player mask: 3 (1+2: boons + walls)
- Enemy mask: 7 (1+2+4: player + walls + enemies)
- Bullet mask: 6 (2+4: walls + enemies)

## Input Map

- `move_up/down/left/right`: WASD + arrows
- `shoot`: Left mouse button

## Build & Validation

```bash
# Format & lint
source .venv/bin/activate
gdformat scripts/ && gdlint scripts/

# Import & generate UIDs
/Applications/Godot.app/Contents/MacOS/Godot --path . -e --headless --quit-after 2000

# Run tests using gdUnit4 (smoke tests for fast iteration)
/Applications/Godot.app/Contents/MacOS/Godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test
```

## Critical Rules

- **Typed GDScript mandatory**: Explicit types for all vars to avoid inference errors
- **Linting must pass**: `gdformat` and `gdlint` before commits
- **Scaling**: All assets need explicit scaling, adjust coordinates by `bg_scale`
- **Y-sorting**: Call `Utils.ysort_by_y(self)` in `_physics_process` for depth
- **Godot 4.5 syntax**: `.emit()` for signals, typed annotations
- **Signal-based communication**: Avoid tight coupling
- **Generate UIDs**: Always run headless import after creating scenes/scripts
- **Persistent state**: Use PlayerState autoload for cross-room data
- **Transitions**: Use SceneTransition.fade_to_black_and_reload() for scene changes
- **Comments**: Explain "why" and complex logic, not self-explanatory "what"
- **Tests**: Keep smoke tests short and focused on core values/behavior
- **Keep AGENTS.md updated** with system changes
