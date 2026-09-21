"""CV-vs-document validation helpers for CV text flows."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from services.cv_analyzer import extract_skills_from_text

from .budget import _env_bool
from .cv_rl_agent import apply_cv_rl_reward, log_cv_rl_decision, select_cv_rl_policy
from .cv_supervised_classifier import predict_supervised_cv_kind
from .models import CVAnalysisResult
from .prompt_safety import assess_prompt_injection_risk
from .providers import _generate_final_response
from .text_utils import _fold_text

__all__ = [
    "CvDocumentAssessment",
    "assess_cv_document_text",
    "assess_cv_document_with_optional_llm",
    "ensure_cv_document_or_raise",
]

SECTION_MARKERS = (
    "curriculum vitae",
    "curriculum",
    "informations personnelles",
    "personal information",
    "contact",
    "coordonnees",
    "coordonnées",
    "profil",
    "profile",
    "resume",
    "professional summary",
    "career summary",
    "summary",
    "objective",
    "objectifs",
    "experience",
    "professional experience",
    "work history",
    "employment history",
    "responsabilites",
    "responsabilités",
    "achievements",
    "accomplishments",
    "realisations",
    "réalisations",
    "formation",
    "education",
    "academic background",
    "etudes",
    "études",
    "skills",
    "hard skills",
    "soft skills",
    "technical skills",
    "competences",
    "compétences",
    "competencies",
    "tools",
    "outils",
    "technologies",
    "projects",
    "project experience",
    "projets",
    "portfolio",
    "certifications",
    "certificates",
    "licences",
    "awards",
    "publications",
    "volunteer",
    "volunteering",
    "volontariat",
    "langues",
    "languages",
    "interets",
    "intérêts",
    "centres d interet",
    "centres d'intérêt",
    "hobbies",
    "references",
    "habilidades",
    "experiencia",
    "educacion",
)

EXPERIENCE_MARKERS = (
    "work experience",
    "professional experience",
    "employment history",
    "career history",
    "career summary",
    "experience professionnelle",
    "responsibilities",
    "responsabilites",
    "missions",
    "achievements",
    "realisations",
    "employment",
    "employer",
    "organization",
    "organisation",
    "company",
    "entreprise",
    "poste",
    "position",
    "stage",
    "internship",
    "freelance",
    "consulting",
    "alternance",
    "cdd",
    "cdi",
    "present",
    "current",
)

ROLE_MARKERS = (
    "manager",
    "assistant",
    "consultant",
    "engineer",
    "ingenieur",
    "developer",
    "developpeur",
    "analyst",
    "analyste",
    "teacher",
    "enseignant",
    "accountant",
    "comptable",
    "sales",
    "commercial",
    "nurse",
    "designer",
    "technician",
    "technicien",
    "coordinator",
    "supervisor",
    "specialist",
    "officer",
)

EDUCATION_MARKERS = (
    "master",
    "licence",
    "bachelor",
    "doctorat",
    "phd",
    "bts",
    "dut",
    "bac+",
    "ingenieur",
    "university",
    "universite",
    "faculty",
    "institute",
    "college",
    "degree",
    "diploma",
    "diplome",
    "certificate",
    "certificat",
    "school",
    "ecole",
    "lycee",
    "high school",
)

SKILL_MARKERS = (
    "excel",
    "word",
    "powerpoint",
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "flutter",
    "sql",
    "docker",
    "linux",
    "communication",
    "leadership",
    "gestion",
    "analyse",
    "salesforce",
    "accounting",
)

NEGATIVE_MARKERS = (
    "lorem ipsum",
    "chapitre",
    "cours",
    "exercice",
    "facture",
    "invoice",
    "conditions generales",
    "politique de confidentialite",
    "privacy policy",
    "cookies",
    "article de blog",
    "blog article",
    "newsletter",
    "communique de presse",
    "press release",
    "formation certifiante",
    "chercheurs d emploi",
    "cliquez pour lire",
    "click to read",
    "urgent offre de formation",
    "terms of service",
)

ACADEMIC_PROGRAM_MARKERS = (
    "semestre",
    "ue",
    "ecue",
    "credits",
    "credit",
    "maquette pedagogique",
    "volume horaire",
    "cours magistral",
    "travaux diriges",
    "travaux pratiques",
    "syllabus",
    "prerequis",
    "pre requis",
    "objectifs pedagogiques",
    "objectif pedagogique",
    "modalites d evaluation",
    "evaluation continue",
    "programme de cours",
    "filiere",
)

JOB_POSTING_MARKERS = (
    "offre d emploi",
    "nous recrutons",
    "profil recherche",
    "postulez",
    "merci d envoyer votre cv",
    "mission principale",
    "candidature a envoyer",
)

CITY_MARKERS = (
    "lome",
    "abidjan",
    "accra",
    "cotonou",
    "dakar",
    "lagos",
    "paris",
    "remote",
    "hybride",
    "hybrid",
)

CANDIDATE_HINT_MARKERS = (
    "candidature",
    "application",
    "open to",
    "open to opportunities",
    "available for",
    "available",
    "disponible",
    "a la recherche",
    "looking for",
    "seeking",
    "profil",
    "profile",
    "about me",
    "based in",
)


@dataclass(slots=True)
class CvDocumentAssessment:
    document_kind: str
    cv_confidence: float
    user_message: str
    signal_summary: dict[str, int]
    prompt_injection_risk: float = 0.0
    prompt_injection_blocked: bool = False
    policy_arm: str | None = None
    policy_decision_id: str | None = None


def _marker_present(text: str, marker: str) -> bool:
    folded = _fold_text(marker)
    if not folded:
        return False
    if " " in folded:
        return folded in text
    return bool(re.search(rf"\b{re.escape(folded)}\b", text))


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if _marker_present(text, marker))


def _unique_year_matches(text: str) -> int:
    return len(set(re.findall(r"\b(?:19\d{2}|20\d{2})\b", text or "")))


def _weird_ratio(text: str) -> float:
    if not text:
        return 1.0
    weird = len(re.findall(r"[^\w\s\.,;:!\\'\"()%\-\/@+#]", text, flags=re.UNICODE))
    return weird / max(len(text), 1)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _user_message(document_kind: str) -> str:
    if document_kind == "cv":
        return "CV importé. Le document semble exploitable pour l'analyse."
    if document_kind == "ambiguous":
        return (
            "Le document a été lu, mais sa structure reste atypique. "
            "Une vérification plus stricte sera appliquée avant le diagnostic."
        )
    return (
        "Ce fichier ne ressemble pas à un CV exploitable. "
        "Importe un CV avec au moins ton profil, tes expériences ou tes compétences."
    )


def _capture_document_assessment_sample(
    cv_text: str,
    *,
    assessment: CvDocumentAssessment,
    used_llm: bool,
) -> None:
    path_raw = str(os.getenv("CV_DOCUMENT_CAPTURE_PATH", "")).strip()
    if not path_raw or not _env_bool("CV_DOCUMENT_CAPTURE_ENABLED", False):
        return
    try:
        path = Path(path_raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        preview = " ".join(cv_text.split())[:320]
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "document_kind": assessment.document_kind,
            "cv_confidence": assessment.cv_confidence,
            "used_llm": used_llm,
            "prompt_injection_risk": assessment.prompt_injection_risk,
            "prompt_injection_blocked": assessment.prompt_injection_blocked,
            "signal_summary": assessment.signal_summary,
            "preview": preview,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def assess_cv_document_text(
    cv_text: str,
    *,
    cv_analysis: CVAnalysisResult | None = None,
) -> CvDocumentAssessment:
    original = str(cv_text or "").replace("\x00", " ").strip()
    prompt_safety = assess_prompt_injection_risk(original)
    if prompt_safety.blocked:
        policy = select_cv_rl_policy()
        assessment = CvDocumentAssessment(
            document_kind="non_cv",
            cv_confidence=0.0,
            user_message=(
                "Le document contient des instructions non pertinentes pour un CV. "
                "Supprime ces instructions puis renvoie un CV propre."
            ),
            signal_summary={
                "contact_signals": 0,
                "section_signals": 0,
                "chronology_signals": 0,
                "experience_signals": 0,
                "education_signals": 0,
                "role_signals": 0,
                "candidate_hint_signals": 0,
                "skill_signals": 0,
                "negative_signals": 0,
                "academic_program_signals": 0,
                "job_posting_signals": 0,
            },
            prompt_injection_risk=prompt_safety.risk_score,
            prompt_injection_blocked=True,
            policy_arm=policy.arm,
            policy_decision_id=policy.decision_id,
        )
        log_cv_rl_decision(
            decision=policy,
            cv_confidence=assessment.cv_confidence,
            document_kind=assessment.document_kind,
            signal_summary=assessment.signal_summary,
        )
        apply_cv_rl_reward(policy.arm, 0.30)
        return assessment

    normalized = _fold_text(original)
    words = len([token for token in re.split(r"\s+", original) if token])
    lines = [line.strip() for line in re.split(r"\r\n", original) if line.strip()]
    bullets = len(re.findall(r"^[\s\-*]", original, flags=re.MULTILINE))

    skills = cv_analysis.skills if cv_analysis is not None else extract_skills_from_text(original)
    experience_years = cv_analysis.experience_years if cv_analysis is not None else None
    education_level = cv_analysis.education_level if cv_analysis is not None else None

    contact_signals = (
        (1 if re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", original, flags=re.IGNORECASE) else 0)
        + (1 if re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", original) else 0)
        + (1 if re.search(r"(linkedin|github|portfolio|behance|website)", original, flags=re.IGNORECASE) else 0)
        + (1 if _count_markers(normalized, CITY_MARKERS) > 0 else 0)
    )
    section_signals = _count_markers(normalized, SECTION_MARKERS)
    chronology_signals = min(4, _unique_year_matches(original))
    if re.search(r"\b\d{1,2}\s*(?:ans?|years?)\b", normalized):
        chronology_signals = max(chronology_signals, 1)
    experience_signals = _count_markers(normalized, EXPERIENCE_MARKERS)
    education_signals = (
        _count_markers(normalized, EDUCATION_MARKERS)
        + (1 if experience_years is not None else 0)
        + (1 if education_level else 0)
    )
    role_signals = _count_markers(normalized, ROLE_MARKERS)
    candidate_hint_signals = _count_markers(normalized, CANDIDATE_HINT_MARKERS)
    skill_signals = min(
        len(skills) + _count_markers(normalized, SKILL_MARKERS),
        6,
    )
    negative_signals = _count_markers(normalized, NEGATIVE_MARKERS)
    academic_program_signals = _count_markers(normalized, ACADEMIC_PROGRAM_MARKERS)
    job_posting_signals = _count_markers(normalized, JOB_POSTING_MARKERS)

    score = 0.05
    score += min(0.22, contact_signals * 0.07)
    score += min(0.24, section_signals * 0.05)
    score += min(0.18, chronology_signals * 0.04)
    score += min(0.16, experience_signals * 0.04)
    score += min(0.12, education_signals * 0.04)
    score += min(0.08, role_signals * 0.03)
    score += min(0.06, skill_signals * 0.01)

    if words >= 180:
        score += 0.08
    elif words >= 90:
        score += 0.05
    elif words >= 45:
        score += 0.02
    else:
        score -= 0.14

    if len(lines) >= 6 or bullets >= 3:
        score += 0.05

    if _weird_ratio(original) > 0.06:
        score -= 0.12

    score -= min(0.40, negative_signals * 0.12)
    score -= min(0.42, academic_program_signals * 0.08)
    score -= min(0.35, job_posting_signals * 0.10)

    if (
        academic_program_signals >= 3
        and experience_signals == 0
        and candidate_hint_signals == 0
        and role_signals == 0
    ):
        score -= 0.30

    if (
        job_posting_signals >= 2
        and candidate_hint_signals == 0
        and contact_signals <= 1
    ):
        score -= 0.30

    if (
        negative_signals == 0
        and words >= 20
        and contact_signals >= 2
        and (role_signals >= 1 or skill_signals >= 2)
    ):
        score = max(score, 0.45)

    if (
        negative_signals == 0
        and words >= 20
        and section_signals >= 1
        and contact_signals >= 1
    ):
        score = max(score, 0.44)

    if (
        negative_signals == 0
        and words >= 20
        and candidate_hint_signals >= 1
        and (contact_signals >= 1 or role_signals >= 1)
    ):
        score = max(score, 0.43)

    if (
        negative_signals == 0
        and words >= 12
        and contact_signals >= 1
        and skill_signals >= 3
    ):
        score = max(score, 0.43)

    if (
        negative_signals == 0
        and words >= 12
        and role_signals >= 1
        and candidate_hint_signals >= 1
    ):
        score = max(score, 0.42)

    if (
        negative_signals == 0
        and words >= 10
        and contact_signals >= 1
        and (section_signals >= 1 or candidate_hint_signals >= 1)
    ):
        score = max(score, 0.42)

    if (
        negative_signals == 0
        and words >= 8
        and role_signals >= 1
        and chronology_signals >= 1
        and candidate_hint_signals >= 1
    ):
        score = max(score, 0.42)

    # Short cover letters should not be rejected as hard non-CV.
    if (
        negative_signals == 0
        and 30 <= words <= 180
        and candidate_hint_signals >= 1
        and contact_signals >= 1
        and section_signals == 0
        and chronology_signals <= 1
    ):
        score = max(score, 0.46)

    if contact_signals == 0 and section_signals < 2 and chronology_signals == 0 and experience_signals == 0:
        score -= 0.20

    cv_confidence = round(_clamp(score), 3)
    policy = select_cv_rl_policy()
    document_kind = "ambiguous"
    if cv_confidence >= policy.cv_threshold:
        document_kind = "cv"
    elif cv_confidence < policy.non_cv_threshold:
        document_kind = "non_cv"

    if (
        document_kind == "cv"
        and cv_confidence < 0.80
        and contact_signals == 0
        and candidate_hint_signals == 0
        and experience_signals == 0
    ):
        document_kind = "ambiguous"
        cv_confidence = round(min(cv_confidence, 0.61), 3)

    if (
        document_kind == "cv"
        and (
            (academic_program_signals >= 3 and experience_signals == 0)
            or (job_posting_signals >= 2 and candidate_hint_signals == 0)
        )
    ):
        document_kind = "non_cv"
        cv_confidence = round(min(cv_confidence, 0.39), 3)

    if (
        academic_program_signals >= 2
        and experience_signals == 0
        and chronology_signals == 0
        and role_signals == 0
    ):
        document_kind = "non_cv"
        cv_confidence = round(min(cv_confidence, 0.34), 3)

    supervised_prediction = predict_supervised_cv_kind(original)
    if supervised_prediction is not None:
        supervised_kind, supervised_confidence = supervised_prediction
        if (
            document_kind == "non_cv"
            and supervised_kind == "ambiguous"
            and cv_confidence >= 0.20
            and candidate_hint_signals >= 1
            and contact_signals >= 1
        ):
            document_kind = "ambiguous"
            cv_confidence = round(max(0.42, min(0.61, (cv_confidence + supervised_confidence) / 2)), 3)
        elif (
            document_kind == "non_cv"
            and supervised_kind == "cv"
            and supervised_confidence >= 0.80
            and contact_signals >= 1
            and (section_signals >= 1 or chronology_signals >= 1)
        ):
            document_kind = "ambiguous"
            cv_confidence = round(max(cv_confidence, 0.45), 3)
        elif (
            document_kind == "ambiguous"
            and supervised_kind == "cv"
            and supervised_confidence >= 0.78
            and (section_signals >= 1 or chronology_signals >= 1)
        ):
            document_kind = "cv"
            cv_confidence = round(max(cv_confidence, 0.62), 3)
        elif (
            document_kind == "ambiguous"
            and supervised_kind == "non_cv"
            and supervised_confidence >= 0.80
            and negative_signals >= 1
            and section_signals == 0
            and candidate_hint_signals == 0
        ):
            document_kind = "non_cv"
            cv_confidence = round(min(cv_confidence, 0.40), 3)

    assessment = CvDocumentAssessment(
        document_kind=document_kind,
        cv_confidence=cv_confidence,
        user_message=_user_message(document_kind),
        signal_summary={
            "contact_signals": contact_signals,
            "section_signals": section_signals,
            "chronology_signals": chronology_signals,
            "experience_signals": experience_signals,
            "education_signals": education_signals,
            "role_signals": role_signals,
            "candidate_hint_signals": candidate_hint_signals,
            "skill_signals": skill_signals,
            "negative_signals": negative_signals,
            "academic_program_signals": academic_program_signals,
            "job_posting_signals": job_posting_signals,
        },
        prompt_injection_risk=prompt_safety.risk_score,
        prompt_injection_blocked=False,
        policy_arm=policy.arm,
        policy_decision_id=policy.decision_id,
    )
    log_cv_rl_decision(
        decision=policy,
        cv_confidence=assessment.cv_confidence,
        document_kind=assessment.document_kind,
        signal_summary=assessment.signal_summary,
    )
    return assessment


async def _arbitrate_ambiguous_document_with_deepseek(
    cv_text: str,
    *,
    client_ip: str,
) -> tuple[str | None, float | None]:
    if not _env_bool("CV_DOCUMENT_DEEPSEEK_AMBIGUOUS_ENABLED", True):
        return None, None

    prompt = (
        "Tu classes un document en une seule question: ressemble-t-il a un CV professionnel exploitable \n"
        "Reponds en JSON strict avec les champs document_kind et confidence.\n"
        "document_kind doit valoir uniquement cv ou non_cv.\n"
        "confidence doit etre un nombre entre 0 et 1.\n\n"
        f"Document:\n{cv_text[:5000]}"
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_kind": {"type": "string", "enum": ["cv", "non_cv"]},
            "confidence": {"type": "number"},
        },
        "required": ["document_kind", "confidence"],
    }
    llm_text, _provider, _model, _error, _status = await _generate_final_response(
        prompt,
        explicit_model="deepseek:deepseek-chat",
        structured_schema=schema,
        expected_mode="no_match",
        attempt=0,
        client_ip=client_ip,
    )
    if not llm_text:
        return None, None
    try:
        payload = json.loads(llm_text)
        document_kind = str(payload.get("document_kind") or "").strip()
        confidence = float(payload.get("confidence") or 0.0)
    except Exception:
        return None, None
    if document_kind not in {"cv", "non_cv"}:
        return None, None
    return document_kind, round(_clamp(confidence), 3)


async def ensure_cv_document_or_raise(
    cv_text: str,
    *,
    cv_analysis: CVAnalysisResult | None = None,
    use_llm: bool,
    client_ip: str,
) -> CvDocumentAssessment:
    assessment, _used_llm = await assess_cv_document_with_optional_llm(
        cv_text,
        cv_analysis=cv_analysis,
        use_llm=use_llm,
        client_ip=client_ip,
    )

    if assessment.prompt_injection_blocked:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PROMPT_INJECTION_BLOCKED",
                "message": assessment.user_message,
                "documentKind": assessment.document_kind,
                "cvConfidence": assessment.cv_confidence,
                "riskScore": assessment.prompt_injection_risk,
            },
        )

    if assessment.document_kind != "cv":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "NOT_A_CV",
                "message": assessment.user_message,
                "documentKind": assessment.document_kind,
                "cvConfidence": assessment.cv_confidence,
            },
        )
    return assessment


async def assess_cv_document_with_optional_llm(
    cv_text: str,
    *,
    cv_analysis: CVAnalysisResult | None = None,
    use_llm: bool,
    client_ip: str,
) -> tuple[CvDocumentAssessment, bool]:
    assessment = assess_cv_document_text(cv_text, cv_analysis=cv_analysis)
    used_llm = False
    if (
        not assessment.prompt_injection_blocked
        and assessment.document_kind == "ambiguous"
        and use_llm
    ):
        llm_kind, llm_confidence = await _arbitrate_ambiguous_document_with_deepseek(
            cv_text,
            client_ip=client_ip,
        )
        if llm_kind in {"cv", "non_cv"}:
            used_llm = True
            assessment = CvDocumentAssessment(
                document_kind=llm_kind,
                cv_confidence=llm_confidence or assessment.cv_confidence,
                user_message=_user_message(llm_kind),
                signal_summary=assessment.signal_summary,
                prompt_injection_risk=assessment.prompt_injection_risk,
                prompt_injection_blocked=assessment.prompt_injection_blocked,
                policy_arm=assessment.policy_arm,
                policy_decision_id=assessment.policy_decision_id,
            )

    _capture_document_assessment_sample(
        cv_text,
        assessment=assessment,
        used_llm=used_llm,
    )

    if assessment.policy_arm:
        reward = 0.45
        if assessment.document_kind == "cv":
            has_signals = bool(cv_analysis and (len(cv_analysis.skills) >= 2 or cv_analysis.experience_years is not None))
            reward = 0.9 if has_signals else 0.65
        elif assessment.document_kind == "non_cv":
            reward = 0.8 if assessment.cv_confidence <= 0.28 else 0.55
        elif assessment.document_kind == "ambiguous":
            reward = 0.60
        if used_llm:
            reward = max(0.25, reward - 0.15)
        apply_cv_rl_reward(assessment.policy_arm, reward)

    return assessment, used_llm
