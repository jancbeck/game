// Rain drops as GPU particles. Each drop is born at the top of the rain volume and lives on its
// own: it falls at its own terminal velocity (7 to 9 m/s), and its sideways speed follows the
// wind at its position with its own lag (0.15 to 0.6 s) and its own turbulence. The wind is a
// field, not a global value: gust bands travel downwind across the courtyard, so drops in a gust
// lean while drops ahead of it still fall straight.
//
// A drop lands where it reaches the frame's visible surface: its depth along the camera axis
// crosses the depth of the frame at its own pixel. There the same particle turns into its splash
// for SPLASH_S, then dies. Drops hidden behind walls never cross and die below the lower ward or
// at the end of their lifetime.
//
// To the draw shader (rain_draw.gdshader): column 3 of the transform is the position, column 1
// the drop's motion during one camera shutter. CUSTOM: x seed; y fall speed (> 0, a drop) or 0
// (a splash); z the drop's last depth difference, or for a splash floor(puddle * 100) + crown
// size in m; w the age of the drop or of the splash.
shader_type particles;
render_mode disable_velocity, disable_force;

// where drops are born: a parallelogram at height top_m (o + u * a + v * b)
uniform vec3 spawn_o;
uniform vec3 spawn_a;
uniform vec3 spawn_b;
uniform float fall_min = 7.0;
uniform float fall_max = 9.0;
uniform float shutter = 0.02;          // s of motion per streak
uniform float clock = 0.0;

// wind: mean along wind_dir, gust bands travelling downwind at gust_speed
uniform vec2 wind_dir = vec2(0.978, -0.208);
uniform float wind_mean = 1.0;         // m/s in a lull
uniform float wind_gust = 3.4;         // m/s added at a gust's peak
uniform float gust_speed = 7.0;        // m/s, how fast a gust band crosses the yard
uniform float gust_scale = 14.0;       // m, gust band size along the wind
uniform float turbulence = 0.7;        // m/s, each drop's own sideways jitter

// the frame: camera geometry and depth, for landing
uniform vec3 cam_origin;
uniform vec3 cam_x;
uniform vec3 cam_y;
uniform vec3 cam_fwd;
uniform float px_per_m = 73.142857;
uniform vec2 frame_size = vec2(2560.0, 1440.0);
uniform sampler2D depth_tex : filter_nearest, repeat_disable;
uniform sampler2D puddle_tex : filter_linear, repeat_disable;
uniform bool wide_on = false;
uniform vec4 wide_rect = vec4(-1280.0, -720.0, 5120.0, 2880.0);   // frame px
uniform sampler2D wide_depth : filter_nearest, repeat_disable;
uniform float wide_offset = 0.0;
uniform float floor_m = -3.5;
uniform float land_tolerance = 0.45;   // m along the camera axis
uniform float splash_share = 0.6;      // share of landings that splash
const float SPLASH_S = 0.22;

uint hash_u(uint x) {
	x ^= x >> 16u; x *= 0x7feb352du;
	x ^= x >> 15u; x *= 0x846ca68bu;
	x ^= x >> 16u;
	return x;
}

float rnd(inout uint s) {
	s = hash_u(s);
	return float(s) / 4294967295.0;
}

float hash31(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(hash31(i), hash31(i + vec3(1, 0, 0)), f.x), mix(hash31(i + vec3(0, 1, 0)), hash31(i + vec3(1, 1, 0)), f.x), f.y);
	float b = mix(mix(hash31(i + vec3(0, 0, 1)), hash31(i + vec3(1, 0, 1)), f.x), mix(hash31(i + vec3(0, 1, 1)), hash31(i + vec3(1, 1, 1)), f.x), f.y);
	return mix(a, b, f.z);
}

// gust strength 0..1 at a ground position: bands along the wind that travel downwind and
// change shape slowly
float gust_at(vec2 xz, float t) {
	float along = dot(xz, wind_dir) - gust_speed * t;
	float across = dot(xz, vec2(-wind_dir.y, wind_dir.x));
	vec3 q = vec3(along / gust_scale, across / (gust_scale * 2.5), t * 0.05);
	float g = 0.65 * vnoise(q) + 0.35 * vnoise(q * 2.1 + 7.3);
	return smoothstep(0.42, 0.78, g);
}

vec2 wind_at(vec3 p, float t) {
	return wind_dir * (wind_mean + wind_gust * gust_at(p.xz, t));
}

