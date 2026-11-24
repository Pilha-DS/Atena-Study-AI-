# Atena Study AI

Plataforma pessoal de estudos (single-user) com hierarquia **Curso → Tópico → Matéria → Conteúdo**, materiais, anotações, exercícios, provas e geração de estrutura com DeepSeek.

## Stack

- **API:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, OpenAI SDK (DeepSeek)
- **Web:** Next.js 15, React 19, TypeScript, Tailwind CSS
- **Dados:** PostgreSQL 16
- **Infra:** Docker Compose (+ Qdrant reservado para RAG futuro)

## Estrutura

```
apps/api   # backend FastAPI
apps/web   # frontend Next.js
```

## Hierarquia

```
Curso (category: string livre)
 └── Tópico
      └── Matéria
           └── Conteúdo
                ├── Materiais / Anotações
                ├── Exercícios (objetiva | discursiva)
                └── Prova (opcional, 1 por conteúdo)
```

- A **categoria** é atributo do curso (ex.: “Ciência da Computação”), não um nível próprio.
- **Tópicos e matérias têm nível** (`iniciante`, `intermediario`, `avancado`), com cores na UI e desbloqueio progressivo.
- Exercícios e provas pertencem ao **conteúdo**.
- Tentativa objetiva é corrigida automaticamente; discursiva fica `pending_review` (pode ser corrigida pela IA).

## Níveis e desbloqueio

- Cada **tópico** e **matéria** tem um nível: `iniciante` (verde), `intermediario` (âmbar) e `avancado` (rosa).
- Regra automática: um nível só libera quando **todos os conteúdos dos níveis anteriores do curso/tópico estão `concluido`**. Níveis sem conteúdos não bloqueiam.
- Um tópico bloqueado bloqueia todas as matérias e conteúdos dele (leitura permitida, exercícios/provas desabilitados).
- No modo **Editar curso** é possível:
  - trocar o nível de tópico/matéria;
  - marcar **Desbloquear manualmente** (`unlocked_manual`) para ignorar o pré-requisito.
- A IA é instruída a criar o primeiro tópico sempre como `iniciante`, progredindo um nível por vez (nada de começar em avançado).

## Materiais em markdown e vídeos pt-BR

- Materiais de texto são escritos **em markdown** pela IA e renderizados com tipografia (títulos, listas, tabelas, código, citações).
- O conteúdo pode ter **vídeos do YouTube em português**, anexados pela IA via busca (`site:youtube.com`) ou manualmente.
- O player usa `youtube-nocookie.com/embed/{id}` e mantém link “Assistir no YouTube”.
- No conteúdo, os botões de IA são:
  - **Gerar exercícios** — exercícios reais (objetivas + discursivas) com base no material;
  - **Gerar prova** — prova com objetivas e discursivas e pontuação;
  - **Gerar com IA (materiais)** — anexa texto markdown, links e até 2 vídeos pt-BR;
  - **Corrigir com IA** — correção de respostas discursivas (exercício e prova), recalculando a nota.

## Subir com Docker

```bash
cp .env.example .env
docker compose up --build
```

Serviços:

| Serviço | URL |
|---------|-----|
| Web | http://localhost:3100 |
| API | http://localhost:8100 |
| API docs | http://localhost:8100/docs |
| Postgres | localhost:5432 |
| Qdrant | localhost:6333 |

> As portas de host `8100` (API) e `3100` (Web) evitam conflito com serviços comuns em `8000`/`3000`.
>
> O serviço `web` roda `npm install` antes do `next dev`. Isso mantém o volume de `node_modules` sincronizado quando novas dependências entram no `package.json` (ex.: `react-markdown`), evitando o erro `Module not found: Can't resolve '...'`. Se o volume ficar corrompido, rode `docker compose down -v` e suba novamente.

A migration `003` é **destrutiva** nas tabelas de estudo (MVP). `app_settings` permanece.

A migration `004` é **aditiva** e adiciona `level`, `unlocked_manual` em `study_topics` e `level`, `unlocked_manual`, `sort_order` em `subjects`. A API aplica as migrations pendentes no startup.

## DeepSeek

1. Abra **Configurações** no menu lateral
2. Informe a API key da DeepSeek (modelo padrão `deepseek-chat`)
3. Em um **curso**, use **Gerar com IA** e descreva o objetivo de estudo
4. A IA cria **tópicos → matérias → conteúdos** *dentro do curso existente* (ou um curso novo), pesquisando na web para enriquecer os materiais
5. Os **materiais** (texto markdown + vídeos pt-BR) são gerados **em segundo plano**: a trilha aparece em segundos e a página do curso mostra o progresso (`IA anexando materiais... X/Y`), atualizando sozinha. Se algo ficar pendente, use **Gerar agora**

Tunables (opcionais, via `.env`):

- `WEB_SEARCH_INTERVAL_SECONDS` (padrão `1.5`) — intervalo mínimo entre buscas web/YouTube;
- `ENRICH_CONCURRENCY` (padrão `5`) — quantos conteúdos são enriquecidos em paralelo.

A key fica salva em `app_settings` (single-user).

## Desenvolvimento local (sem Docker na API/Web)

1. Suba só o banco:

```bash
docker compose up -d db
```

2. API:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://atena:atena@localhost:5432/atena_study
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

3. Web:

```bash
cd apps/web
npm install
export NEXT_PUBLIC_API_URL=http://localhost:8100
npm run dev
```

No desenvolvimento local sem Docker, a API pode continuar em `8000` se a porta estiver livre — ajuste `NEXT_PUBLIC_API_URL` e `CORS_ORIGINS` conforme necessário.

## Testes da API

```bash
cd apps/api
pip install -e ".[dev]"
pytest
```

Cobre: hierarquia curso→tópico→matéria→conteúdo→material; exercício objetiva + tentativa; prova + tentativa; mock de IA gerando `topics`; desbloqueio por nível (automático e manual); exercícios/prova gerados pela IA + correção de discursivas; busca YouTube (filtro/normalização) e materiais markdown + vídeo.

## Fluxo

1. Em **Cursos**, primeiro você vê a lista dos seus cursos (10 por página, paginação feita no backend) e só depois os botões de criar curso (IA ou manual)
2. Use **Criar curso com IA** ou **Criar manualmente** na seção abaixo da lista
3. No curso aberto, use **Gerar com IA** para ampliar a trilha (tópicos / matérias / conteúdos), respeitando a progressão iniciante→avançado
4. Estudar pela trilha do curso (tópicos agrupados por nível, bloqueios coloridos)
5. No conteúdo: materiais em markdown / vídeos pt-BR, anotações, **exercícios** e **prova** — todos geráveis/corrigíveis pela IA
6. Acompanhar no **dashboard** (que lista apenas cursos com progresso) e usar a **busca**

Rotas antigas `/categories` e `/topics` redirecionam para `/courses`.

## Próximas etapas

Pipelines RAG (LangChain/LangGraph + Qdrant), memória conversacional e observabilidade com LangFuse.
