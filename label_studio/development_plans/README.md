# Label Studio - Development Plans NER Annotation

Annotate development plan documents for Named Entity Recognition (NER) model training.

## Quick Start - label studio
```bash
docker compose -f docker-compose.dev.yml up label-studio
```

## 🚀 Quick Start (that creates import file)

```bash
cd /path/to/ac215_Spatially/data
source .venv/bin/activate
uv sync

# Prepare all documents
python label_studio/development_plans/run.py --city boston --doc-type all

# Or filter by document type
python label_studio/development_plans/run.py --city boston --doc-type bpda
python label_studio/development_plans/run.py --city boston --doc-type loi
```

This script:
1. Extracts **full text** from **all PDFs** (or filtered subset)
2. Creates import JSON file at `label_studio/development_plans/imports/boston_{doc_type}_import.json`
3. Shows next steps to start Label Studio locally

**Then start Label Studio:**
```bash
# Start Label Studio
label-studio start
```

## 📝 Configure Label Studio (One Time Setup)

Open http://localhost:8080 in your browser:

1. **Create account** (first time only)
2. **Create project:** "Boston Development Plans NER"
3. **Import labeling config:**
   - Go to: Settings → Labeling Interface → Code view
   - Copy contents from `label_studio/development_plans/config.xml`
   - Paste and click Save
4. **Import data:**
   - Click "Import" button
   - Upload: `label_studio/development_plans/imports/boston_import.json`

## 🎯 Start Annotating!

- Select text with mouse
- Press hotkey (0-9) to label the entity
- Click "Submit" when done with a document
- Export annotations from Label Studio UI when finished

## 📋 Entity Types Explained (7 NER Labels)

The annotation system uses **7 main entity categories**, each covering multiple related subcategories. This structure allows the NER model to learn broad concepts while capturing specific details.

---

### 1. CONSTRUCTION_DETAILS (hotkey: 1)
**What to annotate:** How the property has been designed and constructed - physical specifications and quantitative measurements

**Examples:**
- Lot Area: `27,371 sf`, `50,000 square feet`
- Building dimensions: `6-story building`, `twelve stories`, `18 floors`
- Units: `47 residential units`, `150 apartments`
- FAR (Floor Area Ratio): `FAR of 5.0`, `Floor Area Ratio: 3.5`
- Physical specifications: `approximately 588,000 square feet`, `building footprint`

**Why this matters:** These metrics determine if the project complies with dimensional zoning regulations.

---

### 2. PROPERTY_USAGE (hotkey: 2)
**What to annotate:** What this property will be used for - the purpose and intended use of the development

**Examples:**
- `commercial building`
- `residential development`
- `mixed-use facility`
- `manufacturing use`
- `retail space with apartments above`
- `office and laboratory space`

**Why this matters:** The intended use must be permitted in the applicable zoning district and determines which regulations apply.

---

### 3. ZONING_DISTRICT (hotkey: 3)
**What to annotate:** Specific zoning district name - official zoning classifications that apply to the property

**Examples:**
- Base districts: `New Market Industrial Development Area`, `Economic Development Area (EDA)`, `Residential-2 (R-2)`, `Multi-Family Residential-3 (MFR-3)`
- Overlay districts: `Restricted Parking Overlay District`, `Coastal Flood Resilience Overlay District`, `Historic District`

**Why this matters:** The zoning district(s) define what uses are allowed and what dimensional requirements apply.

---

### 4. ZONING_RELIEF (hotkey: 4)
**What to annotate:** Requests for relief - any request for exceptions, variances, or special permissions from standard zoning requirements

**Examples:**
- `Off-street parking insufficient`
- `Height: Excessive`
- `setback variance`
- `parking reduction`
- `FAR increase`
- `use variance`
- `density increase`
- `open space reduction`

**Why this matters:** This is the **KEY** entity for your model - understanding what zoning relief is requested is the core prediction task.

---

### 5. ARTICLE_REFERENCE (hotkey: 5)
**What to annotate:** Specific zoning article - citations to articles, sections, or chapters in the Boston Zoning Code

**Examples:**
- `Article 50, Section 32`
- `Article 80B`
- `Article 64`
- `Article 59`
- `Section 80E-6`

**Why this matters:** Article references indicate which regulatory framework applies (e.g., Article 80 = Large Project Review).

---

### 6. EXPECTED_IMPACT (hotkey: 6)
**What to annotate:** Property's expected impact - anticipated effects on the community, including job creation and economic benefits

**Examples:**
- `will activate the Site with a new manufacturing use in an emerging industry`
- `create 150 new jobs`
- `will revitalize the neighborhood`
- `generate tax revenue`
- `provide affordable housing for 50 families`
- `bring new retail opportunities to the area`

**Why this matters:** Expected impacts are often used to justify zoning relief and represent community benefits.

---

### 7. LOCATION_CONTEXT (hotkey: 7)
**What to annotate:** Neighborhood history and transportation - information about the surrounding area's background and accessibility

**Examples:**
- Transportation: `our facility is located walking distance to 9 different buses and shuttles`, `adjacent to the MBTA Orange Line`, `near South Station`
- Neighborhood history: `historically industrial area`, `former warehouse district`, `undergoing revitalization`
- Area characteristics: `in the heart of downtown`, `residential neighborhood`, `emerging innovation district`

**Why this matters:** Location context provides important background for understanding the project's fit within its surroundings and accessibility.

---

## 📝 Annotation Best Practices

✅ **DO:**
- Include surrounding context if it makes the entity clearer (e.g., "approximately 588,000 square feet")
- Label multiple instances of the same entity type
- Be consistent across documents

❌ **DON'T:**
- Include extra whitespace or punctuation at the edges
- Skip entities just because they're repetitive
- Guess if you're unsure - you can skip and come back later

## 📖 Common Commands

```bash
# Stop Label Studio
docker compose -f docker-compose.dev.yml stop label-studio

# Restart Label Studio
docker compose -f docker-compose.dev.yml restart label-studio

# Check status
docker ps --filter name=label_studio
```

**Document types for filtering:** `spra`, `loi`, `bpda`, `pda`, `imp`

## ❓ FAQ

**Q: How does Label Studio track which documents are done?**
A: Label Studio automatically tracks annotation progress in its database. In the UI you'll see:
- Task list with completion status
- Progress bar (e.g., "15 / 100 completed")
- Filters to view "Not Started" / "In Progress" / "Completed" tasks
- Everything persists in the `label_studio_data` Docker volume

**Q: How are PDFs in subdirectories handled?**
A: The prepare command automatically finds ALL PDFs in subdirectories using recursive search. You don't need to flatten your directory structure - just run prepare and it handles everything.

**Q: Can I prepare documents in batches?**
A: Yes! You can run prepare multiple times. Each time it will:
1. Create a new import JSON file
2. You import it into Label Studio (adds to existing tasks)
3. Label Studio tracks everything together

## 🛠 Troubleshooting

**No PDFs?** Run collector first:
```bash
docker compose -f docker-compose.dev.yml up dev-plans-collector
```

**Service won't start?** Check logs:
```bash
docker logs label_studio
```

