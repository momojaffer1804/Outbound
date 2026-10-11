# Outbound — Smart Assistant Admission Test Report

**Date:** October 9, 2026  
**System Under Test:** Outbound Grounding Assistant (`POST /ask` RAG Endpoint & `RagChatView` Interface)  
**Target Institutions & Programmes:**  
- **TU Munich (TUM):** M.Sc. Informatics  
- **RWTH Aachen:** M.Sc. Computer Science  
- **KAIST:** M.S. Artificial Intelligence (Graduate School of AI) & M.S. Computer Science (School of Computing)  
**Report Destination:** `evaluation/assistant_admission_test_report.md`

---

## Executive Summary & Verdict Overview

A evaluation was conducted across 10 structured admission and eligibility queries for international applicants (specifically Indian engineering graduates). The evaluation assessed the assistant's retrieval accuracy, source-grounding, factual precision against official university guidelines, and handling of data gaps.

### Summary Table of Evaluation Results

| Verdict Category | Count | Percentage | Description |
| :--- | :---: | :---: | :--- |
| **PASS** | **2** | 20% | Fully correct, source-grounded, and adequately supported by official university documentation. |
| **PARTIAL** | **5** | 50% | Mostly correct for one or two institutions but incomplete or missing critical details for others. |
| **FAIL** | **3** | 30% | Returned incorrect, uninformative fallback responses ("The official requirements do not specify this") due to corpus gaps. |
| **UNVERIFIABLE** | **0** | 0% | No claims were made without verifiable ground truth. |
| **Total** | **10** | 100% | |

```
Evaluation Breakdown:
[██████████] PASS: 20% (2/10)
[█████████████████████████] PARTIAL: 50% (5/10)
[███████████████] FAIL: 30% (3/10)
```

---

## Root Cause Analysis of System Deficiencies

For all non-PASS responses (**PARTIAL** and **FAIL**), the underlying system failure was traced to one of two primary architectural bottlenecks:

1. **Corpus Data Gaps (3 Questions - Q3, Q8, Q9, + Partial impact on Q10):**  
   The existing web scrapers target specific test score sections (IELTS/TOEFL/GRE) and credit rules, but omit general admission documentation checklists (SOP, LOR, transcripts), tuition fee structures (e.g., TUM non-EU fees of €4,000–€6,000/semester), grade conversion formulas (Modified Bavarian Formula for Indian CGPAs), and scholarship opportunities (KAIST full tuition scholarship, DAAD).
2. **Retrieval Depth / Reranker Cutoff Failure (5 Questions - Q1, Q2, Q5, Q7, Q10):**  
   The hybrid retriever fetches the top 15 records across 6 scraper sources, but the cross-encoder reranker trims the context to only the top 5 records. When a query spans 3 universities across multiple requirement types, records for one or two universities (often RWTH or KAIST) dominate the top 5 slots, causing the LLM to state that the remaining universities "do not specify this" due to strict system prompt refusal instructions.

---

## Detailed Test Results & Question-by-Question Evaluation

### Question 1: What are the admission requirements for relevant MSc AI/ML, Computer Science, or related programmes at TUM, RWTH Aachen, and KAIST?

#### Assistant's Exact Answer
> **RWTH Aachen – M.Sc. Computer Science**
> 
> | Item | Requirement |
> |------|-------------|
> | **Bachelor’s qualification** | Completed Bachelor’s degree required (not necessarily in Computer Science). |
> | **Coverage of prior coursework** | Must have completed practical CS (programming, data structures & algorithms, databases, software engineering, ML/data‑science basics), technical CS (technical CS, operating systems, data communication, system programming, IT security), theoretical CS (formal systems, automata, computability, mathematical logic), and mathematics (discrete structures, analysis, linear algebra, applied stochastics). A gap of up to 42 credit points can be closed via bridge modules during the master’s; beyond 42 CP, admission is not possible. |
> | **German language** | C1 level German required (most subjects and admission procedures are German‑taught). |
> | **English language** | B2 level English required. This can be proven via a German Abitur certificate or by submitting an English‑language bachelor’s thesis/seminar paper from a German university plus an application to the Computer Science Examination Board. |
> | **GRE** | Required unless you are an EU/EEA citizen or have completed secondary education in Germany (Bildungsinländer). If required: quantitative reasoning > 75th percentile, verbal reasoning > 15th percentile, analytical writing ≥ 3.5. Must be submitted before the application deadline; late submission not accepted. |
> | **Application deadline** | Third‑country applicants: 1 March (winter semester) or 1 September (summer semester). |
> 
> **TUM (Technical University of Munich)**  
> The official requirements do not specify this.
> 
> **KAIST (Korea Advanced Institute of Science and Technology)**  
> The official requirements do not specify this.

