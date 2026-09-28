"""Table-driven unit tests for record normalization in app.processing.normalize."""

import pytest
from app.processing.normalize import (
    clean_text,
    normalize_email,
    normalize_record,
    normalize_records,
    normalize_url,
    parse_boolean,
    parse_currency_and_amount,
    parse_date,
    parse_number,
)
from app.schemas.collection import DatasetSchema, SchemaField


# -----------------------------------------------------------------------------
# 1. Currency & Number Parsing (Table-Driven)
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_input,expected_amount,expected_currency,expected_notes",
    [
        ("$1,200.50", 1200.5, "USD", []),
        ("₹1.2 Cr", 12000000.0, "INR", []),
        ("€3.4M", 3400000.0, "EUR", []),
        ("12k", 12000.0, None, []),
        ("1,00,000", 100000.0, None, []),
        ("(500)", -500.0, None, []),
        ("($1,200.50)", -1200.5, "USD", []),
        ("£45.99", 45.99, "GBP", []),
        ("15.5 Lakhs", 1550000.0, None, []),
        ("Rs. 2,500", 2500.0, "INR", []),
        ("500 USD", 500.0, "USD", []),
        ("1.200,50 €", 1200.5, "EUR", []),
        ("Free", None, None, ["currency_unparsed"]),
        ("Call for pricing", None, None, ["currency_unparsed"]),
        ("N/A", None, None, ["currency_unparsed"]),
        ("", None, None, []),
        (None, None, None, []),
        (42, 42.0, None, []),
        (99.99, 99.99, None, []),
    ],
)
def test_parse_currency_and_amount(raw_input, expected_amount, expected_currency, expected_notes):
    amount, currency, notes = parse_currency_and_amount(raw_input)
    assert amount == expected_amount
    assert currency == expected_currency
    assert notes == expected_notes


@pytest.mark.parametrize(
    "raw_input,expected_val,expected_notes",
    [
        ("1,500", 1500.0, []),
        ("2.5M", 2500000.0, []),
        ("invalid", None, ["number_unparsed"]),
    ],
)
def test_parse_number(raw_input, expected_val, expected_notes):
    val, notes = parse_number(raw_input)
    assert val == expected_val
    assert notes == expected_notes


# -----------------------------------------------------------------------------
# 2. Date Parsing (Table-Driven)
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_input,expected_iso,expected_notes",
    [
        ("12 Mar 2024", "2024-03-12", []),
        ("March 12, 2024", "2024-03-12", []),
        ("12th March, 2024", "2024-03-12", []),
        ("2024-03-12", "2024-03-12", []),
        ("2024-03-12T10:30:00Z", "2024-03-12", []),
        # Year only - precision preserved, no invented day
        ("2024", "2024", []),
        # Month-Year - precision preserved, no invented day
        ("March 2024", "2024-03", []),
        ("2024-03", "2024-03", []),
        ("03/2024", "2024-03", []),
        # Unambiguous numeric dates
        ("25/03/2024", "2024-03-25", []),
        ("03/25/2024", "2024-03-25", []),
        ("05/05/2024", "2024-05-05", []),
        ("2024/03/12", "2024-03-12", []),
        # Ambiguous numeric dates (resolved as DD/MM/YYYY by rule and flagged)
        ("12/03/2024", "2024-03-12", ["date_ambiguous"]),
        ("03/12/2024", "2024-12-03", ["date_ambiguous"]),
        ("04/05/2024", "2024-05-04", ["date_ambiguous"]),
        # Invalid date
        ("not-a-date", None, ["date_unparsed"]),
        (None, None, []),
    ],
)
def test_parse_date(raw_input, expected_iso, expected_notes):
    iso_date, notes = parse_date(raw_input)
    assert iso_date == expected_iso
    assert notes == expected_notes


# -----------------------------------------------------------------------------
# 3. Text, Whitespace, Unicode & Casing (Table-Driven)
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_input,expected_output",
    [
        ("   Hello\u200b \t World \n  ", "Hello World"),
        ("The Great Gatsby", "The Great Gatsby"),  # Title casing preserved
        ("Product\ufeffTitle\u200dHere", "ProductTitleHere"),  # Zero-width chars stripped
        ("Café \t\t au \n Lait", "Café au Lait"),  # NFC Unicode + collapsed whitespace
        ("", ""),
        (None, ""),
    ],
)
def test_clean_text(raw_input, expected_output):
    assert clean_text(raw_input) == expected_output


