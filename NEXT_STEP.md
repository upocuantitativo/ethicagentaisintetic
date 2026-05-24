# Estado del proyecto

## Hecho

### 2026-05-24 (sesión actual — pipeline Q1 completo)
1. **8 agentes Q1 creados en `~/.claude/agents/`** (globales, reusables en otros proyectos):
   - `q1-article-orchestrator.md` — coordina el pipeline completo.
   - `q1-research-gap-builder.md` — pregunta de investigación + gap teórico (round 1 antes y round 2 después de resultados).
   - `q1-literature-reviewer.md` — revisión bibliográfica curada en 3 anillos.
   - `q1-intro-writer.md` — introducción con estructura 7-move.
   - `q1-theory-framework-writer.md` — marco teórico **recursivo con ponderación de citas refutadoras y reformulación** (si DL ≥ 13 reformula; si tras 3 iteraciones no converge, escala a gap-builder).
   - `q1-methodology-writer.md` — metodología SEM/PLS-SEM/fsQCA/mixed/OSINT-aware.
   - `json-results-analyst-recursive.md` — análisis recursivo JSON con XAI + robustez + puerta de solvencia (5 criterios).
   - `q1-conclusions-writer.md` — discusión y conclusiones con regla de las 3 contribuciones.
   - Todos llevan baked-in los 10 principios Q1 entrepreneurship (preg. relevante, contribución clara, método sólido, fit revista, capacidad respuesta revisores).

2. **Análisis recursivo del JSON ejecutado** (`analysis/run_analysis.py`):
   - 3 rondas recursivas con puerta de solvencia (convergencia, estabilidad, interpretabilidad, generalización LOCO, sensibilidad a umbrales).
   - **Resultados solventes**: Round 1 (n=89, 4-clase) → 4/4 claims OK. Round 2 (binario) → 3/4 (la 4ª no aplica). Round 3 (n=78 sin controles fáciles) → 4/4 OK.
   - Cohen's κ inter-revisor = 0.772 (95% CI [0.541, 0.942]); RF CV acc 4-clase = 0.73; binario = 0.92–0.94 con 3 estimadores convergiendo.
   - XAI (SHAP + permutation + decision-tree surrogate fidelidad 72%): drivers = log_employees, ai_pct, domain_years, score.
   - Outputs: `analysis/results.json`, `analysis/results_summary.md`, `analysis/entities_unified.csv`.

3. **Revisión bibliográfica Q1** (`literature_review_raw.md`, no se sube):
   - 40 referencias curadas en 3 anillos (anchor / Q1 reciente / bridge legal).
   - Gap sentence y contribution sentence en forma canónica.
   - Target journal: **Small Business Economics** (primario); ETP-Ex Machina special issue (backup).
   - 5 must-cite hostile-reviewer red flags: Bayern 2016, Bryson et al. 2017, LoPucki 2018, Hassan & De Filippi 2021 / Santana & Albareda 2022, Obschonka et al. 2025.

4. **ARTICULO.md + ARTICULO.docx generados** (~7,900 palabras, 6 secciones + abstract + referencias APA7). NO se suben a Git (excluidos via `.gitignore`).

5. **`.gitignore` creado** excluyendo ARTICULO.*, COVER_LETTER.md, REVIEWER_RESPONSE_TEMPLATE.md, BIBLIOGRAPHY.bib, MANUSCRIPT_SELF_AUDIT.md, literature_review_raw.md y artefactos del editor.

### 2026-05-24 (sesión previa)
- Corregido mojibake de doble codificación UTF-8 en `index.html`. Commit `1d002c0`.

---

## Siguiente paso (priorizado)

### Para retomar el ARTÍCULO (Q1 → Small Business Economics)

1. **Verificar las 3 referencias marcadas como `needs verification`** en `literature_review_raw.md` (Csaszar et al. 2024 *Strategy Science*, Li et al. 2025 *Journal of Innovation & Knowledge*, JBR-DAOs-stewardship 2024). Sustituir o eliminar antes de submission.
2. **Generar Cover letter + Highlights + Reviewer Response Template** (artefactos Q1 no opcionales para SBE). Invocar `q1-article-orchestrator`.
3. **Round 2 del agente `q1-research-gap-builder`** sobre los resultados ya solventes: comprobar si la contribución promesa-resultado está perfectamente alineada o si requiere tighten/broaden/pivot.
4. **Pasada formal del agente `q1-theory-framework-writer` recursivo** con disconfirmation-weighting (la sección 2.5 del artículo ya incorpora dos boundary conditions, pero falta el disconfirmation register completo).
5. **Figura 1** (conceptual model) y **Figura 2** (UMAP/PCA scatter de los 89 entities coloreado por taxonomía). `analysis/run_analysis.py` ya genera los datos; falta el script de plot a PNG (`analysis/figures/`).
6. **Co-autoría internacional** (UK/Netherlands/Scandinavia/US/Germany) para fortalecer framing y revisión nativa del inglés.

### Para retomar la EXTENSIÓN DE CHROME (`index.html` como dashboard local)

Estado actual del dashboard:
- 89 companies identified, 61 documented confirmed, 0 pending verification, 38/38 tasks completed.
- 9/9 APIs configuradas en localStorage (Crunchbase, OpenCorporates, GitHub, DeepDAO, SimilarWeb, GPTZero, Etherscan, Companies House UK, SEC EDGAR).
- Cohen's κ = 0.772 (R1 + R2 reviews registrados en localStorage).
- 10 edge cases documentados.
- Verificaciones de 7 pasos completadas para todas las entidades con score > 50.
- Final reviewer notes asignadas a las 60 entidades built-in.

**Pasos para convertir `index.html` en extensión Chrome:**
1. **Crear `manifest.json` v3** declarando `index.html` como popup o sidepanel (`"action": {"default_popup": "index.html"}` o `"side_panel": {"default_path": "index.html"}`).
2. **Refactorizar las llamadas API** que actualmente usan `fetch()` directo desde el HTML para que pasen por un service worker (`background.js`). Las APIs CORS-restringidas (Crunchbase, Companies House) fallarán desde `file://` sin esto.
3. **Mover claves API** de `localStorage` a `chrome.storage.local` para que persistan tras desinstalar/reinstalar.
4. **Añadir permisos** en manifest: `"storage"`, `"activeTab"`, y los `"host_permissions"` para cada API endpoint.
5. **Empaquetar como ZIP** y cargar en `chrome://extensions` en modo developer para test inicial.
6. **(Opcional) Publicar en Chrome Web Store**: requiere cuenta de desarrollador ($5), declaración de privacidad (las APIs leen registros públicos, no datos del usuario), y screenshots de cada vista del dashboard.

---

## Notas sobre el repositorio
- El artículo (`ARTICULO.md`/`ARTICULO.docx`) y los artefactos de soporte de la submission permanecen **siempre locales**, gitignored.
- Todo lo demás (agentes, análisis Python, JSON exportado, NEXT_STEP) se sube a `origin/main`.
- Los agentes Q1 viven en `~/.claude/agents/` (global), no en el repo, para que estén disponibles en cualquier proyecto futuro de Claude Code.
