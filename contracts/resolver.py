"""
contracts/resolver.py
─────────────────────
Maps an employee's attributes → the correct .docx contract template.

Public entry point:
    resolve_template_path(employee) -> Path

Internal flow:
    1. normalize_contract_attributes()  – raw strings → canonical codes
    2. validate_schedule()              – check city/occupation/hours combo is valid
    3. _CITY_RESOLVER[city](attrs)      – dispatch to the right city resolver
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR      = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = BASE_DIR / "contracts"

# ─────────────────────────────────────────────────────────────────────────────
# Alias lookup tables  (raw user input → canonical code)
# ─────────────────────────────────────────────────────────────────────────────

CITY_ALIASES: Dict[str, str] = {
    "berlin":            "berlin",
    "köln":              "koeln_group",
    "koeln":             "koeln_group",
    "bergisch gladbach": "bergisch_gladbach",
    "bergisch_gladbach": "bergisch_gladbach",
    "düsseldorf":        "duesseldorf",
    "dusseldorf":        "duesseldorf",
    "duesseldorf":       "duesseldorf",
    "frankfurt":         "frankfurt",
    "hamburg":           "hamburg",
    "wien":              "wien",
    "vienna":            "wien",
}

CONTRACT_TYPE_ALIASES: Dict[str, str] = {
    "befristet":   "befristet",
    "temporär":    "befristet",
    "temporar":    "befristet",
    "temporary":   "befristet",
    "temp":        "befristet",
    "unbefristet": "unbefristet",
    "permanent":   "unbefristet",
}

OCCUPATION_ALIASES: Dict[str, str] = {
    # ── Shared / Berlin ─────────────────────────────────────────────────────
    "floor supervisor":        "floor_supervisor",
    "floor_supervisor":        "floor_supervisor",
    "hsk":                     "hsk",
    "housekeeping":            "hsk",
    "hsk manager":             "hsk_manager",
    "housekeeping manager":    "hsk_manager",
    "hsk supervisor":          "hsk_supervisor",
    "housekeeping supervisor":  "hsk_supervisor",
    "hsk_supervisor":          "hsk_supervisor",
    "glasreiniger":            "glasreiniger",
    "hausmann":                "hausmann",
    "hm-wm":                   "hausmann",
    "hm_wm":                   "hausmann",
    "minibar":                 "minibar",
    "mb":                      "minibar",
    "nr":                      "nr",
    "public area":             "public_area",
    "public_area":             "public_area",
    "pa-boh":                  "public_area",
    "pa_boh":                  "public_area",
    "stw":                     "stw",
    "stw supervisor":          "stw_supervisor",
    "stw manager":             "stw_manager",
    "reinigungskraft":         "reinigungskraft",
    "reinigungskraft td":      "reinigungskraft_td",
    "reinigungskraft pa":      "reinigungskraft_pa",
    "reinigungskraft hm":      "reinigungskraft_hm",
    "reinigungskraft nr":      "reinigungskraft_nr",
    "reinigungskraft public":  "reinigungskraft_public",
    "reinigungskraft stw":     "reinigungskraft_stw",
    "zimmermädchen":           "zimmermaedchen",
    "zimmermadchen":           "zimmermaedchen",
    "zimmermaedchen":          "zimmermaedchen",
    # ── Wien-specific ────────────────────────────────────────────────────────
    "quality manager":         "quality_manager",
    "objektleitung nr":        "objektleitung_nr",
    "objektleitung_nr":        "objektleitung_nr",
    "ass. hsk manager":        "ass_hsk_manager",
    "ass hsk manager":         "ass_hsk_manager",
    # ── Köln group (Frankfurt / Hamburg) ─────────────────────────────────────
    "supervisor":              "supervisor",
    "sv":                      "supervisor",
    "back of house manager":   "back_of_house_manager",
    "back_of_house_manager":   "back_of_house_manager",
}

SUBGROUP_ALIASES: Dict[str, str] = {
    "adlon":                 "adlon",
    "adlon group":           "adlon",
    "hotel adlon kempinski": "adlon",
    "ghb":                   "ghb",
    "ghb group":             "ghb",
    "grand hyatt berlin":    "ghb",
    "china club berlin":     "ghb",
    "kontor haus":           "ghb",
    "linden palais":         "ghb",
    "pressehaus podium":     "ghb",
}

# ─────────────────────────────────────────────────────────────────────────────
# Role-token tables  (occupation_code → filename fragment)
# ─────────────────────────────────────────────────────────────────────────────

# Berlin: token varies by contract type for some roles
_BERLIN_ROLE_TOKEN: Dict[str, Dict[str, Optional[str]]] = {
    "floor_supervisor": {"befristet": "floor_supervisor", "unbefristet": "floor_supervisor"},
    "hsk":              {"befristet": "HSK",              "unbefristet": "HSK"},
    "glasreiniger":     {"befristet": "GLASREINIGER",     "unbefristet": "GLASREINIGER"},
    "hausmann":         {"befristet": "HAUSMANN",         "unbefristet": "HAUSMANN"},
    "minibar":          {"befristet": "MINIBAR",          "unbefristet": "MINIBAR"},
    "minijob":          {"befristet": "minijob",          "unbefristet": None},
    "nr":               {"befristet": "NR",               "unbefristet": "NR"},
    "public_area":      {"befristet": "PUBLIC AREA",      "unbefristet": "PUBLIC AREA"},
    "stw":              {"befristet": "STW",              "unbefristet": "STW"},
    "reinigungskraft":  {"befristet": "REINIGUNGSKRAFT",  "unbefristet": None},
}

# Köln group: one token per occupation, shared across all Köln-group cities
_KOELN_GROUP_ROLE_TOKEN: Dict[str, str] = {
    "hausmann":              "HM-WM",
    "hsk":                   "HSK",
    "hsk_supervisor":        "HSK SUPERVISOR",
    "nr":                    "NR",
    "minibar":               "MB",
    "stw":                   "STW",
    "supervisor":            "SV",
    "public_area":           "PA-BOH",
    "back_of_house_manager": "Back of House Manager",
}

# Wien: token encodes the exact variant used in filenames
_WIEN_ROLE_TOKEN: Dict[str, str] = {
    "reinigungskraft":        "Reinigungskraft_TD",  # no plain variant; TD template covers it
    "reinigungskraft_td":     "Reinigungskraft_TD",
    "reinigungskraft_pa":     "Reinigungskraft_PA",
    "reinigungskraft_hm":     "Reinigungskraft_HM",
    "reinigungskraft_nr":     "Reinigungskraft_NR",
    "reinigungskraft_public": "Reinigungskraft_Public",
    "reinigungskraft_stw":    "Reinigungskraft_STW",
    "zimmermaedchen":         "Zimmermädchen",
    "hsk_supervisor":         "HSK_Supervisor",
    "hsk_manager":            "HSK_Manager",
    "ass_hsk_manager":        "Ass_HSK_Manager",
    "stw_supervisor":         "STW_Supervisor",
    "stw_manager":            "STW_Manager",
    "objektleitung_nr":       "Objektleitung_NR",
    "quality_manager":        "Quality_Manager",
}

# ─────────────────────────────────────────────────────────────────────────────
# Köln-group routing table
# ─────────────────────────────────────────────────────────────────────────────
# Maps city → contract_type → (sub-folder, file prefix, type token in filename).
# Bergisch Gladbach has a different filename scheme so is handled separately.

@dataclass(frozen=True)
class _KoelnRoute:
    folder:     str  # path relative to contracts/koeln_group/<city>/  ("." = city root)
    prefix:     str  # filename prefix:  FRA_AV, MUC_AV, DUS_AV, HAM_AV
    type_token: str  # BEFRISTET or UNBEFRISTET as it appears in the filename

_KOELN_ROUTING: Dict[str, Dict[str, _KoelnRoute]] = {
    "duesseldorf": {
        "unbefristet": _KoelnRoute(".",                       "DUS_AV", "UNBEFRISTET"),
    },
    "frankfurt": {
        "befristet":   _KoelnRoute("befristet",               "FRA_AV", "BEFRISTET"),
        "unbefristet": _KoelnRoute("unbefristet",             "MUC_AV", "UNBEFRISTET"),
    },
    "hamburg": {
        "befristet":   _KoelnRoute("Vorlagen Befristet",      "HAM_AV", "BEFRISTET"),
        "unbefristet": _KoelnRoute("Vorlagen Unbefristet AV", "MUC_AV", "UNBEFRISTET"),
    },
}

# Cities that route through resolve_koeln_group_template
KOELN_GROUP_CITIES: frozenset = frozenset(_KOELN_ROUTING.keys() | {"bergisch_gladbach"})

# Berlin unbefristet: hotel/group → folder name
_BERLIN_UNBEFRISTET_FOLDER: Dict[str, str] = {
    "adlon": "VORLAGEN Unbefristet_Adlon",
    "ghb":   "VORLAGEN Unbefristet_GHB",
}

# ─────────────────────────────────────────────────────────────────────────────
# Schedule validation rules
# ─────────────────────────────────────────────────────────────────────────────
# Valid (weekly_hours, days_per_week, daily_hours) combos per city + occupation.

ScheduleCombo = Tuple[int, int, float]

CITY_ROLE_SCHEDULE_RULES: Dict[str, Dict[str, List[ScheduleCombo]]] = {
    "berlin": {
        "floor_supervisor": [(40, 5, 8)],
        "glasreiniger":     [(40, 5, 8)],
        "hausmann":         [(40, 5, 8)],
        "hsk":              [(40, 5, 8)],
        "minibar":          [(40, 5, 8)],
        "minijob":          [(20, 5, 4)],
        "nr":               [(40, 5, 8)],
        "public_area":      [(40, 5, 8)],
        "reinigungskraft":  [(40, 5, 8)],
        "stw":              [(40, 5, 8)],
    },
    "bergisch_gladbach": {
        "hsk":            [(25, 5, 5), (30, 5, 6), (35, 5, 7), (40, 5, 8)],
        "hsk_supervisor": [(40, 5, 8)],
        "hausmann":       [(40, 5, 8)],
        "nr":             [(40, 5, 8)],
    },
    "duesseldorf": {
        "nr":  [(40, 5, 8)],
        "stw": [(40, 5, 8)],
    },
    "frankfurt": {
        "nr":                    [(40, 5, 8)],
        "public_area":           [(40, 5, 8)],
        "hsk":                   [(40, 5, 8)],
        "minibar":               [(40, 5, 8)],
        "stw":                   [(40, 5, 8)],
        "hausmann":              [(40, 5, 8)],
        "supervisor":            [(40, 5, 8)],
        "back_of_house_manager": [(40, 5, 8)],
    },
    "hamburg": {
        "nr":                    [(40, 5, 8)],
        "public_area":           [(40, 5, 8)],
        "hsk":                   [(40, 5, 8)],
        "minibar":               [(40, 5, 8)],
        "stw":                   [(40, 5, 8)],
        "hausmann":              [(40, 5, 8)],
        "supervisor":            [(40, 5, 8)],
        "back_of_house_manager": [(40, 5, 8)],
    },
    "wien": {
        "reinigungskraft":        [(20, 5, 4)],
        "reinigungskraft_td":     [(20, 5, 4), (25, 5, 5), (30, 5, 6)],
        "reinigungskraft_pa":     [(32, 4, 8)],
        "reinigungskraft_hm":     [(40, 5, 8)],
        "reinigungskraft_nr":     [(40, 5, 8)],
        "reinigungskraft_public": [(40, 5, 8)],
        "reinigungskraft_stw":    [(40, 5, 8)],
        "zimmermaedchen":         [(24, 3, 8), (30, 5, 6), (32, 4, 8), (40, 5, 8)],
        "hsk_supervisor":         [(32, 4, 8), (40, 5, 8)],
        "hsk_manager":            [(40, 5, 8)],
        "ass_hsk_manager":        [(40, 5, 8)],
        "stw_supervisor":         [(40, 5, 8)],
        "stw_manager":            [(40, 5, 8)],
        "objektleitung_nr":       [(40, 5, 8)],
        "quality_manager":        [(40, 5, 8)],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Normalizers
# ─────────────────────────────────────────────────────────────────────────────

def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and lowercase.  Returns None for blank input."""
    if value is None:
        return None
    return str(value).strip().lower() or None


