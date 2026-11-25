// A person's cloth, leather, linen, hair, skin and eyes, lit by the scene's real-time lights and the
// flat ambient, and drawn into the same linear HDR frame that view.gd grades.
//
// What it does:
//   - cloth is matte: no specular, a soft wrap and a grazing sheen (the nap of wet wool); leather and hair
//     keep a small, broad highlight; skin wraps light around the terminator with a red shift and lets a
//     little light through thin parts (ears, nose), which is the cheap stand-in for subsurface scattering
//   - every light's irradiance is compressed above a knee, so a fire half a metre away cannot burn a sleeve
//     to white while the same fire at three metres stays physical
//   - the albedo's chroma is trimmed (FigureLook.saturation): the view transform's "Punchy" look and the
//     lift of the post push a dark orange-brown to red-magenta, and the set's own cloth is nearly grey
//   - a baked occlusion (UV2.x) darkens creases; UV2.y says which cloth it is (wool, leather, linen, hair)
//   - a cool rim from the sky on the upward-facing edges, so a figure in shade still parts from the wall
//
// Vertex colour COLOR holds the garment colour in sRGB (characters/build_human.py): Godot stores a vertex
// colour in 8 bits, and linear values would band in the dark wool.
shader_type spatial;
render_mode cull_disabled;

uniform int part = 0;                    // 0 garment (cloth, leather, linen, hair by UV2.y), 1 skin, 2 eye
uniform bool has_tex = false;
uniform sampler2D tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec3 tint = vec3(1.0);

uniform float saturation = 0.62;         // share of the albedo's chroma that is kept
uniform float brightness = 1.0;
uniform vec3 balance = vec3(1.0);        // white balance of the cloth's albedo against the scene's light cast
uniform float irr_knee = 5.0;            // irradiance above this is compressed (energy units of the lights)
uniform float ao_amount = 0.85;
uniform vec3 rim_color = vec3(0.30, 0.42, 0.75);
uniform float rim_strength = 0.30;
uniform float spec_gain = 1.0;
uniform vec3 bounce = vec3(0.0);         // light the lit floor throws up at the figure (lights.gd, every frame)
uniform vec3 fill = vec3(0.0);           // the room's indirect light at the figure, from every lamp (lights.gd)

// the part's own look, set in fragment() and read by light()
varying vec3 g_wrap;           // wrap of the diffuse light per colour channel
varying vec4 g_look;           // x translucency, y sheen, z roughness, w specular

vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

