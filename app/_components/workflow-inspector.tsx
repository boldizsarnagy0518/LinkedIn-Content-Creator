"use client";

import { AuthorMemoryDialog } from "@/app/_components/author-memory";

import {
  Activity,
  CalendarClock,
  Check,
  Clipboard,
  MessageSquareText,
  RotateCcw,
  Send,
  SlidersHorizontal
} from "lucide-react";
import { useState } from "react";
import { PublicationMarker } from "@/app/_components/status-marker";
import type { ContentItemDetail, WritingProfile } from "@/types/content";
import styles from "@/app/workspace.module.css";

type InspectorTab = "review" | "publish" | "voice" | "activity";

type Props = {
  detail: ContentItemDetail | null;
  profile: WritingProfile | null;
  busy: boolean;
  reviewBlocked: boolean;
  onRequestChanges: (feedback: string) => Promise<unknown>;
  onApprove: () => Promise<unknown>;
  onRevokeApproval: () => Promise<unknown>;
  onPlan: (plannedFor: string, timezone: string) => Promise<unknown>;
  onConfirmExternal: (note: string) => Promise<unknown>;
  onMarkPublished: (note?: string) => Promise<unknown>;
  onRecordPerformance: (metrics: {
    impressions?: number;
    reactions?: number;
    comments?: number;
    reposts?: number;
    notes?: string;
  }) => Promise<unknown>;
  onSaveProfile: (style: string, audience: string, language: string) => Promise<void>;
};

const tabOptions: Array<{ value: InspectorTab; label: string; icon: typeof Check }> = [
  { value: "review", label: "Átnézés", icon: MessageSquareText },
  { value: "publish", label: "Megjelenés", icon: CalendarClock },
  { value: "voice", label: "Hangprofil", icon: SlidersHorizontal },
  { value: "activity", label: "Napló", icon: Activity }
];

function eventLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function WorkflowInspector(props: Props) {
  const [tab, setTab] = useState<InspectorTab>("review");
  const [memoryOpen, setMemoryOpen] = useState(false);

  return (
    <aside className={styles.inspector} aria-label="Workflow inspector">
      <nav className={styles.inspectorTabs} aria-label="Inspector sections">
        {tabOptions.map((option) => {
          const Icon = option.icon;
          return (
            <button
              key={option.value}
              data-active={tab === option.value}
              onClick={() => setTab(option.value)}
              title={option.label}
              aria-label={option.label}
            >
              <Icon size={17} />
              <span>{option.label}</span>
            </button>
          );
        })}
      </nav>
      <div className={styles.inspectorBody}>
        {tab === "voice" && <div className={styles.inspectorSection}><button className={styles.secondaryButton} onClick={() => setMemoryOpen(true)}>Profil és korábbi posztok</button></div>}
        {tab === "review" && <ReviewPanel key={props.detail?.id ?? "empty"} {...props} />}
        {tab === "publish" && <PublishPanel key={props.detail?.id ?? "empty"} {...props} />}
        {tab === "voice" && <VoicePanel key={props.profile?.updatedAt ?? "empty-profile"} {...props} />}
        {tab === "activity" && <ActivityPanel detail={props.detail} />}
      </div>
      {memoryOpen && <AuthorMemoryDialog onClose={() => setMemoryOpen(false)} />}
    </aside>
  );
}

