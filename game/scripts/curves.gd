## Light curves and noise, ported from scene/anim.py with the same hashes and seeds, so a source
## flickers in the game exactly as in the videos: fire(t, seed) here equals
## anim.fire_intensity(t, seed) there.
##
## A light group's intensity is level^1.3, the factor anim.py puts on a source's light energy.
## A flipbook follows its group's intensity directly.
extends RefCounted

const MASK := 0xFFFFFFFF


static func hash_i(i: int, seed: int) -> float:
	var h := (i * 374761393 + seed * 668265263 + 0x9E3779B9) & MASK
	h = ((h ^ (h >> 13)) * 1274126177) & MASK
	h ^= h >> 16
	return h / 2147483647.5 - 1.0


static func noise(x: float, seed: int = 0) -> float:
	var i := floori(x)
	var f := x - i
	var u := f * f * f * (f * (f * 6.0 - 15.0) + 10.0)
	var a := hash_i(i, seed)
	var b := hash_i(i + 1, seed)
	return a + (b - a) * u


static func fbm(x: float, seed: int = 0, octaves: int = 3, lacunarity: float = 2.13, gain: float = 0.5) -> float:
	var total := 0.0
	var amp := 1.0
	var norm := 0.0
	for o in octaves:
		total += amp * noise(x * pow(lacunarity, o) + 17.3 * o, seed + 101 * o)
		norm += amp
		amp *= gain
	return total / norm


static func seed_of(text: String) -> int:
	var h := 2166136261
	for c in text.to_utf8_buffer():
		h = ((h ^ c) * 16777619) & MASK
	return h & 0xFFFFFF


static func fire(t: float, seed: int) -> float:
	var v := 1.0 + 0.17 * fbm(t * 2.3, seed, 3) + 0.09 * noise(t * 0.37, seed + 7)
	var dip := maxf(0.0, noise(t * 0.9, seed + 13) - 0.55) * 0.55
	return maxf(0.5, v - dip)


static func interior(t: float, seed: int) -> float:
	return 1.0 + 0.11 * fbm(t * 1.5, seed, 3) + 0.06 * noise(t * 0.29, seed + 5)


static func lamp(t: float, seed: int) -> float:
	var gutter := maxf(0.0, noise(t * 0.7, seed + 3) - 0.7) * 0.6
	return 1.0 + 0.05 * fbm(t * 2.0, seed, 3) - gutter


static func banked(t: float, seed: int) -> float:
	return 1.0 + 0.22 * fbm(t * 0.22, seed, 2) + 0.03 * noise(t * 1.1, seed + 9)


static func level(curve: String, t: float, seed: int) -> float:
	match curve:
		"fire":
			return fire(t, seed)
		"interior":
			return interior(t, seed)
		"lamp":
			return lamp(t, seed)
		"banked":
			return banked(t, seed)
	return 1.0


## Factor on the group's light layer and on its real-time lights (anim.py: energy * level^1.3).
static func intensity(curve: String, t: float, seed: int) -> float:
	return pow(level(curve, t, seed), 1.3)


## Wind strength 0..1: long lulls, gusts of a few seconds.
static func gust(t: float, seed: int = 0) -> float:
	var g := 0.45 + 0.65 * fbm(t * 0.17, seed + 401, 3) + 0.2 * noise(t * 0.6, seed + 409)
	return pow(clampf(g, 0.0, 1.0), 1.5)
