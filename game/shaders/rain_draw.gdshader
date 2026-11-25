// One rain particle (rain_process.gdshader), drawn as what it is now:
//   a drop: a streak stretched along its motion during one camera shutter (transform column 1)
//           as the camera sees it, a few millimetres wide;
//   a splash: a small crown of droplets thrown up and out on ballistic arcs and a ring spreading
//           on the surface; in a puddle the crown is larger and the ring stays longer.
// Both take their light from what lies behind them, so drops near the fire glint orange.
// In the wide view (zoom 0.5) a streak a few pixels long reads as a snow dot, so streaks are
// stretched along their fall and wind to a minimum length on screen and fainter, as thin streaks.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform float intensity = 1.0;
uniform float width_m = 0.012;
uniform vec3 tint = vec3(0.55, 0.62, 0.75);
uniform sampler2D screen : hint_screen_texture, filter_linear_mipmap;
// open fires: xyz position, w = flicker intensity; drops near them catch their light
uniform vec4 fires[4];
uniform int fire_count = 0;
uniform vec3 fire_color = vec3(1.0, 0.42, 0.12);
uniform float fire_glint = 3.0;
uniform float fire_reach = 2.2;      // m
uniform float min_px = 1.2;          // streaks never get thinner than this on screen
uniform float wide = 0.0;            // 0 at zoom 1 and closer, 1 at zoom 0.5
uniform float wide_len_px = 24.0;    // minimum streak length on screen at wide = 1 (px of the 2560 canvas)
uniform float wide_alpha = 0.5;      // streak brightness at wide = 1
uniform float min_splash_px = 6.0;
uniform float px_per_m = 73.0;       // screen px per metre at the current zoom
uniform float splash_s = 0.22;

varying vec2 corner;
varying float fade;
varying vec3 glint;
varying float splash;     // 1 for a splash
varying float age;        // splash age 0..1
varying float seed;
varying float puddle;

void vertex() {
	vec3 p = MODEL_MATRIX[3].xyz;
	seed = INSTANCE_CUSTOM.x;
	splash = INSTANCE_CUSTOM.y <= 0.0 ? 1.0 : 0.0;
	vec3 centre = (VIEW_MATRIX * vec4(p, 1.0)).xyz;
	vec2 uv = VERTEX.xy + 0.5;
	vec3 q;
	glint = vec3(0.0);
	if (splash > 0.5) {
		puddle = floor(INSTANCE_CUSTOM.z) / 99.0;
		float size = fract(INSTANCE_CUSTOM.z);
		age = clamp(INSTANCE_CUSTOM.w / splash_s, 0.0, 1.0);
		float s = max(size, min_splash_px / px_per_m);
		// a little toward the camera, so the surface it sits on does not cut it
		centre.z += 0.15;
		vec2 l = uv * 2.0 - 1.0;
		q = centre + vec3(l.x * s, l.y * s + s * 0.35, 0.0);
		corner = vec2(l.x, l.y + 0.35);
		fade = 1.0;
	} else {
		puddle = 0.0;
		age = 0.0;
		vec3 v = (VIEW_MATRIX * vec4(MODEL_MATRIX[1].xyz, 0.0)).xyz;
		vec2 axis = normalize(v.xy + vec2(0.0, -1e-5));
		vec2 side = vec2(-axis.y, axis.x);
		float vary = 0.8 + 0.4 * fract(seed * 5.3);
		float len = max(length(v.xy) * vary, wide * wide_len_px * vary / px_per_m);
		float w = max(width_m, min_px / px_per_m);
		// the streak trails behind the drop
		q = centre + vec3(axis * (uv.y - 1.0) * len + side * (uv.x * 2.0 - 1.0) * w, 0.0);
		corner = vec2(uv.x * 2.0 - 1.0, uv.y);
		for (int i = 0; i < fire_count; i++) {
			float d = length(p - fires[i].xyz) / fire_reach;
			glint += fire_color * fires[i].w * fire_glint / (1.0 + d * d * d * d);
		}
		// drops vary in brightness and fade in over their first moments; streaks widened to
		// min_px at a wide zoom are dimmer per pixel
		fade = (0.35 + 0.65 * fract(seed * 11.9)) * smoothstep(0.0, 0.12, INSTANCE_CUSTOM.w) * min(1.0, width_m / w * 1.6) * mix(1.0, wide_alpha, wide);
	}
	POSITION = PROJECTION_MATRIX * vec4(q, 1.0);
}

float hash(float n) {
	return fract(sin(n) * 43758.5453);
}

float crown(vec2 local) {
	float u = age;
	float a = 0.0;
	// droplets: out along random directions, up and back down
	for (int i = 0; i < 6; i++) {
		float fi = float(i);
		float ang = hash(seed * 17.0 + fi * 3.1) * 6.2832;
		float out_r = (0.35 + 0.45 * hash(seed * 7.0 + fi)) * u;
		float up = (0.6 + 0.5 * hash(seed * 11.0 + fi * 1.7)) * 4.0 * u * (1.0 - u) * (1.0 + 0.6 * puddle);
		// the ground seen at 38 degrees: depth squashes to 0.62
		vec2 pos = vec2(cos(ang) * out_r, sin(ang) * out_r * 0.62 + up * 0.55);
		float r = 0.11 + 0.03 * puddle;
		a += smoothstep(r, r * 0.3, length(local - pos)) * (1.0 - u);
	}
	float ru = clamp(u / mix(0.6, 1.0, puddle), 0.0, 1.0);
	vec2 e = vec2(local.x, local.y / 0.62);
	a += smoothstep(0.08, 0.0, abs(length(e) - 0.2 - 0.6 * ru)) * (1.0 - ru) * 0.45;
	return a;
}

void fragment() {
	vec3 behind = textureLod(screen, SCREEN_UV, 3.0).rgb;
	if (splash > 0.5) {
		ALBEDO = tint * 0.1 + behind * 1.8;
		ALPHA = clamp(crown(corner) * intensity * 1.1 * mix(1.0, wide_alpha + 0.15, wide), 0.0, 1.0);
	} else {
		float across = 1.0 - abs(corner.x);
		float along = sin(3.14159 * corner.y);
		ALBEDO = tint * 0.09 + behind * 1.5 + glint;
		ALPHA = clamp(across * across * along * fade * intensity * 0.85, 0.0, 1.0);
	}
}
