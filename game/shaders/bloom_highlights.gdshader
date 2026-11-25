// First pass of the post: the parts of the frame above the bloom threshold, as Blender's Glare
// node picks them (after the HueSat saturation step), drawn to the screen so the second pass can
// read them back with blurred mip levels. Values are in the unexposed units the post works in.
shader_type canvas_item;

uniform float prescale = 16.0;
uniform float exposure_gain = 1.0;   // 2^exposure_applied_ev
uniform float saturation = 1.0;
uniform float threshold = 1.0;

void fragment() {
	vec3 c = texture(TEXTURE, UV).rgb * prescale / exposure_gain;
	float v = max(c.r, max(c.g, c.b));
	c = v - saturation * (v - c);
	float m = max(c.r, max(c.g, c.b));
	COLOR = vec4(c * max(m - threshold, 0.0) / max(m, 1e-6), 1.0);
}