// (depth of the frame surface at the drop's pixel, depth of the drop), both along the camera
// axis from cam_origin; x = 1e9 where no frame covers the pixel
vec2 depths(vec3 p) {
	vec3 rel = p - cam_origin;
	vec2 px = vec2(dot(rel, cam_x) * px_per_m + frame_size.x * 0.5, frame_size.y * 0.5 - dot(rel, cam_y) * px_per_m);
	float d = dot(rel, cam_fwd);
	if (px.x >= 0.0 && px.y >= 0.0 && px.x < frame_size.x && px.y < frame_size.y) {
		return vec2(textureLod(depth_tex, px / frame_size, 0.0).r, d);
	}
	if (wide_on) {
		vec2 uv = (px - wide_rect.xy) / wide_rect.zw;
		if (all(greaterThanEqual(uv, vec2(0.0))) && all(lessThan(uv, vec2(1.0)))) {
			return vec2(textureLod(wide_depth, uv, 0.0).r + wide_offset, d);
		}
	}
	return vec2(1e9, d);
}

float puddle_at(vec3 p) {
	vec3 rel = p - cam_origin;
	vec2 px = vec2(dot(rel, cam_x) * px_per_m + frame_size.x * 0.5, frame_size.y * 0.5 - dot(rel, cam_y) * px_per_m);
	return textureLod(puddle_tex, px / frame_size, 0.0).r;
}

void start() {
	uint s = hash_u(NUMBER * 747796405u + RANDOM_SEED);
	float seed = rnd(s);
	vec3 p = spawn_o + spawn_a * rnd(s) + spawn_b * rnd(s);
	p.y += rnd(s) * 0.5;
	float fall = mix(fall_min, fall_max, rnd(s));
	vec2 w = wind_at(p, clock);
	VELOCITY = vec3(w.x, -fall, w.y);
	vec2 dd = depths(p);
	CUSTOM = vec4(seed, fall, dd.y - dd.x, 0.0);
	TRANSFORM = mat4(vec4(1.0, 0.0, 0.0, 0.0), vec4(VELOCITY * shutter, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(p, 1.0));
}

void process() {
	if (CUSTOM.y <= 0.0) {
		// a splash: stays where it landed, then dies
		CUSTOM.w += DELTA;
		if (CUSTOM.w > SPLASH_S) {
			ACTIVE = false;
		}
	} else {
	float seed = CUSTOM.x;
	float fall = CUSTOM.y;
	float tau = mix(0.15, 0.6, fract(seed * 13.7));
	float t = clock;
	vec3 p = TRANSFORM[3].xyz;
	// the drop's own turbulence: slow noise in its own phase, stronger in gusts
	float g = gust_at(p.xz, t);
	vec2 turb = (vec2(vnoise(vec3(t * 1.3, seed * 91.0, 0.0)), vnoise(vec3(t * 1.1, seed * 57.0, 5.0))) - 0.5) * 2.0 * turbulence * (0.5 + g);
	vec2 target = wind_at(p, t) + turb;
	float k = 1.0 - exp(-DELTA / tau);
	VELOCITY.xz += (target - VELOCITY.xz) * k;
	VELOCITY.y = -fall;
	p += VELOCITY * DELTA;
	CUSTOM.w += DELTA;

	vec2 dd = depths(p);
	float diff = dd.y - dd.x;       // > 0: the drop is behind the frame surface at its pixel
	bool landed = CUSTOM.z < 0.0 && diff >= 0.0 && diff < land_tolerance && dd.x < 1e8;
	CUSTOM.z = diff;
	if (landed) {
		if (fract(seed * 7.31) < splash_share) {
			vec3 hit = p - cam_fwd * diff;   // back along the view ray onto the surface
			float pud = puddle_at(hit);
			float size = mix(0.09, 0.15, fract(seed * 3.7)) * (1.0 + 0.5 * pud);
			CUSTOM = vec4(seed, 0.0, floor(pud * 99.0) + size, 0.0);
			VELOCITY = vec3(0.0);
			TRANSFORM = mat4(vec4(1.0, 0.0, 0.0, 0.0), vec4(0.0, 1.0, 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(hit, 1.0));
		} else {
			ACTIVE = false;
		}
	} else {
		if (p.y < floor_m) {
			ACTIVE = false;
		}
		TRANSFORM = mat4(vec4(1.0, 0.0, 0.0, 0.0), vec4(VELOCITY * shutter, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(p, 1.0));
	}
	}
}
