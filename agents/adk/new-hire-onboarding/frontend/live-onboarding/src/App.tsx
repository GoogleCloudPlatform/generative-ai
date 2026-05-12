import {
  Activity,
  BadgeCheck,
  Box,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardSignature,
  FileCheck2,
  FileText,
  Laptop,
  Mail,
  PackageCheck,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  Workflow,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  confirmHardware,
  getCase,
  getCurrentCase,
  signPacket,
  startCase,
} from "./api";
import type { Artifact, CaseEvent, LiveCase } from "./types";

type BusyAction = "start" | "sign" | "hardware" | "refresh" | null;

const steps = [
  {
    id: "WELCOME_SENT",
    title: "Packet sent",
    detail: "Local document generated",
    icon: Mail,
    pill: "thinking",
    pillLabel: "Thinking",
  },
  {
    id: "DOCUMENTS_SIGNED",
    title: "Signature",
    detail: "Employee signs locally",
    icon: ClipboardSignature,
    pill: "read",
    pillLabel: "Reading",
  },
  {
    id: "IT_PROVISIONED",
    title: "IT ready",
    detail: "ADK wake completes",
    icon: Laptop,
    pill: "edit",
    pillLabel: "Editing",
  },
  {
    id: "HARDWARE_DELIVERED",
    title: "Laptop",
    detail: "Delivery confirmed",
    icon: PackageCheck,
    pill: "grep",
    pillLabel: "Grepping",
  },
  {
    id: "COMPLETED",
    title: "Day One",
    detail: "Schedule artifact stored",
    icon: CalendarDays,
    pill: "done",
    pillLabel: "Done",
  },
];

const artifactCopy: Record<string, string> = {
  "welcome-packet": "Employee-facing packet before signature.",
  "signed-packet": "Signed local artifact saved after employee action.",
  "hardware-receipt": "Receipt generated from the employee delivery confirmation.",
  "day-one-schedule": "Final itinerary after the second ADK wake turn.",
};

const artifactThumbCopy: Record<string, string> = {
  "welcome-packet": "Packet",
  "signed-packet": "Signed",
  "hardware-receipt": "Receipt",
  "day-one-schedule": "Brief",
};

function stepIndex(step: string | undefined) {
  return Math.max(0, steps.findIndex((item) => item.id === step));
}

function statusLabel(caseData: LiveCase | null) {
  if (!caseData) return "Backend not started";
  if (caseData.status === "completed") return "Day One ready";
  if (caseData.status.includes("waking")) return "ADK wake turn running";
  if (!caseData.document_signed) return "Waiting for employee signature";
  if (!caseData.hardware_delivered) return "Waiting for laptop delivery";
  return "Processing";
}

function waitingOn(caseData: LiveCase | null) {
  if (!caseData) return "Create case";
  if (caseData.pending_signals.length) return caseData.pending_signals.join(", ");
  if (caseData.status === "completed") return "Nothing";
  if (caseData.status.includes("waking")) return "Runner completion";
  return "Employee action";
}

function isWakeRunning(caseData: LiveCase | null) {
  return Boolean(caseData?.status.includes("waking"));
}

function getSelectedArtifact(caseData: LiveCase | null, selectedId: string | null) {
  if (!caseData?.artifacts.length) return null;
  return (
    caseData.artifacts.find((artifact) => artifact.id === selectedId) ??
    caseData.artifacts[0]
  );
}

function hasArtifact(caseData: LiveCase, artifactId: string) {
  return caseData.artifacts.some((artifact) => artifact.id === artifactId);
}

function nextAction(caseData: LiveCase | null) {
  const firstName = employeeFirstName(caseData);
  if (!caseData) return `Start the HR case to generate ${firstName}'s packet.`;
  if (!caseData.document_signed) return `Review the packet and sign it as ${firstName}.`;
  if (!caseData.hardware_delivered) return `Confirm that ${firstName} received the laptop.`;
  return "Open the Day One schedule artifact.";
}

function employeeFirstName(caseData: LiveCase | null) {
  return caseData?.employee.name.split(" ")[0] ?? "Olivia";
}

function formatStep(step: string) {
  return step.replaceAll("_", " ");
}

