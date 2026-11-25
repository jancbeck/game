// The pre-rendered frame as a full-screen quad, composited in linear light:
//   colour = base + sum(group_i * intensity_i)
// from up to three sources of the same picture (compositor.gd): the main frame, the wide view
// around it (zoom < 1) and a hotspot's 2x tile (zoom 2). view_rect maps the screen to the main
// frame's uv; every other source is placed by its own rect in that uv.
// On top: rain on the ground (ripple rings that bend the reflections in puddles, small splashes on
// wet upward faces) and the hover outline from the ids masks. It writes the frame's depth, so
// real-time objects behind a wall, a post or the cart fail the depth test where the frame is closer.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_always, shadows_disabled, fog_disabled;

#define MAX_GROUPS 16
#define MAX_IDS 32

uniform vec4 view_rect = vec4(0.0, 0.0, 1.0, 1.0);   // screen -> main frame uv
uniform vec2 frame_size = vec2(2560.0, 1440.0);
uniform float lod = 0.0;           // log2(main-frame texels per screen pixel)

// main frame
uniform sampler2D base_tex : filter_linear_mipmap, repeat_disable;
uniform sampler2DArray groups_tex : filter_linear_mipmap, repeat_disable;
uniform int group_count = 0;
uniform float intensity[MAX_GROUPS];
uniform sampler2D depth_m : filter_nearest, repeat_disable;   // metres along the camera axis
uniform sampler2D puddle_tex : filter_linear, repeat_disable;
uniform sampler2D wet_tex : filter_linear, repeat_disable;
uniform sampler2D ids_tex : filter_nearest, repeat_disable;

// wide view
uniform bool wide_on = false;
uniform vec4 wide_rect = vec4(-0.5, -0.5, 2.0, 2.0);
uniform float wide_lod_bias = -1.0;   // log2(wide texels per main-frame texel)
uniform sampler2D wide_base : filter_linear_mipmap, repeat_disable;
uniform sampler2DArray wide_groups : filter_linear_mipmap, repeat_disable;
uniform int wide_count = 0;
uniform float wide_intensity[MAX_GROUPS];
uniform sampler2D wide_depth : filter_nearest, repeat_disable;
uniform sampler2D wide_ids : filter_nearest, repeat_disable;
uniform float wide_offset = 0.0;

// zoom tile
uniform float tile_mix = 0.0;
uniform vec4 tile_rect = vec4(0.0, 0.0, 0.5, 0.5);
uniform float tile_lod_bias = 1.0;
uniform sampler2D tile_base : filter_linear_mipmap, repeat_disable;
uniform sampler2DArray tile_groups : filter_linear_mipmap, repeat_disable;
uniform int tile_count = 0;
uniform float tile_intensity[MAX_GROUPS];
uniform sampler2D tile_depth : filter_nearest, repeat_disable;
uniform sampler2D tile_ids : filter_nearest, repeat_disable;
uniform sampler2D tile_puddle : filter_linear, repeat_disable;
uniform sampler2D tile_wet : filter_linear, repeat_disable;

uniform float time = 0.0;
uniform float rain = 1.0;          // 0 turns ripples and splashes off
uniform vec3 sky_glint = vec3(0.035, 0.05, 0.08);

// hover outline: strength per hotspot number; width in canvas pixels
uniform float highlight[MAX_IDS];
uniform bool any_highlight = false;
uniform vec2 px_uv = vec2(0.00039, 0.00069);
uniform float outline_px = 9.0;
uniform vec3 outline_color = vec3(1.0, 0.86, 0.62);
uniform float outline_gain = 0.28;

void vertex() {
	// QuadMesh of size 2: VERTEX.xy is already in clip space
	POSITION = vec4(VERTEX.xy, 0.5, 1.0);
}

vec2 local_uv(vec2 fuv, vec4 r) {
	return (fuv - r.xy) / r.zw;
}

// 1 inside the unit square, fading to 0 over `px` texels at the edge
float inside(vec2 uv, vec2 size_px, float px) {
	vec2 d = min(uv, 1.0 - uv) * size_px;
	return clamp(min(d.x, d.y) / px, 0.0, 1.0);
}

