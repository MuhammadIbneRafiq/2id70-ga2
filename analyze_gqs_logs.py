"""
GQS Log Analyzer - Cross-Version Neo4j Comparison
===================================================
Extracts query complexity metrics from GQS log files.
Each team member runs GQS on a different Neo4j version,
then runs this script to produce comparable metrics.

Usage:
    python analyze_gqs_logs.py <log_directory> [--neo4j-version <version>]

Example:
    python analyze_gqs_logs.py GQS/logs/6/neo4j --neo4j-version 5.20.0
"""

import os
import re
import sys
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def parse_queries_from_log(filepath):
    """Parse a GQS log file and extract individual queries and metadata."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.split("\n")

    metadata = {}
    queries = []
    schema_statements = []
    bug_reports = []
    current_query = []

    for line in lines:
        # Extract metadata
        if line.startswith("-- Time:"):
            metadata["time"] = line.replace("-- Time:", "").strip()
        elif line.startswith("-- Database:"):
            metadata["database"] = line.replace("-- Database:", "").strip()
        elif line.startswith("-- seed value:"):
            metadata["seed"] = line.replace("-- seed value:", "").strip()

        # Bug report lines
        elif line.startswith("--org.example.gqs.exceptions.ResultMismatchException"):
            bug_reports.append({"type": "ResultMismatchException", "detail": line})
        elif "--DatabaseCrashed:" in line:
            bug_reports.append({"type": "DatabaseCrashed", "detail": line})
        elif "The contents of the result sets mismatch" in line:
            bug_reports.append({"type": "LogicBug", "detail": line})
        elif "Computed Result:" in line:
            bug_reports.append({"type": "ComputedResult", "detail": line})
        elif "Executed Result:" in line:
            bug_reports.append({"type": "ExecutedResult", "detail": line})

        # Schema statements
        elif line.startswith("CREATE CONSTRAINT"):
            schema_statements.append({"type": "constraint", "statement": line})
        elif line.startswith("CREATE INDEX") or line.startswith("CREATE TEXT INDEX"):
            schema_statements.append({"type": "index", "statement": line})

        # Query lines (MATCH, OPTIONAL MATCH, or continuation)
        elif line.startswith("MATCH ") or line.startswith("OPTIONAL MATCH "):
            # If we had a previous query building, save it
            if current_query:
                queries.append(" ".join(current_query))
            current_query = [line]
        elif line.startswith("CREATE ("):
            if current_query:
                queries.append(" ".join(current_query))
                current_query = []
            queries.append(line)  # Node/relationship creation
        elif current_query and line and not line.startswith("--") and not line.startswith("CREATE "):
            current_query.append(line)

    if current_query:
        queries.append(" ".join(current_query))

    return metadata, queries, schema_statements, bug_reports


def analyze_query(query):
    """Extract complexity metrics from a single Cypher query."""
    metrics = {}

    # Query length
    metrics["length_chars"] = len(query)

    # Clause counts
    metrics["match_clauses"] = len(re.findall(r'\bMATCH\b', query))
    metrics["optional_match"] = len(re.findall(r'\bOPTIONAL MATCH\b', query))
    metrics["with_clauses"] = len(re.findall(r'\bWITH\b', query))
    metrics["unwind_clauses"] = len(re.findall(r'\bUNWIND\b', query))
    metrics["return_clauses"] = len(re.findall(r'\bRETURN\b', query))
    metrics["where_clauses"] = len(re.findall(r'\bWHERE\b', query))
    metrics["order_by"] = len(re.findall(r'\bORDER BY\b', query))
    metrics["limit_clauses"] = len(re.findall(r'\bLIMIT\b', query))
    metrics["skip_clauses"] = len(re.findall(r'\bSKIP\b', query))
    metrics["distinct"] = len(re.findall(r'\bDISTINCT\b', query))

    # Pattern complexity
    # Count node patterns like (n0 :L0{...})
    node_patterns = re.findall(r'\(n\d+', query)
    metrics["node_refs"] = len(node_patterns)
    metrics["unique_nodes"] = len(set(node_patterns))

    # Count relationship patterns like [r0 :T10]
    rel_patterns = re.findall(r'\[r\d+', query)
    metrics["relationship_refs"] = len(rel_patterns)
    metrics["unique_relationships"] = len(set(rel_patterns))

    # Label usage
    labels = re.findall(r':L(\d+)', query)
    metrics["label_refs"] = len(labels)
    metrics["unique_labels"] = len(set(labels))

    # Relationship type usage
    rel_types = re.findall(r':T(\d+)', query)
    metrics["rel_type_refs"] = len(rel_types)
    metrics["unique_rel_types"] = len(set(rel_types))

    # Property key usage
    prop_keys = re.findall(r'\b(k\d+)\b', query)
    metrics["property_refs"] = len(prop_keys)
    metrics["unique_properties"] = len(set(prop_keys))

    # WHERE condition complexity
    and_count = len(re.findall(r'\bAND\b', query))
    or_count = len(re.findall(r'\bOR\b', query))
    not_count = len(re.findall(r'\bNOT\b', query))
    metrics["and_conditions"] = and_count
    metrics["or_conditions"] = or_count
    metrics["not_conditions"] = not_count
    metrics["total_conditions"] = and_count + or_count + not_count

    # String operations
    metrics["contains_ops"] = len(re.findall(r'\bCONTAINS\b', query))
    metrics["starts_with_ops"] = len(re.findall(r'\bSTARTS WITH\b', query))
    metrics["ends_with_ops"] = len(re.findall(r'\bENDS WITH\b', query))
    metrics["string_ops_total"] = metrics["contains_ops"] + metrics["starts_with_ops"] + metrics["ends_with_ops"]

    # Aggregation functions
    metrics["count_agg"] = len(re.findall(r'\bcount\(', query))
    metrics["sum_agg"] = len(re.findall(r'\bsum\(', query))
    metrics["avg_agg"] = len(re.findall(r'\bavg\(', query))
    metrics["min_agg"] = len(re.findall(r'\bmin\(', query))
    metrics["max_agg"] = len(re.findall(r'\bmax\(', query))
    metrics["collect_agg"] = len(re.findall(r'\bcollect\(', query))
    metrics["aggregations_total"] = sum([
        metrics["count_agg"], metrics["sum_agg"], metrics["avg_agg"],
        metrics["min_agg"], metrics["max_agg"], metrics["collect_agg"]
    ])

    # Built-in functions
    metrics["toInteger"] = len(re.findall(r'\btoInteger\(', query))
    metrics["toBoolean"] = len(re.findall(r'\btoBoolean\(', query))
    metrics["toUpper"] = len(re.findall(r'\btoUpper\(', query))
    metrics["toLower"] = len(re.findall(r'\btoLower\(', query))
    metrics["trim_funcs"] = len(re.findall(r'\b[lr]?Trim\(', query))

    # Estimate graph pattern depth (max relationship chain)
    # Count consecutive relationship patterns
    chains = re.findall(r'(\[r\d+[^\]]*\])', query)
    metrics["max_pattern_depth"] = len(chains)

    # Is it a CREATE query (data insertion) vs MATCH query (read)
    metrics["is_create"] = query.strip().startswith("CREATE (")
    metrics["is_match"] = query.strip().startswith("MATCH") or query.strip().startswith("OPTIONAL MATCH")

    return metrics


def compute_summary_stats(values, name=""):
    """Compute summary statistics for a list of numeric values."""
    if not values:
        return {"count": 0, "mean": 0, "median": 0, "std": 0, "min": 0, "max": 0, "p25": 0, "p75": 0}

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        "count": n,
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "std": round(statistics.stdev(values), 2) if n > 1 else 0,
        "min": min(values),
        "max": max(values),
        "p25": sorted_vals[n // 4] if n >= 4 else sorted_vals[0],
        "p75": sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1],
    }


def analyze_log_directory(log_dir, neo4j_version="unknown"):
    """Analyze all GQS logs in a directory and produce a report."""
    log_dir = Path(log_dir)
    log_files = list(log_dir.glob("*.log"))

    if not log_files:
        print(f"No .log files found in {log_dir}")
        return None

    all_queries = []
    all_schema = []
    all_bugs = []
    all_metadata = []
    file_stats = []

    for lf in log_files:
        metadata, queries, schema, bugs = parse_queries_from_log(lf)
        metadata["filename"] = lf.name
        metadata["filesize_bytes"] = lf.stat().st_size
        all_metadata.append(metadata)
        all_queries.extend(queries)
        all_schema.extend(schema)
        all_bugs.extend(bugs)
        file_stats.append({
            "file": lf.name,
            "queries": len(queries),
            "schema_stmts": len(schema),
            "bugs": len(bugs),
            "size_kb": round(lf.stat().st_size / 1024, 1),
        })

    # Analyze each query
    match_queries = [q for q in all_queries if q.strip().startswith("MATCH") or q.strip().startswith("OPTIONAL MATCH")]
    create_queries = [q for q in all_queries if q.strip().startswith("CREATE (")]

    query_metrics = [analyze_query(q) for q in match_queries]

    # Aggregate metrics
    metric_keys = [
        "length_chars", "match_clauses", "optional_match", "with_clauses",
        "unwind_clauses", "where_clauses", "unique_nodes", "unique_relationships",
        "unique_labels", "unique_rel_types", "unique_properties",
        "and_conditions", "or_conditions", "not_conditions", "total_conditions",
        "string_ops_total", "aggregations_total", "order_by", "limit_clauses",
        "skip_clauses", "distinct",
    ]

    aggregated = {}
    for key in metric_keys:
        values = [m[key] for m in query_metrics]
        aggregated[key] = compute_summary_stats(values, key)

    # Schema analysis
    constraint_count = len([s for s in all_schema if s["type"] == "constraint"])
    index_count = len([s for s in all_schema if s["type"] == "index"])

    # Bug analysis
    bug_types = Counter(b["type"] for b in all_bugs)
    has_logic_bugs = bug_types.get("LogicBug", 0) > 0
    has_crashes = bug_types.get("DatabaseCrashed", 0) > 0
    has_syntax_errors = any("Invalid input" in b["detail"] for b in all_bugs)

    # Property key distribution (for frequency-based selection analysis)
    all_props = []
    for q in match_queries:
        all_props.extend(re.findall(r'\b(k\d+)\b', q))
    prop_freq = Counter(all_props)
    top_20_props = prop_freq.most_common(20)

    # Label distribution
    all_labels = []
    for q in match_queries:
        all_labels.extend(re.findall(r':L(\d+)', q))
    label_freq = Counter(all_labels)

    # Relationship type distribution
    all_rel_types = []
    for q in match_queries:
        all_rel_types.extend(re.findall(r':T(\d+)', q))
    rel_type_freq = Counter(all_rel_types)

    report = {
        "neo4j_version": neo4j_version,
        "log_directory": str(log_dir),
        "summary": {
            "total_log_files": len(log_files),
            "total_match_queries": len(match_queries),
            "total_create_queries": len(create_queries),
            "total_schema_statements": len(all_schema),
            "constraints_created": constraint_count,
            "indexes_created": index_count,
            "total_bugs_found": len(all_bugs),
            "logic_bugs_found": bug_types.get("LogicBug", 0),
            "database_crashes": bug_types.get("DatabaseCrashed", 0),
            "has_syntax_errors": has_syntax_errors,
        },
        "file_breakdown": file_stats,
        "query_complexity_stats": aggregated,
        "property_key_distribution": {
            "total_unique_properties": len(prop_freq),
            "top_20_most_used": [{"key": k, "count": c} for k, c in top_20_props],
        },
        "label_distribution": {
            "total_unique_labels": len(label_freq),
            "frequencies": dict(label_freq.most_common()),
        },
        "relationship_type_distribution": {
            "total_unique_rel_types": len(rel_type_freq),
            "frequencies": dict(rel_type_freq.most_common()),
        },
        "bug_analysis": {
            "bug_type_counts": dict(bug_types),
            "has_logic_bugs": has_logic_bugs,
            "has_crashes": has_crashes,
            "has_syntax_errors": has_syntax_errors,
        },
    }

    return report


def print_report(report):
    """Pretty-print the analysis report."""
    print("=" * 70)
    print(f"  GQS LOG ANALYSIS REPORT - Neo4j {report['neo4j_version']}")
    print("=" * 70)

    s = report["summary"]
    print(f"\n--- OVERVIEW ---")
    print(f"  Log files analyzed:      {s['total_log_files']}")
    print(f"  Total MATCH queries:     {s['total_match_queries']}")
    print(f"  Total CREATE queries:    {s['total_create_queries']}")
    print(f"  Schema statements:       {s['total_schema_statements']}")
    print(f"    Constraints:           {s['constraints_created']}")
    print(f"    Indexes:               {s['indexes_created']}")
    print(f"  Bugs found:              {s['total_bugs_found']}")
    print(f"    Logic bugs:            {s['logic_bugs_found']}")
    print(f"    Database crashes:      {s['database_crashes']}")
    print(f"    Syntax errors:         {s['has_syntax_errors']}")

    print(f"\n--- FILE BREAKDOWN ---")
    for fs in report["file_breakdown"]:
        print(f"  {fs['file']}: {fs['queries']} queries, {fs['schema_stmts']} schema stmts, {fs['bugs']} bugs, {fs['size_kb']} KB")

    print(f"\n--- QUERY COMPLEXITY STATISTICS ---")
    print(f"  {'Metric':<30} {'Mean':>8} {'Median':>8} {'Std':>8} {'Min':>6} {'Max':>6} {'P25':>6} {'P75':>6}")
    print(f"  {'-'*28:<30} {'-'*8:>8} {'-'*8:>8} {'-'*8:>8} {'-'*6:>6} {'-'*6:>6} {'-'*6:>6} {'-'*6:>6}")
    for key, stats in report["query_complexity_stats"].items():
        label = key.replace("_", " ").title()
        print(f"  {label:<30} {stats['mean']:>8.1f} {stats['median']:>8.1f} {stats['std']:>8.1f} {stats['min']:>6} {stats['max']:>6} {stats['p25']:>6} {stats['p75']:>6}")

    print(f"\n--- PROPERTY KEY DISTRIBUTION ---")
    print(f"  Total unique properties: {report['property_key_distribution']['total_unique_properties']}")
    print(f"  Top 10 most used:")
    for item in report["property_key_distribution"]["top_20_most_used"][:10]:
        print(f"    {item['key']}: {item['count']} uses")

    print(f"\n--- LABEL DISTRIBUTION ---")
    print(f"  Total unique labels: {report['label_distribution']['total_unique_labels']}")
    for label, count in sorted(report["label_distribution"]["frequencies"].items(), key=lambda x: -x[1]):
        print(f"    L{label}: {count} uses")

    print(f"\n--- RELATIONSHIP TYPE DISTRIBUTION ---")
    print(f"  Total unique rel types: {report['relationship_type_distribution']['total_unique_rel_types']}")
    for rt, count in sorted(report["relationship_type_distribution"]["frequencies"].items(), key=lambda x: -x[1])[:15]:
        print(f"    T{rt}: {count} uses")

    print(f"\n--- BUG ANALYSIS ---")
    for bt, count in report["bug_analysis"]["bug_type_counts"].items():
        print(f"  {bt}: {count}")
    if not report["bug_analysis"]["bug_type_counts"]:
        print("  No bugs detected.")

    print("\n" + "=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_gqs_logs.py <log_directory> [--neo4j-version <version>]")
        print("Example: python analyze_gqs_logs.py GQS/logs/6/neo4j --neo4j-version 5.20.0")
        sys.exit(1)

    log_dir = sys.argv[1]
    neo4j_version = "unknown"

    for i, arg in enumerate(sys.argv):
        if arg == "--neo4j-version" and i + 1 < len(sys.argv):
            neo4j_version = sys.argv[i + 1]

    if not os.path.isdir(log_dir):
        print(f"Error: {log_dir} is not a valid directory")
        sys.exit(1)

    report = analyze_log_directory(log_dir, neo4j_version)

    if report:
        print_report(report)

        # Save JSON report for cross-version comparison
        json_path = os.path.join(log_dir, f"gqs_analysis_{neo4j_version.replace('.', '_')}.json")
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nJSON report saved to: {json_path}")
        print("Share this JSON file with your team for cross-version comparison!")


if __name__ == "__main__":
    main()
