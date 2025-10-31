extends Node2D

@export var npc_name : String = "Sergeant Bran"
var conversation : Dictionary
var is_busy : bool = false

func _ready() -> void:
    add_to_group("npc")
    _build_conversation()

func begin_conversation(player : Node) -> void:
    if is_busy:
        return
    is_busy = true
    ConversationManager.start_conversation(conversation, self, player)

func on_conversation_finished() -> void:
    is_busy = false

func _build_conversation() -> void:
    conversation = {
        "start": "introduction",
        "introduction": {
            "speaker": npc_name,
            "text": "You're the new inquisitor from the mainland? The harbor's gone restless since the Sleeper cult was crushed.",
            "options": [
                {
                    "text": "Ask about the disappearances.",
                    "next": "disappearances",
                    "notebook_entry": "Bran suspects the disappearances are tied to Sleeper relics.",
                    "advance_time": true
                },
                {
                    "text": "[Faith] Invoke your oath to demand compliance.",
                    "skill_check": {
                        "skill": "faith",
                        "difficulty": 15,
                        "success_next": "faith_success",
                        "failure_next": "faith_failure"
                    }
                },
                {
                    "text": "Leave for now.",
                    "next": "farewell"
                }
            ]
        },
        "disappearances": {
            "speaker": npc_name,
            "voice_skill": "wit",
            "voice_text": "You catch a nervous twitch when he mentions the mines.",
            "text": "Workers vanish near the old ore lifts. Rumors say a blue glow seeps from the cracks again.",
            "options": [
                {
                    "text": "Press for access to the lifts.",
                    "skill_check": {
                        "skill": "guile",
                        "difficulty": 13,
                        "success_next": "lift_access",
                        "failure_next": "no_access"
                    }
                },
                {
                    "text": "Thank Bran and conclude.",
                    "next": "farewell",
                    "faction_delta": {"Myrtanian Legion": 1}
                }
            ]
        },
        "faith_success": {
            "speaker": npc_name,
            "text": "Right, right. No need to draw steel. I'll share what I know... but tread lightly.",
            "options": [
                {
                    "text": "Continue.",
                    "next": "disappearances",
                    "faction_delta": {"Myrtanian Legion": 1}
                }
            ]
        },
        "faith_failure": {
            "speaker": npc_name,
            "text": "Save the sermons, inquisitor. Respect goes both ways.",
            "options": [
                {
                    "text": "Apologize and try again later.",
                    "next": "farewell",
                    "faction_delta": {"Myrtanian Legion": -1}
                }
            ]
        },
        "lift_access": {
            "speaker": npc_name,
            "text": "Fine. Take this seal. It'll keep the foremen from blocking you."
                + " Report back if you find anything breathing Sleeper magic again.",
            "options": [
                {
                    "text": "Accept the seal.",
                    "next": "farewell",
                    "notebook_entry": "Obtained Bran's seal to enter the ore lifts.",
                    "faction_delta": {"Old Camp Remnants": 1, "Harbor Commons": 1}
                }
            ]
        },
        "no_access": {
            "speaker": npc_name,
            "text": "Not with that tone. The miners barely trust me as is.",
            "options": [
                {
                    "text": "Change the subject.",
                    "next": "disappearances"
                }
            ]
        },
        "farewell": {
            "end": true
        }
    }
