"""
Import and clean Cumbria Constabulary FOI 1306/25 – crimes on hospital grounds 2019/20–2023/24.

Source: PDF response dated 13 Oct 2025 (FOI reference FOI 1306/25).

Available data (in priority order):
  PRIMARY  – crimes by offence category × financial year   → cumbria_crimes_by_category_year.csv
  SECONDARY– crimes by outcome × hospital (all years)      → cumbria_crimes_by_outcome_hospital.csv

Individual crime records with all four dimensions (year + category + outcome + hospital)
were not provided in the FOI response.

Usage:
    python import_cumbria_foi.py
"""

import csv
import os

FORCE = "Cumbria Constabulary"
YEARS = ["2019/20", "2020/21", "2021/22", "2022/23", "2023/24"]

# ---------------------------------------------------------------------------
# Q1b – offence category × year
# Zeros represent blank cells in the original table.
# Grand-total column is excluded; row sums are verified against it below.
# ---------------------------------------------------------------------------
CATEGORY_YEAR_RAW = [
    # (offence_category, 2019/20, 2020/21, 2021/22, 2022/23, 2023/24)
    ("Absconding From Lawful Custody",                                           1, 0, 3, 1, 0),
    ("Arson",                                                                    2, 2, 2, 4, 0),
    ("Bicycle Theft",                                                            2, 0, 1, 0, 1),
    ("Burglary Business and Community",                                          5, 3, 3, 2, 1),
    ("Burglary Residential",                                                     1, 0, 1, 0, 0),
    ("Criminal Damage",                                                         69,48,54,50,33),
    ("Dangerous Driving",                                                        0, 1, 0, 0, 0),
    ("Disclosure, Obstruction, False Or Misleading Statements Etc",              0, 0, 0, 1, 0),
    ("Interfering With A Motor Vehicle",                                         1, 0, 0, 0, 0),
    ("NFIB52B Hacking-Personal",                                                 1, 0, 0, 2, 0),
    ("NFIB5A Cheque, Plastic Card And Online Bank Accounts (Not PSP)",           2, 0, 1, 0, 0),
    ("NFIB90 Other Fraud Not Covered Elsewhere",                                 2, 9, 1, 1, 0),
    ("Other Forgery",                                                            0, 0, 0, 1, 0),
    ("Other Notifiable Offences",                                                0, 0, 0, 2, 0),
    ("Other Offences Against The State Or Public Order",                         5, 3, 2, 4, 3),
    ("Other Sexual Offences",                                                   11,10,10,19,13),
    ("Other Theft",                                                             52,25,27,20,11),
    ("Perverting The Course Of Justice",                                         0, 0, 0, 1, 0),
    ("Possession Of Article With Blade Or Point",                                3, 6, 4, 0, 2),
    ("Possession Of Drugs",                                                     11, 6, 6, 8,12),
    ("Possession Of Other Weapons",                                              1, 2, 2, 0, 2),
    ("Public Fear, Alarm Or Distress",                                          64,34,54,55,25),
    ("Racially Or Religiously Aggravated Public Fear, Alarm Or Distress",        8,15,20,18,13),
    ("Rape",                                                                     8, 4, 3, 3, 1),
    ("Shoplifting",                                                              0, 1, 0, 0, 0),
    ("Stalking And Harassment",                                                 19,16,38,25, 7),
    ("Theft From The Person",                                                    2, 0, 1, 0, 0),
    ("Theft From Vehicle",                                                       6, 2, 0, 0, 0),
    ("Threat Or Possession With Intent To Commit Criminal Damage",               0, 1, 1, 3, 0),
    ("Trafficking In Controlled Drugs",                                          1, 0, 0, 1, 0),
    ("Violence With Injury",                                                    99,60,89,74,26),
    ("Violence Without Injury",                                                259,257,246,218,128),
]

# Verify column totals match Q1a
EXPECTED_YEAR_TOTALS = {
    "2019/20": 635,
    "2020/21": 505,
    "2021/22": 569,
    "2022/23": 513,
    "2023/24": 278,
}


