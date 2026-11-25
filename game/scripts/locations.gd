## Where a location's scene.json lives. The start location (config.json -> start, the courtyard)
## keeps config.json -> data; any other location <name> is exported to
## locations/<name>/data/scene.json, with every path inside it relative to game/ like the courtyard's.
extends RefCounted

const DEFAULT_START := "courtyard"

## name -> data path, for checks that need a location without an export.
static var overrides := {}


## The first location: `--start=<name>` on the command line, else config.json -> start.
static func start(config: Dictionary) -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--start="):
			return arg.substr(8)
	return config.get("start", DEFAULT_START)


static func data_path(config: Dictionary, name: String) -> String:
	if overrides.has(name):
		return overrides[name]
	if name == config.get("start", DEFAULT_START):
		return config.get("data", "data/scene.json")
	return "locations/%s/data/scene.json" % name


static func exists(config: Dictionary, name: String) -> bool:
	return name != "" and FileAccess.file_exists("res://" + data_path(config, name))


## The name the lists show for a location: config.json -> location_names, else the id spelled out.
static func title(config: Dictionary, name: String) -> String:
	return config.get("location_names", {}).get(name, name.replace("_", " ").capitalize())
