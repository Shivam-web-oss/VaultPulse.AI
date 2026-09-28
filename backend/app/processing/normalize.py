"""Deterministic record normalization (Phase E).

Pure Python functions for parsing numbers/currencies, standardizing dates,
cleaning text, and sanitizing URLs according to DatasetSchema field declarations.
No LLM calls are made here.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.collection import DatasetSchema, SchemaField

# -----------------------------------------------------------------------------
# Currencies & Numbers
# -----------------------------------------------------------------------------

# Map common currency symbols and abbreviations to standard ISO-4217 currency codes
CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "฿": "THB",
    "₩": "KRW",
    "₽": "RUB",
    "₺": "TRY",
    "₫": "VND",
    "₱": "PHP",
    "₪": "ILS",
    "R$": "BRL",
    "C$": "CAD",
    "A$": "AUD",
    "NZ$": "NZD",
    "HK$": "HKD",
    "S$": "SGD",
}

CURRENCY_WORDS: dict[str, str] = {
    "usd": "USD",
    "eur": "EUR",
    "gbp": "GBP",
    "inr": "INR",
    "rs": "INR",
    "rs.": "INR",
    "rupees": "INR",
    "rupee": "INR",
    "jpy": "JPY",
    "cny": "CNY",
    "rmb": "CNY",
    "cad": "CAD",
    "aud": "AUD",
    "nzd": "NZD",
    "chf": "CHF",
    "sgd": "SGD",
    "hkd": "HKD",
    "sek": "SEK",
    "nok": "NOK",
    "dkk": "DKK",
    "zar": "ZAR",
    "brl": "BRL",
    "mxn": "MXN",
    "krw": "KRW",
    "rub": "RUB",
}

# Multipliers including Indian numbering system words (Cr, Lakh)
MULTIPLIERS: dict[str, float] = {
    "k": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "mln": 1e6,
    "million": 1e6,
    "b": 1e9,
    "bln": 1e9,
    "billion": 1e9,
    "t": 1e12,
    "trillion": 1e12,
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "cr": 1e7,
    "crore": 1e7,
    "crores": 1e7,
}


def parse_currency_and_amount(
    value: Any,
) -> Tuple[Optional[float], Optional[str], List[str]]:
    """Parse numeric amount and ISO currency code from strings or numeric types.

    Handles:
    - Symbols: "$1,200.50", "€3.4M", "£45"
    - Indian denominations: "₹1.2 Cr", "15 Lakhs", "Rs. 500", "1,00,000"
    - Multipliers: "12k", "3.4M"
    - Accounting negatives: "(500)", "($1,200)"
    - Formatted numbers: "1,200.50", "1,00,000"

    Returns (amount, currency_code, notes). Unparseable values return
    (None, detected_currency, notes=["currency_unparsed"]).
    """
    notes: List[str] = []
    if value is None:
        return None, None, notes

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), None, notes

    raw_str = str(value).strip()
    if not raw_str:
        return None, None, notes

    # Unicode normalization
    s = unicodedata.normalize("NFC", raw_str).strip()

    # Check for accounting negative notation: (500) -> -500
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-") or s.startswith("−"):
        is_negative = True
        s = s[1:].strip()

    detected_currency: Optional[str] = None

    # Detect multi-character currency symbols first (e.g. R$, C$, NZ$)
    for sym, code in sorted(CURRENCY_SYMBOLS.items(), key=lambda x: -len(x[0])):
        if sym in s:
            detected_currency = code
            s = s.replace(sym, " ")
            break

    # Detect currency words (e.g. INR, USD, Rs., Rupees)
    if not detected_currency:
        for word, code in sorted(CURRENCY_WORDS.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", re.IGNORECASE)
            if pattern.search(s):
                detected_currency = code
                s = pattern.sub(" ", s)
                break

    # Detect multipliers (e.g. Cr, Lakh, k, M, Bn)
    multiplier = 1.0
    # Match multiplier words/abbreviations at end of number or token
    mult_pattern = re.compile(r"\b(cr|crore|crores|lakh|lakhs|lac|lacs|k|m|mln|million|b|bln|billion|t|trillion)\b", re.IGNORECASE)
    mult_match = mult_pattern.search(s)
    if mult_match:
        mult_word = mult_match.group(1).lower()
        multiplier = MULTIPLIERS.get(mult_word, 1.0)
        s = mult_pattern.sub(" ", s)
    else:
        # Also check attached suffix like 12k, 3.4M
        suffix_match = re.search(r"(\d+(?:\.\d+)?)\s*([kKmMbBtT])\b", s)
        if suffix_match:
            unit = suffix_match.group(2).lower()
            multiplier = MULTIPLIERS.get(unit, 1.0)
            s = s[:suffix_match.start(2)] + s[suffix_match.end(2):]

    # Clean remaining string to isolate numeric digits and separators
    cleaned_num = s.strip()

    # Handle Indian and Western comma formats: "1,00,000", "1,200.50"
    if "," in cleaned_num and "." in cleaned_num:
        if cleaned_num.rfind(",") > cleaned_num.rfind("."):
            # European format: 1.200,50 -> 1200.50
            cleaned_num = cleaned_num.replace(".", "").replace(",", ".")
        else:
            # Standard format: 1,200.50 -> 1200.50
            cleaned_num = cleaned_num.replace(",", "")
    elif "," in cleaned_num:
        # Check if comma is decimal (e.g. "12,5") or grouping (e.g. "1,00,000", "1,200")
        parts = cleaned_num.split(",")
        if len(parts) == 2 and len(parts[1]) != 3 and len(parts[1]) <= 2:
            cleaned_num = cleaned_num.replace(",", ".")
        else:
            cleaned_num = cleaned_num.replace(",", "")

    # Extract first valid floating-point number from cleaned_num
    num_match = re.search(r"[-+]?\d*\.?\d+", cleaned_num)
    if not num_match or not num_match.group(0) or num_match.group(0) == ".":
        notes.append("currency_unparsed")
        return None, detected_currency, notes

    try:
        amount = float(num_match.group(0)) * multiplier
        if is_negative:
            amount = -amount
        return amount, detected_currency, notes
    except (ValueError, OverflowError):
        notes.append("currency_unparsed")
        return None, detected_currency, notes


def parse_number(value: Any) -> Tuple[Optional[float], List[str]]:
    """Parse a generic numeric value (integer or float)."""
    amount, _currency, notes = parse_currency_and_amount(value)
    if amount is None and "currency_unparsed" in notes:
        notes.remove("currency_unparsed")
        notes.append("number_unparsed")
    return amount, notes


# -----------------------------------------------------------------------------
# Dates
# -----------------------------------------------------------------------------

# Ambiguous Date Resolution Rule:
# When a numeric date is formatted with slashes, dots, or dashes where both
# the first and second components are <= 12 and unequal (e.g. '12/03/2024' or
# '04/05/2024'), the date is resolved using the international day-first standard
# (DD/MM/YYYY). The normalized date is formatted as YYYY-MM-DD, and the warning
# 'date_ambiguous' is added to the record's normalization notes.

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_date(value: Any) -> Tuple[Optional[str], List[str]]:
    """Unify dates to ISO 8601 (YYYY-MM-DD, YYYY-MM, or YYYY).

    Maintains precision for year-only and month-year values without inventing days.
    Resolves ambiguous DD/MM vs MM/DD using day-first rule and flags 'date_ambiguous'.
    """
    notes: List[str] = []
    if value is None:
        return None, notes

    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d"), notes

    raw_str = str(value).strip()
    if not raw_str:
        return None, notes

    s = unicodedata.normalize("NFC", raw_str).strip()

    # 1. Year only: "2024"
    if re.fullmatch(r"\d{4}", s):
        return s, notes

    # 2. ISO full or partial
    # YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T\s].*)?$", s)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}", notes

    # YYYY-MM
    iso_ym = re.fullmatch(r"^(\d{4})-(\d{2})$", s)
    if iso_ym:
        y, m = int(iso_ym.group(1)), int(iso_ym.group(2))
        if 1 <= m <= 12:
            return f"{y:04d}-{m:02d}", notes

    # 3. Month name formats: "12 Mar 2024", "March 12, 2024", "12th March 2024", "March 2024"
    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th...)
    clean_ord = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s, flags=re.IGNORECASE)
    clean_ord = clean_ord.replace(",", " ").strip()

    # "March 2024" or "Mar 2024"
    m_y_match = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", clean_ord)
    if m_y_match:
        m_str = m_y_match.group(1).lower()
        if m_str in _MONTHS:
            return f"{int(m_y_match.group(2)):04d}-{_MONTHS[m_str]:02d}", notes

    # "2024 March"
    y_m_match = re.fullmatch(r"(\d{4})\s+([A-Za-z]+)", clean_ord)
    if y_m_match:
        m_str = y_m_match.group(2).lower()
        if m_str in _MONTHS:
            return f"{int(y_m_match.group(1)):04d}-{_MONTHS[m_str]:02d}", notes

    # "12 Mar 2024" or "12-Mar-2024"
    d_m_y_match = re.fullmatch(r"(\d{1,2})[\s\-]+([A-Za-z]+)[\s\-]+(\d{4})", clean_ord)
    if d_m_y_match:
        d = int(d_m_y_match.group(1))
        m_str = d_m_y_match.group(2).lower()
        y = int(d_m_y_match.group(3))
        if m_str in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[m_str]:02d}-{d:02d}", notes

    # "March 12 2024"
    m_d_y_match = re.fullmatch(r"([A-Za-z]+)[\s\-]+(\d{1,2})[\s\-]+(\d{4})", clean_ord)
    if m_d_y_match:
        m_str = m_d_y_match.group(1).lower()
        d = int(m_d_y_match.group(2))
        y = int(m_d_y_match.group(3))
        if m_str in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[m_str]:02d}-{d:02d}", notes

    # 4. Numeric formats with separators "/", ".", "-"
    # "03/2024" (MM/YYYY)
    my_num = re.fullmatch(r"(\d{1,2})/(\d{4})", s)
    if my_num:
        m = int(my_num.group(1))
        y = int(my_num.group(2))
        if 1 <= m <= 12:
            return f"{y:04d}-{m:02d}", notes

    # "2024/03/12" or "2024.03.12"
    ymd_num = re.fullmatch(r"(\d{4})[/\.](\d{1,2})[/\.](\d{1,2})", s)
    if ymd_num:
        y = int(ymd_num.group(1))
        m = int(ymd_num.group(2))
        d = int(ymd_num.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}", notes

    # "12/03/2024", "12.03.2024", "12-03-2024"
    dmy_num = re.fullmatch(r"(\d{1,2})[/\.\-](\d{1,2})[/\.\-](\d{2,4})", s)
    if dmy_num:
        p1 = int(dmy_num.group(1))
        p2 = int(dmy_num.group(2))
        raw_year = int(dmy_num.group(3))
        y = raw_year + 2000 if raw_year < 100 else raw_year

        if p1 > 12 and 1 <= p2 <= 12 and 1 <= p1 <= 31:
            # Unambiguously Day / Month: e.g. 25/03/2024
            return f"{y:04d}-{p2:02d}-{p1:02d}", notes
        elif p2 > 12 and 1 <= p1 <= 12 and 1 <= p2 <= 31:
            # Unambiguously Month / Day: e.g. 03/25/2024
            return f"{y:04d}-{p1:02d}-{p2:02d}", notes
        elif 1 <= p1 <= 12 and 1 <= p2 <= 12:
            if p1 == p2:
                # Same day and month: e.g. 05/05/2024
                return f"{y:04d}-{p1:02d}-{p2:02d}", notes
            else:
                # Ambiguous: resolve using documented day-first rule (DD/MM/YYYY)
                notes.append("date_ambiguous")
                return f"{y:04d}-{p2:02d}-{p1:02d}", notes

    notes.append("date_unparsed")
    return None, notes


# -----------------------------------------------------------------------------
# Text, URLs, Emails
# -----------------------------------------------------------------------------

# Control characters to strip (categories Cc, Cf), excluding standard whitespace like \t, \n, \r
_ZERO_WIDTH_CHARS = {
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\ufeff",  # zero-width no-break space / BOM
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
}

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "mc_eid",
    "_ga",
    "ref",
    "ref_",
}


def clean_text(value: Any) -> str:
    """Trim, collapse whitespace, strip zero-width and control characters, normalize Unicode (NFC)."""
    if value is None:
        return ""

    s = unicodedata.normalize("NFC", str(value))

    # Strip zero-width characters
    for zw in _ZERO_WIDTH_CHARS:
        s = s.replace(zw, "")

    # Filter control characters except newline, tab, carriage return
    s = "".join(ch for ch in s if not (unicodedata.category(ch).startswith("C") and ch not in "\t\n\r"))

    # Collapse internal whitespace and trim
    return re.sub(r"\s+", " ", s).strip()


def normalize_email(value: Any) -> str:
    """Clean text and lowercase email address."""
    return clean_text(value).lower()


def normalize_url(value: Any) -> str:
    """Normalize URL: lowercase host/scheme, remove tracking params (utm_*), strip trailing slashes."""
    raw = clean_text(value)
    if not raw:
        return ""

    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception:
        return raw

    # If no scheme was present, attempt default http or return cleaned
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    netloc = parsed.netloc.lower() if parsed.netloc else ""

    # Clean path: strip trailing slash
    path = parsed.path.rstrip("/")

    # Filter out tracking query params like utm_*
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [
        (k, v) for k, v in query_params
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    new_query = urllib.parse.urlencode(filtered_params)

    return urllib.parse.urlunsplit((scheme, netloc, path, new_query, parsed.fragment))


def parse_boolean(value: Any) -> Optional[bool]:
    """Parse boolean values from bools or strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "1", "yes", "y", "t"):
            return True
        if low in ("false", "0", "no", "n", "f"):
            return False
    return None


