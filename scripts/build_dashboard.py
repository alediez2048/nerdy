"""Export dashboard data and generate HTML in one step."""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from output.export_dashboard import build_dashboard_data
from output.dashboard_builder import generate_dashboard_html

# Step 1: Export data from ledger
data = build_dashboard_data("data/ledger.jsonl")
with open("output/dashboard_data.json", "w") as f:
    json.dump(data, f, indent=2, default=str)
print(f"Dashboard data exported ({len(data)} keys)")

# Step 2: Generate HTML
generate_dashboard_html(data, "output/dashboard.html")
print("Dashboard HTML written to output/dashboard.html")
