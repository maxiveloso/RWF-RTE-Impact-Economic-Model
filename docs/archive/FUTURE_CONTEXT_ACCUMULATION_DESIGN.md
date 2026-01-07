# Diseño: Contexto Acumulativo entre Chunks (FUTURO)

**Estado:** No implementado - Evaluar necesidad basada en resultados reales

## Problema a resolver

Cuando un claim requiere información de múltiples secciones del documento:

**Ejemplo:**
- Chunk 1: Menciona "apprenticeship program" pero no el valor 25%
- Chunk 2: Menciona "25% wage increase" pero no menciona apprenticeship
- Resultado actual: Ambos chunks LOW confidence
- Resultado esperado: Conectar ambos → HIGH confidence

## Diseño propuesto

### 1. Estructura de contexto acumulativo

```python
class ChunkContext:
    def __init__(self):
        self.findings = []  # Lista de hallazgos parciales
        self.progressive_summary = ""

    def add_finding(self, chunk_num, match_type, confidence, snippet):
        self.findings.append({
            'chunk': chunk_num,
            'match_type': match_type,
            'confidence': confidence,
            'snippet': snippet
        })

    def get_context_for_next_chunk(self):
        """Resume hallazgos previos para próximo chunk"""
        if not self.findings:
            return ""

        summary = "PREVIOUS FINDINGS:\n"
        for finding in self.findings[-3:]:  # Solo últimos 3 chunks
            summary += f"- Chunk {finding['chunk']}: {finding['match_type']} "
            summary += f"(confidence: {finding['confidence']:.0%})\n"
            summary += f"  Evidence: {finding['snippet'][:200]}...\n"

        return summary
```

### 2. Prompt modificado con contexto

```python
def verify_claim_with_chunking_contextual(
    parameter_name: str,
    claim_text: str,
    claim_value: str,
    document_text: str,
    document_name: str,
    chunk_size: int
) -> Dict:

    context = ChunkContext()

    for i, chunk in enumerate(chunks, 1):
        # Incluir contexto de chunks previos
        context_summary = context.get_context_for_next_chunk()

        prompt = f"""
PARAMETER TO VERIFY:
- Name: {parameter_name}
- Claimed Value: {claim_value}

{context_summary}

CURRENT CHUNK ({i}/{len(chunks)}):
{chunk}

TASK:
Consider both the current chunk AND previous findings above.
If previous chunks found partial evidence, check if this chunk provides
the missing pieces to confirm the claim.
"""

        result = call_llm(prompt)

        # Guardar hallazgo
        context.add_finding(
            chunk_num=i,
            match_type=result['match_type'],
            confidence=result['confidence'],
            snippet=result['snippet']
        )

        # Early exit solo si confidence MUY alta
        if result['confidence'] >= 0.90:  # Mayor threshold
            break
```

### 3. Costo adicional

| Métrica | Sin contexto | Con contexto |
|---------|--------------|--------------|
| Chars por request | 50K | 50K + ~500 (contexto) |
| Tokens por request | ~12.5K | ~12.6K (+0.8%) |
| Costo incremental | - | ~1% más |
| Latencia | ~5-10s/chunk | ~5-11s/chunk |

**Impacto mínimo:** Solo ~1% más costo/latencia.

## Cuándo implementar

### Criterios de decisión:

**Implementar SI:**
- ≥10% de verificaciones tienen confidence 50-70% (partial matches)
- Revisión manual muestra que información está distribuida
- Claims complejos que requieren múltiples evidencias

**NO implementar SI:**
- >80% de verificaciones tienen confidence >85% o <40% (clear cut)
- Early exit funciona bien (mayoría termina en chunk 1-2)
- No hay pattern de información fragmentada

## Alternativa más simple: Post-processing

En lugar de contexto en tiempo real, hacer **análisis post-hoc**:

```python
def consolidate_partial_matches(all_chunk_results):
    """Si múltiples chunks tienen partial matches, combinar evidencia"""

    partial_chunks = [r for r in all_chunk_results if 0.4 < r['confidence'] < 0.7]

    if len(partial_chunks) >= 2:
        # Combinar snippets de todos los partial matches
        combined_evidence = "\n\n".join([r['snippet'] for r in partial_chunks])

        # Re-verificar con evidencia combinada
        final_prompt = f"""
PARAMETER: {parameter_name}
CLAIMED VALUE: {claim_value}

COMBINED EVIDENCE FROM MULTIPLE SECTIONS:
{combined_evidence}

Does this combined evidence support the claim?
"""
        return call_llm(final_prompt)

    return None  # No consolidation needed
```

**Ventaja:** Solo se ejecuta cuando hay múltiples partial matches (raro).
**Costo:** 1 request extra solo en casos edge.

## Recomendación final

1. **Ejecutar verify_claims sin contexto acumulativo**
2. **Analizar resultados:**
   - ¿Cuántos tienen confidence 50-70%?
   - ¿Cuántos early exit en chunk 1-2?
   - ¿Hay pattern de información fragmentada?
3. **Si >15% son partial matches → implementar post-processing consolidation**
4. **Si >30% son partial matches → implementar contexto acumulativo completo**

---

**Creado:** 2026-01-05
**Estado:** Diseño pendiente de validación con datos reales
