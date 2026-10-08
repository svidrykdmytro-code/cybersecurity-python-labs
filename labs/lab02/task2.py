import argparse
import csv
import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_RULES = DATA_DIR / "firewall_rules.json"
DEFAULT_REPORT = DATA_DIR / "fw_audit_report.json"
DEFAULT_CLEAN = DATA_DIR / "firewall_rules_clean.json"
DEFAULT_AUDIT_LOG = DATA_DIR / "fw_audit.log"

VALID_ACTIONS = {"ALLOW", "DENY"}
ANY_PORT = "ANY"
ANY_ADDRESSES = {"0.0.0.0/0", "ANY"}
OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IP_PATTERN = re.compile(rf"^{OCTET}(?:\.{OCTET}){{3}}$")
CIDR_PATTERN = re.compile(rf"^{OCTET}(?:\.{OCTET}){{3}}/(?:3[0-2]|[12]?\d)$")
PORT_PATTERN = re.compile(r"^\d{1,5}$")
RISKY_PORTS = {
    "21": "FTP",
    "22": "SSH",
    "23": "Telnet",
    "445": "SMB",
    "1433": "MSSQL",
    "3306": "MySQL",
    "3389": "RDP",
    "5432": "PostgreSQL",
}
REQUIRED_FIELDS = ("id", "source", "destination", "port", "action")

logger = logging.getLogger("fw_audit")


