from __future__ import annotations

from typing import Any


PROFILE_NAMES = {
    "electronic": "электронная структура",
    "ir": "ИК-спектроскопия",
    "uv_vis": "UV-Vis и диаграмма Яблонского",
    "ir_uv": "совмещённый ИК/UV-Vis профиль",
    "qcxms": "фрагментационный масс-спектр",
    "qmmm": "электростатическое QM/MM-встраивание",
    "solvent_ensemble": "ансамбль конформеров и растворителя",
    "periodic": "периодическая суперъячейка",
    "absolute_intensity": "оценка интегральных ИК-интенсивностей",
}


def interpret_quantum_result(result: dict[str, Any], profile: str) -> dict[str, Any]:
    findings: list[str] = []
    recommendations: list[str] = []
    evidence: list[dict[str, Any]] = []

    if result.get("scf_converged"):
        findings.append("Самосогласованное поле сошлось.")
    gap = result.get("gap_ev")
    if isinstance(gap, (int, float)):
        findings.append(f"Расчётная HOMO-LUMO щель составляет {gap:.3f} эВ.")
        evidence.append({"metric": "HOMO-LUMO gap", "value": gap, "unit": "eV"})

    vibration = result.get("vibrational_analysis") or {}
    modes = vibration.get("modes") or []
    imaginary = [mode for mode in modes if mode.get("imaginary")]
    if modes:
        findings.append(f"Получено {len(modes)} колебательных мод.")
        if imaginary:
            findings.append(
                f"Обнаружено мнимых частот: {len(imaginary)}; геометрия может не быть минимумом."
            )
            recommendations.append("Оптимизировать геометрию и повторить расчёт Гессиана.")

    excited = result.get("excited_state_analysis") or {}
    states = excited.get("states") or []
    if states:
        strongest = max(states, key=lambda state: state.get("oscillator_strength", 0.0))
        findings.append(
            "Наиболее интенсивный вертикальный переход: "
            f"{strongest['state']} при {strongest['wavelength_nm']:.1f} нм."
        )
        evidence.append(
            {
                "metric": "strongest_transition",
                "state": strongest["state"],
                "wavelength_nm": strongest["wavelength_nm"],
                "oscillator_strength": strongest["oscillator_strength"],
            }
        )

    mass = result.get("mass_spectrum_analysis") or {}
    fragments = mass.get("fragments") or []
    if fragments:
        base_peak = max(fragments, key=lambda fragment: fragment.get("intensity", 0.0))
        findings.append(
            f"Базовый пик фрагментационного скрининга: m/z {base_peak['mz']:.3f}."
        )
        recommendations.append(
            "Сопоставить кандидаты с экспериментальным EI/ESI-спектром и MassBank."
        )

    ensemble = result.get("ensemble_analysis") or {}
    conformers = ensemble.get("conformers") or []
    if conformers:
        populated = sum(1 for conformer in conformers if conformer.get("boltzmann_weight", 0) >= 0.05)
        findings.append(
            f"В ансамбле {len(conformers)} конформеров, из них {populated} имеют вес не менее 5%."
        )

    limitations = list((result.get("provenance") or {}).get("limitations") or [])
    if limitations:
        recommendations.append("Учитывать ограничения уровня теории при сравнении с экспериментом.")

    return {
        "profile": profile,
        "profile_name": PROFILE_NAMES.get(profile, profile),
        "summary": (
            f"Расчётный профиль «{PROFILE_NAMES.get(profile, profile)}» завершён. "
            + (" ".join(findings[:2]) if findings else "Численные результаты требуют экспертной проверки.")
        ),
        "findings": findings,
        "evidence": evidence,
        "recommendations": recommendations,
        "limitations": limitations,
        "confidence": "method_limited" if limitations else "nominal",
    }
