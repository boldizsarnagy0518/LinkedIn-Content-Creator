"use client";

import { Archive, FileText, Inbox, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { StatusMarker } from "@/app/_components/status-marker";
import type { QueueFilter } from "@/app/_hooks/use-contentops-workspace";
import type { ContentItemSummary } from "@/types/content";
import styles from "@/app/workspace.module.css";

type Props = {
  items: ContentItemSummary[];
  selectedId: string | null;
  filter: QueueFilter;
  loading: boolean;
  onFilterChange: (filter: QueueFilter) => void;
  onSelect: (id: string) => void;
  onCapture: () => void;
};

const filters: Array<{ value: QueueFilter; label: string }> = [
  { value: "active", label: "Minden aktív" },
  { value: "captured", label: "Ötletek" },
  { value: "draft", label: "Szövegek" },
  { value: "changes_requested", label: "Javítandó" },
  { value: "approved", label: "Kész" },
  { value: "archived", label: "Archívum" }
];

function formatQueueDate(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

export function ContentQueue(props: Props) {
  const [query, setQuery] = useState("");
  const visibleItems = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return props.items;
    return props.items.filter((item) => item.title.toLocaleLowerCase().includes(needle));
  }, [props.items, query]);

  return (
    <aside className={styles.queue} aria-label="Content queue">
      <div className={styles.queueHeader}>
        <div>
          <p className={styles.eyebrow}>Saját műhely</p>
          <h2>Ötletek és szövegek</h2>
        </div>
        <button className={styles.iconButtonStrong} onClick={props.onCapture} title="Új ötlet" aria-label="Új ötlet">
          <Plus size={18} />
        </button>
      </div>

      <label className={styles.searchField}>
        <Search size={16} aria-hidden="true" />
        <span className={styles.srOnly}>Keresés a címekben</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Keresés a címekben" />
      </label>

      <div className={styles.filterRail} aria-label="Queue filter">
        {filters.map((option) => (
          <button
            key={option.value}
            aria-pressed={props.filter === option.value}
            className={props.filter === option.value ? styles.filterActive : styles.filterButton}
            onClick={() => props.onFilterChange(option.value)}
          >
            {option.value === "archived" && <Archive size={13} aria-hidden="true" />}
            {option.label}
          </button>
        ))}
      </div>

      <div className={styles.queueList}>
        {props.loading ? (
          <div className={styles.queueEmpty}><span className={styles.loadingBar} /> Betöltés</div>
        ) : visibleItems.length === 0 ? (
          <div className={styles.queueEmpty}>
            {props.filter === "archived" ? <Archive size={22} /> : <Inbox size={22} />}
            <p>{query ? "Nincs találat" : "Itt még nincs feljegyzés"}</p>
          </div>
        ) : (
          visibleItems.map((item, index) => (
            <button
              key={item.id}
              aria-current={item.id === props.selectedId ? "true" : undefined}
              className={item.id === props.selectedId ? styles.queueItemActive : styles.queueItem}
              onClick={() => props.onSelect(item.id)}
            >
              <span className={styles.queueIndex}>{String(index + 1).padStart(2, "0")}</span>
              <span className={styles.queueCopy}>
                <strong>{item.title}</strong>
                <span>
                  <StatusMarker status={item.status} />
                  <time dateTime={item.updatedAt}>{formatQueueDate(item.updatedAt)}</time>
                </span>
              </span>
              <FileText size={15} aria-hidden="true" />
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
