This article was produced as part of the final project for Harvard’s  
[AC215 Fall 2025](https://harvard-iacs.github.io/2025-AC215/) course.

**Project Repository:** https://github.com/hunkim98/ac215_Spatially  
**Team:** Spatially — Hun Kim, Devraj Raghuvanshi, Angelica Kim, Zewen (Zoe) Qiu  
**Video:** _[link]_

### Table of Contents

1. Introduction
2. Problem Statement
3. Data Collection and Processing
4. Model Fine-Tuning
5. Infrastructure and Deployment
6. Features
7. Reflections

---

## Introduction

Why are some neighborhoods full of high-rise towers while others are lined with low-rise homes? The answer lies in **zoning ordinances**—the legal rules that determine how land can be used and what can be built. These ordinances have a profound impact on the built environment. A familiar example is Boston’s Back Bay. Its iconic low-rise streetscape exists largely because the area is zoned **H-3-65**, capping building height at 65 feet.

[Image of Back Bay](#)

Despite their importance, zoning ordinances are notoriously difficult to work with. Many exceed 1,000 pages, use dense legal language, and are updated frequently. This creates challenges for both **developers**, who must navigate the regulations, and **government officials**, who rely on these rules to make informed decisions.

Given that zoning ordinances are:

- large in size
- frequently updated
- structurally complex

they present an ideal use case for **AI Operations**, the focus of Harvard’s AC215. Our team chose zoning as our domain of intervention for this reason.

[Image of our interface](#)

---

## Problem Statement

Our goal is to provide governments with an **automated pipeline** that collects zoning ordinances, zoning maps, census data, and development plans; processes them; and ultimately deploys an LLM-based RAG system that allows users to query any zoning-related information.

We selected governments as the target audience because, ideally, municipalities themselves should be able to deploy such systems and make zoning information accessible to their residents.

---

## Data Collection and Processing

Our project integrates five main datasets:

- Zoning ordinances
- Zoning maps
- Census data
- Census-tract boundaries
- Development plans

We added data beyond the zoning ordinance for two reasons:

1. To provide **context** that helps the LLM interpret zoning language
2. To support questions about **development activity** and **economic conditions** in a city

### What's with the development plans?

Zoning maps and census data are expected sources, but development plans are less obvious. As we reviewed the ordinance text, we noticed that many zoning descriptions depend heavily on local context. For example, Article 26, Section 1 describes the S2 Main Street Mixed Use district:

> “S2 buildings can fill the width of the lot to help create a continuous and active main street… [and] include requirements for Outdoor Amenity Space and a maximum for the blank wall of a facade.”

However, terms like _continuous and active main street_ or _blank wall maximums_ are vague without real-world examples. Development plans provide that missing context by showing how developers interpret zoning rules in practice.

### How did we collect the data?

Since our project is based in Boston, we began with the **Boston Planning & Development Agency (BPDA)**, which offers extensive public records. We built a scraper for BPDA development plans using their online archive:

https://apps.bostonplans.org/recordslibrary/

Next, we built a collector for zoning ordinances. Many U.S. municipalities store their codes on **Municode**, so we built a scraper for Municode as well and used it to collect Boston and Cambridge ordinances.

[Municode Platform Image](#)

For zoning maps and census-tract maps, we tapped into city GIS systems, most of which use **ArcGIS Feature Server**. We built a general-purpose collector that takes only a resource URL as input.

[Boston Zoning Maps Image](#)

For census data, we built a collector that fetches from the **U.S. Census Bureau API**. We collected ACS tables across income, demographics, employment, housing, and transportation—pulling tract-level data (11-digit GEOIDs) for fine-grained spatial analysis. Because these tables contain hundreds of variables, we needed a schema that could grow without redesign. We created three core tables:

- **ACS_TABLE** — groups variables into topical categories
- **ACS_VARIABLE** — stores variable identifiers (e.g., median income)
- **ACS_VALUE** — stores the actual measurements with year for temporal analysis

This normalized structure allows new ACS datasets to be added seamlessly.

[Census Data Table Structure Image](#)

### How did we process the data?

Zoning ordinances and development plans needed to be vectorized for retrieval. We used **Google Vertex AI** for embeddings. Zoning ordinances come with clean metadata (articles, sections), but development plans are unstructured and vary across developers.

To use metadata filtering in the vector DB, we needed structured fields—so we fine-tuned a **Named Entity Recognition (NER)** model to extract metadata automatically.

---

## Model Fine-Tuning

We fine-tuned a customized NER model based on **legal-bert-base-uncased**. We collected ~1,400 development plans from the BPDA and manually annotated them using **Label Studio**.

[Label Studio Image](#)

We initially targeted entities such as:

- Construction details
- Property usage
- Zoning district
- Zoning relief
- Article references
- Expected impact
- Location context

However, early results showed poor accuracy due to a severe imbalance: most tokens had no label (O). To fix this, we applied three strategies:

### 1. Downsampling

Only ~35% of chunks contained any entities. We downsampled non-entity chunks, shifting the distribution from **35/65** to **78/22**.

### 2. Stratified training/validation splits

We created splits that guaranteed representation for rare entity types.

### 3. Class-weighted loss

We assigned weight **0.1** to the “O” label and **1.0** to all entity labels to reduce bias toward predicting “O”.

### Outcome

Before improvements, the model predicted **100% O labels** with >98% confidence.  
After improvements:

- Only **55.56%** of tokens were O
- **44.44%** were valid entity labels
- The model produced consistent B-/I-tag patterns
- Confidence scores became reasonable (20–50%)

---

## Retrieval-Augmented Generation (RAG)

The core of our application is the RAG layer, which connects a user’s question to the relevant legal text and development history. Instead of asking an LLM to hallucinate zoning rules, we wanted it to act as an intelligent interface over the official documents.

### How retrieval works

Retrieving the right answer from thousands of pages requires balancing two things: guaranteeing precision and understanding meaning. So, we built a two-stage retrieval process:

1.  **Metadata Filtering (Speed & Precision):** Before searching for text, we strictly filter the database using the structured data we extracted earlier (City, Zoning District, NER tags). This instantly discards 99% of irrelevant documents.
2.  **Vector Search (Semantic Understanding):** Within that highly relevant slice, we use Google Vertex AI embeddings to find the specific paragraphs that match the user's intent.

This combination ensures that when a user asks about "setbacks in the S-3 district," the system is fast because it ignores the rest of the city, and accurate because it only retrieves rules that legally apply.

### Scoping the search

When a user is exploring a city broadly, the system searches the entire corpus of ordinances and development plans. This is great for comparative questions like, _"How does Cambridge regulate lab space compared to office space?"_

When a user clicks a specific parcel, however, the system narrows its focus. It uses PostGIS to identify the exact zoning district for that location, then restricts the vector search to:

1.  The specific articles of the zoning code that apply to that district.
2.  Past development plans from that same district or immediate vicinity.

This spatial filtering is what allows the model to answer highly specific questions like _"Can I build a 6-story building here?"_ with a degree of precision that a general chatbot simply cannot match.

### Fighting hallucinations

In a domain like zoning, a "hallucination" where the model invents a rule is unacceptable. To mitigate this, we treat the retrieved text as a strict boundary. The model is configured to answer only using the provided snippets and to explicitly cite its sources. On the frontend, we visualize these citations. Every claim in the model's answer is linked to the specific article, section, or development plan it came from.

---

## Infrastructure and Deployment

We built both the backend and frontend to deliver a production-ready application.

### Backend & Database

- **PostgreSQL + PostGIS** for spatial queries
- **pgvector** for embeddings
- Backend deployed on **Google Kubernetes Engine (GKE)**
- Horizontal Pod Autoscaler: scales from 1 → 4 pods based on load
- Custom domain via GoDaddy + Nginx Ingress + ExternalDNS

We intentionally avoided Pulumi or cloud-specific deployment tools so governments could more easily adopt the repository.

[Nginx Ingress Image](#)

### Frontend

We used **Next.js**, allowing zoning map data to be pre-rendered for performance. Deployment on **Vercel** was straightforward.

---

## Features

Our deployed application begins with a list of cities instead of a single combined map. This design choice:

1. Matches real user behavior—people usually have a specific municipality in mind
2. Avoids the heavy rendering cost of loading all zoning maps simultaneously

[City Page Image](#)

Because end-users such as developers and city officials care deeply about **accuracy**, the interface privileges document sources. The left panel highlights source documents, while the chat UI appears as a minimal floating panel.

[User Interface Image](#)

Users can query:

1. Zoning information
2. Census data
3. Development plans

We implemented two main agents:

### 1. City Data Agent

Handles general questions about development trends, zoning policies, and demographics.

[General Information Example Response Image](#)

### 2. Location Data Agent

Handles spatial queries—for example, zoning at a particular address or parcel that the user has selected on the map.

[Zoning Information at a Specific Location Example Response Image](#)

A **Smart Data Agent** routes requests between these two based on the user's query type.

[Smart Data Agent Diagram](#)

### 3. SQL Agent for Census Queries

Both agents use a specialized **SQL Agent** powered by **Google Gemini 2.0 Flash** for text-to-SQL conversion. When users ask census questions, the agent converts natural language queries into SQL, explores the database schema, validates queries for safety, and executes them against our normalized census database. It uses PostgreSQL full-text search on variable names to find relevant census data, preventing false positives and handling word variations.

---

## Reflections

### What We Learned from Experts

Throughout the project, we spoke with government officials and real estate developers to ground our work in real needs. These conversations shaped key design decisions.

**Phillip Smith** (Oxford Properties Group) suggested integrating development plans—something we hadn't initially considered. He explained that developers routinely study past proposals to understand how zoning rules are actually interpreted. This insight led us to build the BPDA scraper and fine-tune our NER model for metadata extraction.

**Will Cohen**, a GIS specialist for the City of Boston, emphasized the importance of showing document sources explicitly. For government officials, trust comes from traceability. This feedback shaped our UI: the left panel highlights source documents, while the chat remains a minimal floating panel.

### Limitations We Discovered

Both experts—and our own testing—confirmed that LLMs still struggle with:

1. **Nuanced legal language** — Zoning ordinances are written by lawyers over decades, with context-dependent terms that resist simple retrieval
2. **Spatial reasoning** — Questions like "Can I build a 6-story building here?" require understanding setbacks, overlays, and adjacent zones simultaneously

A well-designed RAG system can surface relevant passages, but it cannot fully replace human interpretation. We learned to be honest about this boundary.

3. **Text2SQL Conversion** — Converting natural language to SQL requires the agent to reason through user intent and extract relevant data beyond what's explicitly requested. For example, when a user asks "Can I raise the rent level next year?", the system must understand that this requires both rent data and income data to assess economic capacity. We addressed this through detailed prompting that guides the agent to think comprehensively about what data would help answer the underlying question. Going forward, adding metadata about variable names and their semantic relationships in our census database could further improve query accuracy.

### What This Project Taught Us

Building Spatially was an exercise in bridging domains: legal text, geospatial data, urban planning, and machine learning. The hardest part wasn't any single technical challenge—it was designing a system flexible enough to accommodate messy, real-world data while remaining simple enough for municipalities to adopt.

We hope this project serves as a foundation others can build upon. The collectors, processors, and agents are modular by design. If even one city finds this useful, we'll consider it a success.

You can explore our work at **https://teamspatially.com**.
