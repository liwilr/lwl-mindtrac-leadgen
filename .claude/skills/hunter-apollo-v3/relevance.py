"""Drops non-BD contacts inside relevant buckets: careers/HR mailboxes and HR, recruiting,
social-media or junior-support titles. Short words match whole-word/token only ("hr" is inside
"Fakhry", "intern" inside "International")."""

import re

# Exact tokens of the email local-part (split on . _ + -).
_EXCLUDED_EMAIL_TOKENS = {
    "career", "careers", "job", "jobs", "jobopenings", "vacancy", "vacancies",
    "hiring", "recruit", "recruiter", "recruiting", "recruitment",
    "talent", "hr", "humanresources", "apply", "applications", "cv", "resume",
    "rrhh", "empleo", "empleos", "trabajaconnosotros", "postulaciones", "seleccion",
    "recrutamento", "vagas", "carreiras", "curriculo", "trabalheconosco",
    # Recycling-programme inboxes: not sales contacts (product-specific ones, e.g. nfu, come from the workflow request).
    "reciclaje", "recycling",
    # Customer-service inboxes (same reasoning as the "customer service" title exclusion).
    "servicioalcliente", "servicialcliente", "atencionalcliente", "customerservice", "soporte", "support", "reclamos",
}

# Multi-word phrases: plain substring checks.
_EXCLUDED_TITLE_PHRASES = (
    "human resource", "recruiter", "recruiting", "recruitment",
    "talent acquisition", "social media", "community manager",
    "content creator", "content writer", "graphic designer", "receptionist",
    "office manager", "administrative assistant", "customer service",
    "customer support",
    # Spanish equivalents
    "recursos humanos", "reclutamiento", "selección de personal", "seleccion de personal",
    "redes sociales", "diseñador gráfico", "diseñadora gráfica", "recepcionista",
    "asistente administrativo", "asistente administrativa", "servicio al cliente",
    "atención al cliente", "atencion al cliente",
    # IT / technical support (not a buying or selling role)
    "it support", "technical support", "help desk", "helpdesk", "soporte técnico", "soporte tecnico",
    "mesa de ayuda", "suporte técnico", "suporte tecnico",
)

# Short words: whole-word matching.
_EXCLUDED_TITLE_WORDS = ("hr", "intern", "trainee", "career", "careers", "rrhh", "practicante", "pasante",
                         "soporte", "suporte", "sistemas")
_WORD_RES = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in _EXCLUDED_TITLE_WORDS]


def is_excluded_email(email):
    """True if this address's local-part is a careers/HR/recruiting/recycling mailbox."""
    local_part = (email or "").split("@", 1)[0].lower()
    tokens = re.split(r"[._+\-]", local_part)
    # Trailing digits are ignored, so "jobs2" matches "jobs".
    return any(t in _EXCLUDED_EMAIL_TOKENS or t.rstrip("0123456789") in _EXCLUDED_EMAIL_TOKENS for t in tokens if t)


def is_excluded_title(title):
    """True if the title is HR/recruiting/social-media/IT-support/junior-support work."""
    text = (title or "").lower()
    if any(r.search(text) for r in _WORD_RES):
        return True
    return any(phrase in text for phrase in _EXCLUDED_TITLE_PHRASES)


def is_relevant_contact(email, position):
    """Last gate before keeping a row."""
    return not is_excluded_email(email) and not is_excluded_title(position)
