# Boas práticas já implementadas

Convenções deste repositório. Agentes devem seguir o que já existe em vez de introduzir padrões paralelos.

## Arquitetura

1. **Parser é a fonte única de HTML.** Seletores e regex ficam em `parsers.py`. Notebooks exploram; não viram segunda implementação de produção.
2. **Cliente só faz HTTP.** `DetranClient` baixa páginas, mantém cookies, aplica retry. Não parseia domínio.
3. **Storage só persiste.** `storage.py` fala com Postgres (raw/mart). Sem HTTP.
4. **CLI orquestra.** `run.py` amarra client → parsers → storage.

## Domínio e dados

1. **Dataclasses imutáveis** (`frozen=True`, `slots=True`) para `Edital` / `Lote`.
2. **Dinheiro como `Decimal`**, não `float`. Parsing BRL via `parse_brl`.
3. **Hash do card** (`raw_hash`) para detectar mudança de HTML do item.
4. **Camadas raw/mart:** raw = histórico append-only; mart = upsert do estado atual. Não misturar responsabilidades.
5. **Não inventar campos.** Se o HTML do card não tem o atributo (ex.: `tipo_veiculo`), não fingir que o parser “extrai” — documentar e, se necessário, enriquecer por outro caminho (filtro POST, detalhe, PDF).

## HTTP e robustez

1. **User-Agent + Accept-Language de browser** — sem isso o portal responde 403.
2. **Sessão com cookies** (`httpx.Client` persistente).
3. **Retry exponencial** só em status retryable (`403`, `429`, `503`).
4. **Paginação explícita** (`parse_lotes_max_page` + `?page=N`), não infinite scroll.

## Postgres local

1. Docker Compose, porta host **5435** (evitar conflito com Postgres padrão).
2. Credenciais e URL em `.env` (nunca commitado); template em `.env.example`.
3. Schema versionado em `sql/001_init.sql` — mudanças de coluna exigem SQL + models + storage alinhados.
4. Mart **não faz purge** automático de leilões/lotes ausentes no run atual; números do mart ≥ do último scrape.

## Notebooks

1. Usar para exploração, análise e watchlist — não para substituir a CLI de carga.
2. Watchlist (`04`): critérios em dicionário `INTERESSE`; “novo” ≈ `first_seen_at = last_seen_at` no último run.
3. Heurísticas de marca/modelo/ano a partir de `marca_modelo` ficam na análise; o mart guarda a string bruta.

## Qualidade e dívida conhecida

| Já feito | Ainda aberto |
|----------|----------------|
| Pipeline CLI end-to-end | CI (GitHub Actions) |
| Camadas raw/mart | Scrape de `/lotes/detalhes/{id}` |
| Retry HTTP | Enriquecimento `tipo_veiculo` |
| Docs de agente (`AGENTS.md`, REFERENCE, PRACTICES) | Deploy AWS |
| Testes mínimos de parser (`tests/fixtures/`) | Suite completa + cobertura |

Ao adicionar testes: preferir fixtures HTML offline exercitando `parsers.py` (sem rede).

## Estilo de mudança

1. Diff mínimo; reutilizar helpers existentes.
2. Sem dependência nova se stdlib ou pacote já instalado resolve.
3. Atualizar [REFERENCE.md](REFERENCE.md) quando seletores/URLs/schema mudarem.
4. Atualizar este arquivo quando uma nova convenção for adotada de propósito.
