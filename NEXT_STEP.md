# Estado del proyecto

## Hecho

### 2026-09-28 — Dashboard y evidencias públicas
- Lista de tareas del dashboard: las 32 tareas pendientes pasan a "Done" (confirmado por el autor); fases 1–5 en "Complete".
- Fase 4 lista ahora las 45 entidades de la muestra analítica (las 29 de Stage-4 se publican en `STAGE4_ENTITIES`,
  fuera de `SAMPLE_DATA` para no alterar los ids que lee `run_analysis.py`). "To Verify" = 0.
- Pasos marcados solo con base registrada: clasificación final (dataset de auditoría) y verificación de terceros
  donde hay fuente independiente (22). El resto de pasos (registro, contacto, dirección, financiero, NLP) siguen abiertos.
- `analysis/evidence_urls.csv`: URL de evidencia comprobada para 43/45. **Sin fuente pública: 0xCover (user_3,
  clasificada Confirmed) y Facility (builtin_11, dominio aparcado)** → el manuscrito dice "every record carries
  public evidence": hay que resolverlo antes de enviar.
- Referencia Ratliff (2025): URL de Wired corregida (la anterior daba 404). Saurabh et al.: título corregido.
- Todos los DOI resuelven (Crossref); muestra y consort_flow sin cambios.

### 2026-09-27 — Sincronización Clean → Marked y control final pre-envío
- Cambios del autor en `JEMI_R1_Manuscript_Clean.docx` (eliminación de rayas, recortes de frases,
  retirada de los dos marcadores [AUTHOR TO CONFIRM], "anchoring lens" → "primary analytical framework")
  trasladados a `JEMI_R1_Manuscript_Marked.docx` (azul = añadido, rojo tachado = eliminado); quitados
  los "###" residuales de los títulos del Marked.
- Correcciones: cita Poltronieri (Martins → Xavier, verificado en Crossref); título Floridi
  "AI4People—An ethical framework"; orden alfabético de referencias (S…, Weber-Wulff/Williamson);
  abstract "It has been assembled an…" → "An … sample … was assembled."; Apéndice B empezaba por "Second,".
- Cartas: quitada mención a [AUTHOR TO CONFIRM] (Cover Letter y Response to Editors); recuentos
  actualizados (cuerpo 11,676 palabras; abstract 342).
- Citas ↔ referencias: 45/45 cruzadas, sin huérfanas. Tablas 1–3 y Figuras 1–6 citadas. PDFs regenerados.
- Copias de seguridad previas en el scratchpad de la sesión.

### 2026-09-05 — REVISIÓN R1 PARA JEMI (major revision) — paquete completo

**Hallazgo central de la sesión.** Al preparar el *case-level audit dataset* que exige el
requisito editorial 1, se auditó la procedencia de las 89 filas del workbench de R0 y se
estableció que **44 eran filas de demostración del dashboard (`real:false` en `index.html`),
no entidades observadas**: sembradas como "Pending Verification" y volcadas a un estado final
por `entity_overrides` cuyas notas contienen la *lista de tareas* de verificación, no su
resultado. Las 44 se buscaron en el registro que cada una declaraba, en OpenCorporates y en la
web abierta: **36 NOT FOUND, 8 NAME COLLISION, 0 establecidas**. Ver
`revision_r1/DATA_INTEGRITY_ALERT.md` y `analysis/registry_verdicts.csv`.

**Muestra analítica reconstruida: 45 entidades** (19 verificadas + 26 controles), todas con URL
de evidencia pública. Todo el análisis se recalculó sobre esa base.

#### Resultados R1 (`analysis/run_analysis_v2.py`, seed 42)
- **P1 SOPORTADA**: RF 0.858 [0.667, 1.000] vs línea base mayoritaria 0.578; permutación p = 0.003.
  Sobrevive a holdouts temporal (0.696), jurisdiccional (0.682), por familia de fuente
  (0.818 / 0.824) y por canal de reclutamiento (0.828). CV agrupada por fuente: 0.848.
- **Coste de quitar el score: −0.075** (0.933 con fuga → 0.858 sin ella). Es la respuesta al
  punto 1 de los editores estadísticos.
- **Score como detector**: AUC 0.921 global; **0.900 [0.783, 1.000] en las 29 Stage-4** que no
  seleccionó.
- **P2 SOPORTADA**: 5 dimensiones no redundantes (V de Cramér 0.31–0.76); índice de delegación
  separa grupos (U = 411, p = 8.8×10⁻⁵, r = 0.664). 15 de 216 perfiles ocupados.
- **P3 NO SOPORTADA**: ARI mediana 0.090 (rango [0.000, 0.216]) frente a la banda ex-ante
  [0.15, 0.45] fijada antes de mirar los resultados. Solo 11.1% dentro de banda.
- **P4 NO ESTABLECIDA**: κ = 0.772 pero IC [0.543, 0.944] — el límite inferior queda por debajo
  de 0.70. Se retira además la afirmación κ → 1.00 (tautológica).
- **Corrección factual encontrada en nuestros propios datos**: los 4 desacuerdos entre
  codificadores NO caen en la frontera Synthetic/Shell como decía R0; **los 4 involucran la
  etiqueta Multi-Agent System**, es decir el eje de arquitectura chocando con función delegada y
  gobernanza. Esto respalda empíricamente el rediseño multidimensional.
- **AI-Enhanced Shell: 0 casos verificables.** Se degrada a celda conjeturada no observada
  (decisión del usuario).

