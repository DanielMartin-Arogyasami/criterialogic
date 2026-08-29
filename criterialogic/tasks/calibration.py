"""Cross-cutting calibration & abstention.
Reuses any task's predictions (which carry a confidence) and is scored by
metrics.calibration (ECE + selective accuracy). No separate item set is needed.
"""
TASK_NAME = "calibration"
