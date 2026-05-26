from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from contextlib import suppress
import logging

from .data_store import store
from .models import Incident, SimulationRequest, TelemetryEvent
from .processors import analyze_telemetry, build_forecast_message
from .telemetry_samples import SAMPLE_EVENTS
from .azure_scheduler import get_scheduler, stop_scheduler
from .ingestion_health import build_ingestion_checklist
from .correlation_enricher import get_correlation_enricher
from .models import ActiveIncidentCard, CorrelatedEvidence, EvidenceRecord

logger = logging.getLogger(__name__)

app = FastAPI(title="Azure RCA Planner MVP", version="0.1.0")

# Global scheduler reference
scheduler = None
scheduler_task: asyncio.Task | None = None
correlation_enricher = get_correlation_enricher()


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on app startup"""
    global scheduler, scheduler_task
    try:
        scheduler = get_scheduler()
        if scheduler_task is None or scheduler_task.done():
            scheduler_task = asyncio.create_task(scheduler.start(), name="telemetry-scheduler")
            logger.info("Telemetry scheduler task started")
        else:
            logger.info("Telemetry scheduler task already running")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on app shutdown"""
    global scheduler, scheduler_task
    if scheduler:
        stop_scheduler(reset=True)

    if scheduler_task:
        try:
            await asyncio.wait_for(scheduler_task, timeout=15)
        except asyncio.TimeoutError:
            logger.warning("Telemetry scheduler did not stop within timeout, cancelling task")
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task
        finally:
            scheduler_task = None

    scheduler = None
    logger.info("Telemetry scheduler shutdown completed")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "incidents": len(store.get_incidents())})


@app.get("/scheduler/status")
def scheduler_status() -> JSONResponse:
    """Get telemetry scheduler status"""
    global scheduler
    if scheduler:
        return JSONResponse(scheduler.get_status())
    return JSONResponse({"error": "Scheduler not initialized"})


@app.get("/ingestion/checklist")
def ingestion_checklist() -> JSONResponse:
    """Get a pass/warn/fail ingestion readiness checklist."""
    global scheduler
    if not scheduler:
        checklist = build_ingestion_checklist(None)
        return JSONResponse(checklist, status_code=503)

    checklist = build_ingestion_checklist(scheduler.get_status())
    status_code = 503 if checklist["overall_status"] == "fail" else 200
    return JSONResponse(checklist, status_code=status_code)


@app.post("/telemetry", response_model=TelemetryEvent)
def ingest_telemetry(event: TelemetryEvent):
    persisted = store.add_telemetry(event)
    incident = analyze_telemetry(persisted)
    if incident:
        store.add_incident(incident)
        store.persist_incident_evidence(incident)
    correlation = correlation_enricher.ingest(persisted)
    if correlation:
        store.add_correlation(correlation)
    return persisted


@app.get("/incidents", response_model=list[Incident])
def list_incidents():
    return store.get_incidents()


@app.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str):
    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/dashboard/incidents/active", response_model=list[ActiveIncidentCard])
def list_active_incident_cards():
    incidents = sorted(store.get_incidents(), key=lambda item: item.detected_at, reverse=True)
    return [
        ActiveIncidentCard(
            incident_id=incident.id,
            detected_at=incident.detected_at,
            incident_type=incident.incident_type,
            title=incident.title,
            severity=incident.severity,
            affected_component=incident.affected_component,
            likely_root_cause=incident.likely_root_cause,
            probability_score=incident.probability_score,
            confidence_label=incident.confidence_label,
            evidence_count=incident.evidence_count,
            primary_evidence=incident.primary_evidence,
            evidence_links=list(incident.supporting_evidence_links),
        )
        for incident in incidents
    ]


@app.get("/incidents/{incident_id}/evidence", response_model=list[EvidenceRecord])
def get_incident_evidence(incident_id: str):
    incident = store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return store.get_incident_evidence(incident_id)


@app.get("/evidence", response_model=list[EvidenceRecord])
def list_evidence():
    return store.get_evidence_records()


@app.get("/evidence/{evidence_id}", response_model=EvidenceRecord)
def get_evidence(evidence_id: str):
    evidence = store.get_evidence_record(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@app.get("/correlations", response_model=list[CorrelatedEvidence])
def list_correlations():
    return store.get_correlations()


@app.get("/correlations/{correlation_id}", response_model=CorrelatedEvidence)
def get_correlation(correlation_id: str):
    correlation = store.get_correlation(correlation_id)
    if not correlation:
        raise HTTPException(status_code=404, detail="Correlation not found")
    return correlation


@app.get("/forecast")
def forecast() -> JSONResponse:
    return JSONResponse(build_forecast_message())


@app.post("/simulate")
def simulate(request: SimulationRequest):
    scenario = request.scenario
    event = SAMPLE_EVENTS.get(scenario)
    if not event:
        raise HTTPException(status_code=404, detail="Scenario not found")
    persisted = store.add_telemetry(event)
    incident = analyze_telemetry(persisted)
    if incident:
        store.add_incident(incident)
        store.persist_incident_evidence(incident)
    correlation = correlation_enricher.ingest(persisted)
    if correlation:
        store.add_correlation(correlation)
    return {"scenario": scenario, "event": persisted, "incident_created": incident is not None}
