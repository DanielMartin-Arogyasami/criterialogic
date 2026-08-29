"""Task A — criteria structuring: free-text eligibility -> LogicalForm.
Gold: Chia. Scored with entity/relation F1 + logical-form exact match
(see metrics.extraction). Requires a parser/LLM that emits a LogicalForm; wired
here as a task name + contract. Not exercised by the zero-dependency demo.
"""
TASK_NAME = "structuring"
