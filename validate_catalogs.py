#!/usr/bin/env python3
"""Validate that catalogs are comprehensive against device samples."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set


def flatten_capabilities(caps: Dict, prefix: str = "") -> Set[str]:
    """Recursively flatten nested capabilities to leaf-level entities.

    Filter out test artifacts and only return actual capability keys.
    """
    keys = set()
    test_artifacts = {
        "custom_components",
        "data",
        "home_assistant",
        "integration_manifest",
        "issues",
        "setup_times",
    }

    for key, value in caps.items():
        # Skip test artifacts
        if key in test_artifacts:
            continue

        current_key = f"{prefix}/{key}" if prefix else key

        # If value has nested properties, recurse
        if isinstance(value, dict):
            # Check if this is a leaf capability or a parent object
            has_access = "access" in value or "type" in value

            if has_access:
                # This is a leaf capability - add it
                keys.add(current_key)
            else:
                # This is a parent object - recurse to get children
                nested_keys = flatten_capabilities(value, current_key)
                keys.update(nested_keys)

    return keys


def load_capabilities(file_path: Path) -> Set[str]:
    """Load and flatten capabilities from JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "capabilities" in data:
            caps = data["capabilities"]
        else:
            caps = data

        return flatten_capabilities(caps)


def get_catalog_keys(catalog_file: Path) -> Set[str]:
    """Extract all entity keys from a catalog file."""
    keys = set()
    with open(catalog_file, "r", encoding="utf-8") as f:
        content = f.read()
        # Find all lines like: "keyName": ElectroluxDevice(
        # or "keyName": create_*_entity(
        import re

        pattern = r'^\s*"([^"]+)":\s*(?:ElectroluxDevice|create_\w+_entity)\('
        for match in re.finditer(pattern, content, re.MULTILINE):
            key = match.group(1)
            keys.add(key)
    return keys


def validate_appliance_type(
    appliance_type: str,
    catalog_file: Path,
    sample_files: List[Path],
    core_catalog_file: Path | None = None,
) -> Dict:
    """Validate one appliance type."""
    print(f"\n{'='*80}")
    print(f"Validating {appliance_type}")
    print(f"{'='*80}")

    # Get catalog keys from both appliance-specific and core catalogs
    catalog_keys = get_catalog_keys(catalog_file)
    if core_catalog_file and core_catalog_file.exists():
        core_keys = get_catalog_keys(core_catalog_file)
        catalog_keys.update(core_keys)

    print(f"\nCatalog has {len(catalog_keys)} entities (including core catalog)")

    # Collect all keys from samples
    all_sample_keys = set()
    for sample_file in sample_files:
        if not sample_file.exists():
            print(f"  ⚠️  Sample not found: {sample_file}")
            continue

        try:
            caps = load_capabilities(sample_file)
            all_sample_keys.update(caps)
            print(f"  [OK] {sample_file.name}: {len(caps)} leaf capabilities")
        except Exception as e:
            print(f"  [WARNING] Error loading {sample_file}: {e}")

    print(f"\nTotal unique capabilities in samples: {len(all_sample_keys)}")

    # Find missing from catalog
    missing_from_catalog = all_sample_keys - catalog_keys

    # Find in catalog but not samples (expected - templates for other models)
    extra_in_catalog = catalog_keys - all_sample_keys

    # Report
    print("\nAnalysis:")
    print(f"  - In samples but MISSING from catalog: {len(missing_from_catalog)}")
    print(
        f"  - In catalog but not in samples (OK - template coverage): {len(extra_in_catalog)}"
    )

    if missing_from_catalog:
        print("\n[MISSING] from catalog (should add these):")
        for key in sorted(missing_from_catalog):
            print(f"     - {key}")

    if extra_in_catalog:
        print("\n[TEMPLATE COVERAGE] (good - supports other models):")
        for key in sorted(list(extra_in_catalog)[:10]):  # Show first 10
            print(f"     - {key}")
        if len(extra_in_catalog) > 10:
            print(f"     ... and {len(extra_in_catalog) - 10} more")

    return {
        "appliance_type": appliance_type,
        "catalog_count": len(catalog_keys),
        "sample_count": len(all_sample_keys),
        "missing_from_catalog": sorted(missing_from_catalog),
        "extra_in_catalog": sorted(extra_in_catalog),
    }


def main():
    """Run validation."""
    root = Path(__file__).parent
    samples_dir = root / "samples"
    catalogs_dir = root / "custom_components" / "electrolux"
    core_catalog = catalogs_dir / "catalog_core.py"

    results = []

    # Air Conditioner
    results.append(
        validate_appliance_type(
            "Air Conditioner (AC)",
            catalogs_dir / "catalog_air_conditioner.py",
            [
                samples_dir / "ac_device_details.json",
            ],
            core_catalog,
        )
    )

    # Refrigerator
    results.append(
        validate_appliance_type(
            "Refrigerator (RF)",
            catalogs_dir / "catalog_refrigerator.py",
            [
                samples_dir / "RF-EHE6899SA" / "get_appliance_capabilities.json",
            ],
            core_catalog,
        )
    )

    # Washing Machine / Washer-Dryer
    results.append(
        validate_appliance_type(
            "Washer/Washer-Dryer (WM/WD)",
            catalogs_dir / "catalog_washer.py",
            [
                samples_dir / "WM-EW7F3816DB" / "get_appliance_capabilities.json",
                samples_dir / "WD-914611000.json",
                samples_dir / "WD-914611500.json",
            ],
            core_catalog,
        )
    )

    # Oven
    results.append(
        validate_appliance_type(
            "Oven (OV)",
            catalogs_dir / "catalog_oven.py",
            [
                # No structured sample yet
            ],
            core_catalog,
        )
    )

    # Tumble Dryer
    results.append(
        validate_appliance_type(
            "Tumble Dryer (TD)",
            catalogs_dir / "catalog_dryer.py",
            [
                samples_dir / "TD-916099949.json",
                samples_dir / "TD-916099971.json",
            ],
            core_catalog,
        )
    )

    # Purifier
    results.append(
        validate_appliance_type(
            "Air Purifier (PUREA9)",
            catalogs_dir / "catalog_purifier.py",
            [
                samples_dir / "PUREA9.json",
            ],
            core_catalog,
        )
    )

    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")

    total_missing = sum(len(r["missing_from_catalog"]) for r in results)

    for result in results:
        status = (
            "[OK]"
            if not result["missing_from_catalog"]
            else f"[MISSING: {len(result['missing_from_catalog'])}]"
        )
        print(f"{result['appliance_type']:40} {status}")

    if total_missing == 0:
        print("\n[SUCCESS] All catalogs are comprehensive! No capabilities missing.")
        return 0
    else:
        print(
            f"\n[WARNING] Total capabilities missing across all catalogs: {total_missing}"
        )
        print("\nReview the detailed output above to add missing capabilities.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
