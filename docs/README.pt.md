# scraping-detranmg

Scraper de **editais e lotes de leilão** do portal [leilao.detran.mg.gov.br](https://leilao.detran.mg.gov.br/).

Pipeline local: scraping → Postgres (`raw` / `mart`) → notebooks de exploração, análise e watchlist, e UI NiceGUI para marcar lotes.

> Agentes de IA: comece por [`AGENTS.md`](../AGENTS.md). Referência técnica: [`REFERENCE.md`](REFERENCE.md). Práticas do projeto: [`PRACTICES.md`](PRACTICES.md).

## O que já foi feito

| Entrega | Status |
|---------|--------|
| Pacote Python (`httpx` + BeautifulSoup) | Pronto |
| Extração de editais (home) e lotes (listagem + paginação) | Pronto |
| CLI `python -m detran_scraper.run [--lotes] [--lances]` | Pronto |
| Postgres local (Docker, porta **5435**) com camadas raw/mart | Pronto |
| Notebooks 01–03 (exploração + Altair no mart) | Pronto |
| Notebook 04 (watchlist / alerta de lotes novos) | Pronto |
| UI NiceGUI (`python -m detran_ui`, extra `[ui]`) | Pronto |
| Revalidação dos seletores após filtros novos no portal (2026-07) | OK — parsers intactos |
| Testes automatizados de parser (fixtures HTML offline) | Mínimo |
| CI (GitHub Actions) | Pendente |
| Histórico de lances + detalhe (zona logada, `--lances`) | Pronto |
| Persistência de `tipo_veiculo` (só existe como filtro UI) | Pendente |
| Deploy AWS | Pendente |

**Última carga de referência** (`2026-08-09`): 87 editais · 8.605 lotes no run; mart pode acumular mais (upsert sem purge).

## Estrutura

```
scraping-detranmg/
├── AGENTS.md                 # entrada para agentes de IA
├── README.md                 # visão geral (inglês)
├── docs/
│   ├── README.pt.md          # esta página
│   ├── REFERENCE.md          # URLs, seletores, schema, pipeline
│   └── PRACTICES.md          # convenções já adotadas
├── sql/                      # 001_init.sql + 002_lotes_interesse.sql + 003_lotes_lances.sql
├── notebooks/
│   ├── 01_exploracao_editais.ipynb
│   ├── 02_exploracao_lotes.ipynb
│   ├── 03_analise_mart.ipynb
│   └── 04_watchlist_alertas.ipynb
├── src/detran_scraper/
│   ├── client.py
│   ├── models.py
│   ├── parsers.py
│   ├── storage.py
│   └── run.py
├── src/detran_ui/            # UI NiceGUI (`pip install -e ".[ui]"`)
├── tests/
│   └── test_parsers.py
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -e ".[dev]"
copy .env.example .env        # DATABASE_URL → localhost:5435
docker compose up -d
```

## Uso

```bash
# só editais
python -m detran_scraper.run

# editais + lotes
python -m detran_scraper.run --lotes
python -m detran_scraper.run --lotes --max-editais 1
python -m detran_scraper.run --lances
```

```python
from detran_scraper import DetranClient, parse_editais, parse_lotes_from_pages

with DetranClient() as client:
    editais = parse_editais(client.fetch_home())
    pages = client.fetch_lotes_pages("/lotes/lista-lotes/3416/2026")
    lotes = parse_lotes_from_pages(pages, leilao_id=3416)
```

## Modelo de dados

```
run.py --lotes
  ├─► raw.scrape_runs
  ├─► raw.editais / raw.lotes     # snapshot por run
  ├─► mart.editais / mart.lotes   # estado atual (upsert)
  ├─► mart.editais_status_history
  └─► mart.lotes_interesse        # flag da UI (sql/002)
```

### Campos (listagem)

**Edital:** `leilao_id`, `numero_edital`, `municipio`, `patio`, `status`, `data_encerramento`, `url_detalhes`.

**Lote:** `lote_id`, `leilao_id`, `numero_lote`, `condicao`, `marca_modelo`, `valor_atual`. Com `--lances`: `valor_inicial`, cor, anos, combustível, incremento, status e tabela `lotes_lances`.

O portal oferece filtros de **tipo / marca / modelo / ano / cor / condição**, mas o tipo **não** vem no HTML do card; ver [`REFERENCE.md`](REFERENCE.md).

## Notebooks

| Notebook | Objetivo |
|----------|----------|
| `01` | Validar HTTP/HTML/parser de editais |
| `02` | Validar parser de lotes e paginação |
| `03` | KPIs e gráficos Altair no mart |
| `04` | Watchlist: interesse + alerta de lotes novos |

Pré-requisito para `03` e `04`: rodar `python -m detran_scraper.run --lotes` (ou `--max-editais 1 --lotes` para um teste rápido).

```bash
jupyter notebook notebooks/03_analise_mart.ipynb
jupyter notebook notebooks/04_watchlist_alertas.ipynb
```

Fluxo watchlist: rodar `--lotes` → abrir o `04` → editar `INTERESSE` → ver aderentes e novos (`first_seen_at = last_seen_at`).

Para marcar lotes na interface (em vez do dicionário `INTERESSE`):

```bash
pip install -e ".[ui]"
python -m detran_ui
```

Abre `http://127.0.0.1:8080`. A flag grava em `mart.lotes_interesse` (filtro rápido “Somente interesse”).

## Testes

```bash
pytest
```

Fixtures HTML em `tests/fixtures/` — sem rede.