float w_main(vec2 fuv) {
	if (wide_on) return inside(fuv, frame_size, 3.0);
	return step(0.0, min(min(fuv.x, 1.0 - fuv.x), min(fuv.y, 1.0 - fuv.y)));
}

float w_tile(vec2 fuv) {
	if (tile_mix <= 0.0) return 0.0;
	return tile_mix * inside(local_uv(fuv, tile_rect), tile_rect.zw * frame_size, 4.0);
}

vec3 composite(vec2 fuv) {
	// explicit LOD: the puddle branch moves uv, and implicit derivatives break across branches
	float wm = w_main(fuv);
	float wt = w_tile(fuv);
	vec3 c = vec3(0.0);
	if (wm < 1.0 && wide_on) {
		vec2 uv = local_uv(fuv, wide_rect);
		float l = max(lod + wide_lod_bias, 0.0);
		vec3 w = textureLod(wide_base, uv, l).rgb;
		for (int i = 0; i < wide_count; i++) {
			w += textureLod(wide_groups, vec3(uv, float(i)), l).rgb * wide_intensity[i];
		}
		c = w * (1.0 - wm);
	}
	if (wm > 0.0 && wt < 1.0) {
		float l = max(lod, 0.0);
		vec3 m = textureLod(base_tex, fuv, l).rgb;
		for (int i = 0; i < group_count; i++) {
			m += textureLod(groups_tex, vec3(fuv, float(i)), l).rgb * intensity[i];
		}
		c += m * wm * (1.0 - wt);
	}
	if (wt > 0.0) {
		vec2 uv = local_uv(fuv, tile_rect);
		float l = max(lod + tile_lod_bias, 0.0);
		vec3 t = textureLod(tile_base, uv, l).rgb;
		for (int i = 0; i < tile_count; i++) {
			t += textureLod(tile_groups, vec3(uv, float(i)), l).rgb * tile_intensity[i];
		}
		c += t * wt;
	}
	return c;
}

// depth along the main camera's axis, from the source that dominates here
float depth_at(vec2 fuv) {
	if (w_tile(fuv) > 0.5) return texture(tile_depth, local_uv(fuv, tile_rect)).r;
	if (w_main(fuv) > 0.5) return texture(depth_m, fuv).r;
	if (wide_on) return texture(wide_depth, local_uv(fuv, wide_rect)).r + wide_offset;
	return 190.0;
}

float mask(vec2 fuv, bool wet) {
	if (w_tile(fuv) > 0.5) {
		vec2 uv = local_uv(fuv, tile_rect);
		return wet ? texture(tile_wet, uv).r : texture(tile_puddle, uv).r;
	}
	if (w_main(fuv) > 0.5) return wet ? texture(wet_tex, fuv).r : texture(puddle_tex, fuv).r;
	return 0.0;
}

int id_at(vec2 fuv) {
	float v = 0.0;
	if (w_tile(fuv) > 0.5) v = textureLod(tile_ids, local_uv(fuv, tile_rect), 0.0).r;
	else if (w_main(fuv) > 0.5) v = textureLod(ids_tex, fuv, 0.0).r;
	else if (wide_on) v = textureLod(wide_ids, local_uv(fuv, wide_rect), 0.0).r;
	return clamp(int(round(v * 255.0)), 0, MAX_IDS - 1);
}

vec3 hash3(vec2 p) {
	vec3 q = vec3(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)), dot(p, vec2(419.2, 371.9)));
	return fract(sin(q) * 43758.5453);
}

// Rings spreading from drops that land at random in cells of `cell` metres.
// Returns (slope x, slope z, ring brightness).
vec3 ripples(vec2 xz, float cell, float period, float seed) {
	vec2 base = floor(xz / cell);
	vec3 acc = vec3(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = base + vec2(float(i), float(j));
			vec3 h = hash3(c + seed);
			float age = fract(time / period + h.z) * period;
			vec2 centre = (c + 0.15 + 0.7 * h.xy) * cell;
			vec2 d = xz - centre;
			float r = length(d);
			float front = age * 0.3;
			float fade = 1.0 - age / period;
			float x = (r - front) / 0.03;
			float wave = sin(x * 2.4) * exp(-x * x) * fade * fade;
			acc.xy += (d / max(r, 1e-4)) * wave;
			acc.z += max(wave, 0.0);
		}
	}
	return acc;
}

