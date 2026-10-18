import type { ContentWorkflowStatus, PublicationPlanStatus } from "@/types/content";
import styles from "@/app/workspace.module.css";

const workflowLabels: Record<ContentWorkflowStatus, string> = {
  captured: "Ötlet",
  draft: "Draft",
  changes_requested: "Javítandó",
  approved: "Kész",
  archived: "Archivált"
};

const publicationLabels: Record<PublicationPlanStatus, string> = {
  planned: "Tervezett",
  scheduled_externally: "Időzítve",
  published: "Megjelent",
  cancelled: "Visszavonva"
};

export function StatusMarker({ status }: { status: ContentWorkflowStatus }) {
  return (
    <span className={styles.statusMarker} data-status={status}>
      <span aria-hidden="true" />
      {workflowLabels[status]}
    </span>
  );
}

export function PublicationMarker({ status }: { status: PublicationPlanStatus }) {
  return (
    <span className={styles.statusMarker} data-status={status}>
      <span aria-hidden="true" />
      {publicationLabels[status]}
    </span>
  );
}
