// What a figure does to the floor it stands on: the shadow of its body from up to three lamps, and a
// small dark pool of ambient occlusion at the feet. The frame is a picture with no geometry, so this is
// a quad on the floor, depth-tested against the frame's depth: it draws only where the floor is the
// surface seen there, and multiplies the frame (blend_mul), so the texture of the flagstones stays.
//
// The body is a vertical capsule. For a lamp at L, the point at height h of the axis lands on the floor
// at L.xz + (F.xz - L.xz) * L.y / (L.y - h), so the capsule's shadow is the stripe from the feet to the
// projected head, as wide as the body and softer with distance (the lamp is a flame, not a point).
shader_type spatial;
render_mode unshaded, blend_mul, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 foot = vec3(0.0);           // world position of the feet
uniform float body_height = 1.6;
uniform float body_radius = 0.22;
uniform vec4 lamp_a = vec4(0.0);         // xyz position, w how much of the floor's light it gives (0 = none)
uniform vec4 lamp_b = vec4(0.0);
uniform vec4 lamp_c = vec4(0.0);
uniform vec3 shade = vec3(0.20, 0.24, 0.38);   // what the frame is multiplied by in full shadow
uniform float pool = 0.38;               // strength of the pool under the feet
uniform vec2 pool_size = vec2(0.30, 0.30);   // its half axes in metres: across, along the figure's facing
uniform float pool_yaw = 0.0;            // the figure's rotation about Y
uniform float strength = 1.5;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// 1 inside the shadow of the capsule from one lamp, 0 outside
float cast_shadow(vec4 lamp, vec2 g) {
	if (lamp.w <= 0.001 || body_height < 0.3) {
		return 0.0;
	}
	vec2 f = foot.xz;
	vec2 away = f - lamp.xz;
	float dist = length(away);
	float lh = lamp.y - foot.y;
	float k = lh > body_height + 0.25 ? lh / (lh - body_height) : 3.5;
	k = min(k, 3.5);
	vec2 top = lamp.xz + away * k;
	vec2 a = f;
	vec2 ab = top - a;
	float len2 = max(dot(ab, ab), 1e-4);
	float t = clamp(dot(g - a, ab) / len2, 0.0, 1.0);
	float d = length(g - (a + ab * t));
	// the stripe narrows toward the head, and its edge softens with the distance from the feet
	float r = body_radius * (1.0 - 0.35 * t);
	float soft = 0.05 + 0.22 * t * min(1.0, sqrt(len2) / 1.5);
	float inside = 1.0 - smoothstep(r - soft, r + soft, d);
	// the far end of a long shadow is thin and faint
	float fade = 1.0 - 0.55 * t;
	// the lamp lights the floor from the front only: nothing falls toward the lamp
	float side = smoothstep(-0.05, 0.1, dot(g - f, away) / max(dist, 0.05));
	return inside * fade * mix(0.5, 1.0, side) * lamp.w;
}

void fragment() {
	vec2 g = wpos.xz;
	float s = cast_shadow(lamp_a, g) + cast_shadow(lamp_b, g) + cast_shadow(lamp_c, g);
	// the pool is an ellipse in the figure's own frame (x across, z along)
	vec2 q = g - foot.xz;
	float c = cos(pool_yaw);
	float sn = sin(pool_yaw);
	vec2 local = vec2(c * q.x - sn * q.y, sn * q.x + c * q.y) / pool_size;
	float contact = pool * exp(-dot(local, local));
	float k = clamp(max(s, 0.0) * strength + contact, 0.0, 1.0);
	ALBEDO = mix(vec3(1.0), shade, k);
}
