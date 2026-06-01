# Contract Structure

Describes how contract templates are organized on disk and how `contracts/resolver.py` maps employee attributes to a template file.

---

## Directory Layout

```
contracts/
├── resolver.py                        ← picks the right template from employee attributes
├── generator.py                       ← renders template → DOCX + PDF, saved to output/
├── hours.py                           ← weekly/daily hours schedule helpers
│
├── berlin/
│   ├── befristet/
│   │   └── 2026/
│   │       ├── ASN_AV_berlin_floor_supervisor_befristet_40.docx
│   │       ├── ASN_AV_berlin_glasreiniger_befristet_40.docx
│   │       ├── ASN_AV_berlin_hausmann_befristet_40.docx
│   │       ├── ASN_AV_berlin_hsk_befristet_40.docx
│   │       ├── ASN_AV_berlin_minibar_befristet_40.docx
│   │       ├── ASN_AV_berlin_minijob_befristet.docx    ← no hours suffix
│   │       ├── ASN_AV_berlin_nr_befristet_40.docx
│   │       ├── ASN_AV_berlin_public_area_befristet_40.docx
│   │       ├── ASN_AV_berlin_reinigungskraft_befristet_40.docx
│   │       └── ASN_AV_berlin_stw_befristet_40.docx
│   └── unbefristet/
│       ├── VORLAGEN Unbefristet_Adlon/
│       │   └── ASN_AV_berlin_<role>_unbefristet_adlon_40.docx
│       └── VORLAGEN Unbefristet_GHB/
│           └── ASN_AV_berlin_<role>_unbefristet_ghb_40.docx
│
├── koeln_group/
│   ├── bergisch_gladbach/
│   │   └── befristet/
│   │       └── ASN_AV_bergisch_gladbach_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│   ├── duesseldorf/
│   │   └── unbefristet/
│   │       └── ASN_AV_duesseldorf_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│   ├── frankfurt/
│   │   ├── befristet/
│   │   │   └── ASN_AV_frankfurt_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│   │   └── unbefristet/
│   │       └── ASN_AV_frankfurt_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│   └── hamburg/
│       ├── befristet/
│       │   └── ASN_AV_hamburg_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│       └── unbefristet/
│           └── ASN_AV_hamburg_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx
│
└── wien/                              ← flat folder, all effectively unbefristet
    └── ASN_AV_wien_<Role>_<hours>_Std[_<days>_Tage_<daily>_Std].docx
```

---

## Resolver Inputs

| Field | Employee Attribute | Notes |
|---|---|---|
| `city_code` | `work_city` | Normalised via `CITY_ALIASES` |
| `contract_type_code` | `contract_type` | `befristet` / `unbefristet` |
| `occupation_code` | `occupation` | Normalised via `OCCUPATION_ALIASES` |
| `weekly_hours` | `weekly_hours` | Integer; required for koeln_group & wien |
| `days_per_week` | `work_days_per_week` | Integer; used for wien narrowing |
| `daily_hours` | `daily_hours` | Float; used for wien narrowing |
| `subgroup_code` | `hotel_name` | Required for Berlin unbefristet (`adlon` / `ghb`) |

---

## City Routing

```
work_city              → city_code          → resolver function
─────────────────────────────────────────────────────────────────
berlin                   berlin               resolve_berlin_template()
köln / koeln             koeln_group          resolve_koeln_group_template()
bergisch gladbach        bergisch_gladbach      ↑ (same)
düsseldorf / duesseldorf duesseldorf            ↑
frankfurt                frankfurt              ↑
hamburg                  hamburg                ↑
wien / vienna            wien                 resolve_wien_template()
```

---

## Berlin Templates

**Befristet** — folder: `contracts/berlin/befristet/2026/`

Naming: `ASN_AV_berlin_<role>_befristet_40.docx`

