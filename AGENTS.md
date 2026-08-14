# AGENTS.md — ponto de entrada para agentes de IA

Leia este arquivo antes de alterar o repositório. Detalhes técnicos e convenções estão nos docs linkados abaixo.

## Mapa rápido

| Precisa de… | Vá em… |
|-------------|--------|
| Visão humana / setup | [README.md](README.md) |
| URLs, seletores, schema, pipeline | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Convenções já adotadas no código | [docs/PRACTICES.md](docs/PRACTICES.md) |
| Código do scraper | `src/detran_scraper/` |
| UI local (lotes + flag) | `src/detran_ui/` |
| Schema Postgres | `sql/001_init.sql` + `sql/002_lotes_interesse.sql` |

## Escopo do projeto

Scraper local do portal [leilao.detran.mg.gov.br](https://leilao.detran.mg.gov.br/): editais + lotes → Postgres (`raw` / `mart`) → notebooks + UI NiceGUI.

**Não está no escopo atual:** AWS, testes automatizados (dívida), scrape completo de detalhe do lote, persistência de `tipo_veiculo` (filtro do portal, não campo no card).

## Onde mudar o quê

| Mudança | Arquivo(s) |
|---------|------------|
| HTML / seletores / regex | `parsers.py` (fonte única) |
| HTTP, headers, paginação | `client.py` |
| Campos de domínio | `models.py` + `sql/001_init.sql` + `storage.py` |
| Orquestração CLI | `run.py` |
| UI / flag de interesse | `src/detran_ui/` (não misturar com o scraper) |
| Exploração / watchlist | `notebooks/` (não duplicar lógica de produção sem necessidade) |

## Regras operacionais

1. Preferir o menor diff que resolve o problema.
2. Não inventar campos no card que o HTML não expõe (ex.: `tipo_veiculo`).
3. Validar parser contra HTML real ou fixture antes de “corrigir” no escuro.
4. Após mudança de schema do scraper: atualizar `sql/001_init.sql`, models e storage juntos. Tabela da UI: `sql/002_*.sql` (a UI aplica na subida).
5. Não commitar `.env`, dumps HTML locais (`_diag/`), nem outputs grandes de notebook sem pedido.

## Comando de referência

```bash
docker compose up -d
python -m detran_scraper.run --lotes
pip install -e ".[ui]"
python -m detran_ui
```
