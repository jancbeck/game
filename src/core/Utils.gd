extends Node


func ysort_by_y(node: CanvasItem) -> void:
	# Depth sorting: large y draws above small y
	node.z_index = int(node.global_position.y)
