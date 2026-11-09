"""Generate a clearly marked partial snapshot for layout QA, not publication."""
from pathlib import Path
from dashboard_data import get_snapshot
from dashboard_report import build_report

data=get_snapshot()
out=Path(__file__).resolve().parent/'dashboard-qa'/'layout-preview.pdf'
build_report(data,out,allow_partial=True)
print('QA_REPORT',out,'completed jobs',data['completed'])
