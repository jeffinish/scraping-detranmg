# scraping-detranmg

Scraper de **editais e lotes de leilão** do portal oficial [leilao.detran.mg.gov.br](https://leilao.detran.mg.gov.br/).

Pipeline local validado: scraping → Postgres (`raw`/`mart`) → notebooks de exploração e visualização.

## Status do projeto

| Fase | Descrição | Status |
|------|-----------|--------|
| 1 | Fundação (estrutura + módulo Python) | Concluída |
| 2 | Notebook de exploração e validação (editais) | Concluída |
| 3 | Postgres local (Docker Compose + camadas raw/mart) | Concluída |
| 4 | Pipeline CLI + testes automatizados | Parcial (CLI ok; testes pendentes) |
| 5 | Visualizações no notebook (Altair) | Concluída |
| 6 | Scraping de lotes/veículos | Concluída |
| 7 | Infraestrutura AWS | Planejado |

Plano detalhado, snapshot da carga e roadmap: [`docs/PLANO.md`](docs/PLANO.md)

### Marco MVP local (esta PR)

Entrega end-to-end em ambiente de desenvolvimento:

- Extração de **21 editais** e **1.481 lotes** com `python -m detran_scraper.run --lotes`
- Persistência em camadas `raw` (histórico) e `mart` (estado atual)
- Três notebooks: exploração de editais, exploração de lotes, análise visual do `mart`

### Próximos passos (pós-merge)

| Trilha | Foco | Entregável principal |
|--------|------|----------------------|
| **A — Confiabilidade** | Testes + CI | `tests/test_parsers.py`, fixture HTML, GitHub Actions |
| **C — Detalhe lote** | Página `/lotes/detalhes/{id}` | `valor_inicial`, cor, ano, combustível |
| **D — Produção** | Empacotar → AWS | Dockerfile, ECS/Lambda + RDS |

## Estrutura

```
scraping-detranmg/
├── docker-compose.yml
├── docs/
│   └── PLANO.md                  # plano de trabalho e roadmap
├── sql/
│   └── 001_init.sql              # schemas raw + mart + lotes
├── notebooks/
│   ├── 01_exploracao_editais.ipynb
│   ├── 02_exploracao_lotes.ipynb
│   └── 03_analise_mart.ipynb     # visualização Altair sobre mart
├── src/detran_scraper/
│   ├── client.py                 # HTTP + cookies + retry
│   ├── models.py                 # dataclass Edital, Lote
│   ├── parsers.py                # parse HTML → editais + lotes
│   ├── storage.py                # persistência raw/mart
│   └── run.py                    # CLI scrape → Postgres (--lotes)
├── pyproject.toml
└── .env.example
```

## Modelo de dados (camadas)

```
scrape (run.py --lotes)
    │
    ├─► raw.scrape_runs              metadado da execução
    ├─► raw.editais / raw.lotes      snapshot a cada run (append-only)
    ├─► mart.editais / mart.lotes    último estado por leilao_id / lote_id
    └─► mart.editais_status_history  auditoria Publicado → Finalizado
```

| Tabela | Papel |
|--------|-------|
| `raw.editais` / `raw.lotes` | Histórico: cada extração gera novas linhas |
| `mart.editais` / `mart.lotes` | Tratada: 1 linha por leilão / lote com estado atual |
| `mart.editais_status_history` | Auditoria de mudanças de status |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -e ".[dev]"
copy .env.example .env
```

Dependências principais: `httpx`, `beautifulsoup4`, `pandas`, `sqlalchemy`, `altair`, `jupyter`.

## Carga completa (referência)

Última execução com `python -m detran_scraper.run --lotes`:

| Camada | Registros |
|--------|----------:|
| `mart.editais` | 21 |
| `mart.lotes` | 1.481 |

Detalhes, top modelos e achados técnicos: [`docs/PLANO.md`](docs/PLANO.md).

## Postgres local

Porta do host: **5435** (evita conflito com outros Postgres locais).

```bash
docker compose up -d
docker compose ps

copy .env.example .env   # DATABASE_URL → localhost:5435

python -m detran_scraper.run

# editais + lotes/veículos (todos os editais; use --max-editais para testes)
python -m detran_scraper.run --lotes
python -m detran_scraper.run --lotes --max-editais 1

docker compose exec postgres psql -U scraper -d detran_leiloes -c \
  "SELECT leilao_id, numero_edital, status FROM mart.editais LIMIT 5;"
```

## Uso rápido (Python)

```python
from detran_scraper import DetranClient, parse_editais, parse_lotes_from_pages

with DetranClient() as client:
    html = client.fetch_home()
    editais = parse_editais(html)
    pages = client.fetch_lotes_pages("/lotes/lista-lotes/3416/2026")
    lotes = parse_lotes_from_pages(pages, leilao_id=3416)

print(f"{len(editais)} editais, {len(lotes)} lotes")
```

## Notebooks

| Notebook | Objetivo |
|----------|----------|
| `01_exploracao_editais.ipynb` | Validar HTTP, HTML e parser de editais |
| `02_exploracao_lotes.ipynb` | Validar parser de lotes e paginação |
| `03_analise_mart.ipynb` | KPIs e gráficos Altair sobre dados no Postgres |

```bash
jupyter notebook notebooks/03_analise_mart.ipynb
```

## Dados extraídos (editais)

| Campo | Exemplo |
|-------|---------|
| `leilao_id` | `3416` |
| `numero_edital` | `1692/2026` |
| `municipio` | `Joao Monlevade` |
| `patio` | `JS Servicos De Reboque E Estacionamento Ltda` |
| `status` | `Publicado` / `Finalizado` |
| `data_encerramento` | `2026-08-21 17:55:00` |
| `url_detalhes` | link para lista de lotes |

## Dados extraídos (lotes/veículos)

| Campo | Exemplo |
|-------|---------|
| `lote_id` | `312935` |
| `leilao_id` | `3416` |
| `numero_lote` | `1` |
| `condicao` | `CONSERVADO` |
| `marca_modelo` | `HONDA/C100 BIZ 1999` |
| `valor_atual` | `200.00` |
| `valor_inicial` | `null` na listagem (detalhe do lote — fase futura) |
| `url_detalhes` | `/lotes/detalhes/312935` |
