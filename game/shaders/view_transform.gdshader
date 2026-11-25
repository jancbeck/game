// Linear HDR world -> display. First the compositor post of the main still (build_scene.setup_post),
// in Blender's order and in the units it ran in (before the view exposure):
//   HueSat saturation -> Glare bloom -> ColorBalance lift/gamma/gain -> vignette
// then Blender's view transform and look from a baked 3D LUT (scene/bake_view_lut.py).
// The LUT axes sample log2(x / mid_grey) evenly from log_min to log_max stops.
// It runs in an HDR 2D SubViewport (the bloom reads HDR highlights from the screen mips) and
// writes display values, which the window shows as they are.
shader_type canvas_item;

#define OCTAVES 9

uniform sampler3D lut : filter_linear;
uniform sampler2D screen : hint_screen_texture, filter_linear_mipmap;
uniform bool use_lut = true;
uniform float lut_size = 65.0;
uniform float log_min = -12.5;
uniform float log_max = 5.0;
uniform float mid_grey = 0.18;
uniform float prescale = 16.0;

uniform bool post = true;
uniform float exposure_gain = 1.0;          // 2^exposure_applied_ev
uniform float saturation = 1.0;
uniform float bloom_weight[OCTAVES];        // per octave, sigma 1, 2, 4 ... 256 frame px
uniform float view_scale = 1.0;             // viewport px per frame px
uniform vec3 lift = vec3(1.0);
uniform vec3 gamma = vec3(1.0);
uniform vec3 gain = vec3(1.0);
uniform float vignette = 0.0;
uniform vec2 frame_size = vec2(2560.0, 1440.0);
uniform vec2 vignette_axes = vec2(0.95, 0.9);   // ellipse size, both relative to the frame width
uniform float vignette_sigma = 100.0;            // Gaussian sigma of the mask blur, frame px

vec3 linear_to_srgb(vec3 c) {
	c = clamp(c, 0.0, 1.0);
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

// Gaussian of the given sigma (viewport px) over the highlights, from a blurred mip level and a
// 3 x 3 tent of taps around it.
vec3 blur_at(vec2 uv, vec2 px, float sigma) {
	float lod = max(0.0, log2(sigma) - 1.0);
	float s = 1.35 * sigma;
	vec3 acc = vec3(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			float w = (i == 0 ? 0.5 : 0.25) * (j == 0 ? 0.5 : 0.25);
			acc += w * textureLod(screen, uv + vec2(float(i), float(j)) * s * px, lod).rgb;
		}
	}
	return acc;
}

float erf_approx(float x) {
	// Abramowitz and Stegun 7.1.26
	float t = 1.0 / (1.0 + 0.3275911 * abs(x));
	float y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * exp(-x * x);
	return sign(x) * y;
}

// Blender's ellipse mask (sizes relative to the frame width), blurred: the distance to the
// ellipse edge through a Gaussian edge profile.
float vignette_mask(vec2 uv) {
	vec2 p = (uv - 0.5) * frame_size;
	vec2 ab = vignette_axes * frame_size.x * 0.5;
	float f = dot(p / ab, p / ab) - 1.0;
	float g = length(2.0 * p / (ab * ab));
	float d = -f / max(g, 1e-6);
	return 0.5 * (1.0 + erf_approx(d / (vignette_sigma * 1.41421356)));
}

void fragment() {
	vec3 c = texture(TEXTURE, UV).rgb * prescale;
	if (post) {
		vec3 u = c / exposure_gain;
		float v = max(u.r, max(u.g, u.b));
		u = v - saturation * (v - u);
		vec3 bloom = vec3(0.0);
		for (int k = 0; k < OCTAVES; k++) {
			if (bloom_weight[k] > 0.0) {
				bloom += bloom_weight[k] * blur_at(SCREEN_UV, SCREEN_PIXEL_SIZE, exp2(float(k)) * view_scale);
			}
		}
		u += bloom;
		// Blender 5 ColorBalance, lift/gamma/gain, on linear values
		u = pow(max(((u - 1.0) * (2.0 - lift) + 1.0) * gain, 0.0), 1.0 / gamma);
		u *= 1.0 - vignette + vignette * vignette_mask(UV);
		c = u * exposure_gain;
	}
	vec3 display;
	if (use_lut) {
		vec3 s = (log2(max(c, vec3(1e-12)) / mid_grey) - log_min) / (log_max - log_min);
		s = clamp(s, 0.0, 1.0);
		vec3 uvw = (s * (lut_size - 1.0) + 0.5) / lut_size;
		display = texture(lut, uvw).rgb;
	} else {
		display = linear_to_srgb(c);
	}
	COLOR = vec4(display, 1.0);
}