| occupation_code | File |
|---|---|
| `floor_supervisor` | `ASN_AV_berlin_floor_supervisor_befristet_40.docx` |
| `glasreiniger` | `ASN_AV_berlin_glasreiniger_befristet_40.docx` |
| `hausmann` | `ASN_AV_berlin_hausmann_befristet_40.docx` |
| `hsk` | `ASN_AV_berlin_hsk_befristet_40.docx` |
| `minibar` | `ASN_AV_berlin_minibar_befristet_40.docx` |
| `minijob` | `ASN_AV_berlin_minijob_befristet.docx` (no hours suffix) |
| `nr` | `ASN_AV_berlin_nr_befristet_40.docx` |
| `public_area` | `ASN_AV_berlin_public_area_befristet_40.docx` |
| `reinigungskraft` | `ASN_AV_berlin_reinigungskraft_befristet_40.docx` |
| `stw` | `ASN_AV_berlin_stw_befristet_40.docx` |

**Unbefristet — Adlon** — folder: `contracts/berlin/unbefristet/VORLAGEN Unbefristet_Adlon/`

Roles: `floor_supervisor`, `glasreiniger`, `hausmann`, `hsk`, `minibar`, `nr`, `public_area`, `stw` — all at 40h.

**Unbefristet — GHB** — folder: `contracts/berlin/unbefristet/VORLAGEN Unbefristet_GHB/`

Roles: `floor_supervisor`, `glasreiniger`, `hausmann`, `hsk`, `minibar`, `nr`, `public_area` — all at 40h.

> Berlin unbefristet requires `subgroup_code` = `adlon` or `ghb` (derived from `hotel_name`).

---

## Koeln Group Templates

Cities: `bergisch_gladbach`, `duesseldorf`, `frankfurt`, `hamburg`

### Bergisch Gladbach — `contracts/koeln_group/bergisch_gladbach/befristet/`

Naming: `ASN_AV_bergisch_gladbach_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`

| Role | Available schedules (hours/days/daily) |
|---|---|
| `hsk` | 25/5/5 · 30/5/6 · 35/5/7 · 40/5/8 |
| `hsk_supervisor` | 40/5/8 |
| `hausmann` | 40/5/8 |
| `nr` | 40/5/8 |

### Düsseldorf — `contracts/koeln_group/duesseldorf/unbefristet/`

`ASN_AV_duesseldorf_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`

Roles: `nr` (token `NR`), `stw` (token `STW`)

### Frankfurt — `contracts/koeln_group/frankfurt/`

- Befristet (`befristet/`): `ASN_AV_frankfurt_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`
  - Roles: `nr`, `public_area`
- Unbefristet (`unbefristet/`): `ASN_AV_frankfurt_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`
  - Roles: `back_of_house_manager`, `hausmann`, `hsk`, `minibar`, `nr`, `public_area`, `stw`, `supervisor`

### Hamburg — `contracts/koeln_group/hamburg/`

- Befristet (`befristet/`): `ASN_AV_hamburg_<role>_befristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`
  - Roles: `nr`, `public_area`
- Unbefristet (`unbefristet/`): `ASN_AV_hamburg_<role>_unbefristet_<hours>_Std_<days>_Tage_<daily>_Std.docx`
  - Same roles as Frankfurt unbefristet.

> Koeln-group role names are canonical resolver occupation codes, matching Berlin-style lowercase tokens.

---

## Wien Templates

Folder: `contracts/wien/` (flat)

Naming: `ASN_AV_wien_<Role>_<hours>_Std[_<days>_Tage_<daily>_Std].docx`

All templates are effectively unbefristet (no contract_type suffix in filenames).

| occupation_code | Available files |
|---|---|
| `reinigungskraft` / `reinigungskraft_td` | `_TD_20_Std_5_Tage_4_Std`, `_TD_25_Std_5_Tage_5_Std`, `_TD_30_Std_5_Tage_6_Std` |
| `reinigungskraft_pa` | `_PA_32_Std_4_Tage_8_Std` |
| `reinigungskraft_hm` | `_HM_40_Std` |
| `reinigungskraft_nr` | `_NR_40_Std` |
| `reinigungskraft_public` | `_Public_40_Std` |
| `reinigungskraft_stw` | `_STW_40_Std` |
| `zimmermaedchen` | `_24_Std_3_Tage_8_Std`, `_30_Std_5_Tage_6_Std`, `_32_Std_4_Tage_8_Std`, `_40_Std` |
| `hsk_supervisor` | `_HSK_Supervisor_32_Std_4_Tage_8_Std`, `_HSK_Supervisor_40_Std` |
| `hsk_manager` | `_HSK_Manager_40_Std` |
| `ass_hsk_manager` | `_Ass_HSK_Manager_40_Std` |
| `stw_supervisor` | `_STW_Supervisor_40_Std` |
| `stw_manager` | `_STW_Manager_40_Std` |
| `objektleitung_nr` | `_Objektleitung_NR_40_Std` |
| `quality_manager` | `_Quality_Manager_40_Std` |