def _verify_category_totals():
    for i, year in enumerate(YEARS):
        total = sum(row[i + 1] for row in CATEGORY_YEAR_RAW)
        expected = EXPECTED_YEAR_TOTALS[year]
        if total != expected:
            raise ValueError(
                f"Column total mismatch for {year}: got {total}, expected {expected}"
            )


# ---------------------------------------------------------------------------
# Q1c/1d – outcome × hospital (all years combined, split across two tables)
# ---------------------------------------------------------------------------
HOSPITALS_T1 = [
    "Brampton War Memorial Hospital",
    "Carleton Clinic",
    "Cockermouth Community Hospital",
    "Cumberland Infirmary",
    "Furness General Hospital",
    "James Cook University Hospital",
    "Keswick (Mary Hewetson) Community Hospital",
]

HOSPITALS_T2 = [
    "Maryport Victoria Cottage Hospital",
    "Millom Hospital",
    "Penrith Hospital",
    "Royal Lancaster Infirmary",
    "Ryhope Hospital",
    "West Cumberland Hospital",
    "Westmorland General Hospital",
    "Workington Community Hospital",
]

# Each entry: (outcome_label, count_per_hospital_in_order)
# Zeros represent blank cells; hospitals with no entry for an outcome are 0.
OUTCOME_HOSPITAL_T1 = [
    # fmt: off
    # (outcome, Brampton, Carleton, Cockermouth, Cumberland, Furness, James Cook, Keswick)
    ("Adult Caution With Alternate Offence",                                                          0,  1, 0,   0,   1,  0, 0),
    ("Cannabis Warning",                                                                              0,  0, 0,   1,   1,  0, 0),
    ("Caution - Adults",                                                                              0,  2, 0,   5,   9,  0, 0),
    ("Caution - Youths",                                                                              0,  0, 0,   0,   0,  0, 0),
    ("Charge/Summons",                                                                                0, 94, 0, 150, 101,  0, 0),
    ("Charge/Summonsed With Alternate Offence",                                                       0,  7, 0,  12,   7,  0, 0),
    ("Community Resolution",                                                                          0, 23, 0,  10,  15,  0, 0),
    ("Diversionary, Educational Or Intervention Activity Undertaken",                                 0,  0, 0,   1,   5,  0, 0),
    ("Evidential Difficulties Victim Based - Named Suspect Not Identified",                           0,  7, 0,  10,   4,  0, 0),
    ("Formal Action Against The Offender Is Not In The Public Interest (Police)",                     0,  4, 0,   2,   0,  0, 0),
    ("Investigation Complete: No Suspect Identified",                                                 2, 59, 2,  74,  50,  0, 1),
    ("Named Suspect - Further Investigation Not In Public Interest",                                  1, 99, 1,  65,  74,  0, 1),
    ("Named Suspect Identified: Evidential Difficulties - Victim Does Not Support Police Action",     4,413, 3, 120, 153,  0, 3),
    ("Named Suspect Identified: Victim Supports Police Action But Evidential Difficulties",           2, 99, 2,  47,  57,  1, 2),
    ("Other Agency Delegations",                                                                      0,  1, 0,   5,   1,  0, 0),
    ("Penalty Notice For Disorder",                                                                   0,  1, 0,   0,   1,  0, 0),
    ("Prosecution Not In The Public Interest (CPS)",                                                  0,  1, 0,   0,   0,  0, 0),
    ("Prosecution Prevented - Named Suspect Too Ill To Prosecute",                                    0, 77, 2,  24,  73,  0, 0),
    ("Prosecution Prevented - Victim Or Key Witness Dead Or Too Ill To Give Evidence",                0,  9, 0,   1,   7,  0, 0),
    ("Prosecution Time Limit Expired",                                                                0, 11, 0,   4,   2,  0, 0),
    # fmt: on
]