function ReviewPanel(props: Props) {
  const [feedback, setFeedback] = useState("");
  const current = props.detail?.versions.at(-1) ?? null;
  const canReview = Boolean(current && props.detail?.status !== "archived" && !props.reviewBlocked);
  const canApprove = Boolean(
    current &&
    props.detail?.status === "draft" &&
    !props.reviewBlocked &&
    !props.detail.activeApproval
  );

  if (!props.detail) return <InspectorEmpty label="Válassz egy szöveget az átnézéshez" />;
  if (!current) return <InspectorEmpty label="Az első mentett draft után itt nézheted át a szöveget" />;

  return (
    <section className={styles.inspectorSection}>
      <header>
        <p className={styles.eyebrow}>Átnézés</p>
        <h2>Elkészült a szöveg?</h2>
        <p className={styles.handoffNote}>v{current.versionNumber} · mentett változat</p>
      </header>

      {props.reviewBlocked && <p className={styles.inlineNote}>Jóváhagyáshoz a legfrissebb mentett verziót nyisd meg. A helyi módosításokat előbb mentsd.</p>}
      {props.detail.activeApproval ? (
        <div className={styles.approvalStamp}>
          <Check size={20} />
          <div>
            <strong>Jóváhagyva · v{current.versionNumber}</strong>
            <span>{formatDate(props.detail.activeApproval.approvedAt)}</span>
          </div>
          <button
            className={styles.iconButton}
            title="Jóváhagyás visszavonása"
            aria-label="Jóváhagyás visszavonása"
            onClick={() => void props.onRevokeApproval()}
            disabled={props.busy}
          >
            <RotateCcw size={16} />
          </button>
        </div>
      ) : (
        <button className={styles.approveButton} onClick={() => void props.onApprove()} disabled={!canApprove || props.busy}>
          <Check size={17} /> v{current.versionNumber} jóváhagyása
        </button>
      )}

      {props.detail.status === "changes_requested" && (
        <p className={styles.inlineNote}>A visszajelzés után új változatot kell menteni.</p>
      )}

      <form className={styles.inspectorForm} onSubmit={async (event) => {
        event.preventDefault();
        const result = await props.onRequestChanges(feedback);
        if (result) setFeedback("");
      }}>
        <label>
          <span>Mit változtatnál?</span>
          <textarea
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            rows={5}
            placeholder="Például: rövidebben, saját példával, kevésbé formálisan."
            disabled={!canReview}
          />
        </label>
        <button className={styles.secondaryButton} disabled={!canReview || feedback.trim().length === 0 || props.busy}>
          <MessageSquareText size={16} /> Visszajelzés és draftkérés
        </button>
      </form>

      <div className={styles.feedbackList}>
        {props.detail.feedback.toReversed().map((item) => (
          <article key={item.id}>
            <span>v{props.detail?.versions.find((version) => version.id === item.versionId)?.versionNumber ?? "?"}</span>
            <p>{item.message}</p>
            <time dateTime={item.createdAt}>{formatDate(item.createdAt)}</time>
          </article>
        ))}
      </div>
    </section>
  );
}

function PublishPanel(props: Props) {
  const [plannedFor, setPlannedFor] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [publicationNote, setPublicationNote] = useState("");
  const [metrics, setMetrics] = useState({ impressions: "", reactions: "", comments: "", reposts: "", notes: "" });
  const detail = props.detail;
  const current = detail?.versions.at(-1) ?? null;

  if (!detail) return <InspectorEmpty label="Válassz egy szöveget a megjelenéshez" />;

  const plan = detail.publicationPlan;
  const published = plan?.status === "published";

  return (
    <section className={styles.inspectorSection}>
      <header>
        <p className={styles.eyebrow}>Kézi publikálás</p>
        <h2>Megjelenés</h2>
        {plan && <PublicationMarker status={plan.status} />}
      </header>

      {!plan || plan.status === "cancelled" ? (
        <form className={styles.inspectorForm} onSubmit={(event) => {
          event.preventDefault();
          if (current) void props.onPlan(new Date(plannedFor).toISOString(), Intl.DateTimeFormat().resolvedOptions().timeZone);
        }}>
          <label>
            <span>Tervezett időpont</span>
            <input type="datetime-local" value={plannedFor} onChange={(event) => setPlannedFor(event.target.value)} />
          </label>
          <button className={styles.primaryButton} disabled={!detail.activeApproval || props.reviewBlocked || !plannedFor || props.busy}>
            <CalendarClock size={16} /> Terv mentése
          </button>
        </form>
      ) : (
        <div className={styles.planSummary}>
          <span>{Intl.DateTimeFormat().resolvedOptions().timeZone}</span>
          <strong>{formatDate(plan.plannedFor)}</strong>
          <button className={styles.secondaryButton} disabled={props.reviewBlocked || props.busy} onClick={async () => {
            const plannedVersion = detail.versions.find((version) => version.id === plan.versionId);
            if (!plannedVersion) return;
            try { await navigator.clipboard.writeText(plannedVersion.body); }
            catch { window.alert("A másolás nem sikerült. Másold ki a szöveget kézzel."); return; }
          }}>
            <Clipboard size={16} /> Jóváhagyott szöveg másolása
          </button>
          <a className={styles.secondaryButton} href="https://www.linkedin.com/feed/?shareActive=true" target="_blank" rel="noopener noreferrer">LinkedIn megnyitása</a>
        </div>
      )}

      {plan?.status === "planned" && (
        <form className={styles.inspectorForm} onSubmit={async (event) => {
          event.preventDefault();
          const result = await props.onConfirmExternal(confirmation);
          if (result) setConfirmation("");
        }}>
          <label>
            <span>LinkedIn-időzítés visszaigazolása</span>
            <textarea rows={3} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </label>
          <button className={styles.secondaryButton} disabled={!confirmation.trim() || props.busy}>
            <Check size={16} /> Időzítettem a LinkedInen
          </button>
        </form>
      )}

      {(plan?.status === "scheduled_externally" || plan?.status === "planned") && (
        <form className={styles.inspectorForm} onSubmit={async (event) => {
          event.preventDefault();
          const result = await props.onMarkPublished(publicationNote);
          if (result) setPublicationNote("");
        }}>
          <label>
            <span>Publikálási megjegyzés</span>
            <textarea rows={3} value={publicationNote} onChange={(event) => setPublicationNote(event.target.value)} />
          </label>
          <button className={styles.approveButton} disabled={props.busy}>
            <Send size={16} /> Már közzétettem
          </button>
        </form>
      )}

      {detail.performanceSnapshots.length > 0 && <div className={styles.snapshotList}>
        <h3>Korábbi eredmények</h3>
        {detail.performanceSnapshots.map((snapshot) => <article key={snapshot.id}>
          <time dateTime={snapshot.recordedAt}>{formatDate(snapshot.recordedAt)}</time>
          <p>{snapshot.impressions ?? "–"} megjelenés · {snapshot.reactions ?? "–"} reakció · {snapshot.comments ?? "–"} hozzászólás · {snapshot.reposts ?? "–"} megosztás</p>
          {snapshot.notes && <p>{snapshot.notes}</p>}
        </article>)}
      </div>}
      {published && (
        <form className={styles.metricsGrid} onSubmit={async (event) => {
          event.preventDefault();
          const number = (value: string) => value === "" ? undefined : Number(value);
          const result = await props.onRecordPerformance({
            impressions: number(metrics.impressions),
            reactions: number(metrics.reactions),
            comments: number(metrics.comments),
            reposts: number(metrics.reposts),
            notes: metrics.notes
          });
          if (result) setMetrics({ impressions: "", reactions: "", comments: "", reposts: "", notes: "" });
        }}>
          {(["impressions", "reactions", "comments", "reposts"] as const).map((metric) => (
            <label key={metric}>
              <span>{metric}</span>
              <input
                type="number"
                min="0"
                value={metrics[metric]}
                onChange={(event) => setMetrics((currentMetrics) => ({ ...currentMetrics, [metric]: event.target.value }))}
              />
            </label>
          ))}
          <label className={styles.metricsNotes}>
            <span>Megfigyelés</span>
            <textarea rows={3} value={metrics.notes} onChange={(event) => setMetrics((value) => ({ ...value, notes: event.target.value }))} />
          </label>
          <button className={styles.secondaryButton} disabled={props.busy}>Eredmények mentése</button>
        </form>
      )}
    </section>
  );
}