function nextSignalLabel(caseData: LiveCase | null) {
  if (!caseData) return "Ready to start";
  if (caseData.pending_signals.length) return caseData.pending_signals.join(", ");
  if (caseData.status === "completed") return "Complete";
  if (caseData.status.includes("waking")) return "ADK runner";
  return "Employee action";
}

function activeStateDetail(caseData: LiveCase | null) {
  if (!caseData) return "Create a case to generate the first local packet.";
  if (caseData.status.includes("waking")) return "Webhook received; ADK is resuming the paused run.";
  if (!caseData.document_signed) return "Paused until the employee signs the generated packet.";
  if (!caseData.hardware_delivered) return "Paused until the employee confirms laptop delivery.";
  return "All required artifacts have been generated and stored locally.";
}

function agentTickerRows(caseData: LiveCase | null) {
  const waking = isWakeRunning(caseData);
  return [
    {
      label: waking ? "ADK wake turn running" : "Waiting for backend signal",
      pill: waking ? "grep" : "thinking",
    },
    {
      label: caseData?.document_signed ? "Signed packet confirmed" : "Packet unsigned",
      pill: caseData?.document_signed ? "done" : "read",
    },
    {
      label: caseData?.hardware_delivered ? "Delivery confirmed" : "Hardware pending",
      pill: caseData?.hardware_delivered ? "done" : "edit",
    },
  ];
}