def normalize_city(value: Optional[str]) -> Optional[str]:
    raw = _clean(value)
    if raw is None:
        return None
    canonical = CITY_ALIASES.get(raw)
    if canonical is None:
        raise ValueError(f"Unknown city: {value!r}")
    return canonical


def normalize_contract_type(value: Optional[str]) -> Optional[str]:
    raw = _clean(value)
    if raw is None:
        return None
    canonical = CONTRACT_TYPE_ALIASES.get(raw)
    if canonical is None:
        raise ValueError(f"Unknown contract type: {value!r}")
    return canonical


def normalize_occupation(value: Optional[str]) -> str:
    raw = _clean(value)
    if raw is None:
        raise ValueError("occupation is required")
    canonical = OCCUPATION_ALIASES.get(raw)
    if canonical is None:
        raise ValueError(f"Unknown occupation: {value!r}")
    return canonical


def normalize_subgroup(value: Optional[str]) -> Optional[str]:
    raw = _clean(value)
    if raw is None:
        return None
    return SUBGROUP_ALIASES.get(raw, raw)


def normalize_weekly_hours(value: Optional[Any]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        hours = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid weekly_hours: {value!r}")
    rounded = round(hours)
    if abs(hours - rounded) > 1e-6:
        raise ValueError(f"weekly_hours must be a whole number; got {value!r}")
    return int(rounded)


def normalize_days_per_week(value: Optional[Any]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid work_days_per_week: {value!r}")


def normalize_hours_per_day(value: Optional[Any]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid daily_hours: {value!r}")


def normalize_department(value: Optional[str]) -> Optional[str]:
    """Not used for template resolution but kept for potential future use."""
    raw = _clean(value)
    if raw is None:
        return None
    mapping = {
        "reinigung":                            "reinigung",
        "housekeeping/zimmermädchen":           "housekeeping/zimmermaedchen",
        "nachtrieinigung":                      "nachtrieinigung",
        "hausmann-/wäschemannabteilung":        "hausmann",
        "hausmann-/waschenmannabteilung":       "hausmann",
        "public area":                          "public_area",
        "stwearding/geschirrspüler-abteilung":  "stw",
        "stewarding/geschirrspueler-abteilung": "stw",
    }
    return mapping.get(raw, raw)


def normalize_contract_attributes(employee) -> Dict[str, Any]:
    """Extract and normalize all contract-relevant fields from an employee object."""
    return {
        "city_code":          normalize_city(getattr(employee, "work_city", None)),
        "contract_type_code": normalize_contract_type(getattr(employee, "contract_type", None)),
        "occupation_code":    normalize_occupation(getattr(employee, "occupation", None)),
        "weekly_hours":       normalize_weekly_hours(getattr(employee, "weekly_hours", None)),
        "days_per_week":      normalize_days_per_week(getattr(employee, "work_days_per_week", None)),
        "daily_hours":        normalize_hours_per_day(getattr(employee, "daily_hours", None)),
        "subgroup_code":      normalize_subgroup(getattr(employee, "hotel_name", None)),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Schedule validation
# ─────────────────────────────────────────────────────────────────────────────

def _combo_matches(combo: ScheduleCombo, weekly: int, days: int, daily: float) -> bool:
    return int(combo[0]) == weekly and int(combo[1]) == days and float(combo[2]) == daily


def validate_schedule(attrs: Dict[str, Any]) -> None:
    """
    Verify that the employee's schedule is a known-valid combination for their
    city + occupation.  Raises ValueError with an actionable message on failure.
    """
    city       = attrs.get("city_code")
    occupation = attrs.get("occupation_code")
    weekly     = attrs.get("weekly_hours")
    days       = attrs.get("days_per_week")
    daily      = attrs.get("daily_hours")

    city_rules = CITY_ROLE_SCHEDULE_RULES.get(city) if city else None
    if city_rules is None:
        return  # city not in the rules table → no restriction

    allowed = city_rules.get(occupation)
    if allowed is None:
        raise ValueError(
            f"Occupation '{occupation}' is not supported for city '{city}'"
        )

    if weekly is None:
        raise ValueError(
            f"weekly_hours is required for {city} / {occupation}. "
            f"Available: {sorted({c[0] for c in allowed})}"
        )
    if days is None:
        raise ValueError(
            f"work_days_per_week is required for {city} / {occupation}. "
            f"Available: {sorted({c[1] for c in allowed})}"
        )
    if daily is None:
        raise ValueError(
            f"daily_hours is required for {city} / {occupation}. "
            f"Available: {sorted({c[2] for c in allowed})}"
        )

    if not any(_combo_matches(c, int(weekly), int(days), float(daily)) for c in allowed):
        allowed_text = " | ".join(f"{w}h / {d}d / {dh}h" for w, d, dh in allowed)
        raise ValueError(
            f"Invalid schedule {weekly}h / {days}d / {daily}h "
            f"for {city} / {occupation}.  Allowed: {allowed_text}"
        )

# ─────────────────────────────────────────────────────────────────────────────
# File-system helpers
# ─────────────────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Normalise a string for fuzzy filename matching: lowercase, _ → space, strip dots."""
    return text.lower().replace("_", " ").replace(".", "")


def _pick_by_contains(directory: Path, required: List[str]) -> Path:
    """
    Return the first .docx in *directory* whose normalised name contains every
    string in *required* (case-insensitive, underscores treated as spaces).
    Word lock-files (~$...) are silently skipped.
    """
    norm_required = [_norm(s) for s in required]
    candidates = sorted(directory.glob("*.docx"))
    for path in candidates:
        if path.name.startswith("~$"):
            continue  # Word lock-file, not a real template
        if all(s in _norm(path.name) for s in norm_required):
            return path
    listed = "\n".join(f"  {p.name}" for p in candidates if not p.name.startswith("~$"))
    raise FileNotFoundError(
        f"No template in {directory}\n"
        f"  matching: {required}\n"
        f"  checked:\n{listed or '  (none)'}"
    )


def _pick_by_contains_fallback(directory: Path, required_sets: List[List[str]]) -> Path:
    """
    Try each required-set in order and return the first match.
    Useful when filename conventions drifted across years/folders.
    """
    last_err: Optional[Exception] = None
    for required in required_sets:
        try:
            return _pick_by_contains(directory, required)
        except FileNotFoundError as exc:
            last_err = exc
    raise last_err or FileNotFoundError(f"No template found in {directory}")


def _extract_hours_from_filename(path: Path) -> Optional[int]:
    """Parse the weekly-hours number out of a Wien filename (_NN_std pattern)."""
    match = re.search(r"_(\d+)_std", path.stem.lower())
    return int(match.group(1)) if match else None


def _require(value: Any, field: str) -> Any:
    """Raise ValueError if *value* is None or empty string."""
    if value is None or value == "":
        raise ValueError(f"'{field}' is required to resolve a contract template")
    return value

# ─────────────────────────────────────────────────────────────────────────────
# City-specific resolvers
# ─────────────────────────────────────────────────────────────────────────────

def resolve_berlin_template(attrs: Dict[str, Any]) -> Path:
    contract_type = _require(attrs["contract_type_code"], "contract_type")
    occupation    = _require(attrs["occupation_code"],    "occupation")
    subgroup      = attrs.get("subgroup_code")
    hours         = attrs.get("weekly_hours") or 40  # almost all Berlin files are 40h

    role_token = (_BERLIN_ROLE_TOKEN.get(occupation) or {}).get(contract_type)
    if role_token is None:
        raise ValueError(
            f"No Berlin template for occupation '{occupation}' / '{contract_type}'"
        )

    if contract_type == "unbefristet":
        folder = _BERLIN_UNBEFRISTET_FOLDER.get(subgroup or "")
        if not folder:
            raise ValueError(
                f"Berlin unbefristet requires hotel/group 'adlon' or 'ghb'; got '{subgroup}'"
            )
        base_dir = CONTRACTS_DIR / "berlin" / "unbefristet" / folder
        return _pick_by_contains_fallback(base_dir, [
            ["ASN_AV_berlin", role_token, "UNBEFRISTET", f"{hours} Std"],
            ["ASN_AV_berlin", role_token, "UNBEFRISTET", f"_{hours}"],
        ])

    # befristet
    base_dir = CONTRACTS_DIR / "berlin" / "befristet" / "2026"

    if occupation == "minijob":
        # Minijob files don't include an hours token in their name
        return _pick_by_contains(base_dir, ["ASN_AV_berlin_Minijob_befristet"])

    # Two naming conventions coexist: "40 Std" (older) and "_40" (current 2026 folder)
    return _pick_by_contains_fallback(base_dir, [
        ["ASN_AV_berlin", role_token, "BEFRISTET", f"{hours} Std"],
        ["ASN_AV_berlin", role_token, "BEFRISTET", f"_{hours}"],
    ])


def resolve_koeln_group_template(attrs: Dict[str, Any]) -> Path:
    city          = _require(attrs["city_code"],          "city")
    occupation    = _require(attrs["occupation_code"],    "occupation")
    weekly_hours  = _require(attrs["weekly_hours"],       "weekly_hours")
    contract_type = attrs.get("contract_type_code") or "befristet"

    if city not in KOELN_GROUP_CITIES:
        raise ValueError(f"'{city}' is not a Köln-group city")

    hours_token = f"{weekly_hours} Std"
    city_root   = CONTRACTS_DIR / "koeln_group" / city

    # ── Bergisch Gladbach ──────────────────────────────────────────────────────
    # All contracts are befristet; files sit directly in the city root.
    # Filename pattern: ASN_AV_bergisch_gladbach_{occupation}_befristet_{hours}...docx
    if city == "bergisch_gladbach":
        return _pick_by_contains(
            city_root,
            ["ASN_AV_bergisch_gladbach", occupation, "befristet", hours_token],
        )

    # ── All other Köln-group cities: routing table ─────────────────────────────
    role_token = _KOELN_GROUP_ROLE_TOKEN.get(occupation)
    if role_token is None:
        raise ValueError(f"No template mapping for occupation '{occupation}' in {city}")

    city_routes = _KOELN_ROUTING.get(city)
    if city_routes is None:
        raise ValueError(f"No routing configuration for Köln-group city '{city}'")

    route = city_routes.get(contract_type)
    if route is None:
        available = list(city_routes.keys())
        raise ValueError(
            f"'{contract_type}' contracts are not available for {city}. "
            f"Available types: {available}"
        )

    base_dir = city_root if route.folder == "." else city_root / route.folder
    return _pick_by_contains(
        base_dir,
        [route.prefix, role_token, route.type_token, hours_token],
    )


def resolve_wien_template(attrs: Dict[str, Any]) -> Path:
    occupation    = _require(attrs["occupation_code"], "occupation")
    weekly_hours  = attrs.get("weekly_hours")
    days_per_week = attrs.get("days_per_week")
    daily_hours   = attrs.get("daily_hours")

    base_dir   = CONTRACTS_DIR / "wien"
    role_token = _WIEN_ROLE_TOKEN.get(occupation)
    if role_token is None:
        raise ValueError(f"No Wien template for occupation '{occupation}'")

    role_slug = role_token.lower().replace(" ", "_").replace(".", "")

    def _role_files() -> List[Path]:
        prefix = f"asn_av_wien_{role_slug}_"
        return sorted(
            p for p in base_dir.glob("*.docx")
            if not p.name.startswith("~$")
            and p.stem.lower().replace(".", "").startswith(prefix)
        )

    def _hour_files(hours: int) -> List[Path]:
        hour_token = f"_{hours}_std"
        return [
            p for p in _role_files()
            if hour_token in p.stem.lower().replace(".", "")
        ]

    # No weekly_hours → only valid when exactly one template exists for this role
    if weekly_hours is None:
        role_files = _role_files()
        if len(role_files) == 1:
            return role_files[0]
        available = sorted(h for h in map(_extract_hours_from_filename, role_files) if h)
        raise ValueError(
            f"weekly_hours required for Wien / '{occupation}'. "
            f"Available hours: {available}"
        )

    hour_files = _hour_files(weekly_hours)

    if len(hour_files) == 1:
        return hour_files[0]

    # Multiple files for same role + hours → narrow by days_per_week / daily_hours
    if len(hour_files) > 1 and days_per_week is not None and daily_hours is not None:
        day_token   = f"_{int(days_per_week)}_tage_"
        daily_token = f"_{int(float(daily_hours))}_std"
        narrowed = [
            p for p in hour_files
            if day_token   in p.stem.lower().replace(".", "")
            and daily_token in p.stem.lower().replace(".", "")
        ]
        if len(narrowed) == 1:
            return narrowed[0]
        if len(narrowed) > 1:
            raise FileNotFoundError(
                f"Multiple Wien templates matched for '{occupation}' "
                f"{weekly_hours}h / {days_per_week}d / {daily_hours}h:\n"
                + "\n".join(f"  {p.name}" for p in narrowed)
            )

    if len(hour_files) > 1:
        raise FileNotFoundError(
            f"Multiple Wien templates matched for '{occupation}' {weekly_hours}h:\n"
            + "\n".join(f"  {p.name}" for p in hour_files)
        )

    # Last resort: fuzzy search (handles older "ASN AV_40 Std_..." naming convention)
    return _pick_by_contains_fallback(base_dir, [
        ["ASN_AV_wien", role_token, str(weekly_hours), "Std"],
        ["ASN AV",      f"{weekly_hours} Std", role_token],
    ])

# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

# Dispatch table: city_code → resolver function
_CITY_RESOLVER = {
    "berlin": resolve_berlin_template,
    "wien":   resolve_wien_template,
    **{city: resolve_koeln_group_template for city in KOELN_GROUP_CITIES},
}


def resolve_template_path(employee) -> Path:
    """
    Normalize the employee's contract attributes, validate the schedule, then
    return the absolute path to the correct .docx template file.
    """
    attrs = normalize_contract_attributes(employee)
    city  = _require(attrs["city_code"], "work_city")

    validate_schedule(attrs)

    resolver = _CITY_RESOLVER.get(city)
    if resolver is None:
        raise ValueError(f"No template resolver registered for city '{city}'")

    return resolver(attrs)
