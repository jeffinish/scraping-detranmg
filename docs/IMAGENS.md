# Imagens da galeria — download, heurística e rótulos

Fonte de verdade deste capítulo. Chat de rótulos: leia **só este arquivo**; não reabra scrape/dbt/Airflow a menos que o download tenha falhado.

## Objetivo em três degraus

1. **Arquivo histórico** — persistir JPEGs para treino futuro (feito: CAS + Postgres).
2. **Filtro ingênuo + rótulo humano** — a foto é usável? (não preta, não placeholder, não qualidade inútil). **Ainda não** avalia se o veículo está bom/ruim.
3. **Qualidade** — só nas fotos com `valida = true` no rótulo humano. Fora deste capítulo.

`naive_valida` é heurística automática. `mart.lotes_imagens_labels.valida` é o **baseline humano**. Não misturar as duas colunas.

## Layout no disco

Content-addressed (um JPEG por hash; o mesmo placeholder do portal existe uma vez):

```
{IMAGENS_DIR}/                    # default: data/imagens/ (gitignored)
  blobs/{sha256[:2]}/{sha256}.jpg
  rotulos/
    labels.csv                    # amostra para o humano preencher
    {lote_id}_{slot}_{sha12}.jpg  # cópias da amostra
```

`IMAGENS_DIR` no `.env` se o disco não for o default do repo.

O Postgres é o índice: `(lote_id, slot) → sha256 → arquivo`. Histórico de runs em `raw.lotes_imagens` (append-only). Estado atual em `mart.lotes_imagens`.

## O que o download faz

```bash
python -m detran_scraper.run --imagens              # incremental
python -m detran_scraper.run --imagens --max-lotes 20
```

- **Não cria** `raw.scrape_runs` (o tombstone `ativo` do dbt quebraria). Anexa ao último scrape completo de lotes (`max_editais` NULL, com linhas em `raw.lotes`).
- Só **CONSERVADO** ainda sem linha em `mart.lotes_imagens`.
- GET `img_{lote_id}_1.jpg` … até o JPEG placeholder (~5 KB, HTTP 200) ou 404. Teto 12 slots.
- Heurística `naive_avaliar`: `too_small` | `not_image` | `tiny_resolution` | `black` | `flat` | `ok`.
- Placeholder (`too_small`) pára a varredura daquele lote; o blob ainda é gravado (dedup).

DAG `detran_scrape_dbt`: task `scrape_imagens` em paralelo com `dbt_run`, depois de `scrape_lotes`. Requer Pillow na imagem Airflow (`docker compose … build airflow`). No host o CLI basta.

Primeira carga (~2.000 CONSERVADO × ~5 GETs) ~15–40 min. Dias seguintes: só lote novo.

## Rótulos humanos (este capítulo)

```bash
python -m detran_scraper.run --export-rotulos --max-lotes 200
python -m detran_scraper.run --export-rotulos --stress          # ~40 bordas; limpa as cópias em rotulos/
# editar data/imagens/rotulos/labels.csv — coluna valida
python -m detran_scraper.run --import-rotulos data/imagens/rotulos/labels.csv
```

O export pega hashes ainda sem rótulo, **incluindo** placeholder/`too_small`, para amostrar `naive_valida = false`. Um JPEG por sha256; a classe falsa vem primeiro. `--stress` mistura placeholder (calibração), arquivos pequenos, lotes sem placeholder, slot 12 e aleatório. Coluna `strato` é dica da amostra — o import ignora.

`labels.csv`:

| Coluna | Quem preenche | Valores |
|--------|----------------|---------|
| `sha256`, `lote_id`, `slot`, `arquivo`, `naive_valida`, `naive_motivo` | export | não alterar `sha256` |
| `valida` | **você** | `sim` / `nao` (também `1`/`0`, `true`/`false`) |
| `motivo` | opcional | `ok`, `black`, `too_small`, `flat`, `outro` |
| `notes` | opcional | texto livre |

Linhas com `valida` vazia são ignoradas no import. O upsert é por **sha256** (o conteúdo, não o slot).

**Critério desta etapa:** foto tecnicamente usável (dá para ver alguma coisa nítida o bastante). Não rotular estado do veículo, marca, sucata vs conservado do portal, nem “bom negócio”.

## Tabelas

| Tabela | Papel |
|--------|--------|
| `raw.lotes_imagens` | snapshot por scrape de lotes (`run_id` do scrape, não de um run de imagens) |
| `mart.lotes_imagens` | último hash/heurística por `(lote_id, slot)` |
| `mart.lotes_imagens_labels` | `valida`, `motivo`, `notes`, `labeled_at` |

Schema: `sql/006_lotes_imagens.sql`. Código: `src/detran_scraper/imagens.py`.

## Chat de rótulos — o que fazer / não fazer

Fazer: export/import CSV, rubrica, acordo heurística × humano, amostragem, métricas de cobertura, UI/notebook **só** de triagem se faltar.

Não fazer: `--lotes`, dbt, DAG, download em massa, modelo de visão, score de qualidade do veículo, mudar seletores do portal.

## Prompt para abrir o chat

Cole isto num **chat novo** (Composer), com `@docs/IMAGENS.md` e `.cursor/rules/imagens-labels.mdc`:

```
Capítulo só de rótulos humanos das fotos. Leia docs/IMAGENS.md e siga .cursor/rules/imagens-labels.mdc.

Não rode scrape/dbt/Airflow. Não baixe a galeria de novo a menos que mart.lotes_imagens esteja vazio.

Objetivo: eu rotulo uma amostra (labels.csv → valida sim/nao = foto usável, sem julgar o veículo). Você: exportar amostra se faltar, conferir cobertura, importar o CSV quando eu preencher, medir acordo vs naive_valida.

Comece dizendo quantas fotos já temos no mart e se já existe labels.csv.
```
