# PENDING SOURCE DOCUMENTS - Action Items

**Generado:** 2026-01-05
**Estado:** 39 parameter-source pairs sin documentos procesados

---

## RESUMEN EJECUTIVO

- **Total parámetros:** 77
- **Con documentos procesados:** 38 (ya verificados anteriormente)
- **Sin documentos procesados:** 39 parameter-source pairs
- **Documentos en `source_documents`:** 12

## PROBLEMA IDENTIFICADO

La tabla `sources` NO tiene foreign key `source_document_id`. La búsqueda de documentos se hace por:
1. Local file search (por keywords del citation)
2. Supabase `source_documents` table search por `original_url`
3. Fuzzy match por citation

**Issues actuales:**
- Muchos sources tienen URLs que NO matchean exactamente con `source_documents.original_url`
- Algunos sources tienen URLs genéricas (home pages, no PDFs específicos)
- Papers académicos tienen URLs diferentes (NBER abstract page vs PDF directo)

---

## CATEGORÍA 1: DOCUMENTOS QUE YA EXISTEN EN SUPABASE (need URL fix)

Estos documentos están en `source_documents` pero los `sources` tienen URLs ligeramente diferentes:

### 1. PLFS 2023-24 (13 parámetros)

**En `source_documents`:**
- Filename: `MSDE_annual_report_24_25.pdf`
- URL: `https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf`

**En `sources` (no matchean):**
- URL variant 1: `https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf` ✅ EXACTO
- URL variant 2: `https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf` ❌ DIFERENTE

**Acción requerida:**
- Descargar `AnnualReport_PLFS2023-24L2.pdf` (versión MOSPI)
- O actualizar sources para que apunten a la URL DGE que ya está procesada

**Parámetros afectados:**
- Working Life Duration (Formal)
- Returns to Education - Secondary
- ITI Employment Rate
- Interstate Migration Premium
- Formal Sector Transition Matrix
- RTE Discrimination Effects
- Sector-specific Apprentice Distribution

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Se mantuvo URL variant 1 y se eliminó URL variant 2.
---

### 2. MSDE Annual Report 2023-24 (2 parámetros)

**En `source_documents`:**
- Filename: `MSDE_annual_report_23-24.pdf`
- URL: `https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf`

**En `sources`:**
- URL: `https://www.msde.gov.in/static/uploads/2024/11/4f71465f72e9f90ff079f76ca2e374a9.pdf`

**Acción requerida:**
- Verificar si son el mismo documento con diferentes URLs
- Si es diferente, descargar la versión MSDE

**Parámetros:**
- Apprenticeship Placement Rate
- Apprenticeship Stipend During Training

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- `PLFS_Annual_Report_23_24.pdf` debe apuntar a `https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf` (esto viene del punto anterior) ya que `https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf` fue sustituido por el URL de DGE.
- `https://www.msde.gov.in/static/uploads/2024/11/4f71465f72e9f90ff079f76ca2e374a9.pdf` debe hacer referencia a `MSDE_annual_report_23-24`

---

### 3. NBER Paper - Muralidharan & Sundararaman (1-2 parámetros)

**En `source_documents`:**
- Filename: `muralidharan_sundararaman_2013_aggregate_effect_school_choice.pdf`
- URL: `https://www.nber.org/papers/w19441`

**En `sources`:**
- URL variant 1: `https://www.nber.org/papers/w19441` ✅ EXACTO
- URL variant 2: `https://www.nber.org/system/files/working_papers/w19441/w19441.pdf` ❌ DIFERENTE

**Acción requerida:**
- Ambas URLs son el mismo paper, actualizar sources o añadir segunda entrada

**Parámetros:**
- Private School Test Score Gain (Treatment Effect for RTE)

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- El URL correcto es `https://www.nber.org/system/files/working_papers/w19441/w19441.pdf` y esto ya fue actualizado en el csv. Hay que actualizar supabase.

---

### 4. IZA Paper - Chen et al. 2022 (2 parámetros)

**En `source_documents`:**
- Filename: `chen_kanjilal_bhaduri_2022_returns_education_india_plfs.pdf`
- URL: `https://docs.iza.org/dp15002.pdf`

**En `sources`:**
- URL: `https://docs.iza.org/dp15002.pdf` ✅ EXACTO

**Estado:** ✅ DEBERÍA FUNCIONAR

**Parámetros:**
- Returns to Education (β₁) - Higher Secondary
- Returns to Education (β₁) - Higher Secondary (duplicate)

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Deduplicated

---

### 5. World Bank WPS8752 (1 parámetro)

**En `source_documents`:**
- Filename: `World_Bank_2018_Realize_Education_Promise.pdf` (puede ser diferente)
- URL: `https://documents1.worldbank.org/curated/en/123371550594320297/txt/WPS8752.txt`

**En `sources`:**
- URL: `https://documents1.worldbank.org/curated/en/123371550594320297/txt/WPS8752.txt`

**Estado:** ✅ DEBERÍA FUNCIONAR (pero es .txt, no PDF)

**Parámetros:**
- Test Score to Years of Schooling Conversion

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Debería funcionar

---

## CATEGORÍA 2: DOCUMENTOS QUE FALTAN (need download & process)

### 6. Social Discount Rate Paper (1 parámetro)

**URL:** `https://iegindia.org/upload/profile_publication/doc-310320_153806wp388.pdf`

**Acción requerida:**
1. Descargar PDF
2. OCR si es necesario
3. Subir a `source_documents`

**Parámetros:**
- Social Discount Rate (δ) for India

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- El archivo se encuentra en la carpeta /sources/murty_panda_2020_social_time_preference_rate_climate.pdf

---

### 7. NFHS-5 Report (1 parámetro)

