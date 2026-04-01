"""
GQS Cross-Version Comparison Tool
===================================
Compares GQS analysis reports from different Neo4j versions.
Each team member generates a JSON report using analyze_gqs_logs.py,
then this script compares them side-by-side.

Usage:
    python compare_versions.py <report1.json> <report2.json> [report3.json ...]

Example:
    python compare_versions.py gqs_analysis_5_20_0.json gqs_analysis_4_4_0.json
"""

import json
import sys
import os


def load_reports(filepaths):
    """Load multiple JSON analysis reports."""
    reports = []
    for fp in filepaths:
        with open(fp, "r") as f:
            reports.append(json.load(f))
    return reports


def print_comparison(reports):
    """Print a side-by-side comparison of multiple version reports."""
    versions = [r["neo4j_version"] for r in reports]
    col_width = 18

    print("=" * (35 + col_width * len(versions)))
    print("  GQS CROSS-VERSION COMPARISON")
    print("=" * (35 + col_width * len(versions)))

    # Header
    header = f"  {'Metric':<33}"
    for v in versions:
        header += f"{'v' + v:>{col_width}}"
    print(header)
    print(f"  {'-' * 31:<33}" + (f"{'-' * (col_width - 2):>{col_width}}" * len(versions)))

    # --- Overview ---
    print(f"\n  --- OVERVIEW ---")
    overview_keys = [
        ("Log files", "total_log_files"),
        ("MATCH queries", "total_match_queries"),
        ("CREATE queries", "total_create_queries"),
        ("Schema statements", "total_schema_statements"),
        ("Constraints", "constraints_created"),
        ("Indexes", "indexes_created"),
        ("Bugs found", "total_bugs_found"),
        ("Logic bugs", "logic_bugs_found"),
        ("Database crashes", "database_crashes"),
    ]
    for label, key in overview_keys:
        row = f"  {label:<33}"
        for r in reports:
            val = r["summary"].get(key, "N/A")
            row += f"{val:>{col_width}}"
        print(row)

    # --- Query Complexity ---
    print(f"\n  --- QUERY COMPLEXITY (Mean values) ---")
    complexity_keys = [
        ("Query length (chars)", "length_chars"),
        ("MATCH clauses/query", "match_clauses"),
        ("OPTIONAL MATCH/query", "optional_match"),
        ("WITH clauses/query", "with_clauses"),
        ("UNWIND clauses/query", "unwind_clauses"),
        ("WHERE clauses/query", "where_clauses"),
        ("Unique nodes/query", "unique_nodes"),
        ("Unique rels/query", "unique_relationships"),
        ("Unique labels/query", "unique_labels"),
        ("Unique rel types/query", "unique_rel_types"),
        ("Unique properties/query", "unique_properties"),
        ("AND conditions/query", "and_conditions"),
        ("OR conditions/query", "or_conditions"),
        ("NOT conditions/query", "not_conditions"),
        ("Total conditions/query", "total_conditions"),
        ("String operations/query", "string_ops_total"),
        ("Aggregations/query", "aggregations_total"),
        ("ORDER BY/query", "order_by"),
        ("LIMIT/query", "limit_clauses"),
        ("DISTINCT/query", "distinct"),
    ]
    for label, key in complexity_keys:
        row = f"  {label:<33}"
        for r in reports:
            stats = r["query_complexity_stats"].get(key, {})
            val = stats.get("mean", "N/A")
            if isinstance(val, (int, float)):
                row += f"{val:>{col_width}.1f}"
            else:
                row += f"{val:>{col_width}}"
        print(row)

    # --- Complexity Spread (Std Dev) ---
    print(f"\n  --- QUERY COMPLEXITY (Std Dev - measures diversity) ---")
    for label, key in complexity_keys:
        row = f"  {label:<33}"
        for r in reports:
            stats = r["query_complexity_stats"].get(key, {})
            val = stats.get("std", "N/A")
            if isinstance(val, (int, float)):
                row += f"{val:>{col_width}.1f}"
            else:
                row += f"{val:>{col_width}}"
        print(row)

    # --- Property Distribution ---
    print(f"\n  --- PROPERTY KEY DIVERSITY ---")
    row = f"  {'Unique properties':<33}"
    for r in reports:
        val = r["property_key_distribution"]["total_unique_properties"]
        row += f"{val:>{col_width}}"
    print(row)

    # --- Label Distribution ---
    print(f"\n  --- LABEL DIVERSITY ---")
    row = f"  {'Unique labels':<33}"
    for r in reports:
        val = r["label_distribution"]["total_unique_labels"]
        row += f"{val:>{col_width}}"
    print(row)

    # --- Relationship Type Distribution ---
    print(f"\n  --- RELATIONSHIP TYPE DIVERSITY ---")
    row = f"  {'Unique rel types':<33}"
    for r in reports:
        val = r["relationship_type_distribution"]["total_unique_rel_types"]
        row += f"{val:>{col_width}}"
    print(row)

    # --- Queries per hour estimate ---
    print(f"\n  --- THROUGHPUT ---")
    row = f"  {'Queries generated':<33}"
    for r in reports:
        val = r["summary"]["total_match_queries"]
        row += f"{val:>{col_width}}"
    print(row)

    print("\n" + "=" * (35 + col_width * len(versions)))

    # --- Key findings ---
    print(f"\n  --- KEY FINDINGS ---")

    # Check if complexity is similar across versions
    mean_conditions = [r["query_complexity_stats"]["total_conditions"]["mean"] for r in reports]
    if len(set(round(v, 0) for v in mean_conditions)) == 1:
        print("  [=] Query condition complexity is SIMILAR across versions")
    else:
        max_c = max(mean_conditions)
        min_c = min(mean_conditions)
        diff_pct = ((max_c - min_c) / max(min_c, 1)) * 100
        if diff_pct > 20:
            print(f"  [!] Query condition complexity DIFFERS by {diff_pct:.0f}% across versions")
            print(f"      This suggests GQS may generate version-dependent queries")
        else:
            print(f"  [~] Query condition complexity varies by {diff_pct:.0f}% (minor)")

    mean_nodes = [r["query_complexity_stats"]["unique_nodes"]["mean"] for r in reports]
    max_n = max(mean_nodes)
    min_n = min(mean_nodes)
    diff_pct = ((max_n - min_n) / max(min_n, 1)) * 100
    if diff_pct > 20:
        print(f"  [!] Graph pattern size DIFFERS by {diff_pct:.0f}% across versions")
    else:
        print(f"  [~] Graph pattern size varies by {diff_pct:.0f}% (minor)")

    # Bug detection comparison
    bugs = [r["summary"]["total_bugs_found"] for r in reports]
    if any(b > 0 for b in bugs):
        print(f"  [*] Bugs found: {', '.join(f'v{v}: {b}' for v, b in zip(versions, bugs))}")
        logic_bugs = [r["summary"]["logic_bugs_found"] for r in reports]
        if any(lb > 0 for lb in logic_bugs):
            print(f"  [*] LOGIC BUGS found: {', '.join(f'v{v}: {lb}' for v, lb in zip(versions, logic_bugs))}")
    else:
        print(f"  [-] No bugs found on any version (expected for short runs)")

    print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_versions.py <report1.json> <report2.json> [report3.json ...]")
        print("Example: python compare_versions.py gqs_analysis_5_20_0.json gqs_analysis_4_4_0.json")
        sys.exit(1)

    filepaths = sys.argv[1:]
    for fp in filepaths:
        if not os.path.isfile(fp):
            print(f"Error: {fp} not found")
            sys.exit(1)

    reports = load_reports(filepaths)
    print_comparison(reports)


if __name__ == "__main__":
    main()
