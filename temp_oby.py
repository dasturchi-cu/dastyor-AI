import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

_OBY_LBL = {
    'uz_lat': {'name_lbl': 'F.I.SH.', 'bdate': 'Tug\'ilgan yili, kuni va oyi', 'bplace': 'Tug\'ilgan joyi', 'nation': 'Millati', 'party': 'Partiyaviyligi', 'edu': 'Ma\'lumoti', 'grad': 'Qaysi oliy (o\'rta) maktabni tamomlagan', 'spec': 'Mutaxassisligi', 'degree': 'Ilmiy darajasi', 'stitle': 'Ilmiy unvoni', 'langs': 'Qaysi chet tillarini biladi', 'military': 'Harbiy yoki maxsus unvoni', 'awards': 'Davlat mukofotlari', 'deputy': 'Deputatlik statusi', 'exp_title': 'MEHNAT FAOLIYATI', 'exp_col1': 'Yillar', 'exp_col2': 'Ish joyi va lavozimi', 'rel_suffix': 'YAQIN QARINDOSHLARI HAQIDA MA\'LUMOT', 'rel_c1': 'Qarindoshligi', 'rel_c2': 'F.I.SH.', 'rel_c3': 'Tug\'ilgan yili va joyi', 'rel_c4': 'Ish joyi va lavozimi', 'rel_c5': 'Yashash manzili', 'photo': '4x6', 'addr':'Yashash manzili'},
    'ru': {'name_lbl': 'Ф.И.О.', 'bdate': 'Год, число и месяц рождения', 'bplace': 'Место рождения', 'nation': 'Национальность', 'party': 'Партийность', 'edu': 'Образование', 'grad': 'Какое учебное заведение окончил(а)', 'spec': 'Специальность', 'degree': 'Учёная степень', 'stitle': 'Учёное звание', 'langs': 'Какими иностранными языками владеет', 'military': 'Воинское звание', 'awards': 'Государственные награды', 'deputy': 'Статус депутата', 'exp_title': 'ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ', 'exp_col1': 'Годы', 'exp_col2': 'Место работы и должность', 'rel_suffix': 'СВЕДЕНИЯ О БЛИЗКИХ РОДСТВЕННИКАХ', 'rel_c1': 'Степень родства', 'rel_c2': 'Ф.И.О.', 'rel_c3': 'Год и место рождения', 'rel_c4': 'Место работы и должность', 'rel_c5': 'Место жительства', 'photo': '4x6', 'addr':'Домашний адрес'}
}

# Add fallbacks
_OBY_LBL['uz_cyr'] = _OBY_LBL['ru'] # Just a placeholder fallback for script simplicity if needed, but wait I should keep original dict.
