"""Falling rain streaks and splash droplets: clear water, mostly see-through.

A streak is a motion-blurred drop, so it covers a pixel only for part of the exposure. It is
drawn as a faint, partly transparent strand:

- Alpha keeps it thin and faint against the dark walls. `build_rain` in build_scene.py scales
  alpha and emission per depth layer, so near layers read a little stronger than far ones.
- The body is a mid-grey water tint lit by the scene, and the specular term is that of water
  (IOR 1.33, low roughness). Away from a light the streak shows only a little sky; next to a fire,
  lantern or window it picks up the warm light, as real rain does at dusk.
- A very low emission keeps the far streaks from vanishing completely in the shadowed parts of
  the courtyard.
"""

BODY = (0.30, 0.33, 0.37)  # diffuse tint of the water strand
GLOW = (0.55, 0.62, 0.75)  # cool sky light scattered in the drop
GLOW_STRENGTH = 0.03  # emission before the layer factor
ALPHA = 0.35  # opacity before the layer factor


def build(mat, nt, bsdf):
    bsdf.inputs["Base Color"].default_value = (*BODY, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.12
    bsdf.inputs["IOR"].default_value = 1.333
    bsdf.inputs["Specular IOR Level"].default_value = 1.0
    bsdf.inputs["Emission Color"].default_value = (*GLOW, 1.0)
    bsdf.inputs["Emission Strength"].default_value = GLOW_STRENGTH
    bsdf.inputs["Alpha"].default_value = ALPHA
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "use_transparent_shadow"):
        mat.use_transparent_shadow = True