@dataclass
class FirewallRule:
    id: int
    source: str
    destination: str
    port: str
    action: str
    errors: list[str] = field(default_factory=list, compare=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "FirewallRule":
        missing = [name for name in REQUIRED_FIELDS if name not in raw]
        if missing:
            raise ValueError(f"missing fields {missing}")
        try:
            rule_id = int(raw["id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid id {raw['id']!r}") from exc
        return cls(
            id=rule_id,
            source=str(raw["source"]).strip(),
            destination=str(raw["destination"]).strip(),
            port=str(raw["port"]).strip().upper(),
            action=str(raw["action"]).strip().upper(),
        )

    @property
    def key(self) -> tuple[str, str, str]:
        return (
            normalize_address(self.source),
            normalize_address(self.destination),
            self.port,
        )

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def describe(self) -> str:
        return (
            f"{self.action} {display_address(self.source)} -> "
            f"{display_address(self.destination)}:{display_port(self.port)}"
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("errors")
        return data


@dataclass
class Finding:
    category: str
    rule_ids: list[int]
    message: str


@dataclass
class AuditResult:
    total: int = 0
    invalid: list[FirewallRule] = field(default_factory=list)
    duplicates: list[Finding] = field(default_factory=list)
    conflicts: list[Finding] = field(default_factory=list)
    high_risk: list[Finding] = field(default_factory=list)
    clean_rules: list[FirewallRule] = field(default_factory=list)


def normalize_address(value: str) -> str:
    upper = value.upper()
    if upper in ANY_ADDRESSES:
        return "ANY"
    if IP_PATTERN.fullmatch(value):
        return f"{value}/32"
    return value


def display_address(value: str) -> str:
    return "Any" if value.upper() in ANY_ADDRESSES else value


def display_port(value: str) -> str:
    return "ANY" if value == ANY_PORT else value


def is_valid_address(value: str) -> bool:
    return (
        value.upper() in ANY_ADDRESSES
        or bool(IP_PATTERN.fullmatch(value))
        or bool(CIDR_PATTERN.fullmatch(value))
    )


def is_valid_port(value: str) -> bool:
    if value == ANY_PORT:
        return True
    return bool(PORT_PATTERN.fullmatch(value)) and 1 <= int(value) <= 65535


def short_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def load_raw_rules(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Rules file not found: {path}")
    suffix = path.suffix.lower()
    with path.open(encoding="utf-8", newline="") as handle:
        if suffix == ".json":
            data = json.load(handle)
            if isinstance(data, dict) and "rules" in data:
                data = data["rules"]
            if not isinstance(data, list):
                raise ValueError("JSON root must be a list of rules")
            return data
        if suffix == ".csv":
            reader = csv.DictReader(handle)
            return [
                {key.strip().lower(): value for key, value in row.items() if key}
                for row in reader
            ]
    raise ValueError(f"Unsupported file format: {suffix or 'none'} (use .json/.csv)")


def parse_rules(raw_rules: list[dict]) -> tuple[list[FirewallRule], list[str]]:
    rules: list[FirewallRule] = []
    broken: list[str] = []
    for index, raw in enumerate(raw_rules, start=1):
        if not isinstance(raw, dict):
            broken.append(f"entry #{index}: not an object")
            continue
        try:
            rules.append(FirewallRule.from_dict(raw))
        except ValueError as exc:
            broken.append(f"entry #{index}: {exc}")
    return rules, broken


def validate_rule(rule: FirewallRule) -> None:
    if not is_valid_address(rule.source):
        rule.errors.append(f"invalid source {rule.source!r}")
    if not is_valid_address(rule.destination):
        rule.errors.append(f"invalid destination {rule.destination!r}")
    if not is_valid_port(rule.port):
        rule.errors.append(f"invalid port {rule.port!r}")
    if rule.action not in VALID_ACTIONS:
        rule.errors.append(f"invalid action {rule.action!r}")


def find_duplicates_and_conflicts(
    rules: list[FirewallRule],
) -> tuple[list[Finding], list[Finding], set[int]]:
    groups: defaultdict[tuple[str, str, str], list[FirewallRule]] = defaultdict(list)
    for rule in rules:
        groups[rule.key].append(rule)

    duplicates: list[Finding] = []
    conflicts: list[Finding] = []
    drop_ids: set[int] = set()

    for group in groups.values():
        by_action: defaultdict[str, list[FirewallRule]] = defaultdict(list)
        for rule in group:
            by_action[rule.action].append(rule)

        for same in by_action.values():
            first = same[0]
            for extra in same[1:]:
                duplicates.append(
                    Finding(
                        "DUPLICATE",
                        [extra.id, first.id],
                        f"Rule #{extra.id} ({extra.describe()}) duplicates "
                        f"Rule #{first.id}",
                    )
                )
                drop_ids.add(extra.id)

        if "ALLOW" in by_action and "DENY" in by_action:
            allow = by_action["ALLOW"][0]
            deny = by_action["DENY"][0]
            conflicts.append(
                Finding(
                    "CONFLICT",
                    [allow.id, deny.id],
                    f"Rule #{allow.id} ({allow.describe()}) conflicts with "
                    f"Rule #{deny.id} ({deny.describe()})",
                )
            )

    return duplicates, conflicts, drop_ids


def find_high_risk(rules: list[FirewallRule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.action != "ALLOW":
            continue
        any_source = rule.source.upper() in ANY_ADDRESSES
        any_port = rule.port == ANY_PORT
        if not (any_source or any_port):
            continue
        if any_source and any_port:
            reason = "Unlimited exposure"
        elif any_port:
            reason = "All ports open"
        elif rule.port in RISKY_PORTS:
            reason = f"{RISKY_PORTS[rule.port]} publicly accessible"
        else:
            reason = "Publicly accessible"
        findings.append(
            Finding(
                "HIGH-RISK", [rule.id], f"Rule #{rule.id}: {rule.describe()} ({reason})"
            )
        )
    return findings


def audit_rules(rules: list[FirewallRule], check_conflicts: bool) -> AuditResult:
    result = AuditResult(total=len(rules))
    seen_ids: set[int] = set()
    for rule in rules:
        validate_rule(rule)
        if rule.id in seen_ids:
            rule.errors.append(f"duplicate rule id {rule.id}")
        seen_ids.add(rule.id)
        if not rule.is_valid:
            result.invalid.append(rule)
            logger.warning("Rule #%s rejected: %s", rule.id, "; ".join(rule.errors))

    valid = [rule for rule in rules if rule.is_valid]
    duplicates, conflicts, drop_ids = find_duplicates_and_conflicts(valid)
    result.duplicates = duplicates
    for finding in duplicates:
        logger.warning("[DUPLICATE] %s", finding.message)

    if check_conflicts:
        result.conflicts = conflicts
        for finding in conflicts:
            logger.warning("[CONFLICT] %s", finding.message)
            drop_ids.add(finding.rule_ids[0])

    result.high_risk = find_high_risk(valid)
    for finding in result.high_risk:
        logger.warning("[HIGH-RISK] %s", finding.message)

    result.clean_rules = [rule for rule in valid if rule.id not in drop_ids]
    return result


def print_report(result: AuditResult, check_conflicts: bool) -> None:
    conflicts_line = (
        f"{len(result.conflicts)} conflicts found" if check_conflicts else "not checked"
    )
    print()
    print("=== Firewall Configuration Audit Report ===")
    print(f"Total Rules       : {result.total}")
    print(f"Invalid Rules     : {len(result.invalid)}")
    print(f"Conflicting Rules : {conflicts_line}")
    print(f"Duplicate Rules   : {len(result.duplicates)} duplicates found")
    print(f"High-Risk Rules   : {len(result.high_risk)} dangerous ALLOW rules")
    print(f"Clean Rules       : {len(result.clean_rules)}")
    print()
    print("=== Critical Findings ===")
    lines = [
        f"[INVALID] Rule #{rule.id}: {'; '.join(rule.errors)}"
        for rule in result.invalid
    ]
    for group in (result.conflicts, result.duplicates, result.high_risk):
        lines.extend(f"[{item.category}] {item.message}" for item in group)
    print("\n".join(lines) if lines else "No issues found.")
    print()


def build_report(
    result: AuditResult, rules_file: Path, check_conflicts: bool, broken: list[str]
) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules_file": short_path(rules_file),
        "conflict_check": check_conflicts,
        "summary": {
            "total_rules": result.total,
            "unparsed_entries": len(broken),
            "invalid_rules": len(result.invalid),
            "duplicate_rules": len(result.duplicates),
            "conflicting_rules": len(result.conflicts),
            "high_risk_rules": len(result.high_risk),
            "clean_rules": len(result.clean_rules),
        },
        "unparsed_entries": broken,
        "invalid_rules": [
            {**rule.to_dict(), "errors": rule.errors} for rule in result.invalid
        ],
        "duplicates": [asdict(item) for item in result.duplicates],
        "conflicts": [asdict(item) for item in result.conflicts],
        "high_risk": [asdict(item) for item in result.high_risk],
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def setup_logging(level: str, audit_log: Path) -> None:
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, level))
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    audit_log.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(audit_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rules-file",
        type=Path,
        default=DEFAULT_RULES,
        help="path to firewall rules file (.json or .csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help="path to audit report JSON",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=DEFAULT_CLEAN,
        help="path to cleaned rules JSON",
    )
    parser.add_argument(
        "--check-conflicts",
        action="store_true",
        help="detect ALLOW/DENY conflicts and drop conflicting ALLOW rules",
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="console logging level",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=DEFAULT_AUDIT_LOG,
        help="path to audit log file",
    )


def run(args: argparse.Namespace) -> int:
    try:
        setup_logging(args.log_level, args.audit_log)
    except OSError as exc:
        print(f"[ERROR] Cannot open audit log {args.audit_log}: {exc}", file=sys.stderr)
        return 1

    logger.info("Parsing firewall rules from %s...", short_path(args.rules_file))
    try:
        raw_rules = load_raw_rules(args.rules_file)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except json.JSONDecodeError as exc:
        logger.error("Malformed JSON in %s: %s", short_path(args.rules_file), exc)
        return 1
    except (ValueError, csv.Error, UnicodeDecodeError, OSError) as exc:
        logger.error("Cannot read %s: %s", short_path(args.rules_file), exc)
        return 1

    rules, broken = parse_rules(raw_rules)
    for problem in broken:
        logger.error("Skipped malformed %s", problem)
    logger.info(
        "Total rules parsed: %d. Validating IP syntax and rule logic...", len(rules)
    )
    logger.debug("Conflict check enabled: %s", args.check_conflicts)

    result = audit_rules(rules, args.check_conflicts)
    print_report(result, args.check_conflicts)

    report = build_report(result, args.rules_file, args.check_conflicts, broken)
    try:
        write_json(args.output, report)
        write_json(args.clean_output, [rule.to_dict() for rule in result.clean_rules])
    except OSError as exc:
        logger.error("Cannot write output: %s", exc)
        return 1

    logger.info("Security report successfully exported to %s", short_path(args.output))
    logger.info(
        "Clean rule set (%d rules) saved to %s",
        len(result.clean_rules),
        short_path(args.clean_output),
    )
    if result.high_risk or result.conflicts or result.invalid:
        logger.warning(
            "Security issues detected! Check audit log at %s",
            short_path(args.audit_log),
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Firewall rules validator and analyzer"
    )
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
