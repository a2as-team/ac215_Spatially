<!-- Connect your issue number here -->
> Add the issue number here if it exists. Github will automatically close the issue when the PR is merged.

🚀 Resolves: #

--- 
### Description

> Please provide a brief description of the PR here. It should also mention how to run the script.

---

### 📝 Required Inputs for Running the Script

- **type**  
  One of: `population`, `mobility`  

- **level**  
  One of: `state`, `county`, `tract`  

- **year**  
  Any year till 2023

- **State**  
  Full state name or abbreviation  

---

### 📝 Optional Inputs

- **county**  
  Full county name or abbreviation  

- **tract**  
  Full tract name or abbreviation  

---

### 🛠️ Run Commands

Example:
```bash
cd data
# activate the virtual environment
source .venv/bin/activate
# run the script
python collector/census/run.py \
    --type population \
    --level tract \
    --year 2020 \
    --state IL \
    --county "" \
    --tract ""
```
