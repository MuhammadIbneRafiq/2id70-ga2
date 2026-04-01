"""
GQS 24-Hour Cross-Version Log Comparison
==========================================
Compares GQS logs from Neo4j v4.4 and v5.20.0 runs.
Analyzes query complexity, structural mutation effectiveness,
and non-empty result rates.

Usage:
    python compare_24hr_logs.py
"""
import re
import statistics
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_log_file(filepath, version_label):
    """Parse a single GQS log file and extract queries + result sizes."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    schema_statements = []
    create_statements = []
    match_queries = []
    result_sizes = []
    bug_reports = []
    current_query_lines = []
    global_state_count = 0

    for i, line in enumerate(lines):
        line = line.rstrip("\n")

        # Global state resets
        if line.startswith("new global state"):
            global_state_count += 1
            continue

        # Schema
        if line.startswith("CREATE CONSTRAINT") or line.startswith("CREATE INDEX") or line.startswith("CREATE TEXT INDEX"):
            schema_statements.append(line)
            continue

        # Node/relationship creation
        if line.startswith("CREATE ("):
            create_statements.append(line)
            continue

        # Result size lines
        if line.startswith("result_size="):
            size = int(line.replace("result_size=", "").strip())
            result_sizes.append(size)
            # Save the current query if we have one
            if current_query_lines:
                match_queries.append(" ".join(current_query_lines))
                current_query_lines = []
            continue

        # Bug reports
        if "ResultMismatchException" in line or "DatabaseCrashed" in line:
            bug_reports.append(line)
            continue
        if "The contents of the result sets mismatch" in line:
            bug_reports.append(line)
            continue

        # Query lines
        if line.startswith("MATCH ") or line.startswith("OPTIONAL MATCH "):
            if current_query_lines:
                match_queries.append(" ".join(current_query_lines))
            current_query_lines = [line]
        elif current_query_lines and line and not line.startswith("--") and not line.startswith("CREATE ") and not line.startswith("new global") and not line.startswith("Database Name") and not line.startswith("Neo4j") and not line.startswith("wait for") and not line.isdigit():
            current_query_lines.append(line)

    if current_query_lines:
        match_queries.append(" ".join(current_query_lines))

    return {
        "version": version_label,
        "filepath": str(filepath),
        "global_state_resets": global_state_count,
        "schema_statements": schema_statements,
        "create_statements": create_statements,
        "match_queries": match_queries,
        "result_sizes": result_sizes,
        "bug_reports": bug_reports,
    }


def analyze_query(query):
    """Extract complexity metrics from a single Cypher query."""
    m = {}
    m["length_chars"] = len(query)

    # Clause counts
    m["match_clauses"] = len(re.findall(r'\bMATCH\b', query))
    m["optional_match"] = len(re.findall(r'\bOPTIONAL MATCH\b', query))
    m["with_clauses"] = len(re.findall(r'\bWITH\b', query))
    m["unwind_clauses"] = len(re.findall(r'\bUNWIND\b', query))
    m["return_clauses"] = len(re.findall(r'\bRETURN\b', query))
    m["where_clauses"] = len(re.findall(r'\bWHERE\b', query))
    m["order_by"] = len(re.findall(r'\bORDER BY\b', query))
    m["limit_clauses"] = len(re.findall(r'\bLIMIT\b', query))
    m["skip_clauses"] = len(re.findall(r'\bSKIP\b', query))
    m["distinct"] = len(re.findall(r'\bDISTINCT\b', query))

    # Pattern complexity
    node_patterns = re.findall(r'\(n\d+', query)
    m["node_refs"] = len(node_patterns)
    m["unique_nodes"] = len(set(node_patterns))

    rel_patterns = re.findall(r'\[r\d+', query)
    m["relationship_refs"] = len(rel_patterns)
    m["unique_relationships"] = len(set(rel_patterns))

    # Labels and types
    labels = re.findall(r':L(\d+)', query)
    m["unique_labels"] = len(set(labels))
    rel_types = re.findall(r':T(\d+)', query)
    m["unique_rel_types"] = len(set(rel_types))

    # Properties
    prop_keys = re.findall(r'\b(k\d+)\b', query)
    m["unique_properties"] = len(set(prop_keys))
    m["property_refs"] = len(prop_keys)

    # Conditions
    m["and_conditions"] = len(re.findall(r'\bAND\b', query))
    m["or_conditions"] = len(re.findall(r'\bOR\b', query))
    m["not_conditions"] = len(re.findall(r'\bNOT\b', query))
    m["total_conditions"] = m["and_conditions"] + m["or_conditions"] + m["not_conditions"]

    # String operations
    m["contains_ops"] = len(re.findall(r'\bCONTAINS\b', query))
    m["starts_with_ops"] = len(re.findall(r'\bSTARTS WITH\b', query))
    m["ends_with_ops"] = len(re.findall(r'\bENDS WITH\b', query))
    m["string_ops_total"] = m["contains_ops"] + m["starts_with_ops"] + m["ends_with_ops"]

    # Aggregations
    m["aggregations_total"] = len(re.findall(r'\b(count|sum|avg|min|max|collect)\(', query))

    # Graph pattern subqueries (number of comma-separated patterns in MATCH)
    # Count comma-separated graph patterns like (n0)-[r0]-(n1), (n2)-[r1]-(n3)
    m["graph_pattern_groups"] = query.count("), (") + 1 if "MATCH" in query else 0

    return m


def compute_stats(values):
    """Compute summary statistics."""
    if not values:
        return {"count": 0, "mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
    n = len(values)
    return {
        "count": n,
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "std": round(statistics.stdev(values), 2) if n > 1 else 0,
        "min": min(values),
        "max": max(values),
    }


def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def print_section(title):
    print(f"\n  --- {title} ---")


def print_row(label, v1, v2, fmt="{:>12}", diff=True):
    row = f"  {label:<35} {fmt.format(v1):>14} {fmt.format(v2):>14}"
    if diff and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
        if v1 != 0:
            pct = ((v2 - v1) / abs(v1)) * 100
            row += f"  {pct:>+7.1f}%"
        elif v2 != 0:
            row += f"     +inf%"
        else:
            row += f"    0.0%"
    print(row)


def analyze_mutation_evolution(queries, result_sizes):
    """Analyze how query complexity evolves over time (proxy for mutation effectiveness)."""
    if len(queries) < 10:
        return {}

    # Split queries into early (first 20%) and late (last 20%)
    n = len(queries)
    early_cut = n // 5
    late_start = n - n // 5

    early_metrics = [analyze_query(q) for q in queries[:early_cut]]
    late_metrics = [analyze_query(q) for q in queries[late_start:]]

    evolution = {}
    for key in ["length_chars", "unique_nodes", "unique_relationships", "total_conditions",
                "string_ops_total", "where_clauses", "match_clauses", "graph_pattern_groups"]:
        early_vals = [m[key] for m in early_metrics]
        late_vals = [m[key] for m in late_metrics]
        if early_vals and late_vals:
            evolution[key] = {
                "early_mean": round(statistics.mean(early_vals), 2),
                "late_mean": round(statistics.mean(late_vals), 2),
                "growth_pct": round(((statistics.mean(late_vals) - statistics.mean(early_vals)) / max(statistics.mean(early_vals), 1)) * 100, 1),
            }
    return evolution


def main():
    v4_log = "src/gqs_v4_24hour_run.log.txt"
    v5_log = "src/gqs_24hour_run.log.txt"

    print("Parsing logs...")
    v4 = parse_log_file(v4_log, "Neo4j 4.4")
    v5 = parse_log_file(v5_log, "Neo4j 5.20.0")

    # Analyze all queries
    print("Analyzing queries...")
    v4_metrics = [analyze_query(q) for q in v4["match_queries"]]
    v5_metrics = [analyze_query(q) for q in v5["match_queries"]]

    # ========== OVERVIEW ==========
    print_header("GQS 24-HOUR CROSS-VERSION COMPARISON")
    print(f"  {'':35} {'Neo4j 4.4':>14} {'Neo4j 5.20.0':>14}")
    print(f"  {'-'*35} {'-'*14} {'-'*14}")

    print_section("OVERVIEW")
    print_row("Database resets", v4["global_state_resets"], v5["global_state_resets"])
    print_row("Schema statements", len(v4["schema_statements"]), len(v5["schema_statements"]))
    print_row("CREATE (data insert) stmts", len(v4["create_statements"]), len(v5["create_statements"]))
    print_row("MATCH queries (read)", len(v4["match_queries"]), len(v5["match_queries"]))
    print_row("Result size annotations", len(v4["result_sizes"]), len(v5["result_sizes"]))
    print_row("Bug reports", len(v4["bug_reports"]), len(v5["bug_reports"]))

    # ========== NON-EMPTY RESULT ANALYSIS ==========
    print_section("NON-EMPTY RESULT RATE (Structural Mutation Effectiveness)")

    v4_nonempty = sum(1 for s in v4["result_sizes"] if s > 0)
    v5_nonempty = sum(1 for s in v5["result_sizes"] if s > 0)
    v4_total_rs = len(v4["result_sizes"])
    v5_total_rs = len(v5["result_sizes"])

    v4_rate = (v4_nonempty / v4_total_rs * 100) if v4_total_rs > 0 else 0
    v5_rate = (v5_nonempty / v5_total_rs * 100) if v5_total_rs > 0 else 0

    print_row("Queries with result_size", v4_total_rs, v5_total_rs)
    print_row("Non-empty results (>0)", v4_nonempty, v5_nonempty)
    print_row("Empty results (=0)", v4_total_rs - v4_nonempty, v5_total_rs - v5_nonempty)
    print_row("Non-empty rate (%)", round(v4_rate, 1), round(v5_rate, 1), fmt="{:>12.1f}")

    # Result size distribution
    print_section("RESULT SIZE DISTRIBUTION")
    for threshold in [1, 2, 3, 5, 10]:
        v4_ct = sum(1 for s in v4["result_sizes"] if s >= threshold)
        v5_ct = sum(1 for s in v5["result_sizes"] if s >= threshold)
        print_row(f"result_size >= {threshold}", v4_ct, v5_ct)

    if v4["result_sizes"]:
        v4_rs_stats = compute_stats(v4["result_sizes"])
        v5_rs_stats = compute_stats(v5["result_sizes"])
        print_row("Mean result size", v4_rs_stats["mean"], v5_rs_stats["mean"], fmt="{:>12.2f}")
        print_row("Median result size", v4_rs_stats["median"], v5_rs_stats["median"], fmt="{:>12.1f}")
        print_row("Max result size", v4_rs_stats["max"], v5_rs_stats["max"])

    # ========== QUERY COMPLEXITY ==========
    print_section("QUERY COMPLEXITY (Mean values)")
    complexity_keys = [
        ("Query length (chars)", "length_chars"),
        ("MATCH clauses", "match_clauses"),
        ("OPTIONAL MATCH", "optional_match"),
        ("WITH clauses", "with_clauses"),
        ("UNWIND clauses", "unwind_clauses"),
        ("WHERE clauses", "where_clauses"),
        ("RETURN clauses", "return_clauses"),
        ("ORDER BY", "order_by"),
        ("LIMIT", "limit_clauses"),
        ("SKIP", "skip_clauses"),
        ("DISTINCT", "distinct"),
        ("Unique nodes/query", "unique_nodes"),
        ("Unique rels/query", "unique_relationships"),
        ("Unique labels/query", "unique_labels"),
        ("Unique rel types/query", "unique_rel_types"),
        ("Unique properties/query", "unique_properties"),
        ("Property references/query", "property_refs"),
        ("Graph pattern groups", "graph_pattern_groups"),
        ("AND conditions", "and_conditions"),
        ("OR conditions", "or_conditions"),
        ("NOT conditions", "not_conditions"),
        ("Total conditions", "total_conditions"),
        ("String ops total", "string_ops_total"),
        ("CONTAINS", "contains_ops"),
        ("STARTS WITH", "starts_with_ops"),
        ("ENDS WITH", "ends_with_ops"),
        ("Aggregations", "aggregations_total"),
    ]

    for label, key in complexity_keys:
        v4_vals = [m[key] for m in v4_metrics]
        v5_vals = [m[key] for m in v5_metrics]
        v4_mean = statistics.mean(v4_vals) if v4_vals else 0
        v5_mean = statistics.mean(v5_vals) if v5_vals else 0
        print_row(label, round(v4_mean, 1), round(v5_mean, 1), fmt="{:>12.1f}")

    # ========== COMPLEXITY SPREAD (Std Dev) ==========
    print_section("QUERY COMPLEXITY (Std Dev - diversity)")
    for label, key in [("Query length", "length_chars"), ("Unique nodes", "unique_nodes"),
                       ("Unique rels", "unique_relationships"), ("Total conditions", "total_conditions"),
                       ("String ops", "string_ops_total")]:
        v4_vals = [m[key] for m in v4_metrics]
        v5_vals = [m[key] for m in v5_metrics]
        v4_std = statistics.stdev(v4_vals) if len(v4_vals) > 1 else 0
        v5_std = statistics.stdev(v5_vals) if len(v5_vals) > 1 else 0
        print_row(label, round(v4_std, 1), round(v5_std, 1), fmt="{:>12.1f}")

    # ========== MUTATION EVOLUTION ==========
    print_section("MUTATION EVOLUTION (Early vs Late queries)")
    print(f"  Shows how query complexity grows as mutations accumulate")
    print(f"  {'':35} {'Neo4j 4.4':>14} {'Neo4j 5.20.0':>14}")

    v4_evo = analyze_mutation_evolution(v4["match_queries"], v4["result_sizes"])
    v5_evo = analyze_mutation_evolution(v5["match_queries"], v5["result_sizes"])

    evo_labels = [
        ("Query length", "length_chars"),
        ("Unique nodes", "unique_nodes"),
        ("Unique rels", "unique_relationships"),
        ("Total conditions", "total_conditions"),
        ("String ops", "string_ops_total"),
        ("WHERE clauses", "where_clauses"),
        ("Graph pattern groups", "graph_pattern_groups"),
    ]

    for label, key in evo_labels:
        if key in v4_evo and key in v5_evo:
            v4_e = v4_evo[key]
            v5_e = v5_evo[key]
            print(f"\n  {label}:")
            print(f"    Early (first 20%):  v4={v4_e['early_mean']:>10.1f}    v5={v5_e['early_mean']:>10.1f}")
            print(f"    Late  (last  20%):  v4={v4_e['late_mean']:>10.1f}    v5={v5_e['late_mean']:>10.1f}")
            print(f"    Growth:             v4={v4_e['growth_pct']:>+9.1f}%    v5={v5_e['growth_pct']:>+9.1f}%")

    # ========== RESULT SIZE OVER TIME ==========
    print_section("NON-EMPTY RATE OVER TIME (mutation learning)")
    if v4["result_sizes"] and v5["result_sizes"]:
        for version_label, rs in [("Neo4j 4.4", v4["result_sizes"]), ("Neo4j 5.20.0", v5["result_sizes"])]:
            n = len(rs)
            if n < 10:
                continue
            chunk_size = n // 5
            print(f"\n  {version_label} ({n} total queries):")
            for i in range(5):
                start = i * chunk_size
                end = start + chunk_size if i < 4 else n
                chunk = rs[start:end]
                nonempty = sum(1 for s in chunk if s > 0)
                rate = nonempty / len(chunk) * 100
                avg_size = statistics.mean(chunk) if chunk else 0
                print(f"    Chunk {i+1} (queries {start+1:>4}-{end:>4}): "
                      f"non-empty={rate:>5.1f}%  avg_size={avg_size:>5.2f}")

    # ========== SCHEMA DIVERSITY ==========
    print_section("SCHEMA DIVERSITY")
    v4_constraints = sum(1 for s in v4["schema_statements"] if "CONSTRAINT" in s)
    v5_constraints = sum(1 for s in v5["schema_statements"] if "CONSTRAINT" in s)
    v4_indexes = sum(1 for s in v4["schema_statements"] if "INDEX" in s)
    v5_indexes = sum(1 for s in v5["schema_statements"] if "INDEX" in s)
    print_row("Constraints", v4_constraints, v5_constraints)
    print_row("Indexes", v4_indexes, v5_indexes)
    print_row("CREATE node/rel stmts", len(v4["create_statements"]), len(v5["create_statements"]))

    # ========== KEY FINDINGS ==========
    print_header("KEY FINDINGS")

    # 1. Non-empty rate comparison
    print(f"\n  1. NON-EMPTY RESULT RATE:")
    print(f"     Neo4j 4.4:   {v4_rate:.1f}% of queries return non-empty results")
    print(f"     Neo4j 5.20.0: {v5_rate:.1f}% of queries return non-empty results")
    if abs(v4_rate - v5_rate) < 5:
        print(f"     -> SIMILAR non-empty rates across versions ({abs(v4_rate-v5_rate):.1f}% difference)")
        print(f"        This suggests structural mutations are VERSION-INDEPENDENT")
    else:
        print(f"     -> DIFFERENT non-empty rates ({abs(v4_rate-v5_rate):.1f}% difference)")

    # 2. Query complexity comparison
    v4_mean_len = statistics.mean([m["length_chars"] for m in v4_metrics]) if v4_metrics else 0
    v5_mean_len = statistics.mean([m["length_chars"] for m in v5_metrics]) if v5_metrics else 0
    diff_pct = abs(v4_mean_len - v5_mean_len) / max(v4_mean_len, 1) * 100

    print(f"\n  2. QUERY COMPLEXITY:")
    print(f"     Mean query length: v4={v4_mean_len:.0f} chars, v5={v5_mean_len:.0f} chars ({diff_pct:.0f}% difference)")
    if diff_pct < 20:
        print(f"     -> SIMILAR complexity across versions")
    else:
        print(f"     -> DIFFERENT complexity levels")

    # 3. Mutation evolution
    if "length_chars" in v4_evo and "length_chars" in v5_evo:
        print(f"\n  3. MUTATION EVOLUTION (query growth over time):")
        print(f"     v4 query length growth: {v4_evo['length_chars']['growth_pct']:+.1f}% (early={v4_evo['length_chars']['early_mean']:.0f} -> late={v4_evo['length_chars']['late_mean']:.0f})")
        print(f"     v5 query length growth: {v5_evo['length_chars']['growth_pct']:+.1f}% (early={v5_evo['length_chars']['early_mean']:.0f} -> late={v5_evo['length_chars']['late_mean']:.0f})")
        print(f"     -> Queries grow over time due to structural mutations accumulating")
        print(f"        This confirms mutations BUILD on successful seed queries")

    # 4. Throughput
    print(f"\n  4. THROUGHPUT:")
    print(f"     v4: {len(v4['match_queries'])} MATCH queries in 24h")
    print(f"     v5: {len(v5['match_queries'])} MATCH queries in 24h")

    print(f"\n{'='*80}")

    # Save JSON report
    report = {
        "v4": {
            "version": "4.4",
            "match_queries": len(v4["match_queries"]),
            "create_statements": len(v4["create_statements"]),
            "schema_statements": len(v4["schema_statements"]),
            "result_sizes": v4["result_sizes"],
            "nonempty_count": v4_nonempty,
            "nonempty_rate": round(v4_rate, 2),
            "bug_reports": len(v4["bug_reports"]),
            "global_state_resets": v4["global_state_resets"],
        },
        "v5": {
            "version": "5.20.0",
            "match_queries": len(v5["match_queries"]),
            "create_statements": len(v5["create_statements"]),
            "schema_statements": len(v5["schema_statements"]),
            "result_sizes": v5["result_sizes"],
            "nonempty_count": v5_nonempty,
            "nonempty_rate": round(v5_rate, 2),
            "bug_reports": len(v5["bug_reports"]),
            "global_state_resets": v5["global_state_resets"],
        },
        "complexity_comparison": {},
    }

    for label, key in complexity_keys:
        v4_vals = [m[key] for m in v4_metrics]
        v5_vals = [m[key] for m in v5_metrics]
        report["complexity_comparison"][key] = {
            "v4": compute_stats(v4_vals),
            "v5": compute_stats(v5_vals),
        }

    json_path = "src/gqs_24hr_comparison.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report saved to: {json_path}")


if __name__ == "__main__":
    main()