OUTCOME_HOSPITAL_T2 = [
    # fmt: off
    # (outcome, Maryport, Millom, Penrith, Royal Lancaster, Ryhope, West Cumberland, Westmorland, Workington)
    ("Adult Caution With Alternate Offence",                                                          0, 0, 0,  0, 0,  0,  0, 0),
    ("Cannabis Warning",                                                                              0, 0, 0,  0, 0,  1,  0, 0),
    ("Caution - Adults",                                                                              1, 0, 1,  0, 0,  3,  1, 0),
    ("Caution - Youths",                                                                              0, 0, 0,  0, 0,  3,  0, 0),
    ("Charge/Summons",                                                                                1, 0, 2,  1, 1, 61,  5, 1),
    ("Charge/Summonsed With Alternate Offence",                                                       0, 0, 0,  0, 0,  3,  1, 0),
    ("Community Resolution",                                                                          0, 0, 1,  1, 0,  3,  3, 0),
    ("Diversionary, Educational Or Intervention Activity Undertaken",                                 0, 0, 0,  2, 0,  1,  0, 0),
    ("Evidential Difficulties Victim Based - Named Suspect Not Identified",                           2, 0, 1,  0, 0,  2,  2, 1),
    ("Formal Action Against The Offender Is Not In The Public Interest (Police)",                     0, 0, 0,  0, 0,  0,  0, 0),
    ("Investigation Complete: No Suspect Identified",                                                 1, 2, 4,  0, 0, 31,  9, 4),
    ("Named Suspect - Further Investigation Not In Public Interest",                                  0, 0, 3,  1, 0, 48, 14, 1),
    ("Named Suspect Identified: Evidential Difficulties - Victim Does Not Support Police Action",     1, 0, 3,  0, 0,124, 15,15),
    ("Named Suspect Identified: Victim Supports Police Action But Evidential Difficulties",           1, 0, 3,  0, 0, 40,  5, 1),
    ("Other Agency Delegations",                                                                      0, 0, 0,  1, 0,  0,  0, 1),
    ("Penalty Notice For Disorder",                                                                   0, 0, 0,  0, 0,  0,  0, 0),
    ("Prosecution Not In The Public Interest (CPS)",                                                  0, 0, 0,  0, 0,  0,  0, 0),
    ("Prosecution Prevented - Named Suspect Too Ill To Prosecute",                                    0, 0, 0,  0, 0, 19, 13, 2),
    ("Prosecution Prevented - Victim Or Key Witness Dead Or Too Ill To Give Evidence",                0, 0, 0,  4, 0,  0,  0, 0),
    ("Prosecution Time Limit Expired",                                                                0, 0, 0,  0, 0,  1,  1, 0),
    # fmt: on
]


# ---------------------------------------------------------------------------
# Build and write CSVs
# ---------------------------------------------------------------------------

def write_category_year(output_path: str) -> int:
    _verify_category_totals()
    rows = []
    for entry in CATEGORY_YEAR_RAW:
        category = entry[0]
        for i, year in enumerate(YEARS):
            count = entry[i + 1]
            if count > 0:
                rows.append({
                    "force": FORCE,
                    "financial_year": year,
                    "offence_category": category,
                    "crime_count": count,
                })
    _write_csv(output_path, ["force", "financial_year", "offence_category", "crime_count"], rows)
    return len(rows)


def write_outcome_hospital(output_path: str) -> int:
    rows = []
    for table_data, hospitals in (
        (OUTCOME_HOSPITAL_T1, HOSPITALS_T1),
        (OUTCOME_HOSPITAL_T2, HOSPITALS_T2),
    ):
        for entry in table_data:
            outcome = entry[0]
            for i, hospital in enumerate(hospitals):
                count = entry[i + 1]
                if count > 0:
                    rows.append({
                        "force": FORCE,
                        "hospital": hospital,
                        "outcome": outcome,
                        "crime_count": count,
                    })
    _write_csv(output_path, ["force", "hospital", "outcome", "crime_count"], rows)
    return len(rows)


def _write_csv(path: str, fieldnames: list, rows: list) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    cat_path = "cumbria_crimes_by_category_year.csv"
    out_path = "cumbria_crimes_by_outcome_hospital.csv"

    n1 = write_category_year(cat_path)
    print(f"Saved {n1} rows → {cat_path}")

    n2 = write_outcome_hospital(out_path)
    print(f"Saved {n2} rows → {out_path}")
