## How the figures are shaded in the place they stand in: the sky rim, how much chroma their cloth keeps,
## where the irradiance of a lamp is compressed, and what the floor shadow is multiplied by. lights.gd
## sets it from scene.json before the figures are made; player.gd reads it when it builds a material.
## The shader is shaders/figure.gdshader, the floor shadow shaders/figure_shadow.gdshader.
extends RefCounted

## Cool light from the sky on the edges that face up (scaled by rim_strength in the shader).
static var rim_color := Color(0.30, 0.42, 0.75)
static var rim_strength := 0.30
## Share of the albedo's chroma that is kept. The sacks and banners of the set are close to grey wool; a
## brown with the recipe's chroma turns crimson under a 2000 K fire and the Punchy view transform.
static var saturation := 0.70
static var brightness := 1.2
## Energy units: a lamp's irradiance above this is compressed, so a fire close to a figure does not clip.
static var irr_knee := 5.0
## Multiplies the cloth's albedo to take the cast out of the light: under the fires and the blue windows of a
## room, a brown wool has little green to reflect and turns plum.
static var balance := Vector3(1.0, 1.0, 1.0)
## What the frame is multiplied by in the full shadow of a figure (the floor with only the sky on it).
static var shade := Color(0.20, 0.24, 0.38)


## `interior`: a room (scene.json "rain": false) has no sky, only dusk through windows and the neutral
## bounce of its own walls.
static func apply_scene(interior: bool) -> void:
	if interior:
		rim_color = Color(0.40, 0.46, 0.62)
		rim_strength = 0.18
		shade = Color(0.24, 0.24, 0.32)
		balance = Vector3(0.93, 1.12, 0.97)
	else:
		rim_color = Color(0.30, 0.42, 0.75)
		rim_strength = 0.24
		shade = Color(0.20, 0.24, 0.38)
		balance = Vector3(0.96, 1.08, 0.98)


## A ShaderMaterial of the figure shader for a glTF surface. `src` is the importer's StandardMaterial3D
## (named "cloth", "skin" or "eyes" by the exporter); the part is taken from its name.
static func material(src: StandardMaterial3D, cloth_tint = null) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/figure.gdshader")
	var part := 0
	match src.resource_name:
		"skin":
			part = 1
		"eyes":
			part = 2
	m.set_shader_parameter("part", part)
	if src.albedo_texture != null:
		m.set_shader_parameter("has_tex", true)
		m.set_shader_parameter("tex", src.albedo_texture)
	var t := Color.WHITE
	if part == 0 and cloth_tint is Color:
		t = cloth_tint
	m.set_shader_parameter("tint", Vector3(t.r, t.g, t.b))
	m.set_shader_parameter("saturation", saturation)
	m.set_shader_parameter("brightness", brightness)
	m.set_shader_parameter("balance", balance)
	m.set_shader_parameter("irr_knee", irr_knee)
	m.set_shader_parameter("rim_color", Vector3(rim_color.r, rim_color.g, rim_color.b))
	m.set_shader_parameter("rim_strength", rim_strength)
	return m
