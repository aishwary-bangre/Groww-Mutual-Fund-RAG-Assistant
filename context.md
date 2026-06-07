# Groww Mutual Fund RAG Assistant - Project Context

This document outlines the context, objectives, requirements, and constraints for the **Groww Mutual Fund RAG Assistant (Facts-Only Q&A)**.

---

## 1. Project Overview & Objective

The objective of this project is to build a facts-only FAQ assistant for mutual fund schemes, using **Groww** as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from official public sources, such as:
- Asset Management Company (AMC) websites
- Association of Mutual Funds in India (AMFI)
- Securities and Exchange Board of India (SEBI)

### Core Mandate
* **Strict Fact-Only Retrieval:** Every response must be based strictly on official, retrieved documents.
* **Zero Advisory Bias:** The system must strictly avoid providing investment advice, opinions, predictions, or recommendations.
* **Verifiable Source Citations:** Every answer must include a single, clear source link and a "last updated" footer.

---

## 2. Target Users

1. **Retail Investors:** Users comparing mutual fund schemes or looking for specific fund details (e.g., exit load, expense ratio) without wanting biased advisory content.
2. **Customer Support & Content Teams:** Agents handling repetitive mutual fund queries who require fast, accurate, and compliance-aligned information.

---

## 3. Scope of Work

### Phase 1: Corpus Definition
* **Target AMC:** Select exactly one Asset Management Company (e.g., SBI Mutual Fund, HDFC Mutual Fund, ICICI Prudential Mutual Fund, etc.) to target.
* **Document Collection:** Collect **15–25 official public URLs** covering:
  - Scheme Factsheets
  - Key Information Memorandums (KIM)
  - Scheme Information Documents (SID)
  - AMC FAQ or help pages
  - AMFI/SEBI guidance pages
  - Statement and tax document download guides

### Phase 2: FAQ Assistant Requirements
The assistant must handle objective queries like:
- Expense ratio of a scheme
- Exit load details
- Minimum SIP / Lumpsum investment amount
- ELSS lock-in periods
- Riskometer classifications
- Benchmark indices
- Step-by-step processes to download statements or capital gains reports

#### Response Format Constraints
* **Length:** Maximum of **3 sentences** per response.
* **Citations:** Exactly **one valid citation link** to the source document.
* **Footer:** Must include:
  `Last updated from sources: <date>`

### Phase 3: Refusal & Guardrails
The system must actively detect and refuse non-factual, subjective, or advisory queries, such as:
- *"Should I invest in this fund?"*
- *"Which fund is better: X or Y?"*
- *"Will this fund give 15% returns next year?"*

#### Refusal Response Guidelines
* Be polite, clear, and professional.
* Reinforce the facts-only limitation.
* Provide a relevant educational link (e.g., AMFI or SEBI investor education pages).

### Phase 4: User Interface (Minimal & Premium)
A simple web interface containing:
- A clean, welcoming landing screen.
- Three pre-configured example questions to guide the user.
- A prominent, visible disclaimer:
  > **Facts-only. No investment advice.**

---

## 4. Technical Guardrails & Constraints

| Category | Constraint / Requirement |
| :--- | :--- |
| **Data Sources** | Official public sources (AMC, AMFI, SEBI) only. **Do not** scrape/use third-party blogs or aggregator websites. |
| **Privacy & Security** | Strict data privacy. Do **not** collect, store, or process PII or sensitive financial tokens (PAN, Aadhaar, Account numbers, OTPs, Emails, Phone numbers). |
| **No Advice** | Absolutely no advisory content, recommendations, or qualitative comparison of performance. |
| **Returns & Math** | Do not perform return calculations or performance predictions. For performance queries, provide a direct link to the official factsheet. |
| **Transparency** | Answers must be short, factual, and directly verifiable with a citation and a timestamp. |

---

## 5. Proposed Technology Stack (To Be Decided/Implemented)

* **Data Scraping & Extraction:** Python scripts (using `BeautifulSoup`, `requests`, or PDF parsers like `PyPDF`/`pdfplumber` for SIDs/KIMs).
* **Vector Store & Indexing:** A lightweight vector database (e.g., Chroma, FAISS, or simple JSON-based vector store) for storing document embeddings.
* **LLM Integration:** Retrieval-Augmented Generation using a suitable LLM (e.g., Gemini API or OpenAI API) with structured prompting/guardrails.
* **User Interface:** A minimal, modern frontend (HTML/CSS/JS or Vite/React) with clean typography, responsive layout, and Groww-inspired styling.

---

## 6. Success Criteria

* **Accuracy:** High fidelity in retrieving factual, scheme-specific details.
* **Constraint Adherence:** Strict compliance with sentence counts, single-citation format, and the mandatory footer.
* **Robust Guardrails:** 100% block/refusal rate on advisory and subjective investment queries.
* **Clean Design:** A fast, responsive, and modern user interface that looks professional and trustworthy.
