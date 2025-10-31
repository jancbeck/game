extends Node
class_name CharacterStats

## Character statistics system inspired by Disco Elysium
## Attributes affect skill checks and dialogue options

signal stat_changed(stat_name: String, new_value: int)
signal skill_check_performed(skill_name: String, result: bool, roll: int, target: int)

# Physical attributes
var intellect: int = 2
var psyche: int = 2
var physique: int = 2
var motorics: int = 2

# Skills derived from attributes (Disco Elysium inspired)
var logic: int = 2
var rhetoric: int = 2
var empathy: int = 2
var authority: int = 2
var perception: int = 2
var endurance: int = 2
var pain_threshold: int = 2
var shivers: int = 2

# Character info
var character_name: String = "Nameless Hero"
var health: int = 100
var morale: int = 100

func _ready():
	update_skills_from_attributes()

func update_skills_from_attributes():
	"""Update skill values based on primary attributes"""
	logic = intellect + 1
	rhetoric = intellect + psyche
	empathy = psyche + 1
	authority = psyche + physique
	perception = motorics + intellect
	endurance = physique + 1
	pain_threshold = physique + 1
	shivers = psyche + motorics

func perform_skill_check(skill_name: String, difficulty: int) -> Dictionary:
	"""
	Perform a skill check similar to Disco Elysium
	Returns a dictionary with result, roll, and success bool
	"""
	var skill_value = get_skill_value(skill_name)
	var roll = randi() % 6 + randi() % 6 + 2  # 2d6 roll (2-12)
	var total = skill_value + roll
	var success = total >= difficulty
	
	var result = {
		"skill": skill_name,
		"skill_value": skill_value,
		"roll": roll,
		"total": total,
		"difficulty": difficulty,
		"success": success,
		"margin": total - difficulty
	}
	
	skill_check_performed.emit(skill_name, success, roll, difficulty)
	return result

func get_skill_value(skill_name: String) -> int:
	"""Get the current value of a skill"""
	match skill_name.to_lower():
		"logic": return logic
		"rhetoric": return rhetoric
		"empathy": return empathy
		"authority": return authority
		"perception": return perception
		"endurance": return endurance
		"pain_threshold": return pain_threshold
		"shivers": return shivers
		"intellect": return intellect
		"psyche": return psyche
		"physique": return physique
		"motorics": return motorics
		_: return 1

func modify_attribute(attribute: String, amount: int):
	"""Modify a primary attribute and update dependent skills"""
	match attribute.to_lower():
		"intellect":
			intellect = max(1, intellect + amount)
			stat_changed.emit("intellect", intellect)
		"psyche":
			psyche = max(1, psyche + amount)
			stat_changed.emit("psyche", psyche)
		"physique":
			physique = max(1, physique + amount)
			stat_changed.emit("physique", physique)
		"motorics":
			motorics = max(1, motorics + amount)
			stat_changed.emit("motorics", motorics)
	
	update_skills_from_attributes()

func modify_health(amount: int):
	"""Modify health value"""
	health = clamp(health + amount, 0, 100)

func modify_morale(amount: int):
	"""Modify morale value"""
	morale = clamp(morale + amount, 0, 100)

func get_stats_summary() -> String:
	"""Return a formatted string of all character stats"""
	var summary = ""
	summary += "=== CHARACTER STATS ===\n"
	summary += "Name: %s\n" % character_name
	summary += "Health: %d/100\n" % health
	summary += "Morale: %d/100\n\n" % morale
	summary += "PRIMARY ATTRIBUTES:\n"
	summary += "Intellect: %d\n" % intellect
	summary += "Psyche: %d\n" % psyche
	summary += "Physique: %d\n" % physique
	summary += "Motorics: %d\n\n" % motorics
	summary += "SKILLS:\n"
	summary += "Logic: %d\n" % logic
	summary += "Rhetoric: %d\n" % rhetoric
	summary += "Empathy: %d\n" % empathy
	summary += "Authority: %d\n" % authority
	summary += "Perception: %d\n" % perception
	summary += "Endurance: %d\n" % endurance
	summary += "Pain Threshold: %d\n" % pain_threshold
	summary += "Shivers: %d\n" % shivers
	return summary
