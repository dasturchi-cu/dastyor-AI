"""Official Obyektivka layout — barcha o'lchamlar «Намуна Объективка (18).doc» dan."""

from __future__ import annotations

from docx.shared import Emu

# Namuna DOCX section margins va sahifa (mm)
PAGE_WIDTH_MM = 209.99
PAGE_HEIGHT_MM = 296.99
PAGE_MARGIN_TOP_MM = 15.01
PAGE_MARGIN_RIGHT_MM = 10.0
PAGE_MARGIN_BOTTOM_MM = 5.93
PAGE_MARGIN_LEFT_MM = 26.9

FONT_FAMILY = "Times New Roman"
FONT_BODY_PT = 11
FONT_TITLE_PT = 14
FONT_REL_TITLE_PT = 12
LINE_HEIGHT = 1.0

PHOTO_WIDTH_MM = 30
PHOTO_HEIGHT_MM = 40

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
REL_COL_DXA = (1260, 2160, 1830, 3027, 2057)

_REL_TOTAL = sum(REL_COL_DXA)
REL_COL_PCT = tuple(round(w * 100 / _REL_TOTAL, 2) for w in REL_COL_DXA)

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
        "rDep2": "сайланadigan органларнинг аъзосими (тўлиқ кўрсатилиши лозим)",
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
