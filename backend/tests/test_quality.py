"""Unit tests for schema-driven validation in app.processing.quality."""

import pytest
from app.processing.quality import deduplicate_records, validate_records
from app.schemas.collection import DatasetSchema, SchemaField


# -----------------------------------------------------------------------------
# 1. Schema-Driven Required-Field Validation
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "missing_value,desc",
    [
        (None, "None value"),
        ("", "Empty string"),
        ("   ", "Whitespace only"),
    ],
)
def test_validate_records_required_fields_empty(missing_value, desc):
    schema = DatasetSchema(
        name="item",
        version="1.0",
        fields=[
            SchemaField(key="title", type="text", label="Title", required=True),
        ],
    )

    records = [{"title": missing_value}]
    result = validate_records(records, schema)

    assert len(result) == 1
    assert result[0]["_is_valid"] is False
    assert any(i["rule"] == "required" and i["field"] == "title" for i in result[0]["_issues"])


def test_validate_records_missing_key():
    schema = DatasetSchema(
        name="item",
        version="1.0",
        fields=[
            SchemaField(key="title", type="text", label="Title", required=True),
            SchemaField(key="optional_notes", type="text", label="Notes", required=False),
        ],
    )

    records = [{}]  # title is missing, optional_notes is missing
    result = validate_records(records, schema)

    assert len(result) == 1
    assert result[0]["_is_valid"] is False
    # Only 'title' should trigger a required error
    required_issues = [i for i in result[0]["_issues"] if i["rule"] == "required"]
    assert len(required_issues) == 1
    assert required_issues[0]["field"] == "title"


# -----------------------------------------------------------------------------
# 2. Schema with Different Fields Than Current Entity (Vehicle Schema)
# -----------------------------------------------------------------------------

def test_validate_records_custom_vehicle_schema():
    """Validates an entity with fields entirely different from product/job/event."""
    schema = DatasetSchema(
        name="vehicle",
        version="1.0",
        fields=[
            SchemaField(key="vin", type="text", label="VIN"),
            SchemaField(key="mileage", type="number", label="Mileage"),
            SchemaField(key="registration_date", type="date", label="Registration Date"),
            SchemaField(key="fuel_type", type="enum", label="Fuel", options=["petrol", "diesel", "electric", "hybrid"]),
            SchemaField(key="owner_email", type="email", label="Owner Email"),
            SchemaField(key="listing_url", type="link", label="Listing URL"),
        ],
    )

    records = [
        # 1. Perfectly valid vehicle record
        {
            "vin": "1HGCR2F83HA000000",
            "mileage": 45000.0,
            "registration_date": "2021-06-15",
            "fuel_type": "electric",
            "owner_email": "driver@example.com",
            "listing_url": "https://motors.example.com/listings/123",
        },
        # 2. Invalid vehicle record: bad date, bad fuel_type enum, bad email, bad URL, non-numeric mileage
        {
            "vin": "2HGCR2F83HA111111",
            "mileage": "not_a_number",
            "registration_date": "June 2021 15",  # non-ISO format
            "fuel_type": "nuclear",  # not in allowed options
            "owner_email": "invalid_email_at_host",
            "listing_url": "ftp://unsupported.com/car",
        },
    ]

    result = validate_records(records, schema)

    assert len(result) == 2

    # Record 1: valid
    assert result[0]["_is_valid"] is True
    assert len(result[0]["_issues"]) == 0

    # Record 2: flagged, not deleted
    assert result[1]["_is_valid"] is False
    issue_rules = {i["rule"] for i in result[1]["_issues"]}
    assert "type_number" in issue_rules
    assert "date_format" in issue_rules
    assert "enum_choice" in issue_rules
    assert "email_format" in issue_rules
    assert "url_format" in issue_rules


# -----------------------------------------------------------------------------
# 3. Existing Price / URL / Rating Checks Via Generic Mechanism
# -----------------------------------------------------------------------------

