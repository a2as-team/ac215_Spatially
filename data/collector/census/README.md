# 🏛️ Census Data Collector (Business-Driven ACS Tables)

Auto-collect U.S. Census Bureau **American Community Survey (ACS)** data mapped to **real estate investment objectives** with **automatic variable discovery**.

---

## 🎯 Business Use Case Framework

This collector organizes ACS tables by **business objectives** for real estate investment analysis:

| Business Objective | Key Use Cases | Primary ACS Tables |
|-------------------|---------------|-------------------|
| **Maximize Revenue** | Rent pricing, occupancy optimization, unit mix | DP04, S2503, S1901, DP02, S0701 |
| **Minimize Costs** | Construction ROI, right-sizing, regulatory costs | DP04, S1901, S2503, DP05, S0802 |
| **Reduce Risk** | Tenant stability, market volatility, policy risk | S2503, S1701, S2301, S2403, S0701 |
| **Maximize Asset Appreciation** | Neighborhood trends, economic growth, supply/demand | S1501, S1903, DP05, DP04, S0804 |

---

## ✨ Key Features

- **Business-driven table selection**: Each ACS table maps to specific investment decisions
- **Semantic class naming**: Classes named by table content (e.g., `SelectedHousingCharacteristics`)
- **Auto-fetch all variables**: Parse Census API `variables.json` — no hardcoded lists
- **Dataset auto-resolved by prefix**:
  - `DP*` → `acs/acs5/profile` (Data Profiles)
  - `S*` → `acs/acs5/subject` (Subject Tables)
- **Batch processing**: Run all tables across multiple years (2009–2023)

---

## 📦 Project Structure

```
data/
  collector/
    census/
      __init__.py           # exports CensusCollector
      base.py               # BaseCensusCaller (shared logic)
      collector.py          # auto-discovers & registers table callers
      utils_table_vars.py   # fetch_table_variables()
      run.py                # entry point
      tables/
        __init__.py
        DP04.py             # SelectedHousingCharacteristics
        DP02.py             # SocialCharacteristics
        DP05.py             # DemographicAndHousingEstimates
        S1901.py            # Income
        S2503.py            # FinancialCharacteristics
        S1501.py            # EducationalAttainment
        S2301.py            # EmploymentStatus
        S0701.py            # GeographicMobility
        ...
```

---

## 📊 Core ACS Tables for Real Estate Analysis

### Housing & Costs
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **DP04** | `SelectedHousingCharacteristics` | Rent, tenure, vacancy, structure | Median rent, home value, vacancy rates |
| **S2503** | `FinancialCharacteristics` | Housing cost burden, mortgage status | Cost as % of income, housing expenses |

### Income & Poverty
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **S1901** | `Income` | Household income distribution | Median income by household type |
| **S1903** | `MedianIncome` | Detailed income measures | Median income by demographics |
| **S1701** | `PovertyStatus` | Poverty rates and thresholds | % below poverty line |

### Employment & Industry
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **S2301** | `EmploymentStatus` | Labor force participation, unemployment | Employment rate by demographics |
| **S2403** | `Industry` | Industry distribution by sex | Employment by sector |
| **S2404** | `IndustryFullTime` | Full-time year-round employment | High-wage sector employment |

### Demographics & Household
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **DP02** | `SocialCharacteristics` | Household types, education, language | Family structure, education levels |
| **DP05** | `DemographicAndHousingEstimates` | Population by age, race, sex | Total population, demographic composition |
| **S1101** | `HouseholdsAndFamilies` | Household size and composition | Average household size, family types |

### Mobility & Transportation
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **S0701** | `GeographicMobility` | Migration patterns | Moved in past year (in/out flows) |
| **S0801** | `CommutingCharacteristics` | Commute to work | Travel time, means of transportation |
| **S0804** | `MeansOfTransportation` | Transportation mode details | Vehicle availability, transit use |

### Education
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **S1501** | `EducationalAttainment` | Education levels by demographics | % Bachelor's+, % High school+ |

### Other
| Table | Class Name | Description | Key Variables |
|-------|------------|-------------|---------------|
| **S2201** | `SNAP` | Food stamp/SNAP participation | Households receiving assistance |
| **S2501** | `OccupancyCharacteristics` | Tenure and occupancy details | Owner/renter distribution |
| **S0802** | `VehicleAvailability` | Vehicles per household | Parking demand proxy |

---

## 🔗 Census API References

- **API Root**: https://api.census.gov/data.html
- **ACS 5-Year**: `https://api.census.gov/data/{year}/acs/acs5`
- **Data Profiles**: `https://api.census.gov/data/{year}/acs/acs5/profile`
- **Subject Tables**: `https://api.census.gov/data/{year}/acs/acs5/subject`
- **Variables**: `https://api.census.gov/data/{year}/{dataset}/variables.json`

---

## 🚀 Usage

### Run All Tables for a City
```bash
python data/collector/census/run.py --city chicago
```

**Output**: 
- `data/collector/census/downloads/{STATE}_{TABLE_CODE}_{YEAR}.csv`
- `data/collector/census/downloads/manifest.csv` (summary of all downloads)

**Default behavior**:
- Processes years 2014–2024
- State-level geography
- Auto-discovers all table modules in `tables/`


---

## 🛠️ Adding New Tables

1. Create `data/collector/census/tables/{TABLE_CODE}.py`:

```python
from ..base import BaseCensusCaller
from ..utils_table_vars import fetch_table_variables

TABLE_CODE = "DP04"
DATASET = "acs/acs5/profile"

class SelectedHousingCharacteristics(BaseCensusCaller):
    """Selected Housing Characteristics (rent, tenure, vacancy)"""
    
    def __init__(self, dataset=DATASET):
        super().__init__(dataset)

    def call(self, year: int, state: str, county: str | None = None, tract: str | None = None):
        variables = fetch_table_variables(self.dataset, year, TABLE_CODE)
        if not variables:
            raise ValueError(f"No variables found for {TABLE_CODE} in {year}/{self.dataset}")
        return self._query(year=year, variables=variables, state=state, county=county, tract=tract)
```

2. The collector will auto-detect and register the new module

**Naming convention**:
- Class name = PascalCase version of table description
- Use semantic names that reflect business purpose
- Examples: `SelectedHousingCharacteristics`, `Income`, `EmploymentStatus`

---

## 🎓 Census Table Selection Guide

**For housing market analysis**: DP04, S2503, S2501  
**For demographic trends**: DP05, DP02, S1101  
**For income analysis**: S1901, S1903, S1701  
**For employment trends**: S2301, S2403, S2404  
**For mobility patterns**: S0701, S0801, S0804  
**For education levels**: S1501, DP02  