float hash31(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash31(i), hash31(i + vec3(1, 0, 0)), f.x),
			mix(hash31(i + vec3(0, 1, 0)), hash31(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash31(i + vec3(0, 0, 1)), hash31(i + vec3(1, 0, 1)), f.x),
			mix(hash31(i + vec3(0, 1, 1)), hash31(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

varying vec3 mpos;

void vertex() {
	mpos = VERTEX;
}

void fragment() {
	vec3 albedo;
	float occlusion = clamp(UV2.x, 0.0, 1.0);
	float kind = UV2.y;
	float leather = smoothstep(0.2, 0.3, kind) * (1.0 - smoothstep(0.45, 0.55, kind));
	float linen = smoothstep(0.55, 0.65, kind) * (1.0 - smoothstep(0.8, 0.9, kind));
	float hair = smoothstep(0.9, 0.95, kind);
	float alpha = 1.0;
	if (part == 0) {
		albedo = srgb_to_linear(clamp(COLOR.rgb, 0.0, 1.0));
		float wool = 1.0 - max(max(leather, linen), hair);
		// hair: strands run down the head; UV2.x is the distance to the ragged edge (1 at the edge)
		if (hair > 0.5) {
			float ang = atan(mpos.x, mpos.z) * 150.0;          // model space is y up: strands run along y
			float strands = vnoise(vec3(ang, mpos.y * 14.0, 0.0)) * 0.5 + vnoise(vec3(ang * 2.1, mpos.y * 45.0, 3.0)) * 0.5;
			albedo *= 0.78 + 0.5 * strands;
			float ragged = vnoise(vec3(ang * 1.7, mpos.y * 60.0, 7.0));
			alpha = step(occlusion, 0.35 + 0.65 * ragged);
			occlusion = 0.25;
		}
		g_wrap = vec3(0.10 * wool + 0.18 * linen + 0.12 * hair);
		g_look = vec4(0.12 * linen,
				0.55 * wool + 0.12 * leather + 0.35 * linen + 0.25 * hair,
				wool + 0.5 * leather + linen + 0.42 * hair,
				0.85 * leather + 0.6 * hair);
		// fine texture of the cloth at close range: a mottle that follows the surface
		float fibre = vnoise(mpos * 70.0);
		albedo *= 1.0 + (0.5 * wool + 0.3 * linen + 0.2 * leather) * 0.12 * (fibre - 0.5);
		float l = dot(albedo, vec3(0.2126, 0.7152, 0.0722));
		albedo = mix(vec3(l), albedo, saturation);
		albedo *= tint * balance * brightness * (1.0 - 0.18 * leather);
	} else {
		albedo = has_tex ? texture(tex, UV).rgb * tint : tint;
		if (part == 1) {
			g_wrap = vec3(0.62, 0.28, 0.14);
			g_look = vec4(0.28, 0.0, 0.55, 0.5);
			float l = dot(albedo, vec3(0.2126, 0.7152, 0.0722));
			albedo = mix(vec3(l), albedo, 0.9) * 0.88;
		} else {
			g_wrap = vec3(0.0);
			g_look = vec4(0.0, 0.0, 0.12, 1.0);
		}
	}
	ALBEDO = albedo;
	ALPHA = alpha;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;                      // the sky's reflection is left out: light() adds the lamps' highlight
	AO = 1.0 - occlusion * ao_amount;
	AO_LIGHT_AFFECT = 0.3;
	// a cool rim from the sky, strongest on edges that face up
	vec3 wn = (INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz;
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.5);
	float up = clamp(wn.y * 0.5 + 0.5, 0.0, 1.0);
	// the floor lit by the fire, seen from below and from the side: a Lambert bounce
	float down = clamp(0.5 - 0.5 * wn.y, 0.0, 1.0);
	EMISSION = albedo * (bounce * down + fill) * (1.0 - occlusion * ao_amount);
	EMISSION += rim_color * rim_strength * fres * (0.2 + 0.8 * up) * (1.0 - 0.7 * occlusion) * (part == 2 ? 0.0 : 1.0);
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	vec3 irr = LIGHT_COLOR * ATTENUATION / PI;
	float m = max(irr.r, max(irr.g, irr.b));
	irr /= 1.0 + m / irr_knee;
	vec3 diff = clamp((vec3(ndl) + g_wrap) / (1.0 + g_wrap), 0.0, 1.0);
	float vdn = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float sheen = pow(1.0 - vdn, 3.0) * clamp(ndl + 0.35, 0.0, 1.0) * g_look.y;
	// light through thin parts, red
	float back = clamp(-ndl, 0.0, 1.0) * g_look.x;
	vec3 trans = vec3(1.0, 0.35, 0.18) * back;
	DIFFUSE_LIGHT += irr * (diff + vec3(sheen) + trans);
	if (g_look.w > 0.0) {
		vec3 h = normalize(LIGHT + VIEW);
		float ndh = clamp(dot(NORMAL, h), 0.0, 1.0);
		float a = max(g_look.z * g_look.z, 0.03);
		float a2 = a * a;
		float dd = ndh * ndh * (a2 - 1.0) + 1.0;
		float d = a2 / (PI * dd * dd);
		float f = 0.04 + 0.96 * pow(1.0 - clamp(dot(LIGHT, h), 0.0, 1.0), 5.0);
		SPECULAR_LIGHT += irr * PI * d * f * 0.25 * clamp(ndl, 0.0, 1.0) * g_look.w * spec_gain;
	}
}