function VoicePanel(props: Props) {
  const [style, setStyle] = useState(props.profile?.styleInstructions ?? "");
  const [audience, setAudience] = useState(props.profile?.targetAudience ?? "");
  const [language, setLanguage] = useState(props.profile?.language ?? "hu");

  return (
    <section className={styles.inspectorSection}>
      <header>
        <p className={styles.eyebrow}>A saját hangod</p>
        <h2>Hangprofil</h2>
      </header>
      <form className={styles.inspectorForm} onSubmit={(event) => {
        event.preventDefault();
        void props.onSaveProfile(style, audience, language);
      }}>
        <label>
          <span>Stílus és kerülendő fordulatok</span>
          <textarea rows={9} value={style} onChange={(event) => setStyle(event.target.value)} />
        </label>
        <label>
          <span>Közönség</span>
          <input value={audience} onChange={(event) => setAudience(event.target.value)} />
        </label>
        <label>
          <span>Nyelv</span>
          <select value={language} onChange={(event) => setLanguage(event.target.value)}>
            <option value="hu">Magyar</option>
            <option value="en">Angol</option>
          </select>
        </label>
        <button className={styles.primaryButton} disabled={!style.trim() || props.busy}>
          <SlidersHorizontal size={16} /> Profil mentése
        </button>
      </form>
    </section>
  );
}

function ActivityPanel({ detail }: { detail: ContentItemDetail | null }) {
  if (!detail) return <InspectorEmpty label="Válassz egy szöveget az előzményekhez" />;
  return (
    <section className={styles.inspectorSection}>
      <header>
        <p className={styles.eyebrow}>Mentett előzmények</p>
        <h2>Eseménynapló</h2>
      </header>
      <ol className={styles.activityList}>
        {detail.events.map((event) => (
          <li key={event.id}>
            <span aria-hidden="true" />
            <div>
              <strong>{eventLabel(event.eventType)}</strong>
              <time dateTime={event.createdAt}>{formatDate(event.createdAt)}</time>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function InspectorEmpty({ label }: { label: string }) {
  return <div className={styles.inspectorEmpty}>{label}</div>;
}
