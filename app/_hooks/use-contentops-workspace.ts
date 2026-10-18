"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "@/lib/contentops-api";
import type { ContentItemDetail, ContentItemSummary, ContentWorkflowStatus, WritingProfile } from "@/types/content";

export type QueueFilter = "active" | ContentWorkflowStatus;

export function useContentOpsWorkspace() {
  const [items, setItems] = useState<ContentItemSummary[]>([]);
  const [detail, setDetail] = useState<ContentItemDetail | null>(null);
  const [profile, setProfile] = useState<WritingProfile | null>(null);
  const [filter, setFilter] = useState<QueueFilter>("active");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const selectedId = useRef<string | undefined>(undefined);
  const filterRef = useRef<QueueFilter>("active");
  const revision = useRef(0);
  const mutationLock = useRef(false);
  const reading = useRef(false);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showNotice = useCallback((message: string) => {
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
    setNotice(message);
    noticeTimer.current = setTimeout(() => setNotice(null), 4200);
  }, []);

  useEffect(() => () => {
    revision.current += 1;
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
  }, []);

  const load = useCallback(async (quiet = false) => {
    if (mutationLock.current || (quiet && reading.current)) return;
    const requestRevision = ++revision.current;
    const selected = selectedId.current;
    reading.current = true;
    try {
      const [nextProfile, result] = await Promise.all([
        api.getWritingProfile(),
        api.listContentItems(filterRef.current === "active" ? undefined : filterRef.current)
      ]);
      // Keep the selected item even when it falls outside a filter or the latest 100 rows.
      const nextId = selected ?? result.items[0]?.id;
      const nextDetail = nextId ? await api.getContentItem(nextId) : null;
      if (requestRevision !== revision.current) return;
      selectedId.current = nextId;
      setItems(result.items);
      setProfile(nextProfile);
      setDetail(nextDetail);
      setConnected(true);
      setError(null);
    } catch (requestError) {
      if (requestRevision !== revision.current) return;
      setConnected(false);
      if (!quiet) setError(requestError instanceof Error ? requestError.message : "A munkatér nem érhető el.");
    } finally {
      if (requestRevision === revision.current) { reading.current = false; setLoading(false); }
    }
  }, []);

  useEffect(() => {
    void load();
    const check = () => { if (document.visibilityState === "visible") void load(true); };
    const timer = setInterval(check, 15000);
    window.addEventListener("focus", check);
    window.addEventListener("online", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", check);
      window.removeEventListener("online", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [load]);

  const selectItem = useCallback(async (id: string) => {
    if (mutationLock.current) return;
    setLoading(true); setError(null);
    selectedId.current = id;
    await load();
  }, [load]);

  const changeFilter = useCallback((next: QueueFilter) => {
    if (filterRef.current === next || mutationLock.current) return;
    filterRef.current = next;
    selectedId.current = undefined;
    setFilter(next);
    setLoading(true); setError(null);
    void load();
  }, [load]);

  const mutate = useCallback(async (label: string, action: () => Promise<ContentItemDetail>, captured = false) => {
    if (mutationLock.current) return null;
    mutationLock.current = true;
    revision.current += 1;
    reading.current = false;
    setBusy(label); setError(null); setNotice(null);
    let result: ContentItemDetail | null = null;
    try {
      result = await action();
      selectedId.current = result.id;
      setDetail(result);
      setConnected(true);
      if (captured) { filterRef.current = "active"; setFilter("active"); }
      setItems((previous) => [result!, ...previous.filter((item) => item.id !== result!.id)]);
      showNotice(label);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "A művelet nem sikerült.");
    } finally {
      mutationLock.current = false;
      setBusy(null);
      setLoading(false);
    }
    // A failed refresh must never turn a successfully saved write into a failed operation.
    if (result) void load(true);
    return result;
  }, [load, showNotice]);

  const captureIdea = useCallback((rawIdea: string, title?: string, requestKey?: string) =>
    mutate("Ötlet elmentve", () => api.captureIdea(rawIdea, title, requestKey), true), [mutate]);
  const captureResearch = useCallback((topic: string, notes: string, urls: string[], requestKey?: string) =>
    mutate("Kutatás elmentve", () => api.captureResearch(topic, notes, urls, requestKey), true), [mutate]);

  const saveProfile = useCallback(async (style: string, audience: string, language: string) => {
    if (mutationLock.current) return;
    mutationLock.current = true;
    revision.current += 1;
    reading.current = false;
    setBusy("Profil mentése"); setError(null);
    try {
      setProfile(await api.updateWritingProfile(style, audience, language));
      showNotice("Hangprofil elmentve");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "A profil nem menthető.");
    } finally { mutationLock.current = false; setBusy(null); setLoading(false); }
  }, [showNotice]);

  const refresh = useCallback(() => {
    if (mutationLock.current) return Promise.resolve();
    setLoading(true); setError(null);
    return load();
  }, [load]);

  return { items, detail, profile, filter, loading, busy, error, notice, connected,
    setFilter: changeFilter, selectItem, refresh, mutate, captureIdea, captureResearch, saveProfile, showNotice };
}
