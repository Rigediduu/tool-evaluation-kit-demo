from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import yaml

# Represents a single evaluation criterion
@dataclass(frozen=True)
class Criterion:
	cid: str
	name: str
	weight: float

def load_criteria(path: str) -> Tuple[List[Criterion], int, int]:
	"""
	Load criteria and scoring scale from YAML.
	Ensures weights sum to 1.0 and IDs are unique.
	"""
	with open(path, "r", encoding="utf-8") as f:
		data = yaml.safe_load(f)

	scale = data.get("scale", {})
	min_score = int(scale.get("min", 1))
	max_score = int(scale.get("max", 5))

	raw_criteria = data.get("criteria", [])
	criteria: List[Criterion] = []

	for c in raw_criteria:
		criteria.append(
			Criterion(
				cid=str(c["id"]).strip(),
				name=str(c["name"]).strip(),
				weight=float(c["weight"]),
			)
		)

	total_weight = sum(c.weight for c in criteria)
	if abs(total_weight - 1.0) > 1e-5:
		raise ValueError("Criteria weights must sum to 1.0")

	ids = [c.cid for c in criteria]
	if len(ids) != len(set(ids)):
		raise ValueError("Criterion IDs must be unique")

	return criteria, min_score, max_score

def load_scores(path: str) -> List[Dict[str, str]]:
	"""
	Load tool scores from CSV.
	"""
	with open(path, "r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		rows = list(reader)

	if not rows:
		raise ValueError("scores.csv is empty")
	if "tool" not in rows[0]:
		raise ValueError("scores.csv must contain a 'tool' column")

	return rows

def parse_score(value: str, min_score: int, max_score: int) -> float:
	"""
	Parse and validate a numeric score.
	"""
	score = float(value)
	if not (min_score <= score <= max_score):
		raise ValueError(f"Score {score} out of range")
	return score

def compute_results(
	criteria: List[Criterion],
	rows: List[Dict[str, str]],
	min_score: int,
	max_score: int,
) -> List[Dict[str, str]]:
	"""
	Compute weighted scores and rank tools.
	"""
	results: List[Dict[str, str]] = []

	for row in rows:
		tool = row["tool"].strip()
		weighted_total = 0.0
		raw_total = 0.0
		max_raw = 0.0

		for c in criteria:
			score = parse_score(row[c.cid], min_score, max_score)
			weighted_total += score * c.weight
			raw_total += score
			max_raw += max_score

		normalized = (raw_total / max_raw) * 100.0

		results.append(
			{
				"tool": tool,
				"weighted_score": f"{weighted_total:.3f}",
				"normalized_percent": f"{normalized:.1f}",
				"notes": row.get("notes", ""),
			}
		)

	results.sort(key=lambda r: float(r["weighted_score"]), reverse=True)
	return results

def write_csv(path: str, results: List[Dict[str, str]]) -> None:
	"""
	Write results to CSV.
	"""
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8", newline="") as f:
		writer = csv.DictWriter(
			f,
			fieldnames=["tool", "weighted_score", "normalized_percent", "notes"],
		)
		writer.writeheader()
		writer.writerows(results)

def write_markdown(path: str, results: List[Dict[str, str]]) -> None:
	"""
	Write results to Markdown.
	"""
	os.makedirs(os.path.dirname(path), exist_ok=True)

	lines = [
		"# Tool Evaluation Results\n\n",
		"| Rank | Tool | Weighted Score | Normalized (0-100) | Notes | \n",
		"|---:|---|---:|---:|---|\n",
	]

	for i, r in enumerate(results, start=1):
		lines.append(
			f"| {i} | {r['tool']} | {r['weighted_score']} | "
			f"{r['normalized_percent']} | {r['notes']} |\n"
		)

	with open(path, "w", encoding="utf-8") as f:
		f.writelines(lines)

def main() -> None:
	criteria, min_score, max_score = load_criteria("criteria.yaml")
	rows = load_scores("scores.csv")
	results = compute_results(criteria, rows, min_score, max_score)

	write_csv("output/results.csv", results)
	write_markdown("output/results.md", results)

	print("Evaluation complete.")

if __name__ == "__main__":
	main()

