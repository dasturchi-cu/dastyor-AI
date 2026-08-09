import sys

sys.stdout.reconfigure(encoding="utf-8")
from features.obyektivka.docx_polish import _is_label_paragraph

for t in ["25.10.1960", "O'zbek", "йўқ", "Миллати:", "Туғилган йили:"]:
    print(repr(t), _is_label_paragraph(t))