// Short crowns of spray where a drop hits wet stone or wood.
float splashes(vec2 xz, float cell, float seed) {
	vec2 base = floor(xz / cell);
	float s = 0.0;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = base + vec2(float(i), float(j));
			vec3 h = hash3(c + seed);
			float period = 0.35 + 0.5 * h.y;
			float cycle = floor(time / period + h.z);
			float age = (time / period + h.z - cycle) * period;
			float life = 0.09;
			if (age > life) continue;
			// a new spot in the cell every cycle
			vec2 centre = (c + 0.1 + 0.8 * hash3(c + seed + cycle * 0.731).xy) * cell;
			float r = length(xz - centre);
			float u = age / life;
			float ring = smoothstep(0.012, 0.0, abs(r - 0.012 - 0.03 * u));
			s += ring * (1.0 - u);
		}
	}
	return s;
}

// Soft glow around the highlighted objects, outside their silhouette, and a faint rim inside.
float outline(vec2 fuv) {
	float self_h = highlight[id_at(fuv)];
	float outer = 0.0;
	float wsum = 0.0;
	float edge = 0.0;
	for (int k = 0; k < 16; k++) {
		float a = float(k) * 0.392699 + 0.2;
		vec2 dir = vec2(cos(a), sin(a));
		for (int r = 1; r <= 3; r++) {
			float rad = outline_px * float(r) / 3.0;
			float w = 1.0 / float(r);
			float h = highlight[id_at(fuv + dir * rad * px_uv)];
			outer += h * w;
			wsum += w;
			if (r == 1) edge += step(0.001, abs(h - self_h));
		}
	}
	outer /= wsum;
	float glow = outer * (1.0 - step(0.001, self_h)) * 1.8;
	float rim = self_h * (0.12 + 0.8 * edge / 16.0);
	return clamp(glow + rim, 0.0, 1.5);
}

void fragment() {
	vec2 fuv = view_rect.xy + SCREEN_UV * view_rect.zw;
	float d = depth_at(fuv);
	vec4 v = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, 0.0, 1.0);
	vec3 world = (INV_VIEW_MATRIX * vec4(v.xy / v.w, -d, 1.0)).xyz;
	vec3 col;
	float puddle = rain > 0.0 ? mask(fuv, false) : 0.0;
	if (puddle > 0.01) {
		vec3 r = ripples(world.xz, 0.42, 0.95, 0.0) + ripples(world.xz + 0.2, 0.3, 0.7, 17.0);
		// the slope bends what the puddle reflects; the camera looks down at 38 degrees
		vec2 bend = vec2(r.x, -r.y * 0.62) * 0.0016 * puddle;
		col = composite(fuv + bend);
		col += r.z * puddle * (sky_glint + 0.35 * col);
		col *= 1.0 - 0.08 * puddle * clamp(r.z, 0.0, 1.0);
	} else {
		col = composite(fuv);
	}
	if (rain > 0.0) {
		vec3 n = normalize(cross(dFdy(world), dFdx(world)));
		float up = smoothstep(0.6, 0.9, abs(n.y));
		float wet = mask(fuv, true) * up;
		if (wet > 0.05) {
			// spray catches the light around it; on dark surfaces it stays faint
			float s = splashes(world.xz, 0.18, 3.0);
			col += s * wet * (vec3(0.012, 0.015, 0.02) + 0.6 * col);
		}
	}
	if (any_highlight) {
		float o = outline(fuv);
		col = col * (1.0 + 0.8 * o) + outline_color * outline_gain * o;
	}
	ALBEDO = col;
	// orthographic: view-space depth does not depend on x and y
	vec4 clip = PROJECTION_MATRIX * vec4(0.0, 0.0, -d, 1.0);
	DEPTH = clip.z / clip.w;
}
