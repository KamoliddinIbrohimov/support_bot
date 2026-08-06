"""AI mustaqil javob generatsiyasi.

Muammo matni + bazadagi o'xshash yechimlar → Claude javob yaratadi.

"O'qitish" = errors bazasini to'ldirish. Har bir qo'shilgan xatolik-yechim
juftligi AI ning "bilimi" ni oshiradi.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from bot.services.ai_client import complete
from config.logger import logger
from database.models import ErrorEntry

_SYSTEM_UZ = """\
Sen O'zbekistondagi E-POS (elektron kassa, fiskal ro'yxatga olish tizimi) uchun \
texnik yordam botisan. Kassirlar va mijozlarning muammolarini hal qilishda yordam berasan.

Quyida bizning bilimlar bazamizdagi mavjud yechimlar berilgan (kontekst):
{context}

Mijozning muammosi: {problem}

Qoidalar:
- Faqat yuqoridagi kontekst asosida javob ber
- Agar aniq javob topa olmasang — "Bu masala bo'yicha aniq ma'lumot yo'q, \
support xodimiga murojaat qiling" de
- Javob qisqa va aniq bo'lsin (3-5 qadam)
- O'zbek tilida yoz
- Agar kontekstda javob yo'q — null qaytarasiz (faqat "null" so'zi)
"""

_SYSTEM_RU = """\
Ты бот технической поддержки для E-POS (электронная касса, фискальная \
регистрация) в Узбекистане. Помогаешь кассирам и клиентам решать проблемы.

Ниже приведены известные решения из нашей базы знаний (контекст):
{context}

Проблема клиента: {problem}

Правила:
- Отвечай только на основе контекста выше
- Если точного ответа нет — напиши "Нет точных данных по этому вопросу, \
обратитесь к специалисту"
- Ответ должен быть кратким и чётким (3-5 шагов)
- Пиши на русском языке
- Если в контексте нет ответа — верни только слово "null"
"""


@dataclass
class AIAnswer:
    text: str
    used_context: bool  # bazadan kontekst ishlatilganmi


def _build_context(errors: list[ErrorEntry], problem: str, lang: str, top_n: int = 5) -> str:
    """Muammoga eng o'xshash xatoliklarni fuzzy bilan topib, kontekst quradi."""
    scored: list[tuple[float, ErrorEntry]] = []
    problem_norm = problem.lower()

    for err in errors:
        keywords = err.get_keywords(lang) or err.get_keywords("ru") or []
        title = err.get_title(lang) or ""
        solution = err.get_solution(lang) or ""

        best = 0.0
        for kw in keywords:
            s = max(
                fuzz.partial_ratio(kw.lower(), problem_norm),
                fuzz.token_set_ratio(kw.lower(), problem_norm),
            )
            if s > best:
                best = s
        # Title va solution bilan ham solishtiramiz
        best = max(best, fuzz.partial_ratio(title.lower(), problem_norm) * 0.8)
        scored.append((best, err))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [e for score, e in scored[:top_n] if score > 20]

    if not top:
        return ""

    lines = []
    for i, err in enumerate(top, 1):
        title = err.get_title(lang) or err.title or "—"
        solution = err.get_solution(lang) or err.solution or "—"
        lines.append(f"{i}. Muammo: {title}\n   Yechim: {solution[:300]}")

    return "\n\n".join(lines)


async def generate(
    problem: str,
    errors: list[ErrorEntry],
    lang: str = "uz",
) -> AIAnswer | None:
    """Muammo bo'yicha AI mustaqil javob yaratadi.

    Returns:
        AIAnswer — javob topilsa
        None — AI javob bera olmasa yoki null qaytarsa
    """
    if not problem.strip() or not errors:
        return None

    context = _build_context(errors, problem, lang)
    system_template = _SYSTEM_UZ if lang != "ru" else _SYSTEM_RU
    system = system_template.format(
        context=context if context else "(hozircha bazada ma'lumot yo'q)",
        problem=problem[:500],
    )

    raw = await complete(system=system, user=problem[:500], max_tokens=400)
    if not raw:
        return None

    raw = raw.strip()
    if raw.lower() == "null" or not raw:
        return None

    # Javob sifatsiz bo'lsa (juda qisqa yoki "null" iboralari)
    low = raw.lower()
    if len(raw) < 20 or any(w in low for w in ("null", "no answer", "нет ответа")):
        return None

    ctx_mark = "ha" if context else "yoq"
    logger.info(f"[ai-answer] Javob yaratildi: {len(raw)} belgi, context={ctx_mark}")
    return AIAnswer(text=raw, used_context=bool(context))
