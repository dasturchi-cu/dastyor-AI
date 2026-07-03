"""Official Obyektivka layout — barcha o'lchamlar «Намуна Объективка (18).doc» dan."""

from __future__ import annotations

from docx.shared import Emu

# Namuna ref_converted.docx — sectPr pgMar (twips), asimetrik
PAGE_MARGIN_TOP_TWIPS = 851
PAGE_MARGIN_RIGHT_TWIPS = 567
PAGE_MARGIN_BOTTOM_TWIPS = 336
PAGE_MARGIN_LEFT_TWIPS = 1525

PAGE_WIDTH_MM = 209.99
PAGE_HEIGHT_MM = 296.99
PAGE_MARGIN_TOP_MM = round(PAGE_MARGIN_TOP_TWIPS / 56.7, 2)
PAGE_MARGIN_RIGHT_MM = round(PAGE_MARGIN_RIGHT_TWIPS / 56.7, 2)
PAGE_MARGIN_BOTTOM_MM = round(PAGE_MARGIN_BOTTOM_TWIPS / 56.7, 2)
PAGE_MARGIN_LEFT_MM = round(PAGE_MARGIN_LEFT_TWIPS / 56.7, 2)

FONT_FAMILY = "Times New Roman"
# PPT namuna (pt)
FONT_TITLE_PT = 14  # MA'LUMOTNOMA, F.I.Sh, MEHNAT FAOLIYATI
FONT_REL_SECTION_PT = 12  # MA'LUMOT (qarindoshlar sarlavhasi)
FONT_BODY_PT = 11  # body, work history, form values, photo note
FONT_PHOTO_HINT_PT = 11  # photo caption block
LINE_HEIGHT = 1.15

PHOTO_WIDTH_MM = 30
PHOTO_HEIGHT_MM = 40
# Namuna VML v:rect (pt) — PPT A4: o'ng 18mm, yuqori 20mm, 3×4 sm
PHOTO_VML_WIDTH_PT = 85.05   # 30 mm
PHOTO_VML_HEIGHT_PT = 113.4  # 40 mm
PHOTO_VML_MARGIN_LEFT_PT = 406.0  # margin chapidan (143.1mm offset)
PHOTO_VML_MARGIN_TOP_PT = 14.1   # margin tepasidan (4.99mm offset)
PHOTO_VML_Z_INDEX = 251659264
PHOTO_OFFSET_LEFT_MM = round(PHOTO_VML_MARGIN_LEFT_PT * 25.4 / 72 - PAGE_MARGIN_LEFT_MM, 2)
PHOTO_OFFSET_TOP_MM = round(PHOTO_VML_MARGIN_TOP_PT * 25.4 / 72, 2)

# Tab stops (EMU) — namuna DOCX
TAB_COL_POS = Emu(2684780)
TAB_PHOTO_POS = Emu(5600700)
TAB_NAME_CENTER_POS = Emu(3023870)
TAB_YEAR_POS = Emu(428625)
TAB_WORK_TITLE_POS = Emu(2620010)

# Paragraph indents (twips) — namuna DOCX
IND_HDR_RIGHT_TWIPS = 1204
IND_JOB_RIGHT_TWIPS = 2547
IND_VALUE_LEFT_TWIPS = 4320
IND_VALUE_RIGHT_TWIPS = 2016
IND_VALUE_HANGING_TWIPS = 4320
IND_INLINE_LEFT_TWIPS = 1622
IND_INLINE_HANGING_TWIPS = 1622
IND_STACK_LEFT_TWIPS = 1622
IND_STACK_HANGING_TWIPS = 1622
IND_DEP_STACK_LEFT_TWIPS = 1512
IND_DEP_STACK_HANGING_TWIPS = 1512
IND_WORK_HANGING_TWIPS = 1622
IND_REL_COL0_TWIPS = -113

# Qarindoshlar jadvali ustunlari (dxa)
REL_COL_DXA = (1400, 2300, 2164, 2300, 1700)

