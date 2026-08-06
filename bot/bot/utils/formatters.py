from __future__ import annotations

from html import escape

from bot.i18n import t
from database.models import ErrorEntry


def format_match_reply(
    *,
    title: str,
    detected_text: str,
    solution: str,
    score: float,
    lang: str = "uz",
    via_vision: bool = False,
) -> str:
    parts = [
        f"{t('match_header', lang)}\n\n",
        f"{t('match_problem', lang)}\n{escape(title)}\n\n",
        f"{t('match_solution', lang)}\n{escape(solution)}\n\n",
        f"{t('match_accuracy', lang)} {score:.0f}%",
    ]
    if via_vision:
        parts.append(f"\n{t('match_via_vision', lang)}")
    return "".join(parts)


def format_no_match_reply(detected_text: str, lang: str = "uz") -> str:
    return f"{t('no_match', lang)}\n\n{t('no_match_body', lang)}"


def format_empty_ocr_reply(lang: str = "uz") -> str:
    return t("ocr_empty", lang)


def format_errors_list(errors: list[ErrorEntry], lang: str = "uz") -> str:
    if not errors:
        return t("errors_empty", lang)

    lines = [t("errors_header", lang)]
    for e in errors:
        title = e.get_title(lang)
        solution = e.get_solution(lang)
        keywords = e.get_keywords(lang)
        kw_str = ", ".join(keywords) if keywords else "—"
        video_mark = " 🎥" if e.solution_video_file_id else ""
        lines.append(
            f"<b>#{e.id}</b>{video_mark} — {escape(title)}\n"
            f"🔑 <i>{escape(kw_str)}</i>\n"
            f"💡 {escape(solution[:200])}{'…' if len(solution) > 200 else ''}\n"
        )
    return "\n".join(lines)