### Wien Schedule Validation

The resolver enforces allowed `(weekly_hours, days_per_week, daily_hours)` combinations:

| Role | Allowed combinations |
|---|---|
| `reinigungskraft` / `reinigungskraft_td` | 20/5/4 · 25/5/5 · 30/5/6 |
| `reinigungskraft_pa` | 32/4/8 |
| `reinigungskraft_hm/nr/public/stw` | 40/5/8 |
| `zimmermaedchen` | 24/3/8 · 30/5/6 · 32/4/8 · 40/5/8 |
| `hsk_supervisor` | 32/4/8 · 40/5/8 |
| All managers / supervisors / objektleitung / quality | 40/5/8 |

---

## Occupation Alias Map

| User input | occupation_code |
|---|---|
| floor supervisor | `floor_supervisor` |
| hsk / housekeeping | `hsk` |
| hsk manager / housekeeping manager | `hsk_manager` |
| hsk supervisor / housekeeping supervisor | `hsk_supervisor` |
| glasreiniger | `glasreiniger` |
| hausmann / hm-wm | `hausmann` |
| minibar | `minibar` |
| nr | `nr` |
| public area | `public_area` |
| stw | `stw` |
| stw supervisor | `stw_supervisor` |
| stw manager | `stw_manager` |
| reinigungskraft | `reinigungskraft` |
| reinigungskraft td/pa/hm/nr/public/stw | `reinigungskraft_*` |
| zimmermädchen / zimmermaedchen | `zimmermaedchen` |
| quality manager | `quality_manager` |
| objektleitung nr | `objektleitung_nr` |
| ass. hsk manager | `ass_hsk_manager` |

---

## Available Template Context Variables

These Jinja variables are available in all `.docx` templates (populated from the employee record):

| Category | Variables |
|---|---|
| Personal | `salutation`, `first_name`, `last_name`, `full_name`, `gender`, `date_of_birth`, `place_of_birth`, `country_of_birth`, `nationality` |
| Identity | `ausweis_number`, `reise_pass_number` |
| Contact | `phone`, `email` |
| Address | `street_and_house_number`, `zip_code`, `city`, `country`, `full_address` |
| Tax & insurance | `krankenkasse`, `krankenkasse_nummer`, `steuer_id`, `steuerklasse`, `sozialversicherungsnummer` |
| Banking | `bank_name`, `bank_iban`, `bank_bic`, `bank_account_holder` |
| Employment | `work_city`, `occupation`, `employment_type`, `weekly_hours`, `work_days_per_week`, `daily_hours`, `work_schedule`, `contract_type`, `start_date`, `end_date` |
| Other | `disabled`, `status`, `ordio_id` |

---

## Generated Output

- Output folder: `output/` (repo root)
- Filename pattern: `AV_<occupation>_<employee_id>_<first_name>_<last_name>_<start_date>.docx`
- The generator deletes any existing contract for the same employee before saving a new one
- PDF is generated alongside the DOCX automatically

---

## Adding a New Template

1. Drop the `.docx` file in the correct city/type folder following the naming convention for that city.
2. If the role is new, add an entry to `OCCUPATION_ALIASES` in `resolver.py`.
3. For Wien roles with multiple hour variants, add the schedule to `CITY_ROLE_SCHEDULE_RULES["wien"]`.
4. Add the role token to the relevant `_WIEN_ROLE_TOKEN` or `_BERLIN_ROLE_TOKEN` map in `resolver.py`. Koeln-group filenames use the canonical `occupation_code` directly.