function App() {
  const [caseData, setCaseData] = useState<LiveCase | null>(null);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const completedCaseSequenceStarted = useRef<string | null>(null);
  const completedArtifactTimer = useRef<number | null>(null);

  const selectedArtifact = useMemo(
    () => getSelectedArtifact(caseData, selectedArtifactId),
    [caseData, selectedArtifactId],
  );

  const applyCase = useCallback((nextCase: LiveCase) => {
    setCaseData(nextCase);
    setSelectedArtifactId((current) => {
      if (
        nextCase.status === "completed" &&
        hasArtifact(nextCase, "hardware-receipt") &&
        hasArtifact(nextCase, "day-one-schedule") &&
        completedCaseSequenceStarted.current !== nextCase.id
      ) {
        return "hardware-receipt";
      }
      if (current && nextCase.artifacts.some((artifact) => artifact.id === current)) {
        return current;
      }
      return nextCase.artifacts[0]?.id ?? null;
    });
  }, []);

  const refreshCase = useCallback(async () => {
    if (!caseData?.id) return;
    const payload = await getCase(caseData.id);
    if (payload.active) applyCase(payload.case);
  }, [applyCase, caseData?.id]);

  useEffect(() => {
    let cancelled = false;

    getCurrentCase()
      .then((payload) => {
        if (!cancelled && payload.active) applyCase(payload.case);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [applyCase]);

  useEffect(() => {
    if (!caseData?.id || caseData.status === "completed") return undefined;
    const timer = window.setInterval(() => {
      refreshCase().catch((err: Error) => setError(err.message));
    }, 1200);
    return () => window.clearInterval(timer);
  }, [caseData?.id, caseData?.status, refreshCase]);

  useEffect(() => {
    if (
      !caseData ||
      caseData.status !== "completed" ||
      completedCaseSequenceStarted.current === caseData.id ||
      !hasArtifact(caseData, "hardware-receipt") ||
      !hasArtifact(caseData, "day-one-schedule")
    ) {
      return;
    }

    completedCaseSequenceStarted.current = caseData.id;
    setSelectedArtifactId("hardware-receipt");
    if (completedArtifactTimer.current) {
      window.clearTimeout(completedArtifactTimer.current);
    }
    completedArtifactTimer.current = window.setTimeout(() => {
      setSelectedArtifactId((current) =>
        current === "hardware-receipt" ? "day-one-schedule" : current,
      );
    }, 3200);

    return () => {
      if (completedArtifactTimer.current) {
        window.clearTimeout(completedArtifactTimer.current);
        completedArtifactTimer.current = null;
      }
    };
  }, [caseData]);

  async function runAction(action: BusyAction, task: () => Promise<void>) {
    setBusyAction(action);
    setError(null);
    try {
      await task();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyAction(null);
    }
  }

  const handleStart = () =>
    runAction("start", async () => {
      completedCaseSequenceStarted.current = null;
      if (completedArtifactTimer.current) {
        window.clearTimeout(completedArtifactTimer.current);
        completedArtifactTimer.current = null;
      }
      const payload = await startCase();
      if (payload.active) applyCase(payload.case);
    });

  const handleSign = () =>
    runAction("sign", async () => {
      if (!caseData) return;
      const payload = await signPacket(caseData.id);
      if (payload.active) {
        applyCase(payload.case);
        setSelectedArtifactId("signed-packet");
      }
    });

  const handleHardware = () =>
    runAction("hardware", async () => {
      if (!caseData) return;
      const payload = await confirmHardware(caseData.id);
      if (payload.active) {
        applyCase(payload.case);
      }
    });

  const handleRefresh = () =>
    runAction("refresh", async () => {
      await refreshCase();
    });

  const completedCount = caseData ? stepIndex(caseData.current_step) + 1 : 0;
  const waking = isWakeRunning(caseData);
  const canSign = Boolean(caseData && !caseData.document_signed && !waking);
  const canConfirmHardware = Boolean(
    caseData?.document_signed &&
      !caseData.hardware_delivered &&
      caseData.pending_signals.includes("hardware_delivered") &&
      !waking,
  );
  const isBusy = busyAction !== null;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Workflow size={22} aria-hidden="true" />
          </div>
          <div>
            <h1>Live Onboarding Desk</h1>
            <p>Long-running ADK agents that can pause and resume</p>
          </div>
        </div>

        <div className="top-actions">
          <div className="connection-pill">
            <span className={caseData ? "pulse online" : "pulse idle"} />
            {caseData ? "Backend case live" : "Ready to create case"}
          </div>
          <button className="secondary-button" type="button" onClick={handleRefresh}>
            <RefreshCw size={15} aria-hidden="true" />
            Refresh
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={busyAction === "start"}
            onClick={handleStart}
          >
            <Play size={15} aria-hidden="true" />
            {caseData ? "Start fresh case" : "Start Olivia's onboarding"}
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="hero-strip">
        <div>
          <span className="tiny-label">Current workflow</span>
          <h2>{statusLabel(caseData)}</h2>
        </div>
        <div className="hero-stats">
          <Metric label="Current step" value={caseData?.current_step ?? "START"} />
          <Metric label="Waiting on" value={waitingOn(caseData)} />
          <Metric label="Artifacts" value={String(caseData?.artifacts.length ?? 0)} />
          <Metric label="ADK runner" value={caseData?.adk_status ?? "Idle"} />
        </div>
      </section>

      <ActiveStateBand caseData={caseData} />

      <section className="workspace">
        <aside className="hr-panel">
          <PanelHeader
            title="HR command center"
            subtitle="Everything on this side is hydrated from backend case state."
            icon={<ShieldCheck size={18} aria-hidden="true" />}
          />

          <EmployeeCard caseData={caseData} />
          <AgentTicker caseData={caseData} />
          <ProgressRail currentStep={caseData?.current_step} completedCount={completedCount} />
          <ArtifactList
            artifacts={caseData?.artifacts ?? []}
            selectedId={selectedArtifact?.id ?? null}
            onSelect={setSelectedArtifactId}
          />
          <EventLog events={caseData?.events ?? []} />
        </aside>

        <section className="employee-panel">
          <PanelHeader
            title="Employee portal"
            subtitle={nextAction(caseData)}
            icon={<UserRound size={18} aria-hidden="true" />}
            trailing={
              <span className="employee-state">
                {caseData?.status === "completed" ? "Ready" : "Action needed"}
              </span>
            }
          />

          <div className="portal-grid">
            <DocumentStage artifact={selectedArtifact} />
            <ActionDock
              caseData={caseData}
              canSign={canSign}
              canConfirmHardware={canConfirmHardware}
              busyAction={busyAction}
              isBusy={isBusy}
              onSign={handleSign}
              onHardware={handleHardware}
            />
          </div>
        </section>
      </section>
    </main>
  );
}

function ActiveStateBand({ caseData }: { caseData: LiveCase | null }) {
  const waking = isWakeRunning(caseData);

  return (
    <section className="state-band">
      <div>
        <span className="tiny-label">Active case state</span>
        <strong>{statusLabel(caseData)}</strong>
        <p>{activeStateDetail(caseData)}</p>
      </div>
      <div className="state-band-steps">
        <span className={waking ? "state-chip active" : "state-chip"}>
          <Send size={14} aria-hidden="true" />
          {waking ? "ADK wake running" : `Waiting on ${nextSignalLabel(caseData)}`}
        </span>
        <span className="state-chip">{caseData?.adk_status ?? "No ADK run yet"}</span>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PanelHeader({
  title,
  subtitle,
  icon,
  trailing,
}: {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  trailing?: React.ReactNode;
}) {
  return (
    <div className="panel-header">
      <div className="panel-title">
        <span className="panel-icon">{icon}</span>
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>
      {trailing}
    </div>
  );
}

function EmployeeCard({ caseData }: { caseData: LiveCase | null }) {
  const employee = caseData?.employee;
  const photoUrl = employee?.photo_url ?? "/live-onboarding/olivia-bennett.jpg";

  return (
    <section className="employee-card">
      <img
        className="avatar"
        src={photoUrl}
        alt={employee?.name ?? "Olivia Bennett"}
        width="56"
        height="56"
      />
      <div className="employee-info">
        <h4>{employee?.name ?? "Olivia Bennett"}</h4>
        <p>
          {employee?.role ?? "Product Manager"} · {employee?.team ?? "Platform Systems"}
        </p>
      </div>
      <div className="employee-meta">
        <span>Start</span>
        <strong>{employee?.start_date ?? "2026-06-01"}</strong>
      </div>
    </section>
  );
}

function AgentTicker({ caseData }: { caseData: LiveCase | null }) {
  const rows = agentTickerRows(caseData);

  return (
    <section className="agent-ticker">
      <div className="section-heading">
        <h4>Agent activity</h4>
        <span>{isWakeRunning(caseData) ? "running" : "idle"}</span>
      </div>
      <div className="ticker-rows">
        {rows.map((row) => (
          <div className="ticker-row" key={row.label}>
            <span className={`timeline-pill ${row.pill}`}>{row.pill}</span>
            <strong>{row.label}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProgressRail({
  currentStep,
  completedCount,
}: {
  currentStep?: string;
  completedCount: number;
}) {
  const currentIndex = stepIndex(currentStep);

  return (
    <section className="progress-section">
      <div className="section-heading">
        <h4>Agent path</h4>
        <span>{completedCount} / {steps.length}</span>
      </div>
      <div className="step-stack">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const state =
            index < currentIndex || currentStep === "COMPLETED"
              ? "done"
              : index === currentIndex
                ? "active"
                : "locked";

          return (
            <article className={`step-row ${state}`} key={step.id}>
              <span className="step-icon">
                <Icon size={16} aria-hidden="true" />
              </span>
              <div>
                <strong>{step.title}</strong>
                <p>{step.detail}</p>
              </div>
              <span className={`timeline-pill ${step.pill}`}>{step.pillLabel}</span>
              {state === "done" ? <CheckCircle2 size={17} aria-hidden="true" /> : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ArtifactList({
  artifacts,
  selectedId,
  onSelect,
}: {
  artifacts: Artifact[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="artifact-section">
      <div className="section-heading">
        <h4>Local artifacts</h4>
        <span>{artifacts.length}</span>
      </div>
      <div className="artifact-list">
        {artifacts.length ? (
          artifacts.map((artifact) => (
            <button
              className={`artifact-card ${selectedId === artifact.id ? "selected" : ""}`}
              type="button"
              key={artifact.id}
              onClick={() => onSelect(artifact.id)}
            >
              <span className="artifact-thumb" aria-hidden="true">
                <FileText size={14} />
                <strong>{artifactThumbCopy[artifact.id] ?? "Doc"}</strong>
              </span>
              <span>
                <strong>{artifact.title}</strong>
                <small>{artifactCopy[artifact.id] ?? artifact.filename}</small>
              </span>
              <ChevronRight size={16} aria-hidden="true" />
            </button>
          ))
        ) : (
          <div className="empty-box">
            <FileText size={18} aria-hidden="true" />
            Generated packets, receipts, and schedules appear here.
          </div>
        )}
      </div>
    </section>
  );
}

function EventLog({ events }: { events: CaseEvent[] }) {
  return (
    <section className="event-section">
      <div className="section-heading">
        <h4>Live activity</h4>
        <span>{events.length}</span>
      </div>
      <div className="event-list">
        {events.length ? (
          events.slice(0, 8).map((event, index) => (
            <article className="event-row" key={`${event.time}-${event.title}-${index}`}>
              <span className={`event-dot ${event.kind}`} />
              <div>
                <code>{event.time} · {event.kind}</code>
                <strong>{event.title}</strong>
                <p>{event.detail}</p>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-box">
            <Activity size={18} aria-hidden="true" />
            Start the case to see backend events stream into HR.
          </div>
        )}
      </div>
    </section>
  );
}

function DocumentStage({ artifact }: { artifact: Artifact | null }) {
  return (
    <section className="document-stage">
      <div className="document-toolbar">
        <div>
          <span className="tiny-label">Selected artifact</span>
          <h3>{artifact?.title ?? "No packet yet"}</h3>
          <p>
            {artifact
              ? `${artifact.filename} is served by FastAPI from the local artifact store.`
              : "Start Olivia's onboarding to generate the first packet."}
          </p>
        </div>
        {artifact ? (
          <a className="open-link" href={artifact.href} target="_blank" rel="noreferrer">
            Open artifact
          </a>
        ) : null}
      </div>

      <div className="document-frame-wrap">
        {artifact ? (
          <iframe src={artifact.href} title={artifact.title} />
        ) : (
          <div className="document-placeholder">
            <FileCheck2 size={34} aria-hidden="true" />
            <strong>Generated document preview</strong>
            <p>The onboarding packet will render here as a real local HTML artifact.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function ActionDock({
  caseData,
  canSign,
  canConfirmHardware,
  busyAction,
  isBusy,
  onSign,
  onHardware,
}: {
  caseData: LiveCase | null;
  canSign: boolean;
  canConfirmHardware: boolean;
  busyAction: BusyAction;
  isBusy: boolean;
  onSign: () => void;
  onHardware: () => void;
}) {
  return (
    <aside className="action-dock">
      <div
        className={`action-card primary-action-card ${
          caseData?.document_signed ? "complete" : ""
        }`}
      >
        <span className="action-icon">
          <ClipboardSignature size={20} aria-hidden="true" />
        </span>
        <div>
          <h4>Signature</h4>
          <p>Click once to store a signed local packet and wake the ADK session.</p>
        </div>
        <button
          className="green-button"
          type="button"
          disabled={!canSign || isBusy}
          onClick={onSign}
        >
          {caseData?.document_signed
            ? "Packet signed"
            : busyAction === "sign"
              ? "Signing..."
              : "Sign packet"}
        </button>
      </div>

      <div className={`action-card ${caseData?.hardware_delivered ? "complete" : ""}`}>
        <span className="action-icon amber">
          <Box size={20} aria-hidden="true" />
        </span>
        <div>
          <h4>Hardware</h4>
          <p>Confirm laptop delivery to fire the second webhook and finish onboarding.</p>
        </div>
        <button
          className="amber-button"
          type="button"
          disabled={!canConfirmHardware || isBusy}
          onClick={onHardware}
        >
          {caseData?.hardware_delivered
            ? "Laptop confirmed"
            : busyAction === "hardware"
              ? "Confirming..."
              : "Confirm laptop delivered"}
        </button>
      </div>

      <div className="case-summary">
        <div>
          <Sparkles size={16} aria-hidden="true" />
          <span>Employee state</span>
        </div>
        <strong>{statusLabel(caseData)}</strong>
        <p>{caseData ? formatStep(caseData.current_step) : "No active case"}</p>
      </div>

      <div className="case-summary">
        <div>
          <BadgeCheck size={16} aria-hidden="true" />
          <span>Result</span>
        </div>
        <strong>
          {caseData?.status === "completed"
            ? "Signed packet, hardware receipt, and schedule created"
            : "Waiting for the next employee action"}
        </strong>
        <p>{caseData?.session_id ?? "ADK session will appear after start"}</p>
      </div>
    </aside>
  );
}

export default App;
