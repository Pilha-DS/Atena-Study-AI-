"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AppSettings } from "@/lib/types";
import { Button, EmptyState, Input, PageHeader } from "@/components/ui";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [model, setModel] = useState("deepseek-chat");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await api.getSettings();
      setSettings(data);
      setBaseUrl(data.deepseek_base_url);
      setModel(data.deepseek_model);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar configurações");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateSettings({
        deepseek_api_key: apiKey.trim() || undefined,
        deepseek_base_url: baseUrl.trim(),
        deepseek_model: model.trim(),
      });
      setSettings(updated);
      setApiKey("");
      setMessage("Configurações salvas.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function clearKey() {
    if (!confirm("Remover a API key da DeepSeek?")) return;
    setSaving(true);
    try {
      const updated = await api.updateSettings({ clear_api_key: true });
      setSettings(updated);
      setMessage("API key removida.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Falha ao limpar key");
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <EmptyState title="Configurações indisponíveis" description={error} />;
  }

  if (!settings) {
    return <p className="text-muted">Carregando configurações...</p>;
  }

  return (
    <div>
      <PageHeader
        title="Configurações"
        description="Conecte a DeepSeek para gerar cursos e matérias com IA."
        backHref="/"
        backLabel="Voltar ao dashboard"
      />

      <form onSubmit={onSubmit} className="panel max-w-2xl space-y-4 p-5">
        <div className="rounded-xl bg-accent-soft/40 px-4 py-3 text-sm text-ink">
          Status:{" "}
          {settings.deepseek_configured ? (
            <span>
              configurada ({settings.deepseek_api_key_masked})
            </span>
          ) : (
            <span>não configurada</span>
          )}
        </div>

        <label className="block space-y-2 text-sm">
          <span className="text-muted">API key DeepSeek</span>
          <Input
            type="password"
            placeholder={
              settings.deepseek_configured
                ? "Deixe em branco para manter a atual"
                : "sk-..."
            }
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoComplete="off"
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="text-muted">Base URL</span>
          <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="text-muted">Modelo</span>
          <Input value={model} onChange={(e) => setModel(e.target.value)} required />
        </label>

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={saving}>
            {saving ? "Salvando..." : "Salvar"}
          </Button>
          {settings.deepseek_configured ? (
            <Button type="button" variant="secondary" onClick={() => void clearKey()} disabled={saving}>
              Remover API key
            </Button>
          ) : null}
        </div>

        {message ? <p className="text-sm text-muted">{message}</p> : null}
      </form>
    </div>
  );
}