# -----------------------------------------------------------------------------
# Record Normalization
# -----------------------------------------------------------------------------


def normalize_record(
    record: Dict[str, Any],
    schema: Optional[DatasetSchema] = None,
) -> Dict[str, Any]:
    """Normalize a single record according to DatasetSchema.fields.

    - Declared fields are normalized according to type (currency, number, date, text, link, email).
    - Undeclared fields pass through untouched.
    - Preserves raw values in `_raw` sub-dict.
    - Preserves source URL and fetched_at metadata in `_source_url` and `_fetched_at`.
    - Collects normalization notes in `_notes`.
    """
    raw_copy = dict(record)
    normalized = dict(record)
    notes: List[str] = list(record.get("_notes", []))

    # Keep provenance metadata intact
    if "_source_url" not in normalized:
        source_url = record.get("_source_url") or record.get("source_url") or record.get("url")
        if source_url:
            normalized["_source_url"] = str(source_url)

    if "_fetched_at" not in normalized:
        fetched_at = record.get("_retrieved_at") or record.get("_fetched_at") or record.get("fetched_at")
        if fetched_at:
            normalized["_fetched_at"] = fetched_at

    if not schema or not schema.fields:
        normalized["_raw"] = raw_copy
        normalized["_notes"] = notes
        return normalized

    # Build field mapping from schema
    for field in schema.fields:
        k = field.key
        ftype = (field.type or "text").strip().lower()

        if k not in record:
            continue

        val = record[k]

        if ftype in ("currency", "price"):
            amount, detected_curr, cur_notes = parse_currency_and_amount(val)
            normalized[k] = amount
            if detected_curr:
                # Store detected currency in separate field
                normalized[f"{k}_currency"] = detected_curr
                if k == "price" or "currency" not in normalized:
                    normalized["currency"] = detected_curr
            notes.extend(cur_notes)

        elif ftype in ("number", "integer", "float"):
            amount, num_notes = parse_number(val)
            normalized[k] = amount
            notes.extend(num_notes)

        elif ftype == "date":
            date_iso, date_notes = parse_date(val)
            normalized[k] = date_iso
            notes.extend(date_notes)

        elif ftype in ("link", "url"):
            if val is not None:
                normalized[k] = normalize_url(val)

        elif ftype == "email":
            if val is not None:
                normalized[k] = normalize_email(val)

        elif ftype == "rating":
            amount, num_notes = parse_number(val)
            normalized[k] = amount if amount is not None else val
            notes.extend(num_notes)

        elif ftype == "boolean":
            bool_val = parse_boolean(val)
            if bool_val is not None:
                normalized[k] = bool_val

        elif ftype in ("text", "string"):
            if isinstance(val, str):
                normalized[k] = clean_text(val)

    # Save original raw values and notes
    normalized["_raw"] = raw_copy
    normalized["_notes"] = notes
    return normalized


def normalize_records(
    records: List[Dict[str, Any]],
    schema: Optional[DatasetSchema] = None,
) -> List[Dict[str, Any]]:
    """Normalize a batch of records according to DatasetSchema.fields."""
    return [normalize_record(r, schema) for r in records]