**URL (genérica):** `http://rchiips.org/nfhs/`

**Acción requerida:**
1. Buscar PDF específico del NFHS-5 (2019-21) report
2. Descargar y procesar
3. Actualizar URL en sources con PDF específico

**Parámetros:**
- EWS Counterfactual Schooling Distribution

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Este parámetro no es crucial por el momento. Desestimemos pero dejemos registro.

---

### 8. ASER 2023 - Beyond Basics (4 parámetros)

**URL (genérica):** `https://asercentre.org/aser-2023-beyond-basics/`

**Acción requerida:**
1. Buscar PDF del informe ASER 2023 Beyond Basics
2. Descargar y procesar
3. Actualizar URL

**Parámetros:**
- EWS Counterfactual Schooling Distribution
- Time-varying Unemployment
- Formal-Informal Sector Transition Probabilities
- Equivalent Years Validation India

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Estos parámetros no es crucial por el momento. Desestimemos pero dejemos registro.

---

### 9. UDISE Data (1 parámetro)

**URL (genérica):** `https://www.udise.in/`

**Acción requerida:**
1. Identificar documento específico con costos del RTE program
2. Puede ser un report anual de UDISE+ o Ministry of Education

**Parámetros:**
- RTE Program Cost per Student

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Este parámetro no es crucial por el momento. Desestimemos pero dejemos registro.

---

### 10. CAG Report (1 parámetro)

**URL (genérica):** `https://cag.gov.in/`

**Acción requerida:**
1. Buscar audit report del CAG sobre private school fees
2. Probablemente un Performance Audit Report

**Parámetros:**
- Private School Fee Burden (Low-fee)

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Este parámetro no es crucial por el momento. Desestimemos pero dejemos registro.

---

### 11. MOSPI Data (2 parámetros - generic homepage)

**URL (genérica):** `https://www.mospi.gov.in/`

**Acción requerida:**
1. Identificar fuente específica para estos parámetros
2. Puede estar en PLFS u otro report de MOSPI

**Parámetros:**
- School Quality Distribution (RTE)
- Standard Assumptions: Discount, Working Life, Lifecycle

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- Este parámetro no es crucial por el momento. Desestimemos pero dejemos registro.

---

### 12. NITI Aayog Report (1 parámetro)

**URL (genérica):** `https://www.niti.gov.in/`

**En `source_documents` ya hay:**
- `NITI_Aayog_Annual_Report_24_25.pdf`
- `NITI_Aayog_Industrial_Training_Institutes_2023.pdf`

**Acción requerida:**
1. Verificar si el parámetro está en alguno de estos docs
2. Si no, buscar report específico sobre RTE wage premium

**Parámetros:**
- Initial Wage Premium (RTE) - Model-Derived

**ACTUALIZACIÓN RESPUESTA/ACCIÓN TOMADA:**
- No comprendo que acción manual se requiere aquí. El test de verificación del parámetro en los docs es hecho por el script verify_claims

---

## ACCIONES INMEDIATAS

### Opción A: Quick Fix (30 minutos)
1. Actualizar `sources.url` para que matcheen con URLs ya en `source_documents`
2. Re-correr verify_claims en batch mode
3. Esto desbloqueará ~15-20 parámetros

### Opción B: Complete Fix (2-3 horas)
1. Descargar los 6-7 PDFs faltantes
2. Procesar con OCR si es necesario
3. Subir a `source_documents`
4. Re-correr verify_claims
5. Esto completaría TODOS los parámetros

---

## ARCHIVOS RELEVANTES

### Análisis generado:
- `parameters_missing_sources.csv` - Lista completa de 39 parámetros sin documentos

### Ubicación del CSV de verificación:
```bash
# CSV generado por verify_claims_v1_1.py
/path/to/rwf_model/verification_results.csv

# Actualmente vacío porque el último run no verificó ningún parámetro
# (todos fueron skipped por falta de documentos)
```

### Scripts útiles:
- `analyze_missing_sources.py` - Analiza qué falta
- `verify_claims_v1_1.py` - Script principal de verificación (v1.3 batch mode)
- `sync_registry.py` - Sincroniza parameter_registry_v3.py ↔ Supabase

---

## DOCUMENTOS YA PROCESADOS EN `source_documents`

1. ✅ patrinos_2024_returns_to_education.pdf
2. ✅ ILO_2024_25_Global_Wage_Report.pdf
3. ✅ MSDE_annual_report_24_25.pdf (DGE version del PLFS)
4. ✅ brunello_depaola_2008_training_economic_density_italian_provinces.pdf
5. ✅ World_Bank_2018_Realize_Education_Promise.pdf
6. ✅ NITI_Aayog_Annual_Report_24_25.pdf
7. ✅ PLFS_changes_in_2025_Final.pdf
8. ✅ MSDE_annual_report_23-24.pdf (MOSPI version del PLFS)
9. ✅ muralidharan_sundararaman_2013_aggregate_effect_school_choice.pdf (NBER w19441)
10. ✅ chen_kanjilal_bhaduri_2022_returns_education_india_plfs.pdf (IZA DP 15002)
11. ✅ NITI_Aayog_Industrial_Training_Institutes_2023.pdf
12. ✅ Word_Bank_2018_INDIA_SYSTEMATIC_COUNTRY_DIAGNOSTIC.txt

---

## NEXT STEPS

1. **Inmediato:** Revisar `parameters_missing_sources.csv` y decidir estrategia (A o B)
2. **Prioridad:** Los papers académicos (NBER, IZA) deberían matchear - investigar por qué no lo hacen
3. **Mediano plazo:** Descargar y procesar los 6 documentos institucionales faltantes

**FIN DEL DOCUMENTO**
