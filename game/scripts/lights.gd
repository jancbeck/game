## Real-time lights for the figure and the crows, from scene.json -> lights. Each light belongs to
## the light group whose anchor is nearest (within 3 m, or the light's own "group" key) and follows
## that group's intensity, so the figure flickers with the fire it stands by. Open fires also move
## their light a few cm, as anim.py does.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const Curves := preload("res://scripts/curves.gd")
const FigureLook := preload("res://scripts/figure_look.gd")
const LIGHT_GAIN := 0.012      # Godot energy per Blender watt (inverse-square falloff on both sides)
## Irradiance of the flat ambient in the same units as a lamp's energy / d^2: a lamp whose light at a
## figure is a quarter of this casts a faint shadow, one at four times this a hard one.
const AMBIENT_IRRADIANCE := 1.3
const SHADOW_LAMP_MAX_SIZE_M := 1.0     # broad fills and window glows give no shadow
const FLOOR_ALBEDO := 0.16              # of the floor that bounces the lamps' light back up at a figure
const BOUNCE_MAX := 1.2
## The room's indirect light: every lamp lights the figure with energy / (d^2 + R^2), from all sides, as
## walls and floor throw the lamp's light around. R is about the size of a room.
const FILL_RADIUS_M := 2.4
const FILL_GAIN := 1.0
const FILL_MAX := 1.6
const FILL_CHROMA := 0.55

var lights: Array = []         # [{node, energy, pos, group, seed, curve}]
var compositor


func setup(data: SceneData, comp) -> void:
	compositor = comp
	FigureLook.apply_scene(data.scene.get("rain", true) == false)
	var linked := 0
	for i in data.scene.get("lights", []).size():
		var l: Dictionary = data.scene.lights[i]
		var o := OmniLight3D.new()
		o.name = l.name
		o.position = SceneData.v3(l.position)
		o.light_color = Color(l.color[0], l.color[1], l.color[2])
		o.light_energy = l.watts * LIGHT_GAIN
		o.omni_range = l.reach_m
		o.omni_attenuation = 2.0
		o.light_size = l.radius_m
		o.shadow_enabled = l.watts >= 100.0 and not l.get("inside_wall", false)
		o.light_specular = 0.3
		add_child(o)
		var g = null
		if l.get("group"):
			for cand in comp.groups:
				if cand.id == l.group:
					g = cand
		else:
			g = comp.nearest_group(o.position, 3.0)
		if g:
			linked += 1
		lights.append({node = o, energy = o.light_energy, pos = o.position, group = g.id if g else null,
			caster = l.radius_m <= SHADOW_LAMP_MAX_SIZE_M and not l.get("inside_wall", false),
			curve = g.curve if g else "", seed = (g.seed if g else 0) + 31 * i})
	print("lights: %d, %d following a light group" % [lights.size(), linked])


func update(t: float) -> void:
	for l in lights:
		if l.group == null:
			continue
		l.node.light_energy = l.energy * compositor.intensity(l.group)
		if l.curve == "fire":
			var lv: float = compositor.level(l.group)
			var s: int = l.seed
			var jig := 0.035
			l.node.position = l.pos + Vector3(jig * Curves.fbm(t * 2.0, s + 1, 2),
				jig * (0.5 * Curves.fbm(t * 2.5, s + 3, 2) + 1.2 * (lv - 1.0)),
				-jig * Curves.fbm(t * 2.0, s + 2, 2))
	_update_shadows()


## Every figure gets the three lamps that light it most (xyz and the share of the floor's light each
## gives), for the shadow it casts on the floor (figure_shadow.gdshader).
func _update_shadows() -> void:
	for fig in get_tree().get_nodes_in_group("figures"):
		var centre: Vector3 = fig.global_position + Vector3(0.0, 0.9, 0.0)
		var best: Array = []             # [[irradiance, position], ...] strongest first
		var on_floor := Vector3.ZERO     # irradiance of the floor under the figure, per colour channel
		var indirect := Vector3.ZERO     # the room's indirect light, per colour channel
		for l in lights:
			var o: OmniLight3D = l.node
			var p: Vector3 = o.global_position
			var cd2: float = centre.distance_squared_to(p)
			var creach: float = 1.0 - pow(sqrt(cd2) / o.omni_range, 4.0)
			if creach > 0.0:
				indirect += Vector3(o.light_color.r, o.light_color.g, o.light_color.b) * (
					o.light_energy * creach * creach / (cd2 + FILL_RADIUS_M * FILL_RADIUS_M))
			var to_floor: Vector3 = p - fig.global_position
			var fd2: float = maxf(to_floor.length_squared(), 0.25)
			var freach: float = 1.0 - pow(sqrt(fd2) / o.omni_range, 4.0)
			if freach > 0.0 and to_floor.y > 0.0:
				var e: float = o.light_energy * freach * freach / fd2 * to_floor.y / sqrt(fd2)
				on_floor += Vector3(o.light_color.r, o.light_color.g, o.light_color.b) * minf(e, 6.0)
			if not l.caster:
				continue
			var d2: float = maxf(centre.distance_squared_to(p), 0.25)
			var reach: float = 1.0 - pow(sqrt(d2) / o.omni_range, 4.0)
			if reach <= 0.0 or o.light_energy <= 0.0:
				continue
			var irr: float = o.light_energy * reach * reach / d2
			var at := best.size()
			while at > 0 and best[at - 1][0] < irr:
				at -= 1
			if at < 3:
				best.insert(at, [irr, p])
				if best.size() > 3:
					best.pop_back()
		var total := AMBIENT_IRRADIANCE
		for entry in best:
			total += entry[0]
		var v: Array[Vector4] = [Vector4.ZERO, Vector4.ZERO, Vector4.ZERO]
		for i in best.size():
			var p: Vector3 = best[i][1]
			v[i] = Vector4(p.x, p.y, p.z, best[i][0] / total)
		fig.set_shadow_lamps(v[0], v[1], v[2])
		var back := on_floor * FLOOR_ALBEDO
		# indirect light is less saturated than the lamps it comes from
		var grey: float = (indirect.x + indirect.y + indirect.z) / 3.0
		indirect = Vector3(grey, grey, grey).lerp(indirect, FILL_CHROMA) * FILL_GAIN
		fig.set_bounce(Color(minf(back.x, BOUNCE_MAX), minf(back.y, BOUNCE_MAX), minf(back.z, BOUNCE_MAX)),
			Color(minf(indirect.x, FILL_MAX), minf(indirect.y, FILL_MAX), minf(indirect.z, FILL_MAX)))
