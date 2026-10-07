# Industrial-KG Fusion

Pipeline reproducible para auditar datos industriales, extraer eventos y entidades, construir un grafo y evaluar recuperación de registros de mantenimiento.

## Ejecución

Python 3.12. Instalar `requirements.txt` y ejecutar desde la raíz:

```powershell
python -m pip install -r requirements.txt
python tools/run_pipeline.py
python -m unittest discover -s tests
```

`python tools/run_pipeline.py --verify` ejecuta dos veces y compara los artefactos científicos. Los originales deben estar en `data/raw`; la muestra congelada de mantenimiento no se sustituye silenciosamente. `data/raw/source_snapshot.json` documenta fuentes y hashes. Los datos voluminosos y el archivo histórico quedan fuera de Git.

## Experimentos

00–04 recorren auditoría, eventos, extracción y grafo. 05 establece baselines y descubre posibles atajos. 06 aplica una evaluación más estricta de identidad del activo. 07 prueba optimización con consultas nuevas reservadas. 08 prepara relevancia técnica: consultas con solo el problema y candidatos con una intervención disponible.

MetroPT contiene mediciones reales; las órdenes de mantenimiento son sintéticas y no identifican los mismos activos. La integración entre fuentes es conceptual. Las discordancias de identidad se auditan sin inventar correspondencias. La optimización de 07 no confirmó mejora frente al texto.

## Revisión de relevancia

Abrir `review/index.html` sin conexión. Oculta método y posición y permite guardar borradores, descargar CSV y respaldos JSON. Conservar archivos separados por revisor. Relevancia: 0 irrelevante, 1 relacionado pero no reutilizable, 2 útil con adaptación, 3 directamente útil para orientar revisión técnica. Registrar incompatibilidad (`yes`, `no`, `uncertain`), revisor y justificación. Usar desarrollo antes de abrir confirmación.

```powershell
python tools/evaluate_independent_review.py --labels anotaciones.csv --split development
python tools/evaluate_independent_review.py --labels anotaciones.csv --split confirmation
```

El evaluador verifica los pares originales y exige etiquetas completas del grupo solicitado. Informa precisión@10, nDCG relativo al conjunto juzgado, e incertidumbre con intervalos por consulta. No estima recall global. Regenerar la plantilla sobrescribe archivos generados: guardar anotaciones por separado.

`python tools/automatic_relevance_review.py` produce un cribado léxico en `results/automatic_review`. Sus etiquetas son automáticas y no independientes; no equivalen a revisión humana ni validan seguridad. Nunca asigna relevancia 3; todos los juicios de seguridad permanecen inciertos. No se seleccionan métodos con estos resultados.

## Alcance

Prototipo de investigación en laboratorio para exploración y recuperación de precedentes. La identidad física, utilidad industrial, diagnóstico causal y recomendaciones de intervención no están validados. Un piloto operativo requiere identidad fiable, revisión técnica independiente y evaluación externa o temporal con datos reales.

## Resultados e interpretación científica

Las siguientes cifras se leen de los resultados guardados, no de estimaciones de rendimiento futuro. Las hipótesis descriptivas se formulan aquí a partir de los experimentos ya realizados: no constituyen un registro previo de hipótesis. Cada conclusión conserva el alcance de su experimento.

### Datos, extracción e integración

- MetroPT-3: 1516948 observaciones reales, 15 canales, intervalo mediano de 10 segundos. Mantenimiento: muestra fija de 50000 registros sintéticos de una fuente independiente.
- Se retiraron 1150 duplicados exactos; quedaron 48850 registros, 9400 identificadores de activo válidos sintácticamente y 410689 menciones de entidades. Una sintaxis válida no certifica identidad física.
- Grafo integrado: 61278 nodos y 621865 aristas, con 48613 órdenes y 2934 eventos. Pasan 7/7 comprobaciones de integración: procedencia, evidencia, extremos existentes y ausencia de enlaces directos de identidad entre fuentes. Son comprobaciones estructurales, no validación semántica humana.
- La revisión de extracción de 100 registros permanece pendiente. Cobertura es presencia de entidades, no precisión ni recall de extracción.


