# Referência técnica

Fonte de verdade para agentes e desenvolvedores. Atualize este arquivo quando URLs, seletores ou schema mudarem.

## Portal

| Item | Valor |
|------|-------|
| Base | `https://leilao.detran.mg.gov.br` |
| Env | `DETRAN_BASE_URL` (ver `.env.example`) |
| Home (editais) | `/` |
| Listagem de lotes | `/lotes/lista-lotes/{leilao_id}/{ano}` + `?page=N` |
| Detalhe do lote | `/lotes/detalhes/{lote_id}` (HTML estático: valor inicial, cor, anos, combustível; tabela de lances vem vazia) |
| JSON listagem (logado) | `GET /PDO/updateCountdown.php?user={id}&data[]={lote_id}` |
| JSON detalhe (logado) | `GET /PDO/updateSingleCountdown.php?user={id}&data={lote_id}` |
| Cookie | `DETRAN_COOKIE` (header `Cookie` do browser; não commitar) |
| Edital PDF | `/documentos-leiloes/edital/{leilao_id}/{ano}` |
| Tabela veículos PDF | `/documentos-leiloes/tabela-veiculos/{leilao_id}/{ano}` |

HTTP: `httpx` com User-Agent de browser, cookies de sessão e retry em `403` / `429` / `503`. `--lances` envia o cookie de usuário; **não** chama `POST /lotes/ajaxLance`.

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
- Foto (não persistida): `img.card-img-top` → `/Imagens/visualizar/leiloes/leilao_{leilao_id}/img_{lote_id}_1.jpg`. A UI deriva essa URL; o scraper não grava `url_imagem`.
- Paginação: `ul.pagination a.page-link[href*='page=']` → `parse_lotes_max_page`
- Densidade típica: ~8 lotes/página

### Detalhe HTML (`parse_lote_detalhe`)

`dl dt` / `dd`: Valor Inicial, Cor, Ano do Modelo, Ano de Fabricação, Combustível. Sem campo “Tipo”. Galeria `img_{lote_id}_N.jpg` não é persistida.

### JSON logado (`parse_update_countdown` / `parse_update_single`)

- Countdown: `valor`, `valorIncremento`, `status` (1–5).
- Single: o mesmo + `ultimosLances[]` (`valor`, `data_hora`, `pre_arrematante`, `peso`, `valor_quilo`).
- ID do usuário: `#preArrematante` ou `#preArrematamte` (typo do portal na listagem).

## Pipeline

```
python -m detran_scraper.run [--lotes] [--lances] [--max-editais N]
  → apply sql/003 (aditivo)
  → fetch_home → parse_editais
  → [opcional] fetch_lotes_pages por edital → parse_lotes_from_pages
  → [--lances] Em Andamento: updateCountdown + updateSingleCountdown + HTML detalhe
  → persist_editais (raw append + mart upsert + status history)
  → persist_lotes   (raw append + mart upsert; COALESCE nos campos de enriquecimento)
  → persist_lances  (raw append + mart upsert; não apaga histórico)
  → raw.scrape_runs
```

- **raw:** append-only por `run_id`
- **mart:** estado atual por `leilao_id` / `lote_id` (upsert; **não** remove itens que sumiram da home)
- FK: `mart.lotes.leilao_id` → `mart.editais` (persistir editais antes dos lotes)

## Schema (resumo)

Definido em `sql/001_init.sql` (install novo), `sql/002_lotes_interesse.sql` (flag da UI) e `sql/003_lotes_lances.sql` (volume existente; só `ADD COLUMN` / `CREATE TABLE IF NOT EXISTS`). Postgres via Docker na porta host **5435**.

| Tabela | Papel |
|--------|-------|
| `raw.scrape_runs` | Metadado do run (`editais_count`, status) |
| `raw.editais` / `raw.lotes` | Snapshot por run |
| `raw.lotes_lances` | Snapshot de lances por run |
| `mart.editais` / `mart.lotes` | Último estado + `first_seen_at` / `last_seen_at` |
| `mart.lotes_lances` | Lances únicos acumulados (`lote_id`+valor+horário+arrematante) |
| `mart.editais_status_history` | Publicado ↔ Finalizado ↔ Em Andamento |
| `mart.lotes_interesse` | Flag manual da UI (`sql/002_lotes_interesse.sql`; a UI aplica na subida) |

## Modelos Python

`Edital`, `Lote` e `Lance` em `models.py`: `@dataclass(frozen=True, slots=True)`. Para DataFrame use `dataclasses.asdict()`, não `__dict__`.

Campos de lote na listagem: `lote_id`, `leilao_id`, `numero_lote`, `condicao`, `marca_modelo`, `valor_atual`, `valor_inicial=None`, `url_detalhes`, `raw_hash`.

`--lances` preenche `valor_inicial`, `cor`, `ano_modelo`, `ano_fabricacao`, `combustivel`, `valor_incremento`, `status_lote` e grava `Lance`.

## UI local

```bash
pip install -e ".[ui]"
python -m detran_ui
cd ui && npm install && npm run dev
```

API FastAPI em `http://127.0.0.1:8080` (`src/detran_ui/`). Vite/React em `ui/`. Filtros no SQL (marca/modelo/município/condição/status/valor/ano) + flag em `mart.lotes_interesse`. Foto: proxy `/imagens/{lote_id}` com headers de browser; URL derivada, não coluna no mart.

Após `npm run build`, o mesmo `python -m detran_ui` serve a UI em `http://127.0.0.1:8080`.

## Notebooks

| Arquivo | Papel |
|---------|-------|
| `01_exploracao_editais.ipynb` | Validar home + parser de editais |
| `02_exploracao_lotes.ipynb` | Validar listagem + paginação |
| `03_analise_mart.ipynb` | KPIs Altair sobre mart |
| `04_watchlist_alertas.ipynb` | Interesse do usuário + alerta de lotes novos |

## Carga recente (referência)

Run `2026-07-18` (`9ddfb93a-…`): **23** editais, **1.331** lotes, status `success`. Contagens em `mart.*` podem ser maiores (histórico acumulado sem purge).