_REL_TOTAL = sum(REL_COL_DXA)
REL_COL_PCT = tuple(round(w * 100 / _REL_TOTAL, 2) for w in REL_COL_DXA)

# A4 sahifa kengligi (twips) — jadval matn maydoniga sigishi kerak
PAGE_WIDTH_TWIPS = 11906
REL_TABLE_WIDTH_DXA = PAGE_WIDTH_TWIPS - PAGE_MARGIN_LEFT_TWIPS - PAGE_MARGIN_RIGHT_TWIPS


def scaled_rel_col_dxa(target: int | None = None) -> tuple[int, ...]:
    """Ustunlarni berilgan jadval kengligiga proporsional qisqartirish."""
    width = target or REL_TABLE_WIDTH_DXA
    total = sum(REL_COL_DXA)
    scaled: list[int] = []
    used = 0
    for i, w in enumerate(REL_COL_DXA):
        if i == len(REL_COL_DXA) - 1:
            scaled.append(max(1, width - used))
        else:
            col = max(1, round(w * width / total))
            scaled.append(col)
            used += col
    return tuple(scaled)

OB_LABELS: dict[str, dict[str, str]] = {
    "uz_lat": {
        "title": "MA'LUMOTNOMA",
        "photo_hint": (
            "Oq fondagi 3x4 sm, oxirgi 3 oy davomida olingan rangli fotosurat, "
            "elektron ko'rinishda (rasmiy kiyimda)."
        ),
        "none": "yo'q",
        "work": "MEHNAT FAOLIYATI",
        "rel_line1_suffix": "ning yaqin qarindoshlari haqida",
        "rel_line2": "MA'LUMOT",
        "no_rel": "Yaqin qarindoshlar haqida ma'lumot kiritilmagan.",
        "qar": "Qarindoshligi",
        "fish": "Familiyasi, ismi va otasining ismi",
        "tug": "Tug'ilgan yili va joyi",
        "ish": "Ish joyi va lavozimi",
        "tur": "Turar joyi",
        "r1l": "Tug'ilgan yili",
        "r1r": "Tug'ilgan joyi",
        "r2l": "Millati",
        "r2r": "Partiyaviyligi",
        "r3l": "Ma'lumoti",
        "r3r": "Tamomlagan",
        "rSpec": "Ma'lumoti bo'yicha mutaxassisligi",
        "r4l": "Ilmiy darajasi",
        "r4r": "Ilmiy unvoni",
        "r5l": "Qaysi chet tillarini biladi",
        "r5r": "Harbiy (maxsus) unvoni",
        "rAw": "Davlat mukofotlari va premiyalari bilan taqdirlanganmi (qanaqa)",
        "rIdo": "Idoraviy mukofotlar bilan taqdirlanganmi (qanaqa)",
        "rDep1": (
            "Xalq deputatlari, respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa"
        ),
        "rDep2": "saylanadigan organlarning a'zosimi (to'liq ko'rsatish lozim)",
    },
    "uz_cyr": {
        "title": "МАЪЛУМОТНОМА",
        "photo_hint": (
            "Оқ фондаги 3х4 см, охирги 3 ой давомида олинган рангли фотосурат, "
            "электрон кўринишда (расмий кийимда)."
        ),
        "none": "йўқ",
        "work": "МЕҲНАТ ФАОЛИЯТИ",
        "rel_line1_suffix": "нинг яқин қариндошлари ҳақида",
        "rel_line2": "МАЪЛУМОТ",
        "no_rel": "Яқин қариндошлар ҳақида маълумот киритилмаган.",
        "qar": "Қариндошлиги",
        "fish": "Фамилияси, исми ва отасининг исми",
        "tug": "Туғилган йили ва жойи",
        "ish": "Иш жойи ва лавозими",
        "tur": "Турар жойи",
        "r1l": "Туғилган йили",
        "r1r": "Туғилган жойи",
        "r2l": "Миллати",
        "r2r": "Партиявийлиги",
        "r3l": "Маълумоти",
        "r3r": "Тамомлаган",
        "rSpec": "Маълумоти бўйича мутахассислиги",
        "r4l": "Илмий даражаси",
        "r4r": "Илмий унвони",
        "r5l": "Қайси чет тилларини билади",
        "r5r": "Ҳарбий (махсус) унвони",
        "rAw": "Давлат мукофотлари ва премиялари билан тақдирланганми (қанақа)",
        "rIdo": "Идоравий мукофотлар билан тақдирланганми (қанақа)",
        "rDep1": (
            "Халқ депутатлари, республика, вилоят, шаҳар ва туман Кенгаши депутатими ёки бошқа"
        ),
        "rDep2": "сайланадиган органларнинг аъзосими (тўлиқ кўрсатилиши лозим)",
    },
    "en": {
        "title": "REFERENCE SHEET",
        "photo_hint": (
            "Color photograph 3x4 cm, taken in the last 3 months, "
            "in electronic form (formal wear)."
        ),
        "none": "none",
        "work": "WORK HISTORY",
        "rel_line1_suffix": "'s close relatives information",
        "rel_line2": "INFORMATION",
        "no_rel": "No information about close relatives entered.",
        "qar": "Relationship",
        "fish": "Surname, Name and Patronymic",
        "tug": "Year and place of birth",
        "ish": "Place of work and position",
        "tur": "Place of residence",
        "r1l": "Year of birth",
        "r1r": "Place of birth",
        "r2l": "Nationality",
        "r2r": "Party membership",
        "r3l": "Education",
        "r3r": "Graduated",
        "rSpec": "Speciality by education",
        "r4l": "Academic degree",
        "r4r": "Academic title",
        "r5l": "Which foreign languages does he/she know",
        "r5r": "Military (special) rank",
        "rAw": "Has he/she been awarded state awards and prizes (what)",
        "rIdo": "Has he/she been awarded departmental awards (what)",
        "rDep1": (
            "Whether a deputy of national, regional, city or district Council or a member"
        ),
        "rDep2": "of other elective bodies (specify in full)",
    },
    "ru": {
        "title": "СПРАВКА-ОБЪЕКТИВКА",
        "photo_hint": (
            "Цветная фотография 3х4 см, сделанная за последние 3 месяца, "
            "в электронном виде (в деловой одежде)."
        ),
        "none": "нет",
        "work": "ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ",
        "rel_line1_suffix": " о близких родственниках",
        "rel_line2": "СВЕДЕНИЯ",
        "no_rel": "Сведения о близких родственниках не внесены.",
        "qar": "Степень родства",
        "fish": "Фамилия, имя и отчество",
        "tug": "Год и место рождения",
        "ish": "Место работы и должность",
        "tur": "Место жительства",
        "r1l": "Год рождения",
        "r1r": "Место рождения",
        "r2l": "Национальность",
        "r2r": "Партийность",
        "r3l": "Образование",
        "r3r": "Окончил",
        "rSpec": "Специальность по образованию",
        "r4l": "Ученая степень",
        "r4r": "Ученое звание",
        "r5l": "Какими иностранными языками владеет",
        "r5r": "Воинское (специальное) звание",
        "rAw": "Награжден ли государственными наградами и премиями (какими)",
        "rIdo": "Награжден ли ведомственными наградами (какими)",
        "rDep1": (
            "Является ли депутатом Совета народных депутатов, республиканского, областного, городского"
        ),
        "rDep2": "или членом других выборных органов (указать полностью)",
    },
}


def labels_for(lang: str | None) -> dict[str, str]:
    key = (lang or "uz_lat").strip()
    if key in OB_LABELS:
        return OB_LABELS[key]
    if key in ("uz_l", "uz"):
        return OB_LABELS["uz_lat"]
    if key in ("uz_k", "uz_cyr"):
        return OB_LABELS["uz_cyr"]
    return OB_LABELS["uz_lat"]
