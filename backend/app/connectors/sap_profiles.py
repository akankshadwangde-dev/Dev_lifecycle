"""Capability profiles per SAP release, and the ABAP syntax the generator may use for each."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    read: str
    write: str
    checks: str
    unit_tests: str

    def as_dict(self) -> dict:
        return asdict(self)


CLOUD = Profile("cloud", "Cloud", "ADT", "ADT + gCTS", "ATC incl. cloud readiness", "ABAP Unit via ADT")
FULL = Profile("full", "Full", "ADT", "ADT + transports", "ATC", "ABAP Unit via ADT")
HYBRID = Profile("hybrid", "Hybrid", "RFC", "abapGit or paste", "Code Inspector via RFC + abaplint", "ABAP Unit via RFC")
BASIC = Profile("basic", "Basic", "RFC", "Paste by hand", "abaplint (offline)", "Drafted only")


def detect(basis_release: int | None, cloud: bool = False) -> Profile:
    """Pick a profile from the SAP_BASIS release (e.g. 702, 750, 758)."""
    if cloud:
        return CLOUD
    if basis_release is None:
        return BASIC
    if basis_release >= 740:
        return FULL
    if basis_release >= 702:
        return HYBRID
    return BASIC


def syntax_level(basis_release: int | None, cloud: bool = False) -> str:
    if cloud:
        return "cloud"
    if basis_release is None or basis_release < 702:
        return "v700"
    if basis_release < 740:
        return "v702"
    if basis_release < 750:
        return "v740"
    if basis_release < 758:
        return "v750"
    return "v758"


# Guidance given to the build agent so generated code compiles on the target release.
SYNTAX_RULES = {
    "v700": "Classic ABAP only: no inline declarations, no constructor expressions (VALUE, NEW, CONV, COND), "
            "no string templates, no new Open SQL (no @ host variables or comma-separated field lists).",
    "v702": "No inline declarations (DATA(...)), no constructor expressions (VALUE, NEW, CONV, COND, SWITCH), "
            "no new Open SQL. String templates |...| are allowed.",
    "v740": "Inline declarations and constructor expressions are allowed. Use new Open SQL with @ host "
            "variables only if the system is on 7.40 SP05 or later; otherwise classic Open SQL.",
    "v750": "Modern ABAP allowed: inline declarations, constructor expressions, new Open SQL, CDS views. "
            "No features newer than 7.50.",
    "v758": "Modern ABAP allowed, including ABAP SQL features up to 7.58 and released CDS views such as "
            "I_SalesDocument where suitable.",
    "cloud": "ABAP Cloud only: use released APIs and released CDS views (C1 contract), no direct table "
             "access to SAP tables, no SAP GUI, no classic dynpros or classic reports.",
}