| entity_type | records_with_entity | coverage |
| --- | --- | --- |
| equipment_type | 27207 | 55.695 % |
| failure_mode | 15347 | 31.417 % |
| component | 38449 | 78.708 % |
| maintenance_action | 47709 | 97.664 % |
| asset_mention | 47247 | 96.719 % |


Fuentes y trazabilidad: [manifiesto](results/data_manifest.json), [snapshot](data/raw/source_snapshot.json), [extracción](results/text/summary.json), [grafo](results/kg/summary.json), [comprobaciones](results/kg/integration_checks.csv).

### Eventos sensoriales

La calibración usa solo febrero de 2020 y discrimina regímenes de COMP. Los períodos oficiales de falla se consultan después de fijar la extracción.

| Indicador | Resultado |
| --- | --- |
| Eventos | 2934 |
| Ventanas candidatas / elegibles | 9472 / 41042 |
| Fracción marcada | 23,079 % |
| Períodos de falla solapados | 4 de 4 |
| Horas de ventanas observadas marcadas | 789,333 |
| Duración total de los intervalos de evento, incluyendo huecos fusionados | 1110,333 horas |
| Ventanas sin observaciones suficientes | 13283 |

**Conclusión:** se observa cobertura temporal de los cuatro períodos, con una carga de alertas alta. No se estimó una tasa validada de falsas alarmas, anticipación de fallas ni precisión diagnóstica. Las ventanas no etiquetadas no se asumen saludables. Cuatro períodos no bastan para demostrar generalización.

[Calibración y resumen](results/sensor/summary.json) · [Solapamientos](results/sensor/failure_overlap.csv).

### Diagnóstico inicial de recuperación de categorías — notebook 05

12253 registros, seis categorías extraídas del propio texto y hasta 1500 consultas por división. Se eliminan las frases explícitas de falla y los nodos de falla de las características, pero las etiquetas siguen procediendo del extractor: no son verdad independiente.


| split | method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Equipment-disjoint | Graph context | 98.733 % | 99.600 % | 99.933 % | 99.933 % | 100.000 % | 0.991543 | 0.991574 |
| Equipment-disjoint | Hybrid RRF | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 1.000000 | 1.000000 |
| Equipment-disjoint | Prior | 23.333 % | 23.333 % | 23.333 % | 23.333 % | 23.333 % | 0.233333 | 0.233333 |
| Equipment-disjoint | TF-IDF | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 1.000000 | 1.000000 |
| Random | Graph context | 98.800 % | 99.667 % | 99.800 % | 99.867 % | 99.867 % | 0.991689 | 0.991737 |
| Random | Hybrid RRF | 99.800 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.998667 | 0.998667 |
| Random | Prior | 25.867 % | 25.867 % | 25.867 % | 25.867 % | 25.867 % | 0.258667 | 0.258667 |
| Random | TF-IDF | 99.933 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.999667 | 0.999667 |
| Template-disjoint | Graph context | 91.400 % | 99.000 % | 99.000 % | 99.467 % | 100.000 % | 0.933733 | 0.934157 |
| Template-disjoint | Hybrid RRF | 97.600 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.987889 | 0.987889 |
| Template-disjoint | Prior | 1.800 % | 1.800 % | 1.800 % | 1.800 % | 1.800 % | 0.018000 | 0.018000 |
| Template-disjoint | TF-IDF | 99.933 % | 100.000 % | 100.000 % | 100.000 % | 100.000 % | 0.999667 | 0.999667 |


La división aleatoria comparte 204 textos exactos, 55 plantillas y 994 equipos. La división por plantillas elimina coincidencias de texto/plantilla, pero comparte 792 equipos. La división por equipo elimina equipos comunes, pero mantiene 199 textos exactos y 52 plantillas.

