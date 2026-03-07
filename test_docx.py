import sys
sys.path.insert(0, '.')
from bot.services.doc_generator import generate_obyektivka_docx
import os

test_data = {
    'lang': 'uz_lat',
    'fullname': 'Alisherov Yusuf Muratovich',
    'birthdate': '15.03.1988',
    'birthplace': 'Toshkent viloyati, Yunusobod tumani',
    'nation': "o'zbek",
    'party': "yo'q",
    'education': 'oliy',
    'graduated': 'TDYU, 2010',
    'specialty': 'huquqshunos',
    'degree': "yo'q",
    'scientific_title': "yo'q",
    'languages': 'rus, ingliz',
    'military_rank': "yo'q",
    'awards': "yo'q",
    'deputy': "yo'q",
    'work_experience': [
        {'year': '2010-2015 yy.', 'position': "Toshkent shahri Yunusobod tumani hokimi o'rinbosari"},
        {'year': '2015-2020 yy.', 'position': "O'zbekiston Respublikasi Davlat ayblovchisi"},
        {'year': '2020-hozir', 'position': "Vazirlar Mahkamasi huzuridagi Bosh prokuratura"},
    ],
    'relatives': [
        {'degree': 'Otasi', 'fullname': 'Alisherov Muratjon', 'birth_year_place': '1960 yil, Toshkent', 'work_place': 'Nafaqada', 'address': 'Toshkent sh., Yunusobod t.'},
        {'degree': 'Onasi', 'fullname': 'Alisherova Zilola', 'birth_year_place': '1963 yil, Toshkent', 'work_place': 'Nafaqada', 'address': 'Toshkent sh., Yunusobod t.'},
        {'degree': 'Turmush o\'rtog\'i', 'fullname': 'Alisherova Nodira', 'birth_year_place': '1990 yil, Toshkent', 'work_place': 'TDYU, o\'qituvchi', 'address': 'Toshkent sh., Yunusobod t.'},
    ]
}

try:
    path = generate_obyektivka_docx(test_data, output_dir='temp')
    size = os.path.getsize(path)
    print(f"SUCCESS: {path}")
    print(f"File size: {size:,} bytes ({size//1024} KB)")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
