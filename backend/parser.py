"""
parser.py — Web Scraper & Data Extractor for Groww Mutual Fund Pages

Strategy:
  Groww uses Next.js with Server-Side Rendering (SSR). All fund data is
  embedded in the page HTML inside a <script id="__NEXT_DATA__"> JSON tag.
  We extract this JSON directly — no fragile HTML scraping needed.

Output:
  For each fund, produces a clean multi-section text document that Phase 3
  (vector_db.py) will chunk and embed into ChromaDB.
"""

import re
import json
import requests
from datetime import date
from config import CORPUS_URLS, SCRAPER_HEADERS


def fetch_page(url: str) -> str | None:
    """Fetches the raw HTML of a Groww fund page."""
    try:
        response = requests.get(url, headers=SCRAPER_HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def extract_next_data(html: str) -> dict | None:
    """
    Extracts the __NEXT_DATA__ JSON embedded by Next.js SSR.
    Handles extra attributes like nonce and crossorigin on the script tag.
    """
    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def format_fund_document(mf: dict, source_url: str) -> str:
    """
    Converts the raw mfServerSideData dict into a clean, factual text document.
    Each section becomes a separate semantic block suitable for RAG chunking.
    """
    lines = []

    # ── Section 1: Identity ─────────────────────────────────────────────
    lines.append("=== FUND IDENTITY ===")
    lines.append(f"Fund Name: {mf.get('scheme_name', 'N/A')}")
    lines.append(f"Fund House: {mf.get('fund_house', 'N/A')}")
    lines.append(f"Category: {mf.get('category', 'N/A')} - {mf.get('sub_category', 'N/A')}")
    lines.append(f"Plan Type: {mf.get('plan_type', 'N/A')} - {mf.get('scheme_type', 'N/A')}")
    lines.append(f"ISIN: {mf.get('isin', 'N/A')}")
    lines.append(f"Launch Date: {mf.get('launch_date', 'N/A')}")
    lines.append(f"Source URL: {source_url}")

    # ── Section 2: Description ───────────────────────────────────────────
    lines.append("\n=== FUND DESCRIPTION ===")
    lines.append(mf.get('description', 'N/A'))

    cat_info = mf.get('category_info', {}) or {}
    if cat_info.get('definition'):
        lines.append(f"Category Definition: {cat_info['definition']}")
    # Skip generic/incorrect category notes (e.g. Groww's fallback 'Contra funds' text)
    cat_desc = cat_info.get('description', '') or ''
    if cat_desc and 'contra' not in cat_desc.lower():
        lines.append(f"Category Note: {cat_desc}")

    # ── Section 3: Key Facts ─────────────────────────────────────────────
    lines.append("\n=== KEY FACTS ===")
    lines.append(f"Current NAV: Rs. {mf.get('nav', 'N/A')} (as on {mf.get('nav_date', 'N/A')})")
    aum = mf.get('aum')
    if aum:
        lines.append(f"AUM: Rs. {float(aum):,.2f} Crores")
    lines.append(f"Expense Ratio (TER): {mf.get('expense_ratio', 'N/A')}%")
    lines.append(f"Benchmark: {mf.get('benchmark_name') or mf.get('benchmark', 'N/A')}")
    lines.append(f"Groww Rating: {mf.get('groww_rating', 'N/A')}/5")
    lines.append(f"Stamp Duty: {mf.get('stamp_duty', 'N/A')}")

    # Lock-in
    lock = mf.get('lock_in', {}) or {}
    lock_years = lock.get('years', 0) or 0
    lock_months = lock.get('months', 0) or 0
    lock_days = lock.get('days', 0) or 0
    if lock_years or lock_months or lock_days:
        lock_str = []
        if lock_years:
            lock_str.append(f"{lock_years} year(s)")
        if lock_months:
            lock_str.append(f"{lock_months} month(s)")
        if lock_days:
            lock_str.append(f"{lock_days} day(s)")
        lines.append(f"Lock-in Period: {', '.join(lock_str)}")
    else:
        lines.append("Lock-in Period: No lock-in")

    # ── Section 4: Investment Details ────────────────────────────────────
    lines.append("\n=== INVESTMENT DETAILS ===")
    lines.append(f"Minimum SIP Amount: Rs. {mf.get('min_sip_investment', 'N/A')}")
    lines.append(f"Minimum Lumpsum Amount: Rs. {mf.get('min_investment_amount', 'N/A')}")
    lines.append(f"Minimum Additional Investment: Rs. {mf.get('mini_additional_investment', 'N/A')}")
    lines.append(f"Minimum Withdrawal: Rs. {mf.get('min_withdrawal', 'N/A')}")
    lines.append(f"SIP Allowed: {'Yes' if mf.get('sip_allowed') else 'No'}")
    lines.append(f"Lumpsum Allowed: {'Yes' if mf.get('lumpsum_allowed') else 'No'}")
    lines.append(f"Exit Load: {mf.get('exit_load', 'N/A')}")

    # ── Section 5: Fund Manager ──────────────────────────────────────────
    lines.append("\n=== FUND MANAGER ===")
    fm_list = mf.get('fund_manager_details', []) or []
    if fm_list:
        seen_names = set()
        for fm in fm_list:
            name = fm.get('name', mf.get('fund_manager', 'N/A'))
            since = fm.get('since', '')
            if name not in seen_names:
                seen_names.add(name)
                lines.append(f"Fund Manager: {name}" + (f" (since {since})" if since else ""))
    else:
        lines.append(f"Fund Manager: {mf.get('fund_manager', 'N/A')}")

    # ── Section 6: Returns ───────────────────────────────────────────────
    lines.append("\n=== RETURNS (ABSOLUTE) ===")
    simple = mf.get('simple_return', {}) or {}
    return_fields = [
        ('return1m', '1 Month'), ('return3m', '3 Months'),
        ('return6m', '6 Months'), ('return1y', '1 Year'),
        ('return2y', '2 Years'), ('return3y', '3 Years'),
        ('return5y', '5 Years'),
    ]
    for field, label in return_fields:
        val = simple.get(field)
        if val is not None:
            lines.append(f"{label} Return: {round(float(val), 2)}%")

    lines.append("\n=== RETURNS (SIP / XIRR) ===")
    sip = mf.get('sip_return', {}) or {}
    for field, label in return_fields:
        val = sip.get(field)
        if val is not None:
            lines.append(f"{label} SIP Return: {round(float(val), 2)}%")

    # ── Section 7: Top Holdings ──────────────────────────────────────────
    holdings = mf.get('holdings', []) or []
    if holdings:
        lines.append("\n=== TOP HOLDINGS ===")
        for h in holdings[:15]:  # top 15
            name = h.get('company_name') or h.get('name', 'Unknown')
            pct = h.get('corpus_per', h.get('percentage', ''))
            lines.append(f"{name}: {pct}%")

    # ── Section 8: Tax Info ──────────────────────────────────────────────
    if cat_info.get('tax_impact'):
        lines.append("\n=== TAX INFORMATION ===")
        lines.append(f"Tax Impact: {cat_info['tax_impact']}")

    return "\n".join(lines)


def load_all_documents() -> list[dict]:
    """
    Fetches all configured Groww URLs, extracts fund data from __NEXT_DATA__,
    and returns a list of { scheme_metadata, cleaned_text } dicts.
    Phase 3 (vector_db.py) consumes this output for chunking and embedding.
    """
    if not CORPUS_URLS:
        print("No URLs configured in config.py.")
        return []

    all_documents = []
    print(f"Scraping {len(CORPUS_URLS)} Groww fund pages...\n")

    for item in CORPUS_URLS:
        print(f"Fetching: {item['scheme_name']}")
        html = fetch_page(item['url'])
        if not html:
            continue

        next_data = extract_next_data(html)
        if not next_data:
            print(f"  ERROR: Could not find __NEXT_DATA__ in page. Skipping.\n")
            continue

        mf_data = next_data.get('props', {}).get('pageProps', {}).get('mfServerSideData', {})
        if not mf_data:
            print(f"  ERROR: mfServerSideData not found in JSON. Skipping.\n")
            continue

        cleaned_text = format_fund_document(mf_data, item['url'])
        word_count = len(cleaned_text.split())
        print(f"  --> Extracted {word_count} words of structured fund data.\n")

        # Build structured fund managers string
        fm_list = mf_data.get('fund_manager_details', []) or []
        seen = set()
        managers = []
        for fm in fm_list:
            name = fm.get('name', '')
            if name and name not in seen:
                seen.add(name)
                managers.append(name)
        if not managers and mf_data.get('fund_manager'):
            managers = [mf_data['fund_manager']]

        # Lock-in string
        lock = mf_data.get('lock_in', {}) or {}
        lock_parts = []
        if lock.get('years'):
            lock_parts.append(f"{lock['years']} year(s)")
        if lock.get('months'):
            lock_parts.append(f"{lock['months']} month(s)")
        if lock.get('days'):
            lock_parts.append(f"{lock['days']} day(s)")
        lock_str = ", ".join(lock_parts) if lock_parts else "No lock-in"

        # Returns
        simple = mf_data.get('simple_return', {}) or {}
        sip = mf_data.get('sip_return', {}) or {}

        all_documents.append({
            "scheme_metadata": {
                # Identifiers
                "scheme_name": item['scheme_name'],
                "url": item['url'],
                "doc_type": item['doc_type'],
                "scraped_at": str(date.today()),
                "isin": mf_data.get('isin', ''),
                "fund_house": mf_data.get('fund_house', ''),
                "category": mf_data.get('category', ''),
                "sub_category": mf_data.get('sub_category', ''),
                "plan_type": mf_data.get('plan_type', ''),
                "launch_date": mf_data.get('launch_date', ''),
                # Key facts
                "nav": mf_data.get('nav'),
                "nav_date": mf_data.get('nav_date', ''),
                "aum_crores": round(float(mf_data['aum']), 2) if mf_data.get('aum') else None,
                "expense_ratio_pct": mf_data.get('expense_ratio'),
                "exit_load": (mf_data.get('exit_load') or '').strip(),
                "benchmark": mf_data.get('benchmark_name') or mf_data.get('benchmark', ''),
                "groww_rating": mf_data.get('groww_rating'),
                "lock_in": lock_str,
                # Investment limits
                "min_sip_amount": mf_data.get('min_sip_investment'),
                "min_lumpsum_amount": mf_data.get('min_investment_amount'),
                # Fund manager(s)
                "fund_managers": ", ".join(managers),
                # Returns (absolute)
                "return_1y_pct": simple.get('return1y'),
                "return_3y_pct": simple.get('return3y'),
                "return_5y_pct": simple.get('return5y'),
                # Returns (SIP)
                "sip_return_1y_pct": sip.get('return1y'),
                "sip_return_3y_pct": sip.get('return3y'),
                "sip_return_5y_pct": sip.get('return5y'),
            },
            "cleaned_text": cleaned_text
        })

    print(f"Done. {len(all_documents)}/{len(CORPUS_URLS)} funds scraped successfully.")
    return all_documents


if __name__ == "__main__":
    docs = load_all_documents()
    if docs:
        print("\n" + "="*60)
        print("SAMPLE OUTPUT — First Fund:")
        print("="*60)
        print(docs[0]["cleaned_text"])
