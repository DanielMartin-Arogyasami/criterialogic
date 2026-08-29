"""Load eligibility text from the public ClinicalTrials.gov API v2.
This is the source for the compositional stress-test pool and for additional
criteria. It is fully public (no DUA). Network access required at runtime.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://clinicaltrials.gov/api/v2/studies"
def fetch_eligibility(nct_ids: list[str]) -> dict[str, str]:
    """Return {nct_id: eligibility_criteria_text} for the given trials."""
    out: dict[str, str] = {}
    for nct in nct_ids:
        url = f"{API}/{urllib.parse.quote(nct)}?fields=EligibilityCriteria"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        crit = (
            data.get("protocolSection", {})
            .get("eligibilityModule", {})
            .get("eligibilityCriteria", "")
        )
        out[nct] = crit
    return out
def search_trials(query: str, page_size: int = 20) -> list[str]:
    """Return a list of NCT ids for a query (e.g. condition term)."""
    params = urllib.parse.urlencode({"query.term": query, "pageSize": page_size, "fields": "NCTId"})
    with urllib.request.urlopen(f"{API}?{params}", timeout=30) as resp:
        data = json.load(resp)
    return [
        s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        for s in data.get("studies", [])
    ]
