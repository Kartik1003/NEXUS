from typing import List, Dict

class ResultAggregator:
    def aggregate(self, task: str, results: List[Dict]) -> Dict:
        """
        Processes individual step results into a structured aggregation.
        """
        total_steps = len(results)
        if total_steps == 0:
            return {
                "summary": "No execution steps were performed.",
                "sections": [],
                "success_rate": 0.0,
                "total_steps": 0,
                "failed_steps": []
            }

        succeeded = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        success_count = len(succeeded)
        success_rate = round(success_count / total_steps, 2)

        if success_count == total_steps:
            summary = f"Task completed successfully across {total_steps} departments."
        else:
            summary = f"Partial completion: {success_count}/{total_steps} steps succeeded."

        # Group results by department
        sections_map = {}
        for r in results:
            dept = r.get("department", "Default")
            if dept not in sections_map:
                sections_map[dept] = {
                    "department": dept,
                    "results": []
                }
            sections_map[dept]["results"].append({
                "employee": r.get("employee"),
                "content": r.get("result"),
                "success": r.get("success")
            })

        return {
            "summary": summary,
            "sections": list(sections_map.values()),
            "success_rate": success_rate,
            "total_steps": total_steps,
            "failed_steps": [r.get("employee") for r in failed]
        }

    def to_markdown(self, aggregated: Dict) -> str:
        """
        Convert the aggregated dictionary into a clean Markdown report.
        """
        if not aggregated.get("sections"):
            return "No results available."

        lines = [f"# Strategy Report: Execution Summary", ""]
        lines.append(f"> **Status:** {aggregated['summary']}")
        lines.append(f"> **Reliability Score:** {int(aggregated['success_rate'] * 100)}%")
        lines.append("")

        for section in aggregated["sections"]:
            dept_name = section["department"]
            lines.append(f"## Department: {dept_name}")
            for r in section["results"]:
                status_icon = "✅" if r["success"] else "❌"
                lines.append(f"### {status_icon} Employee: {r['employee']}")
                lines.append(r["content"])
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
