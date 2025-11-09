# 🏛️ Census Data Collector

This module is responsible for collecting U.S. Census Bureau data (primarily from the American Community Survey, ACS 5-Year Estimates).  
Each data collector focuses on one theme (population, income, housing, etc.) and maps Census variable codes to readable names.

---

## 📚 Resources

### 1. U.S. Census Bureau (Official)
- Website: https://www.census.gov/data.html  
- API: https://api.census.gov/data.html  
- ACS 5-Year Documentation: https://api.census.gov/data/2023/acs/acs5.html  
- Data Profiles: https://api.census.gov/data/2023/acs/acs5/profile.html  
- Subject Tables: https://api.census.gov/data/2023/acs/acs5/subject.html  

---

## 📦 Modules Overview

| File | Class | Dataset | Description | Main Census Variables |
|------|--------|----------|--------------|------------------------|
| `population.py` | `PopulationCaller` | `acs/acs5` | Total population | `B01003_001E` |
| `age.py` | `AgeCaller` | `acs/acs5` | Median age | `B01002_001E` |
| `race.py` | `RaceCaller` | `acs/acs5` | Race composition (White, Black, Asian, etc.) | `B02001_*E` |
| `income.py` | `IncomeCaller` | `acs/acs5` | Household & per-capita income | `B19013_001E`, `B19301_001E` |
| `employment.py` | `EmploymentCaller` | `acs/acs5/profile` | Employment & unemployment rate | `DP03_0004E`, `DP03_0005PE` |
| `education.py` | `EducationCaller` | `acs/acs5/profile` | Educational attainment (high school, bachelor’s+) | `DP02_0066PE`, `DP02_0067PE` |
| `housing.py` | `HousingCaller` | `acs/acs5` | Median home value, rent, year built | `B25077_001E`, `B25064_001E`, `B25035_001E` |
| `tenure.py` | `TenureCaller` | `acs/acs5` | Owner vs renter occupied units | `B25003_*E` |
| `poverty.py` | `PovertyCaller` | `acs/acs5/subject` | Poverty rate (percent below poverty line) | `S1701_C02_001E` |
| `transportation.py` | `TransportationCaller` | `acs/acs5/profile` | Commute methods & time | `DP03_0019PE–DP03_0025E` |
| `home_value_distribution.py` | `HomeValueDistributionCaller` | `acs/acs5/profile` | Distribution of home values | `DP04_0081E–DP04_0086E` |
| `owner_cost_burden.py` | `OwnerCostBurdenCaller` | `acs/acs5` | Owner monthly costs as % of income | `B25093_001E` |
| `rent_burden.py` | `RentBurdenCaller` | `acs/acs5` | Rent as % of household income | `B25070_001E` |
| `vacancy.py` | `VacancyCaller` | `acs/acs5` | Vacancy status (for rent, for sale) | `B25004_*E` |
| `year_built_distribution.py` | `YearBuiltDistributionCaller` | `acs/acs5` | Housing age distribution | `B25034_*E` |

---