**Conclusión:** los valores cercanos al 100 % son resultados diagnósticos de un corpus sintético con etiquetas derivadas y estructura repetitiva. No acreditan diagnóstico industrial ni recuperación real de fallas. Este hallazgo motivó el objetivo estructurado y controles de 06.

[Auditoría de divisiones](results/retrieval/diagnostic/findings.json) · [Métricas completas](results/retrieval/diagnostic/metrics.csv).

### Recuperación de registros del mismo activo — notebook 06

Cohorte: 38534 registros y 5128 activos; índice de 37034 candidatos; 1500 consultas de 1246 activos. Se excluyen 10 órdenes conflictivas. Todas las consultas tienen al menos un positivo elegible; mediana de 6 positivos en 36799,5 candidatos elegibles.

Se ocultan identificadores numéricos, se excluyen misma fila, orden y plantilla normalizada, se ajustan las representaciones solo con candidatos y se evalúa el conjunto elegible completo. La fusión RRF usa rankings completos. Pasan 8/8 controles programados. La representación del grafo es contexto de entidades a un salto, no un modelo de razonamiento ni una GNN. Se trata de recuperación de activos conocidos: los activos están presentes en el índice, las consultas no.


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Graph context full | 0.200 % | 1.000 % | 2.267 % | 4.400 % | 7.533 % | 0.006049 | 0.008430 |
| Graph context without failure_mode | 0.133 % | 0.867 % | 2.067 % | 3.933 % | 7.667 % | 0.004923 | 0.007334 |
| Hybrid RRF | 0.133 % | 1.067 % | 3.333 % | 4.800 % | 11.133 % | 0.006875 | 0.009785 |
| Masked TF-IDF | 0.400 % | 1.667 % | 3.333 % | 6.600 % | 13.533 % | 0.010198 | 0.014559 |
| Random expectation | 0.022 % | 0.111 % | 0.221 % | 0.442 % | 1.100 % | 0.000649 | 0.000994 |


Hit@k indica si hay al menos un registro del mismo activo entre los k primeros; MRR@k mide el inverso de la posición del primer acierto, o cero si no aparece. Las métricas no deben compararse con el diagnóstico de categorías: cambian objetivo y protocolo.

Hallazgos principales:

- Texto supera la expectativa exacta del azar en Hit@10: lift 15,055839, IC95 % [11,054839; 19,214707]. Grafo completo: lift 10,237971, IC95 % [7,027305; 13,611594]. Existe señal respecto a estas etiquetas sintéticas; no se demuestra identidad física ni utilidad operativa.
- Grafo completo menos texto: Hit@10 −0,010667, IC95 % [−0,019718; −0,001312]. No supera al baseline textual.
- Híbrido menos grafo: Hit@10 +0,010667, IC95 % [0,003987; 0,018018]. Añadir texto mejora ese indicador del grafo solo.
- Híbrido menos texto: MRR@50 −0,004774, IC95 % [−0,008094; −0,002083]. La fusión perjudica el ranking frente a texto; Hit@10 permanece igual.
- Grafo completo menos grafo sin falla: Hit@10 +0,002000, IC95 % [−0,000673; 0,005338], sin mejora confirmada en ese indicador. MRR@50 +0,001096, IC95 % [0,000019; 0,002633]: indicio exploratorio positivo, con intervalo próximo a cero y múltiples comparaciones sin ajuste.

Los IC95 % usan 500 remuestreos por activo, no por filas independientes. No se aplicó corrección por múltiples métricas/comparaciones ni se evaluó sensibilidad a varias semillas; los intervalos no justifican afirmaciones universales.

[Protocolo](results/retrieval/asset/protocol.json) · [Controles](results/retrieval/asset/leakage_checks.csv) · [Todas las diferencias pareadas e IC](results/retrieval/asset/paired_differences.csv) · [Todos los intervalos por método](results/retrieval/asset/confidence_intervals.csv) · [Todos los lifts](results/retrieval/asset/lift.csv).

### Optimización posterior — notebook 07

