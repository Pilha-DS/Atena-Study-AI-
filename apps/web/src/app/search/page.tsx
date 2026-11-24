"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { SearchHit } from "@/lib/types";
import { Button, EmptyState, Input, PageHeader, StatusBadge } from "@/components/ui";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.search(query.trim());
      setResults(response.results);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro na busca");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Busca"
        description="Pesquise conteúdos e materiais pelo título ou descrição."
        backHref="/"
        backLabel="Voltar ao dashboard"
      />

      <form onSubmit={onSubmit} className="panel mb-8 flex flex-col gap-3 p-5 sm:flex-row">
        <Input
          placeholder="Ex.: algoritmos, redes, capítulo 3..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Buscando..." : "Buscar"}
        </Button>
      </form>

      {error ? <EmptyState title="Falha na busca" description={error} /> : null}

      {!error && searched && results.length === 0 ? (
        <EmptyState
          title="Nenhum resultado"
          description="Tente outro termo ou cadastre novos materiais."
        />
      ) : null}

      <div className="space-y-3">
        {results.map((hit) => {
          const href = hit.content_id ? `/contents/${hit.content_id}` : "/courses";
          return (
            <Link
              key={`${hit.kind}-${hit.id}`}
              href={href}
              className="panel slide-up flex items-start justify-between gap-4 px-5 py-4 transition hover:border-accent"
            >
              <div>
                <p className="text-xs uppercase tracking-wide text-muted">{hit.kind}</p>
                <p className="mt-1 font-medium text-ink">{hit.title}</p>
                {hit.description ? (
                  <p className="mt-1 line-clamp-2 text-sm text-muted">{hit.description}</p>
                ) : null}
              </div>
              {hit.status ? <StatusBadge status={hit.status} /> : null}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
