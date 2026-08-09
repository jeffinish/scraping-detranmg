# Referência técnica

Fonte de verdade para agentes e desenvolvedores. Atualize este arquivo quando URLs, seletores ou schema mudarem.

## Portal

| Item | Valor |
|------|-------|
| Base | `https://leilao.detran.mg.gov.br` |
| Env | `DETRAN_BASE_URL` (ver `.env.example`) |
| Home (editais) | `/` |
| Listagem de lotes | `/lotes/lista-lotes/{leilao_id}/{ano}` + `?page=N` |
| Detalhe do lote | `/lotes/detalhes/{lote_id}` (não scrapado na pipeline atual) |
| Edital PDF | `/documentos-leiloes/edital/{leilao_id}/{ano}` |
| Tabela veículos PDF | `/documentos-leiloes/tabela-veiculos/{leilao_id}/{ano}` |

HTTP: `httpx` com User-Agent de browser, cookies de sessão e retry em `403` / `429` / `503`.

## Filtros do portal (UI)

A home e a listagem de lotes têm formulário POST com campos `Leiloes[...]`:

| Campo form | Significado |
|------------|-------------|
| `tipo_veiculo` | ID numérico (ex.: 4=MOTOCICLETA, 6=AUTOMOVEL) |
| `marca` | Marca |
| `modelo` | Modelo |
| `ano_veiculo` | Ano |
| `cor_veiculo` | Cor |
| `condicao_veiculo` | `R`=CONSERVADO, `S`=SUCATA |
| `municipio_id` | Município (home / contexto do edital) |

**Importante:** esses filtros **não** gravam atributos no HTML de cada `div.card.listaLotes`. O card não expõe `tipo_veiculo`. Para tipar lotes no banco, seria necessário enriquecimento (ex.: varredura POST por tipo, ou PDF da tabela).

## Seletores (parsers.py)

### Editais (`parse_editais`)

- Card: `h5.capa-titulo` → parent `div.card`
- Município: `p.capa-municipio`
- Pátio: `div.card-body.p-1.border-top b` (`N - Nome`)
- Status: `div.text-primary` / `div.text-danger` / `div.text-success` → `Publicado` / `Finalizado` / `Em Andamento`
- Encerramento: texto `Encerramento: DD/MM/YYYY HH:MM` em `div.col-12.text-center`
- Link: `a[href*='/lotes/lista-lotes/']` → `leilao_id`

### Lotes (`parse_lotes`)

- Card: `div.card.listaLotes` com `id` = `lote_id`
- Cabeçalho: spans em `div.card-body b` → `numero_lote`, `condicao`
- `marca_modelo`: bold em `div.card-body div.row` / `div.col-12.text-center`
- Valor: `p#valor_atual_lote_{lote_id}` (`R$ 1.234,56`)
- Paginação: `ul.pagination a.page-link[href*='page=']` → `parse_lotes_max_page`
- Densidade típica: ~8 lotes/página

### Detalhe (não na CLI ainda)

Campos observados na página: valor inicial, marca/modelo, cor, ano modelo, ano fabricação, combustível, condição. Sem campo “Tipo”.

## Pipeline

```
python -m detran_scraper.run [--lotes] [--max-editais N]
  → fetch_home → parse_editais
  → [opcional] fetch_lotes_pages por edital → parse_lotes_from_pages
  → persist_editais (raw append + mart upsert + status history)
  → persist_lotes   (raw append + mart upsert)
  → raw.scrape_runs
```

- **raw:** append-only por `run_id`
- **mart:** estado atual por `leilao_id` / `lote_id` (upsert; **não** remove itens que sumiram da home)
- FK: `mart.lotes.leilao_id` → `mart.editais` (persistir editais antes dos lotes)

## Schema (resumo)

Definido em `sql/001_init.sql`. Postgres via Docker na porta host **5435**.

| Tabela | Papel |
|--------|-------|
| `raw.scrape_runs` | Metadado do run (`editais_count`, status) |
| `raw.editais` / `raw.lotes` | Snapshot por run |
| `mart.editais` / `mart.lotes` | Último estado + `first_seen_at` / `last_seen_at` |
| `mart.editais_status_history` | Publicado ↔ Finalizado ↔ Em Andamento |

## Modelos Python

`Edital` e `Lote` em `models.py`: `@dataclass(frozen=True, slots=True)`. Para DataFrame use `dataclasses.asdict()`, não `__dict__`.

Campos de lote na listagem: `lote_id`, `leilao_id`, `numero_lote`, `condicao`, `marca_modelo`, `valor_atual`, `valor_inicial=None`, `url_detalhes`, `raw_hash`.

## Notebooks

| Arquivo | Papel |
|---------|-------|
| `01_exploracao_editais.ipynb` | Validar home + parser de editais |
| `02_exploracao_lotes.ipynb` | Validar listagem + paginação |
| `03_analise_mart.ipynb` | KPIs Altair sobre mart |
| `04_watchlist_alertas.ipynb` | Interesse do usuário + alerta de lotes novos |

## Carga recente (referência)

Run `2026-07-18` (`9ddfb93a-…`): **23** editais, **1.331** lotes, status `success`. Contagens em `mart.*` podem ser maiores (histórico acumulado sem purge).