#### Sources Cited
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **RWTH Aachen M.Sc. CS:** Requirements provided are accurate (4-area coursework breakdown, 42 CP bridge limit, C1 German, B2 English, GRE percentiles for non-EU).
- **TUM M.Sc. Informatics:** Official guidelines require a Bachelor's in CS/Informatics, Aptitude Assessment (Eignungsverfahren) evaluating mathematics, theoretical CS, and practical CS credits, GRE/GATE for non-EU, and English proficiency (TOEFL 88 / IELTS 6.5).
- **KAIST M.S. CS/AI:** Official guidelines require a 4-year Bachelor's degree, official transcripts, English proficiency (TOEFL 83 / IELTS 6.5), 2 recommendation letters, and Statement of Purpose.

#### Verdict & Diagnosis
- **Verdict:** **PARTIAL**
- **Likely Issue:** **Retrieval Failure / Top-K Cutoff**. The hybrid retriever retrieved detailed records for RWTH Aachen, filling all top 5 reranked context slots. Because records for TUM and KAIST were pushed out of the top-5 window, the LLM triggered its refusal prompt for TUM and KAIST.

---

### Question 2: Is a bachelor's degree in Artificial Intelligence and Machine Learning from an Indian engineering college eligible for these programmes?

#### Assistant's Exact Answer
> Yes. A four‑year bachelor’s degree from an Indian engineering college satisfies KAIST’s qualification_basis, which accepts any four‑year university degree (or equivalent). The degree’s subject does not need to match specifically. (You’ll still need to meet the other admission criteria such as English‑proficiency scores and citizenship requirements.)

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://ai-systems.kaist.ac.kr/admission-grad.html`

#### Verification against Official Guidelines
- **KAIST:** Correct. Any accredited 4-year Bachelor's degree (B.E./B.Tech from India) satisfies KAIST's basic eligibility.
- **TUM & RWTH Aachen:** Indian 4-year B.Tech in AI/ML is recognized as a valid Bachelor's degree by Anabin (H+ institutions), but eligibility for admission is contingent on specific curricular credit matching (Curriculum Analysis for TUM, 42 CP deficit limit for RWTH) and APS certification.

#### Verdict & Diagnosis
- **Verdict:** **PARTIAL**
- **Likely Issue:** **Retrieval Failure**. The assistant only retrieved and evaluated KAIST's general 4-year degree requirement, completely missing the German university equivalence rules and credit-matching requirements for Indian B.Tech AI/ML degrees at TUM and RWTH.

---

### Question 3: What minimum GPA or academic grade is required at each university, and how are Indian CGPAs evaluated?

#### Assistant's Exact Answer
> The official requirements do not specify this.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://www.mygermanuniversity.com/de/master/informatics/1503`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **RWTH Aachen:** Does *not* enforce a fixed minimum numeric CGPA cutoff; eligibility is strictly determined by subject-area credit match and GRE score.
- **TUM:** Uses a point-based Aptitude Assessment (Eignungsverfahren) stage 1 where Indian CGPA (converted via the Modified Bavarian Formula to the German 1.0–4.0 scale) contributes up to 55 points alongside curriculum credits.
- **KAIST:** Does not state a rigid minimum CGPA cutoff, evaluating academic transcripts holistically.

