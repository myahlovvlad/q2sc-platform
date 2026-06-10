from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import uuid

import numpy as np

from app.schemas import (
    ApplicabilityDomainResult,
    DirectPredictionRequest,
    DirectPredictionResponse,
    InterpretationPayload,
    Peak,
    ReverseAnalysisRequest,
    ReverseAnalysisResponse,
    ReverseCandidate,
    ScreeningRequest,
    ScreeningResponse,
    ScreeningRow,
    SpectralData,
)
from .audit import AuditTrailTracker
from .chemometrics import ChemometricsEngine
from .descriptors import DescriptorEngine
from .signal import SignalEngine
from .training_data import CALIBRATION_LIBRARY, build_training_matrices
from app.core.resources import adaptive_worker_count


@dataclass
class PredictionInternal:
    response: DirectPredictionResponse
    y_vector_np: np.ndarray | None


class QsarEngine:
    """Application service combining descriptor generation, PLS prediction, AD, screening and reverse analysis."""

    def __init__(self):
        x_train, y_train, feature_names = build_training_matrices()
        self.descriptors = DescriptorEngine()
        self.chemometrics = ChemometricsEngine(n_components=3)
        self.chemometrics.fit(x_train, y_train, feature_names)
        self.signal = SignalEngine()
        self.calibration_library = CALIBRATION_LIBRARY

    def _axis(self, points: int) -> np.ndarray:
        return np.linspace(0.0, 220.0, points)

    def _ad_result(self, x: np.ndarray) -> ApplicabilityDomainResult:
        assert self.chemometrics.ad is not None
        metrics = self.chemometrics.ad.evaluate(x)
        if metrics.inside_ad:
            decision = "ACCEPT"
        elif metrics.t2_hotelling <= metrics.t2_critical * 1.5:
            decision = "WARN"
        else:
            decision = "PARK"
        return ApplicabilityDomainResult(
            inside_ad=metrics.inside_ad,
            t2_hotelling=round(metrics.t2_hotelling, 4),
            t2_critical=round(metrics.t2_critical, 4),
            q_residual=round(metrics.q_residual, 4),
            q_critical=round(metrics.q_critical, 4),
            decision=decision,
        )

    def predict(self, request: DirectPredictionRequest) -> DirectPredictionResponse:
        return self._predict_internal(request).response

    def _predict_internal(self, request: DirectPredictionRequest) -> PredictionInternal:
        tracker = AuditTrailTracker(project_id=request.project_id, pipeline_id=request.pipeline_id)
        tracker.log("Input_Validated", {"name": request.structure.name, "smiles": request.structure.smiles})

        descriptor = self.descriptors.build(
            smiles=request.structure.smiles,
            solvent_eps=request.environment.solvent_eps,
            solvent_ri=request.environment.solvent_ri,
        )
        tracker.log(
            "Descriptor_Extraction",
            {
                "feature_names": descriptor.feature_names,
                "feature_vector": descriptor.vector.round(6).tolist(),
                "structure_hash": descriptor.structure_hash,
            },
        )

        ad = self._ad_result(descriptor.vector)
        tracker.log("Applicability_Domain", ad.model_dump())
        if ad.decision == "PARK":
            tracker.log("Parking", {"reason": "outside_applicability_domain", "recommended_next_step": "heavy_dft"})
            return PredictionInternal(
                response=DirectPredictionResponse(
                    status="PARKED",
                    project_id=request.project_id,
                    pipeline_id=request.pipeline_id,
                    molecule_name=request.structure.name,
                    smiles=request.structure.smiles,
                    ad=ad,
                    spectrum=None,
                    interpretation=None,
                    audit_trail=tracker.export(),
                ),
                y_vector_np=None,
            )

        peaks_np = np.clip(self.chemometrics.predict_peaks(descriptor.vector), 0.0, 220.0)
        intensities = np.array([50.0 + 10.0 * (i + 1) for i in range(len(peaks_np))])
        x_axis = self._axis(request.instrument.spectral_points)
        y_raw = self.signal.lorentzian_expansion(peaks_np, intensities, x_axis)
        y_clean = self.signal.snv(y_raw)
        tracker.log("Spectrum_Prediction", {"peaks_ppm": peaks_np.round(4).tolist(), "points": len(x_axis)})

        vip = self.chemometrics.calculate_vip_scores()
        key_drivers = self.chemometrics.key_drivers(threshold=1.0)
        tracker.log("VIP_Interpretation", {"vip_scores": vip, "key_drivers": key_drivers})

        peak_items = [
            Peak(position=round(float(p), 4), intensity=round(float(i), 4), assignment=[idx], label=f"C{idx + 1}")
            for idx, (p, i) in enumerate(zip(peaks_np, intensities))
            if float(p) > 0.0
        ]
        spectrum = SpectralData(
            x_axis=[round(float(x), 4) for x in x_axis],
            y_axis=[round(float(y), 6) for y in y_clean],
            x_unit="ppm",
            y_unit="intensity",
            peaks=peak_items,
        )
        expert_summary = (
            f"Прогноз принят: структура находится в области применимости. "
            f"Ключевые драйверы: {', '.join(key_drivers) if key_drivers else 'нет VIP >= 1.0'}. "
            f"Режим: {request.compute_mode}; среда: {request.environment.solvent_name}."
        )
        interpretation = InterpretationPayload(
            vip_scores=vip,
            key_drivers=key_drivers,
            expert_summary=expert_summary,
            evidence={"model_family": "PLS_surrogate", "signal_shape": "Lorentzian", "normalization": "SNV"},
        )
        return PredictionInternal(
            response=DirectPredictionResponse(
                status="SUCCESS",
                project_id=request.project_id,
                pipeline_id=request.pipeline_id,
                molecule_name=request.structure.name,
                smiles=request.structure.smiles,
                ad=ad,
                spectrum=spectrum,
                interpretation=interpretation,
                audit_trail=tracker.export(),
            ),
            y_vector_np=y_clean,
        )

    def run_screening(self, request: ScreeningRequest) -> ScreeningResponse:
        ppm_axis = self._axis(request.instrument.spectral_points)
        rows: list[ScreeningRow] = []
        matrix: list[list[float]] = []

        def run_one(candidate) -> ScreeningRow:
            direct_request = DirectPredictionRequest(
                project_id=request.project_id,
                structure={"name": candidate.name, "smiles": candidate.smiles, "source": "screening"},
                environment=request.environment,
                instrument=request.instrument,
                compute_mode="parallel_batch",
            )
            try:
                result = self._predict_internal(direct_request).response
            except (ValueError, FloatingPointError):
                return ScreeningRow(
                    candidate_id=str(uuid.uuid4()),
                    name=candidate.name,
                    smiles=candidate.smiles,
                    status="FAILED",
                    match_score=0.0,
                )
            score = 0.0
            if result.spectrum:
                score = round(100.0 - min(100.0, result.ad.t2_hotelling / max(result.ad.t2_critical, 1e-9) * 10.0), 2)
            return ScreeningRow(
                candidate_id=str(uuid.uuid4()),
                name=candidate.name,
                smiles=candidate.smiles,
                status=result.status,
                match_score=score,
                ad=result.ad,
                spectrum=result.spectrum,
            )

        worker_count = adaptive_worker_count(
            requested=request.max_workers,
            item_count=len(request.candidates),
            memory_gib_per_worker=0.5,
        )
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {executor.submit(run_one, candidate): candidate for candidate in request.candidates}
            for future in as_completed(future_map):
                row = future.result()
                rows.append(row)

        rows.sort(key=lambda row: row.name)
        for row in rows:
            if row.spectrum:
                matrix.append(row.spectrum.y_axis)
            else:
                matrix.append([0.0 for _ in ppm_axis])

        accepted = sum(1 for row in rows if row.status == "SUCCESS")
        parked = sum(1 for row in rows if row.status == "PARKED")
        failed = sum(1 for row in rows if row.status == "FAILED")
        return ScreeningResponse(
            project_id=request.project_id,
            total=len(rows),
            accepted=accepted,
            parked=parked,
            failed=failed,
            ppm_axis=[round(float(x), 4) for x in ppm_axis],
            intensity_matrix=matrix,
            rows=rows,
        )

    def reverse_analyze(self, request: ReverseAnalysisRequest) -> ReverseAnalysisResponse:
        tracker = AuditTrailTracker(project_id=request.project_id)
        x = np.asarray(request.x_axis, dtype=float)
        y = np.asarray(request.y_axis, dtype=float)
        corrected = self.signal.asymmetric_least_squares(y)
        normalized = self.signal.snv(corrected)
        peaks = [Peak(position=round(p, 4), intensity=round(i, 4), label="detected") for p, i in self.signal.detect_top_peaks(x, normalized)]
        tracker.log("Signal_Preprocessing", {"methods": ["AsLS", "SNV"], "points": len(x)})
        tracker.log("Peak_Detection", {"detected_peaks": [peak.model_dump() for peak in peaks]})

        library = request.candidate_library
        if not library:
            library = [
                {"name": name, "smiles": smiles}
                for name, smiles, _eps, _ri, _peaks in self.calibration_library
            ]
        candidates: list[ReverseCandidate] = []
        for idx, item in enumerate(library):
            candidate_request = DirectPredictionRequest(
                project_id=request.project_id,
                structure={"name": item.name if hasattr(item, "name") else item["name"], "smiles": item.smiles if hasattr(item, "smiles") else item["smiles"]},
                environment=request.environment,
                instrument={"spectroscopy_type": "13C_NMR", "frequency_mhz": 400.0, "spectral_points": len(x)},
            )
            explanation = "Сопоставление выполнено по косинусной близости очищенного спектра и surrogate-прогноза."
            try:
                result = self._predict_internal(candidate_request)
            except (ValueError, FloatingPointError):
                result = None
                explanation = "Кандидат не удалось обработать; он оставлен для дополнительной проверки."

            if result is None or result.y_vector_np is None:
                score = 0.0
                delta = 999.0
                status = "PARKED"
            else:
                score = self.chemometrics.spectral_match_score(normalized, result.y_vector_np)
                candidate_peak_positions = [peak.position for peak in result.response.spectrum.peaks] if result.response.spectrum else []
                detected_positions = [peak.position for peak in peaks]
                delta = min([abs(a - b) for a in detected_positions for b in candidate_peak_positions] or [999.0])
                status = "MATCH" if score >= 75 else "WEAK"
            candidates.append(
                ReverseCandidate(
                    rank=idx + 1,
                    name=candidate_request.structure.name,
                    smiles=candidate_request.structure.smiles,
                    match_score=score,
                    delta_peak=round(float(delta), 4),
                    status=status,
                    explanation=explanation,
                )
            )
        candidates.sort(key=lambda c: c.match_score, reverse=True)
        for rank, candidate in enumerate(candidates, start=1):
            candidate.rank = rank
        tracker.log("Candidate_Ranking", {"top_candidate": candidates[0].model_dump() if candidates else None})
        return ReverseAnalysisResponse(project_id=request.project_id, detected_peaks=peaks, candidates=candidates[:10], audit_trail=tracker.export())


ENGINE = QsarEngine()