Se retiraron del índice 1500 consultas nuevas con semilla 314159. Las 1500 consultas expuestas de 06 se usaron para desarrollo. Se compararon seis configuraciones predefinidas, se eligió por MRR@50 de desarrollo y se guardó la selección antes de evaluar confirmación. Las frecuencias y vocabularios se ajustan al índice. La muestra continúa procediendo del corpus ya auditado, sin validación externa ni división temporal real.

Desarrollo:


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| character | 0.200 % | 2.067 % | 3.933 % | 6.933 % | 15.067 % | 0.010057 | 0.014347 |
| graph_idf | 0.200 % | 1.000 % | 2.333 % | 3.800 % | 7.933 % | 0.006155 | 0.008313 |
| word | 0.467 % | 1.933 % | 3.533 % | 6.867 % | 14.000 % | 0.010579 | 0.014763 |
| word_character | 0.400 % | 1.733 % | 3.600 % | 6.933 % | 14.800 % | 0.010584 | 0.015027 |
| word_character_graph | 0.333 % | 1.667 % | 3.200 % | 6.067 % | 13.400 % | 0.009061 | 0.013159 |
| word_graph | 0.067 % | 1.467 % | 3.133 % | 6.133 % | 12.667 % | 0.007382 | 0.011276 |


Se seleccionó `word_character`, pesos 0,5/0,5. Confirmación:


| method | hit@1 | hit@5 | hit@10 | hit@20 | hit@50 | mrr@10 | mrr@50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Random expectation | 0.022 % | 0.109 % | 0.219 % | 0.437 % | 1.087 % | 0.000641 | 0.000982 |
| word | 0.400 % | 1.867 % | 4.733 % | 7.933 % | 15.600 % | 0.012393 | 0.016967 |
| word_character | 0.333 % | 1.667 % | 4.733 % | 8.200 % | 16.200 % | 0.012117 | 0.016837 |



| left | right | metric | difference | ci95_low | ci95_high |
| --- | --- | --- | --- | --- | --- |
| word_character | word | hit@10 | 0.000000 | -0.003646 | 0.003390 |
| word_character | word | mrr@50 | -0.000130 | -0.001713 | 0.001586 |


**Conclusión:** no se confirma mejora de palabras+caracteres frente a palabras. Los IC de ambas diferencias incluyen cero. El 4,733 % de Hit@10 no es una mejora atribuible a optimización sobre el 3,333 % de 06: son consultas e índices diferentes. No se evaluaron todas las configuraciones en confirmación para elegir retrospectivamente otra ganadora.

[Protocolo](results/retrieval/optimization/protocol.json) · [Selección bloqueada](results/retrieval/optimization/locked_selection.json).

### Auditoría de identidad y revisión técnica — notebook 08


| identity_status | records |
| --- | --- |
| discordant_mentions | 45672 |
| matching_only | 318 |
| matching_with_other_mentions | 1 |
| missing_structured_id | 1288 |
| no_textual_id | 1571 |


Entre 47562 registros con identificador estructurado válido, 319 contienen ese mismo código en el texto: 0,6707 %. En toda la muestra deduplicada, 0,6530 %. No se mezclan ambos denominadores. La discordancia no autoriza a reasignar activos; pueden existir menciones de otros componentes/equipos, errores o transformaciones sintéticas.