#### Entregables en `revision_r1/`
| Fichero | Qué es |
|---|---|
| `JEMI_R1_Manuscript_Marked.docx` / `.pdf` | Manuscrito con **cambios en azul** y supresiones en rojo tachado |
| `JEMI_R1_Manuscript_Clean.docx` / `.pdf` | Versión limpia |
| `JEMI_R1_Title_Page.docx` / `.pdf` | Portada con identidad del autor |
| `JEMI_R1_Cover_Letter.docx` / `.pdf` | Carta al editor (declara el hallazgo de procedencia) |
| `JEMI_R1_Response_to_Editors.docx` / `.pdf` | Respuesta a los 10 requisitos — anonimizada |
| `JEMI_R1_Response_to_Statistical_Editors.docx` / `.pdf` | Respuesta a los 12 puntos — anonimizada |
| `JEMI_R1_Response_to_Reviewer.docx` / `.pdf` | Respuesta al revisor — anonimizada |
| `reviewer_data/` | Dataset de auditoría anonimizado + CONSORT + veredictos registrales + README |
| `undetectable_pass/` | Pasada Undetectable.AI + `ASSESSMENT.md` (**NO fusionada**, ver abajo) |

**Métricas JEMI**: cuerpo 11.884 palabras (límite 8.000–12.000) · abstract 351 (250–350) ·
2 apéndices (A: análisis regulatorio por régimen; B: medición del detector de texto IA) ·
anonimato verificado en los 7 .docx (sin nombre, afiliación, ORCID ni metadatos de autor).

#### Cambios aplicados al manuscrito (77 ediciones + 4 pasadas de recorte)
Taxonomía → 5 dimensiones (D1–D5) con tipos derivados · score fuera de todos los modelos ·
CV anidada con preprocesado dentro de folds · líneas base mayoritaria/estratificada y
permutación (nunca 1/K) · 4 holdouts · matriz completa de clustering (18 configuraciones,
estandarizada) · puerta de solvencia **retirada** · secciones legal y ética reescritas por
régimen (se retira la afirmación del "blind spot" de la EU AI Act, mal dirigida) · GDPR Art. 4(1)
reconocido · cronología de apertura reescrita (era imposible: Tang Yu 2022 y Mika 2023 preceden
a HurumoAI 2025) · terminología unificada · conclusión acortada y matizada.

#### Auditoría de referencias (40/40 comprobadas contra Crossref)
35 verificadas, **5 defectuosas y corregidas**: Murray et al. (DOI 404 → `10.5465/amp.2018.0066`,
AMP 35(4) 622–641, 2021) · Sims 2024 (DOI 404, título pertenece a otros autores → Saurabh, Rani
& Upadhyay 2024, TFSC 204, 123417) · Humberd/Murray/Rouse → **Humberd & Latham** (2 autores) ·
Poltronieri (3.er autor: Xavier, no Martins) · Saraswati (Sam, T. H., no H. S.).
Ver `revision_r1/reference_audit.md`.

#### Pasada Undetectable.AI — ejecutada y NO fusionada
53 de 90 párrafos por encima del umbral; 45 reescritos; puntuación media 97.6 → 7.4. **No se
fusionó**: incluso los párrafos que pasan todos los filtros automáticos introducen corrupción
semántica — cambian el sujeto del argumento en §2.3, **reintroducen la sobreafirmación ética que
el editor estadístico n.º 12 exigió corregir**, debilitan una afirmación legal verificada en
§5.6, e inventan referencias cruzadas ("Chapter 4, Section 1"). Evidencia y ficheros en
`revision_r1/undetectable_pass/ASSESSMENT.md`. Quedan 6.889 → 0 créditos (7 párrafos no se
enviaron por falta de crédito).

#### Web actualizada (`index.html`)
Aviso de revisión · KPIs R1 (45 / 44 excluidas / 0.858 / −0.075 / 0.900 / 2 de 4) · tabla de
proposiciones sustituye a la puerta de solvencia · 4 gráficos recalculados con datos R1 ·
tabla Fase 5 corregida · filas de demostración marcadas en el código · **bug corregido**: los
gráficos se dibujaban con la pestaña oculta (canvas 0×0); ahora se renderizan al abrirla.
Verificado en navegador.

---

## Siguiente paso

1. ~~Marcador [AUTHOR TO CONFIRM]~~ resuelto por el autor (retirado del manuscrito, 2026-09-27).
2. **Publicar el repositorio (HECHO 2026-09-27: push realizado, web y audit_dataset.csv públicos; falta solo sustituir "URL withheld" tras la aceptación)** con `analysis/audit_dataset.csv`, `consort_flow.csv`,
   `registry_verdicts.csv`, `results_v2.json` y el código, y sustituir "URL withheld" por el
   enlace real al aceptarse.
3. **Enviar a `jemi@cognitione.org`** antes del **31 de octubre de 2026**: portada + manuscrito
   ciego (limpio y marcado) + 3 cartas de respuesta + `reviewer_data/`.
4. Anotar el nº de manuscrito en el panel de seguimiento cuando llegue el acuse.

### Pendientes reconocidos ante el editor (declarados, no ocultados)
- Muestra de test verdaderamente independiente (requiere muestreo probabilístico desde registro).
- Instrumento calibrado de detección de texto IA (requiere corpus etiquetado a mano).
- Estudio de fiabilidad con potencia suficiente (solo 10 casos doble-codificados sobreviven).

---

## Notas sobre el repositorio
- El manuscrito y los artefactos de submission permanecen locales (gitignored).
- Se suben: código de análisis, dataset de auditoría, veredictos registrales, figuras R1,
  `index.html` y este fichero.
- Pipeline R0 conservado sin alterar en el historial para poder comparar ambos análisis.