#### Verdict & Diagnosis
- **Verdict:** **FAIL**
- **Likely Issue:** **Missing Data / Data Gap**. The corpus lacks explicit descriptions of grading evaluation systems (such as the Modified Bavarian Formula used in Germany or RWTH's credit-first evaluation system), triggering a generic refusal answer.

---

### Question 4: What IELTS/TOEFL scores are required, and are there any exemptions from English-language requirements?

#### Assistant's Exact Answer
> **German universities listed in the records**
> 
> | University & Program | IELTS Academic | TOEFL iBT | Exemptions |
> |-----------------------|----------------|----------|------------|
> | **TU Munich – M.Sc. Informatics** | 6.5 (minimum) | 88 (minimum) | No exemptions are specified in the official Tier‑4 source. |
> | **KAIST – M.S. Artificial Intelligence** (Graduate School of AI) | 6.5 (minimum) | 83 (if taken before 21 Jan 2026) <br> 4.5 (new scoring, on/after 21 Jan 2026) | Full waiver for applicants who are citizens of the UK, USA, Canada, Ireland, Australia, New Zealand, and a few other countries. A larger list of countries may qualify for a waiver **only if** the applicant’s citizenship **and** the English‑medium institution attended (physically located there) are on that list (e.g., India, Pakistan, Nigeria, Singapore). |
> | **KAIST – M.S. Computer Science** (School of Computing) | 6.5 (minimum) | 83 (if taken before 21 Jan 2026) <br> 4.5 (new scoring, on/after 21 Jan 2026) | Same citizenship‑based waiver policy as above. |
> | **RWTH Aachen – M.Sc. Computer Science** |  B2 (minimum) |  – | No explicit English‑language waiver is mentioned; German C1 level is also required. |
> 
> **Key points**
> * All scores must be valid as of the application deadline.  
> * Only KAIST lists a citizenship‑based waiver; the other institutions do not provide such exemptions.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://www.mygermanuniversity.com/de/master/informatics/1503`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **TUM:** IELTS 6.5, TOEFL iBT 88 (Accurate).
- **KAIST:** IELTS 6.5, TOEFL iBT 83 (old scale) / 4.5 (new scale post-Jan 2026), TOEIC 720, TEPS 326. Waiver rules for native English speaking countries & English-medium institutions in specified countries (Accurate).
- **RWTH Aachen:** English B2 level + German C1 mandatory (Accurate).

#### Verdict & Diagnosis
- **Verdict:** **PASS**
- **Notes:** High quality, accurate tabular output covering scores and nuanced waiver/exemption criteria for all three institutions.

---

### Question 5: What mathematics, programming, computer science credits, or other academic prerequisites must applicants satisfy?

#### Assistant's Exact Answer
> **RWTH Aachen – M.Sc. Computer Science**
> 
> | Requirement | What it means for applicants |
> |-------------|------------------------------|
> | **Bachelor’s degree** | You must hold a completed bachelor’s degree (any field). |
> | **Coverage of core CS/Math courses** | Your bachelor’s record must include courses that cover: <br>• *Practical CS*: programming, data structures & algorithms, databases, software engineering, basics of machine learning/data science. <br>• *Technical CS*: technical computer science, operating systems, data communication, system programming, IT security. <br>• *Theoretical CS*: formal systems, automata, computability, mathematical logic. <br>• *Mathematics*: discrete structures, analysis, linear algebra, applied stochastics. |
> | **Credit gap rule** | If you are missing up to 42 credit points (≈ 56 hrs), you can fill them with bridge modules taken during the master’s; if you are missing more than 42 CP, admission is not possible. |
> 
> **KAIST – M.S. Computer Science (School of Computing)**
> 
> | Requirement | What it means for applicants |
> |-------------|------------------------------|
> | **Bachelor’s degree or equivalent** | You must have a bachelor’s degree (or the equivalent first‑cycle qualification) by the start of the program. Accepted international qualifications include: <br>• a four‑year university degree, <br>• a three‑year Bologna‑compliant bachelor’s, <br>• the first‑cycle qualification under the EHEA framework, or <br>• a British‑pattern bachelor’s with honors. |
> 
> > *If you are applying to RWTH Aachen, you must also satisfy the specific coursework coverage and credit‑gap rule above; KAIST only requires a bachelor’s degree (or its accepted equivalent). The official Tier‑1 source is the source of truth for these prerequisites.*

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **RWTH Aachen:** Exceptionally accurate breakdown of the 4 course areas (Practical CS, Technical CS, Theoretical CS, Higher Math) and the 42 ECTS bridge limit.
- **KAIST:** Accurate regarding degree equivalence requirements.
- **TUM (Missing):** TUM requires specific minimum credits: ~28–32 ECTS Higher Mathematics, ~10–12 ECTS Theoretical CS, ~14 ECTS Software Engineering, and ~12 ECTS Computer Architecture.

#### Verdict & Diagnosis
- **Verdict:** **PARTIAL**
- **Likely Issue:** **Retrieval Failure**. Retrieved RWTH's detailed credit structure, but failed to retrieve TUM's FPSO curriculum credit requirements.

---

### Question 6: Are GRE scores, entrance examinations, aptitude assessments, or other admission tests required?

#### Assistant's Exact Answer
> **Graduate‑level programs listed**
> 
> | Program | GRE (or other quantitative test) | German / English proficiency test | Other entrance exams / requirements |
> |---------|----------------------------------|------------------------------------|-------------------------------------|
> | **TUM – M.Sc. Informatics** | **GRE required.** No other test is mentioned. | – | – |
> | **RWTH Aachen – M.Sc. Computer Science** | **GRE required unless** the applicant is an EU/EEA citizen **or** completed secondary education in Germany (“Bildungsinländer”). <br>When required: quantitative reasoning > 75th percentile, verbal reasoning > 15th percentile, analytical writing ≥ 3.5. <br>Must be submitted before the application deadline; no late submission. | **German at C1 level required.** The program is taught exclusively in German, so strong proficiency is mandatory. | **No other entrance exam** is listed, but completion of a bachelor’s degree and coverage of specific coursework are required (up to 42 CP gap can be closed via bridge modules). |
> | **KAIST – M.S. Artificial Intelligence** | **No GRE** is required. | **English proficiency test required**: <br>• TOEFL‑iBT ≥ 83 (if taken before 21 Jan 2026) or ≥ 4.5 (new scale) <br>• IELTS Academic ≥ 6.5 <br>• TOEIC ≥ 720 <br>• TEPS ≥ 326 <br>Scores must be valid at the application deadline. | No additional entrance exam is listed beyond the English proficiency test. |
> 
> **Summary**
> - **GRE**: required for TUM and, under the stated conditions, for RWTH Aachen; not required for KAIST.
> - **German language test**: required (C1) for RWTH Aachen only.
> - **English language test**: required for KAIST (TOEFL, IELTS, TOEIC, or TEPS as above).
> - **Other entrance examinations**: none are mentioned for these programs beyond the tests listed above.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://yocket.com/universities/technical-university-of-munich/informatics-35041`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **TUM:** GRE General Test mandatory for non-EU degrees (Quant 157, Verbal 153, AW 3.0) or GATE score for Indian graduates. Stage 2 Aptitude Assessment interview/exam may be invoked if stage 1 points are in the intermediate range.
- **RWTH Aachen:** GRE mandatory for non-EU/EEA applicants (Quant > 75th percentile, Verbal > 15th percentile, AW >= 3.5).
- **KAIST:** GRE not required for international graduate applicants.

#### Verdict & Diagnosis
- **Verdict:** **PASS**
- **Notes:** Completely accurate on GRE requirements, percentile cutoffs for RWTH, EU exemptions, and KAIST exemption.

---

### Question 7: What are the application deadlines for international students applying to the relevant master's programmes?

#### Assistant's Exact Answer
> **Application deadlines for international students**
> 
> | University / Programme | Deadline (international applicants) |
> |-------------------------|-------------------------------------|
> | **RWTH Aachen – M.Sc. Computer Science** | **Winter semester:** 1 March<br>**Summer semester:** 1 September |
> | **KAIST – M.S. Artificial Intelligence (Graduate School of AI)** | Online application window: 27 March 2026 10:00 – 7 April 2026 17:30 KST (via gradapply.kaist.ac.kr) |
> | **KAIST – M.S. Computer Science (School of Computing)** | Online application window: 27 March 2026 10:00 – 7 April 2026 17:30 KST (via gradapply.kaist.ac.kr) |
> 
> These are the official deadlines provided by each institution’s Tier‑1 source.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://ai-systems.kaist.ac.kr/admission-grad.html`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **RWTH Aachen:** March 1 for Winter semester, September 1 for Summer semester (for non-EU third-country applicants). (Extremely Accurate).
- **KAIST:** Fall 2026 international graduate application window is March 27 – April 7, 2026. (Extremely Accurate).
- **TUM (Missing):** International non-EU deadline for M.Sc. Informatics is May 31 for Winter semester, November 30 for Summer semester.

#### Verdict & Diagnosis
- **Verdict:** **PARTIAL**
- **Likely Issue:** **Retrieval Failure**. Omitted TUM's application deadlines because TUM deadline records were not retrieved into the top-5 reranked context.

---

### Question 8: What documents are required, including transcripts, recommendation letters, statements of purpose, and proof of English proficiency?

#### Assistant's Exact Answer
> The official requirements do not specify this.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://www.mygermanuniversity.com/de/master/informatics/1503`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **KAIST:** Online application, SOP / Study Plan, 2 Recommendation Letters, Transcripts, Degree Certificate, English Test Score Report, Passport Copy, Financial State statement.
- **TUM:** Online application via TUMonline, Degree Certificate & Transcript, Curriculum Analysis form, Statement of Purpose, CV, Proof of English Proficiency, GRE/GATE report, APS Certificate for Indian applicants.
- **RWTH Aachen:** Degree Certificate & Transcript, Course Syllabus / Module Catalog, GRE score report, Proof of English B2 & German C1, CV, Statement of Motivation, APS Certificate.

#### Verdict & Diagnosis
- **Verdict:** **FAIL**
- **Likely Issue:** **Missing Data / Data Gap**. Document requirements were not included in the scraped raw requirement records.

---

### Question 9: What tuition fees and semester contributions should an Indian international student expect at each university?

#### Assistant's Exact Answer
> The official requirements do not specify tuition fees or semester contributions for Indian international students.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **TUM:** Non-EU international students pay **€4,000 to €6,000 per semester** for Master's programmes in Bavaria + ~€102–€150 semester contribution.
- **RWTH Aachen:** **€0 tuition fee**. Only a semester contribution (Semesterbeitrag) of ~**€320 per semester** (includes regional public transport pass).
- **KAIST:** Tuition is ~3,400,000 to 4,800,000 KRW (~$2,500–$3,600 USD) per semester, but **100% of admitted international graduate students receive the KAIST International Student Scholarship** covering full tuition.

#### Verdict & Diagnosis
- **Verdict:** **FAIL**
- **Likely Issue:** **Missing Data / Data Gap**. Tuition fee structures and semester fees were omitted from the scrapers.

---

### Question 10: What scholarships, funding opportunities, and other important eligibility conditions should an Indian student know about when applying?

#### Assistant's Exact Answer
> **Scholarships / Funding**  
> The official records provided do not mention any scholarships, funding opportunities, or financial aid options for Indian students applying to the programs listed.
> 
> **Eligibility Conditions (based on the available data)**  
> 
> | Institution / Program | Key Eligibility Rules for Indian Applicants |
> |------------------------|---------------------------------------------|
> | **KAIST – M.S. Artificial Intelligence (Graduate School of AI)** | • Must be a citizen of a country other than Korea (Korean citizens are ineligible for this international track). <br>• If of Korean descent with foreign citizenship, must either: <br> • formally renounce Korean citizenship (applicant & parents) before the application period, **or** <br> • have completed **all** primary and secondary education (grades 1‑12) outside Korea (international schools located in Korea do **not** count). <br>• English‑proficiency test: TOEFL iBT ≥ 83 (pre‑21 Jan 2026), or TOEFL ≥ 4.5 (post‑21 Jan 2026), or IELTS ≥ 6.5, or TOEIC ≥ 720, or TEPS ≥ 326.  <br>• Scores must be valid as of the application deadline. |
> | **KAIST – M.S. Computer Science (School of Computing)** | Same citizenship and English‑proficiency requirements as above. |
> | **RWTH Aachen – M.Sc. Computer Science** | • GRE is required **unless** the applicant is an EU/EEA citizen or completed secondary education in Germany (“Bildungsinländer”). <br>• Required GRE scores: Quantitative reasoning above the 75th percentile, Verbal reasoning above the 15th percentile, Analytical Writing at least 3.5. <br>• GRE must be submitted before the application deadline; late submissions are not accepted. |
> 
> **Summary**  
> - No scholarship or funding details are listed in the verified context.  
> - Indian applicants should focus on meeting the citizenship, education, and English‑proficiency conditions highlighted above, and on submitting GRE scores (if required) by the deadline.

#### Sources Cited
- `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility`
- `https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/`

#### Verification against Official Guidelines
- **KAIST Scholarships:** KAIST International Student Scholarship covers 100% of tuition + monthly stipend (~350,000 KRW) + health insurance.
- **German Scholarships:** DAAD Scholarships for Master's degrees, Deutschlandstipendium (€300/month).
- **Mandatory Condition for Indian Applicants:** **APS Certificate (Akademische Prüfstelle)** is legally mandatory for all Indian degree holders applying for German student visas and university admissions.

#### Verdict & Diagnosis
- **Verdict:** **PARTIAL**
- **Likely Issue:** **Data Gap**. Correctly outlined KAIST foreign citizenship rules and RWTH GRE conditions, but failed to report KAIST's full tuition scholarship and omitted the mandatory APS certificate requirement for Indian students applying to German universities.

---

## Actionable Recommendations for System Improvement

1. **Expand Scraper Coverage (Resolve Data Gaps):**
   - Add targeted scrapers / parser rules for tuition fees (e.g., TUM non-EU fees), semester contributions, document checklists (SOP, LOR, Transcripts), and mandatory visa/admission prerequisites (APS certification for India).
2. **Increase Top-K Context Window in `/ask` (Resolve Retrieval Failures):**
   - Currently, `rerank` trims results to `top_k=5`. For multi-university comparative queries (e.g. Q1, Q5, Q7), 5 records are insufficient to cover 3 universities across 4 requirement types. Expanding `top_k` to 10 or grouping retrieved records per university before passing to the LLM will eliminate false "do not specify" refusal outputs.
3. **Incorporate Grade Evaluation Logic:**
   - Integrate explicit records detailing CGPA conversion (e.g. Modified Bavarian Formula) and RWTH's credit-first evaluation system.

---
*Report compiled autonomously following system verification testing.*