def test_validate_records_price_url_rating():
    schema = DatasetSchema(
        name="product",
        version="1.0",
        fields=[
            SchemaField(key="name", type="text", label="Name"),
            SchemaField(key="price", type="currency", label="Price"),
            SchemaField(key="rating", type="rating", label="Rating"),
            SchemaField(key="url", type="link", label="URL"),
        ],
    )

    requirement = {
        "schema": schema,
        "constraints": {"maxPrice": 100.0},
    }

    records = [
        # Record 0: All valid
        {"name": "Valid Book", "price": 49.99, "rating": 4.5, "url": "https://books.example.com/1"},
        # Record 1: Price exceeds constraint
        {"name": "Expensive Book", "price": 150.0, "rating": 4.5, "url": "https://books.example.com/2"},
        # Record 2: Invalid rating > 5
        {"name": "Overrated Book", "price": 20.0, "rating": 5.5, "url": "https://books.example.com/3"},
        # Record 3: Invalid URL format
        {"name": "No URL Book", "price": 20.0, "rating": 3.0, "url": "javascript:void(0)"},
    ]

    result = validate_records(records, requirement)

    assert len(result) == 4
    assert result[0]["_is_valid"] is True
    assert result[1]["_is_valid"] is False
    assert any(i["rule"] == "max_price" for i in result[1]["_issues"])
    assert result[2]["_is_valid"] is False
    assert any(i["rule"] == "rating_range" for i in result[2]["_issues"])
    assert result[3]["_is_valid"] is False
    assert any(i["rule"] == "url_format" for i in result[3]["_issues"])


# -----------------------------------------------------------------------------
# 4. Warnings vs Errors (Ambiguous Date Warning Does Not Invalidate Record)
# -----------------------------------------------------------------------------

def test_validate_records_warnings_do_not_invalidate():
    schema = DatasetSchema(
        name="event",
        version="1.0",
        fields=[
            SchemaField(key="name", type="text", label="Event Name"),
            SchemaField(key="date", type="date", label="Date"),
            SchemaField(key="url", type="link", label="URL"),
        ],
    )

    records = [
        {
            "name": "Tech Conference",
            "date": "2024-03-12",
            "url": "https://techconf.org",
            "_notes": ["date_ambiguous"],  # Warning from normalization
        }
    ]

    result = validate_records(records, schema)
    assert len(result) == 1
    # Record has a warning issue but no error issues -> remains valid
    assert result[0]["_is_valid"] is True
    assert len(result[0]["_issues"]) == 1
    assert result[0]["_issues"][0]["rule"] == "date_ambiguous"
    assert result[0]["_issues"][0]["severity"] == "warning"


# -----------------------------------------------------------------------------
# 5. Summary Metrics (% Complete, Counts by Rule and Field)
# -----------------------------------------------------------------------------

def test_validate_records_summary_metrics():
    schema = DatasetSchema(
        name="profile",
        version="1.0",
        fields=[
            SchemaField(key="username", type="text", label="Username"),
            SchemaField(key="email", type="email", label="Email"),
            SchemaField(key="website", type="link", label="Website"),
        ],
    )

    records = [
        # Record 1: 3/3 required fields present
        {"username": "alice", "email": "alice@example.com", "website": "https://alice.dev"},
        # Record 2: 2/3 required fields present (website missing)
        {"username": "bob", "email": "bob@example.com"},
        # Record 3: 1/3 required fields present (email and website missing)
        {"username": "carol", "email": "", "website": None},
    ]

    result = validate_records(records, schema)

    summary = result.summary
    assert summary["total_records"] == 3
    assert summary["valid_records"] == 1
    assert summary["invalid_records"] == 2
    assert summary["counts_by_rule"]["required"] == 3
    assert summary["counts_by_field"]["website"] == 2
    assert summary["counts_by_field"]["email"] == 1

    # Total expected required cells = 3 records * 3 fields = 9
    # Missing cells = 3
    # Complete cells = 6 / 9 = 66.67%
    assert summary["percent_complete"] == 66.67


# -----------------------------------------------------------------------------
# 6. Deduplication Integration
# -----------------------------------------------------------------------------

def test_deduplicate_with_validated_records():
    records = [
        {"name": "Book A", "seller": "Store 1", "url": "https://store1.com/a", "_is_valid": True},
        {"name": "Book A", "seller": "Store 1", "url": "https://store1.com/a/", "_is_valid": True},  # Duplicate
        {"name": "Book B", "seller": "Store 2", "url": "https://store2.com/b", "_is_valid": False},
    ]

    deduped = deduplicate_records(records)
    assert len(deduped) == 2
    assert deduped[0]["name"] == "Book A"
    assert deduped[1]["name"] == "Book B"