@pytest.mark.parametrize(
    "raw_input,expected_output",
    [
        ("  User.Name@Example.COM  ", "user.name@example.com"),
        ("Support@VaultPulse.AI", "support@vaultpulse.ai"),
    ],
)
def test_normalize_email(raw_input, expected_output):
    assert normalize_email(raw_input) == expected_output


# -----------------------------------------------------------------------------
# 4. URL Cleanup (Table-Driven)
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_url,expected_clean_url",
    [
        (
            "HTTPS://Example.COM:8080/products/item/?utm_source=twitter&utm_medium=cpc&id=123#spec",
            "https://example.com:8080/products/item?id=123#spec",
        ),
        (
            "https://example.com/item/",
            "https://example.com/item",
        ),
        (
            "https://example.com/",
            "https://example.com",
        ),
        (
            "http://shop.example.org/item?fbclid=IwAR123&gclid=xyz&ref=partner&sku=ABC",
            "http://shop.example.org/item?sku=ABC",
        ),
        (
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        ),
    ],
)
def test_normalize_url(raw_url, expected_clean_url):
    assert normalize_url(raw_url) == expected_clean_url


# -----------------------------------------------------------------------------
# 5. Schema-Driven Record Normalization
# -----------------------------------------------------------------------------

def test_normalize_record_schema_driven():
    schema = DatasetSchema(
        name="product",
        version="1.0",
        fields=[
            SchemaField(key="title", type="text", label="Title"),
            SchemaField(key="price", type="currency", label="Price"),
            SchemaField(key="url", type="link", label="Product URL"),
            SchemaField(key="release_date", type="date", label="Release Date"),
            SchemaField(key="contact_email", type="email", label="Email"),
        ],
    )

    record = {
        "title": "  Awesome   Headphones  ",
        "price": "₹1.2 Cr",
        "url": "HTTPS://Shop.Example.COM/headphones/?utm_source=google&ref=affiliate",
        "release_date": "12 Mar 2024",
        "contact_email": "Sales@EXAMPLE.COM",
        "extra_untyped_field": "   Should NOT be modified   ",
        "source_url": "https://shop.example.com/source",
        "fetched_at": "2024-03-12T00:00:00Z",
    }

    normalized = normalize_record(record, schema)

    # 1. Schema fields normalized according to type
    assert normalized["title"] == "Awesome Headphones"  # Cleaned, casing preserved
    assert normalized["price"] == 12000000.0  # Parsed amount
    assert normalized["price_currency"] == "INR"  # Detected currency code
    assert normalized["currency"] == "INR"
    assert normalized["url"] == "https://shop.example.com/headphones"  # Lowercase host, no utm/ref, no trailing slash
    assert normalized["release_date"] == "2024-03-12"  # ISO date
    assert normalized["contact_email"] == "sales@example.com"  # Lowercase email

    # 2. Undeclared fields pass through untouched
    assert normalized["extra_untyped_field"] == "   Should NOT be modified   "

    # 3. Raw preservation
    assert normalized["_raw"]["title"] == "  Awesome   Headphones  "
    assert normalized["_raw"]["price"] == "₹1.2 Cr"
    assert normalized["_raw"]["extra_untyped_field"] == "   Should NOT be modified   "

    # 4. Metadata preservation
    assert normalized["_source_url"] == "https://shop.example.com/source"
    assert normalized["_fetched_at"] == "2024-03-12T00:00:00Z"

    # 5. Normalization notes
    assert isinstance(normalized["_notes"], list)
    assert len(normalized["_notes"]) == 0


def test_normalize_record_ambiguous_date_and_unparsed_currency():
    schema = DatasetSchema(
        name="event",
        version="1.0",
        fields=[
            SchemaField(key="event_date", type="date", label="Date"),
            SchemaField(key="ticket_price", type="currency", label="Price"),
        ],
    )

    record = {
        "event_date": "12/03/2024",
        "ticket_price": "Free / Donation",
    }

    normalized = normalize_record(record, schema)
    assert normalized["event_date"] == "2024-03-12"
    assert normalized["ticket_price"] is None
    assert "date_ambiguous" in normalized["_notes"]
    assert "currency_unparsed" in normalized["_notes"]