El [generador publicado](https://github.com/jvachier/industrial-maintenance-synthetic-data/blob/main/src/generators/maintenance_generator.py) modifica Equipment_ID por iteración y conserva las descripciones copiadas. Es un mecanismo plausible de discordancia. La revisión upstream de la muestra congelada es desconocida: no se certifica que ese código explique cada caso local ni se interpreta el sufijo como identidad real.

Se prepararon 81 registros estratificados para comprobar identidades. La revisión técnica utiliza 40 consultas, 20 de desarrollo y 20 de confirmación. Solo el problema consultado entra en el ranking: su intervención conocida y metadatos estructurados quedan fuera. Los candidatos deben incluir acción. Se reúnen los top 10 de palabras, caracteres y grafo IDF; 810 pares únicos quedan disponibles para revisión ciega.

El primer conjunto tenía 727 pares y 353 candidatos sin intervención. Ese hallazgo motivó el filtro de acción disponible; la cifra anterior no se compara con el índice corregido como prueba de mejora independiente. Las anotaciones humanas permanecen pendientes.

### Cribado automático de los 810 pares

Etiquetas por regla léxica fija, coincidencia de familia de código y similitud de problemas. No se asigna grado 3 y todos los juicios de seguridad son inciertos. La regla puede favorecer los métodos textuales y no es independiente del contenido evaluado; estas cifras no prueban precisión técnica real.


| review_split | method | precision_at_10 | pooled_ndcg_at_10 | uncertain_fraction |
| --- | --- | --- | --- | --- |
| confirmation | character | 93.500 % | 0.985682 | 100.000 % |
| confirmation | graph_idf | 28.000 % | 0.303874 | 100.000 % |
| confirmation | word | 92.000 % | 0.978355 | 100.000 % |
| development | character | 90.500 % | 0.980634 | 100.000 % |
| development | graph_idf | 38.500 % | 0.456391 | 100.000 % |
| development | word | 89.500 % | 0.966519 | 100.000 % |


**Conclusión:** 92 % para palabras en confirmación significa concordancia con la regla automática en el top 10. No significa 92 % de recomendaciones correctas, seguras ni aceptadas por especialistas. El 100 % de incertidumbre es una regla de abstención, no una estimación de riesgos. nDCG se refiere al conjunto de candidatos juzgados, no a todos los relevantes de la colección. La división de revisión ya se ha inspeccionado automáticamente y no se presenta como prueba externa ciega.

[Regla y limitaciones](results/automatic_review/protocol.json) · [Pares y justificaciones](results/automatic_review/screened_pairs.csv) · [Revisión independiente pendiente](results/independent_review/protocol.json).

### Hipótesis y estado de la evidencia

| Hipótesis o afirmación | Estado | Alcance y conclusión |
| --- | --- | --- |
| H1. Texto conserva señal respecto a las etiquetas de activo tras los controles implementados | Respaldada en la muestra | Lift Hit@10 superior al azar; no demuestra que la señal identifique máquinas reales |
| H2. Contexto de entidades del grafo conserva señal respecto a esas etiquetas | Respaldada en la muestra | Supera azar, pero pierde frente a texto |
| H3. Añadir texto mejora al grafo solo | Respaldada en Hit@10 de 06 | Comparación pareada positiva; no implica mejora de todos los indicadores |
| H4. Añadir grafo mejora al mejor baseline de texto | No respaldada | Igual Hit@10 y peor MRR@50 para la fusión de 06 |
| H5. Entidades de falla aportan valor incremental al grafo | Evidencia mixta y exploratoria | Hit@10 no confirmado; MRR@50 ligeramente positivo sin ajuste múltiple |
| H6. Palabras+caracteres mejora palabras en nuevas consultas | No confirmada | Diferencias de confirmación compatibles con cero |
| H7. La eventización cubre los períodos de falla conocidos | Observación descriptiva | Solapamiento 4/4, con 23,079 % de ventanas marcadas; falta especificidad y validación de anticipación |
| H8. Las identidades estructuradas concuerdan sistemáticamente con las textuales | No respaldada | 45672 casos discordantes; no se certifica automáticamente qué campo es correcto |
| H9. Un grafo puede integrar fuentes distintas con trazabilidad y sin inventar identidad | Viabilidad estructural demostrada | 7/7 controles; no establece utilidad predictiva ni causalidad |
| H10. El sistema recupera intervenciones útiles y seguras para mantenimiento real | Pendiente | Cribado automático no independiente; faltan especialistas y datos reales relacionados |
| H11. El grafo es más robusto que texto ante información incompleta o deteriorada | No evaluada | Propuesta posterior, todavía sin experimento ni resultado |
| H12. El resultado generaliza a otra fuente, planta o período | No evaluada | No hay validación externa de recuperación |

Las afirmaciones sobre extracción precisa, diagnóstico causal, identidad compartida entre datasets, anticipación validada y preparación para producción tampoco están demostradas. Resultados negativos y pendientes se mantienen como parte del estudio.

### Reproducibilidad y límites de la evidencia

- 00–06: dos ejecuciones completas con kernel limpio por notebook, 54 artefactos idénticos. Es evidencia histórica de esa versión, no certificación de dos ejecuciones completas del pipeline ampliado actual.
- 07: nueve artefactos idénticos en la repetición. 08, después del filtro de intervención: seis artefactos idénticos. La página de revisión tiene generación determinista; su interacción en navegador no se verificó automáticamente.
- 15 pruebas metodológicas pasan. Validan contratos y comportamientos del código, no precisión semántica o utilidad industrial.
- La muestra de mantenimiento es sintética, fija y sin revisión upstream conocida. No se dispone de identificadores compartidos reales entre sensores y texto ni de un corpus independiente de relevancia adjudicada.
- Las hipótesis adicionales se describen después de los resultados, sin atribuirles una preregistración inexistente.

[Verificación original](docs/reproducibility.json) · [Optimización](docs/optimization_reproducibility.json) · [Revisión](docs/independent_review_reproducibility.json) · [Página](docs/review_app_verification.json).

### Conclusión y alcance publicable

El resultado defendible es un prototipo reproducible y un estudio exploratorio sobre auditoría de identidades, atajos de evaluación y comparación de representaciones en mantenimiento sintético, junto con eventización de una fuente sensorial real. No se ha demostrado una mejora del grafo frente al baseline textual ni utilidad industrial de las intervenciones recuperadas.

Scopus es un índice que incluye revistas y actas de congresos; proceedings y Scopus no son alternativas excluyentes. La aceptación se decide por el venue y la revisión del manuscrito, no por el índice. [Cobertura oficial de Scopus](https://www.elsevier.com/products/scopus/content?trial=true).

Valoración conservadora del estado actual, sin predicción de aceptación:

| Destino | Valoración |
| --- | --- |
| Workshop o artículo corto en congreso aplicado | Objetivo inicial plausible si se delimita una contribución metodológica y se redacta un manuscrito sólido; todavía puede rechazarse por novedad o validación insuficientes |
| Artículo completo en congreso selectivo | Evidencia y contribución actuales insuficientes para considerarlo listo |
| Revista indexada en Scopus, incluido Q3/Q4 | No se considera listo; no se puede asignar cuartil al proyecto ni asegurar aceptación en revistas menos citadas |
| Revista competitiva Q1/Q2 | No es un objetivo inmediato defendible con esta evidencia |

Los cuartiles dependen de la revista, categoría, año y sistema de clasificación; no califican directamente un repositorio. Esta valoración es juicio sobre madurez del trabajo, no una revisión externa. Un resultado negativo puede contribuir si aporta una explicación novedosa, controles sólidos y una lección generalizable; reproducibilidad sola no demuestra novedad.

Para avanzar: contrastar literatura y novedad, obtener relevancia adjudicada o una fuente independiente, comprobar robustez en varias semillas, definir métricas primarias y multiplicidad antes de nuevos experimentos, y validar una hipótesis concreta con protocolo reservado. La [revisión de congresos de IEEE](https://conferences.ieeeauthorcenter.ieee.org/understand-peer-review/) considera, entre otros aspectos, si existe una contribución significativa; las [orientaciones de revisión de IEEE Access](https://ieeeaccess.ieee.org/reviewers/reviewer-best-practices/) también exigen benchmarking y validación suficientes y conclusiones respaldadas.

No se han incorporado nuevos datasets externos a estos resultados. Las fuentes externas sugeridas son opciones para próximos estudios, no evidencia ya obtenida.
