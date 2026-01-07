# IMPLEMENTATION STATUS - Source Documents & Verification

**Última actualización:** 2026-01-06
**Basado en:** PENDING_SOURCE_DOCUMENTS.md + actualizaciones del usuario

---

## ✅ ACCIONES COMPLETADAS

### 1. Backup y reversión de verify_claims
- ✅ Creado backup: `verify_claims_v1_1_batch_mode_BACKUP.py`
- ✅ Revertido a versión pre-batch: `verify_claims_v1_1.py`

### 2. Actualización de URLs en Supabase
- ✅ **NBER Paper:** Actualizada URL a PDF directo
  - Antes: `https://www.nber.org/papers/w19441`
  - Ahora: `https://www.nber.org/system/files/working_papers/w19441/w19441.pdf`
  - Estado: 1 source actualizado

- ✅ **IZA Paper:** Sin duplicados encontrados
  - URL: `https://docs.iza.org/dp15002.pdf`
  - Estado: 2 sources, sin duplicados

### 3. CSV actualizado procesado
- ✅ Leído: `src/param_sources/Parameters sources - Latest.csv`
- ✅ 75 parámetros cargados

---

## ⚠️ ACCIONES PARCIALMENTE COMPLETADAS

### 1. PLFS MOSPI URLs
**Problema:** No se pueden borrar sources porque tienen foreign key constraints con `claim_verification_log`

**Sources afectados:** 8 de 9 sources con URL MOSPI
- URL problemática: `https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf`
- URL correcta (DGE): `https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf`

**Solución propuesta:**
```python
# En lugar de DELETE, hacer UPDATE:
supabase.table('sources')\\
    .update({'url': dge_url})\\
    .eq('url', mospi_url)\\
    .execute()
```

**Acción pendiente:** Actualizar URLs MOSPI → DGE en lugar de borrar

---

## 📋 ACCIONES PENDIENTES

### 1. Social Discount Rate Paper (murty_panda)
**Estado:** ✅ PDF existe localmente, ⚠️ necesita procesamiento

**Ubicación:** `/Users/maximvf/.../rwf_model/sources/murty_panda_2020_social_time_preference_rate_climate.pdf`

**Pasos necesarios:**
1. Procesar PDF con OCR (usar `extract_and_upload_document.py`)
2. Subir a `source_documents` table en Supabase
3. Verificar que sources apunte al documento correcto

**Parámetro afectado:**
- Social Discount Rate (δ) for India

---

### 2. Actualizar PLFS MOSPI URLs a DGE

**Script necesario:**
```python
# Actualizar en lugar de borrar
mospi_url = "https://www.mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf"
dge_url = "https://dge.gov.in/dge/sites/default/files/2024-10/Annual_Report_Periodic_Labour_Force_Survey_23_24.pdf"

supabase.table('sources')\\
    .update({'url': dge_url})\\
    .eq('url', mospi_url)\\
    .execute()
```

**Parámetros afectados (8):**
- Working Life Duration (Formal)
- Returns to Education - Secondary
- ITI Employment Rate
- Interstate Migration Premium
- Formal Sector Transition Matrix
- RTE Discrimination Effects
- Sector-specific Apprentice Distribution
- (1 más)

---

### 3. Parámetros NO cruciales (desestimados temporalmente)

Según tus notas en PENDING_SOURCE_DOCUMENTS.md:

- ✋ **NFHS-5:** EWS Counterfactual Schooling Distribution
- ✋ **ASER 2023:** 4 parámetros (EWS, unemployment, transition probs, equivalent years)
- ✋ **UDISE:** RTE Program Cost per Student
- ✋ **CAG:** Private School Fee Burden
- ✋ **MOSPI homepage:** School Quality Distribution, Standard Assumptions
- ✋ **NITI Aayog:** Initial Wage Premium (RTE) - "no comprendo qué acción manual se requiere"

