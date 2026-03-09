import os
from bot.services.obyektivka_docx import generate_obyektivka_docx

data = {
    "fullname": "Alisherov Yusuf Muratovich",
    "birthdate": "01.01.1990",
    "birthplace": "Toshkent viloyati",
    "nation": "o'zbek",
    "party": "yo'q",
    "education": "oliy",
    "graduated": "2015, TDYU",
    "specialty": "huquqshunos",
    "degree": "yo'q",
    "scientific_title": "yo'q",
    "languages": "rus va ingliz",
    "awards": "yo'q",
    "deputy": "yo'q",
    "work_experience": [
        {"year": "2015-2020", "position": "Hokim yordamchisi"},
        {"year": "2020-2023", "position": "Hokim o'rinbosari"}
    ],
    "relatives": [
        {"degree": "Otasi", "fullname": "Alisherov Muratjon", "birth_year_place": "1965, Toshkent", "work_place": "Nafaqada", "address": "Toshkent shahri"}
    ]
}

out_path = "test_oby.docx"
generate_obyektivka_docx(data, None, out_path)
print(f"Generated successfully: {out_path}")