**Nota sobre NITI:** El parámetro "Initial Wage Premium (RTE)" debería verificarse automáticamente por verify_claims si el documento está en `source_documents`. No requiere acción manual más allá de asegurar que el PDF esté procesado.

---

## 📊 ESTADO DE SOURCE_DOCUMENTS

**Total documentos en Supabase:** 12

Documentos existentes:
1. ✅ patrinos_2024_returns_to_education.pdf
2. ✅ ILO_2024_25_Global_Wage_Report.pdf
3. ✅ MSDE_annual_report_24_25.pdf (PLFS DGE version)
4. ✅ brunello_depaola_2008_training_economic_density_italian_provinces.pdf
5. ✅ World_Bank_2018_Realize_Education_Promise.pdf
6. ✅ NITI_Aayog_Annual_Report_24_25.pdf
7. ✅ PLFS_changes_in_2025_Final.pdf
8. ✅ MSDE_annual_report_23-24.pdf (PLFS MOSPI version)
9. ✅ muralidharan_sundararaman_2013_aggregate_effect_school_choice.pdf
10. ✅ chen_kanjilal_bhaduri_2022_returns_education_india_plfs.pdf
11. ✅ NITI_Aayog_Industrial_Training_Institutes_2023.pdf
12. ✅ Word_Bank_2018_INDIA_SYSTEMATIC_COUNTRY_DIAGNOSTIC.txt

Pendiente de subir:
- ⚠️ murty_panda_2020_social_time_preference_rate_climate.pdf

---

## 🚀 PRÓXIMOS PASOS RECOMENDADOS

### Paso 1: Actualizar PLFS MOSPI URLs (5 minutos)
```bash
# Crear script update_mospi_urls.py
python update_mospi_urls.py
```

### Paso 2: Procesar murty_panda PDF (10-15 minutos)
```bash
# Usar script existente de OCR
python extract_and_upload_document.py sources/murty_panda_2020_social_time_preference_rate_climate.pdf
```

### Paso 3: Verificar parámetros (30-60 minutos)
```bash
# Correr verify_claims (versión pre-batch, procesamiento secuencial)
python verify_claims_v1_1.py --debug --resume
```

### Paso 4: Analizar resultados
```bash
# Ver CSV de resultados
cat verification_results.csv
```

---

## 📈 IMPACTO ESTIMADO

**Parámetros que se desbloquearán:**

Con las acciones pendientes (Pasos 1-2):
- **~20-25 parámetros** adicionales podrán verificarse
- Incluye parámetros críticos como salarios PLFS, returns to education, social discount rate

Sin las acciones:
- Solo ~10-12 parámetros verificables actualmente

**Total esperado después de implementación completa:**
- **~38 parámetros verificados** (de 77 totales)
- **~39 parámetros restantes** son no-cruciales o model-derived

---

## 🔧 SCRIPTS DISPONIBLES

1. `verify_claims_v1_1.py` - Versión pre-batch (revertida, funcional)
2. `verify_claims_v1_1_batch_mode_BACKUP.py` - Versión batch (backup)
3. `update_sources_from_csv.py` - Actualiza Supabase desde CSV (ejecutado)
4. `analyze_missing_sources.py` - Analiza fuentes faltantes
5. `parameters_missing_sources.csv` - Lista de 39 parámetros sin docs
6. `PENDING_SOURCE_DOCUMENTS.md` - Análisis original con tus notas

---

## 📍 UBICACIÓN DE ARCHIVOS CLAVE

**CSVs:**
- Input: `src/param_sources/Parameters sources - Latest.csv`
- Output: `verification_results.csv` (se genera al correr verify_claims)
- Analysis: `parameters_missing_sources.csv`

**PDFs locales:**
- `/Users/maximvf/.../rwf_model/sources/` (PDFs sin procesar)
- `/Users/maximvf/.../rwf_model/docs/` (posibles PDFs procesados)

**Scripts de procesamiento:**
- Buscar: `extract_and_upload_document.py` o similar
- Verificar en directorio actual si existe script de OCR

---

**FIN DEL DOCUMENTO**
