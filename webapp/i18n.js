/**
 * DASTYOR AI — Global i18n System  (webapp/i18n.js)
 * ──────────────────────────────────────────────────
 * Supported locales:  uz_lat | uz_cyr | en | ru
 *
 * USAGE IN HTML:
 *   Add  data-i18n="key"  to any element.
 *   Call  I18n.apply()  after changing language,
 *   or just call  I18n.setLang('en')  which auto-applies.
 *
 * USAGE IN JS:
 *   const t = I18n.t;
 *   btn.textContent = t('generate');
 */

const I18n = (() => {
    'use strict';

    const LS_KEY = 'lang';

    // ─────────────────────────────────────────────────────
    // TRANSLATION DICTIONARY
    // Key format: module_element  (e.g. nav_home, cv_name)
    // ─────────────────────────────────────────────────────
    const _dict = {

        // ════════════════════════════════════════════════
        // GLOBAL / NAVIGATION
        // ════════════════════════════════════════════════
        app_name:          { uz_lat: 'DASTYOR AI',         uz_cyr: 'DASTYOR AI',         en: 'DASTYOR AI',           ru: 'DASTYOR AI'           },
        nav_home:          { uz_lat: 'Bosh sahifa',        uz_cyr: 'Бош саҳифа',          en: 'Home',                 ru: 'Главная'              },
        nav_services:      { uz_lat: 'Xizmatlar',          uz_cyr: 'Хизматлар',           en: 'Services',             ru: 'Услуги'               },
        nav_premium:       { uz_lat: 'Premium',            uz_cyr: 'Premium',             en: 'Premium',              ru: 'Премиум'              },
        nav_settings:      { uz_lat: 'Sozlamalar',         uz_cyr: 'Созламалар',          en: 'Settings',             ru: 'Настройки'            },
        nav_more:          { uz_lat: "Ko'proq",            uz_cyr: "Кўпроқ",              en: 'More',                 ru: 'Ещё'                  },
        nav_back:          { uz_lat: 'Orqaga',             uz_cyr: 'Орқага',              en: 'Back',                 ru: 'Назад'                },

        // ════════════════════════════════════════════════
        // INDEX / HOME
        // ════════════════════════════════════════════════
        welcome:           { uz_lat: 'Xush kelibsiz,',    uz_cyr: 'Хуш келибсиз,',       en: 'Welcome,',             ru: 'Добро пожаловать,'    },
        home_activity:     { uz_lat: 'Aktivlik',          uz_cyr: 'Активлик',            en: 'Activity',             ru: 'Активность'           },
        home_active:       { uz_lat: 'Faol',              uz_cyr: 'Фаол',                en: 'Active',               ru: 'Активен'              },
        home_requests:     { uz_lat: "so'rovlar",         uz_cyr: "сўровлар",            en: 'requests',             ru: 'запросов'             },
        home_apps:         { uz_lat: 'Ilovalar tizimi',   uz_cyr: 'Иловалар тизими',     en: 'App System',           ru: 'Система приложений'   },
        home_settings:     { uz_lat: 'Sozlamalar',        uz_cyr: 'Созламалар',          en: 'Settings',             ru: 'Настройки'            },
        home_customize:    { uz_lat: "Ilovani o'zingizga moslang", uz_cyr: "Иловани ўзингизга мосланг", en: 'Customize your app', ru: 'Настройте приложение' },

        // ════════════════════════════════════════════════
        // SETTINGS
        // ════════════════════════════════════════════════
        settings_theme:    { uz_lat: 'Mavzu Rejimi',      uz_cyr: 'Мавзу Режими',        en: 'Theme Mode',           ru: 'Режим темы'           },
        settings_dark:     { uz_lat: 'Tungi rejim yoqiq', uz_cyr: 'Тунги режим ёқиқ',   en: 'Dark mode on',         ru: 'Тёмный режим вкл.'    },
        settings_light_on: { uz_lat: 'Kunduzgi rejim',   uz_cyr: 'Кундузги режим',      en: 'Light mode',           ru: 'Светлый режим'        },
        settings_lang:     { uz_lat: "Til",               uz_cyr: "Тил",                 en: 'Language',             ru: 'Язык'                 },
        settings_support:  { uz_lat: 'Yordam & Info',     uz_cyr: 'Ёрдам & Info',        en: 'Support & Info',       ru: 'Поддержка & Инфо'     },
        settings_via_bot:  { uz_lat: 'Bot orqali',        uz_cyr: 'Бот орқали',          en: 'Via bot',              ru: 'Через бота'           },

        // Theme labels
        theme_dark:        { uz_lat: 'Tungi',             uz_cyr: 'Тунги',               en: 'Dark',                 ru: 'Тёмная'               },
        theme_light:       { uz_lat: 'Kunduzgi',          uz_cyr: 'Кундузги',            en: 'Light',                ru: 'Светлая'              },

        // Language names (shown in picker)
        lang_uz_lat:       { uz_lat: "O'zbek (Lotin)",   uz_cyr: "O'zbek (Lotin)",      en: "Uzbek (Latin)",        ru: "Узбекский (Лат.)"     },
        lang_uz_cyr:       { uz_lat: "O'zbek (Kirill)",  uz_cyr: "Ўзбек (Кирилл)",      en: "Uzbek (Cyrillic)",     ru: "Узбекский (Кир.)"     },
        lang_en:           { uz_lat: "Inglizcha",         uz_cyr: "Инглизча",            en: "English",              ru: "Английский"           },
        lang_ru:           { uz_lat: "Ruscha",            uz_cyr: "Русча",               en: "Russian",              ru: "Русский"              },

        // ════════════════════════════════════════════════
        // SERVICES / MORE PAGE
        // ════════════════════════════════════════════════
        svc_obyektivka:    { uz_lat: 'Obyektivka AI',     uz_cyr: 'Объективка AI',       en: 'CV Record AI',         ru: 'Объективка AI'        },
        svc_obyektivka_d:  { uz_lat: "Rasmiy, davlat standartlaridagi ma'lumotnoma", uz_cyr: "Расмий, давлат стандартларидаги маълумотнома", en: 'Official government-format record', ru: 'Официальная анкета госстандарта' },
        svc_cv:            { uz_lat: 'CV Builder',        uz_cyr: 'CV Builder',          en: 'CV Builder',           ru: 'Конструктор резюме'   },
        svc_cv_d:          { uz_lat: "Zamonaviy, xalqaro formatdagi rezyume", uz_cyr: "Замонавий, халқаро форматдаги резюме", en: 'Modern international-format resume', ru: 'Современное международное резюме' },
        svc_ai_tools:      { uz_lat: 'AI Tools',          uz_cyr: 'AI Tools',            en: 'AI Tools',             ru: 'AI Инструменты'       },
        svc_ai_tools_d:    { uz_lat: "Tarjimon, rasmda o'qish va harf o'girish", uz_cyr: "Таржимон, расмда ўқиш ва ҳарф ўгириш", en: 'Translator, OCR and character converter', ru: 'Переводчик, OCR и конвертер' },
        svc_ocr:           { uz_lat: "Rasm → Word",       uz_cyr: "Расм → Word",         en: "Image → Word",         ru: "Изображение → Word"   },
        svc_ocr_d:         { uz_lat: "Rasmdan matnni ajratib Word hujjat yaratish", uz_cyr: "Расмдан матнни ажратиб Word ҳужжат яратиш", en: 'Extract text from image and create Word doc', ru: 'Извлечь текст из изображения в Word' },
        svc_pdf:           { uz_lat: "Rasm → PDF",        uz_cyr: "Расм → PDF",          en: "Image → PDF",          ru: "Изображение → PDF"    },
        svc_pdf_d:         { uz_lat: "Bir nechta rasmni PDFga birlashtirish", uz_cyr: "Бир нечта расмни PDFга бирлаштириш", en: 'Merge multiple images into one PDF', ru: 'Объединить изображения в PDF' },
        svc_translate:     { uz_lat: 'Tarjima',           uz_cyr: 'Таржима',             en: 'Translation',          ru: 'Перевод'              },
        svc_translate_d:   { uz_lat: "UZ ↔ EN ↔ RU tarjimasi", uz_cyr: "UZ ↔ EN ↔ RU таржимаси", en: 'UZ ↔ EN ↔ RU translation', ru: 'Перевод UZ ↔ EN ↔ RU' },
        svc_translit:      { uz_lat: "Krill ↔ Lotin",     uz_cyr: "Кирилл ↔ Лотин",     en: "Cyrillic ↔ Latin",     ru: "Кириллица ↔ Латиница" },
        svc_translit_d:    { uz_lat: "O'zbek matnini harf tizimlar orasida o'girish", uz_cyr: "Ўзбек матнини ҳарф тизимлар орасида ўгириш", en: 'Convert Uzbek text between scripts', ru: 'Конвертировать узбекский текст между алфавитами' },
        svc_spell:         { uz_lat: "Imlo tekshirish",   uz_cyr: "Имло текшириш",       en: "Spell Check",          ru: "Проверка орфографии"  },
        svc_spell_d:       { uz_lat: "Hujjatdagi imlo xatolarni avtomatik tuzatish", uz_cyr: "Ҳужжатдаги имло хатоларни автоматик тузатиш", en: 'Auto-correct spelling errors in document', ru: 'Автоматическое исправление орфографии' },

        // ════════════════════════════════════════════════
        // COMMON BUTTONS & LABELS
        // ════════════════════════════════════════════════
        btn_generate:      { uz_lat: 'Yaratish',          uz_cyr: 'Яратиш',              en: 'Generate',             ru: 'Создать'              },
        btn_download:      { uz_lat: 'Yuklab olish',      uz_cyr: 'Юклаб олиш',          en: 'Download',             ru: 'Скачать'              },
        btn_upload:        { uz_lat: 'Yuklash',           uz_cyr: 'Юклаш',               en: 'Upload',               ru: 'Загрузить'            },
        btn_clear:         { uz_lat: "Tozalash",          uz_cyr: "Тозалаш",             en: 'Clear',                ru: 'Очистить'             },
        btn_copy:          { uz_lat: "Nusxalash",         uz_cyr: "Нусхалаш",            en: 'Copy',                 ru: 'Копировать'           },
        btn_save:          { uz_lat: "Saqlash",           uz_cyr: "Сақлаш",              en: 'Save',                 ru: 'Сохранить'            },
        btn_cancel:        { uz_lat: "Bekor qilish",      uz_cyr: "Бекор қилиш",         en: 'Cancel',               ru: 'Отмена'               },
        btn_continue:      { uz_lat: "Davom etish",       uz_cyr: "Давом этиш",           en: 'Continue',             ru: 'Продолжить'           },
        btn_send:          { uz_lat: "Yuborish",          uz_cyr: "Юбориш",              en: 'Send',                 ru: 'Отправить'            },
        btn_add:           { uz_lat: "Qo'shish",          uz_cyr: "Қўшиш",               en: 'Add',                  ru: 'Добавить'             },
        btn_remove:        { uz_lat: "O'chirish",         uz_cyr: "Ўчириш",              en: 'Remove',               ru: 'Удалить'              },
        btn_new:           { uz_lat: "Yangi",             uz_cyr: "Янги",                en: 'New',                  ru: 'Новый'                },
        btn_export_word:   { uz_lat: "Word yuklash",      uz_cyr: "Word юклаш",          en: 'Download Word',        ru: 'Скачать Word'         },
        btn_export_pdf:    { uz_lat: "PDF yuklash",       uz_cyr: "PDF юклаш",           en: 'Download PDF',         ru: 'Скачать PDF'          },
        btn_preview:       { uz_lat: "Ko'rish",           uz_cyr: "Кўриш",               en: 'Preview',              ru: 'Просмотр'             },

        // Status messages
        status_processing: { uz_lat: "Jarayon davom etmoqda...", uz_cyr: "Жараён давом этмоқда...", en: 'Processing...', ru: 'Обработка...'      },
        status_success:    { uz_lat: "Muvaffaqiyatli!",   uz_cyr: "Муваффақиятли!",      en: 'Success!',             ru: 'Успешно!'             },
        status_error:      { uz_lat: "Xatolik yuz berdi", uz_cyr: "Хатолик юз берди",    en: 'An error occurred',    ru: 'Произошла ошибка'     },
        status_uploading:  { uz_lat: "Yuklanmoqda...",    uz_cyr: "Юкланмоқда...",       en: 'Uploading...',         ru: 'Загрузка...'          },
        status_ready:      { uz_lat: "Tayyor!",           uz_cyr: "Тайёр!",              en: 'Ready!',               ru: 'Готово!'              },

        // Form placeholders
        ph_name:           { uz_lat: "Ism Familiya",      uz_cyr: "Исм Фамилия",         en: 'Full Name',            ru: 'Полное имя'           },
        ph_email:          { uz_lat: "elektron pochta",   uz_cyr: "электрон почта",      en: 'email address',        ru: 'эл. почта'            },
        ph_phone:          { uz_lat: "telefon raqami",    uz_cyr: "телефон рақами",      en: 'phone number',         ru: 'номер телефона'       },
        ph_text:           { uz_lat: "Matn kiriting...",  uz_cyr: "Матн киритинг...",    en: 'Enter text...',        ru: 'Введите текст...'     },

        // ════════════════════════════════════════════════
        // OBYEKTIVKA PAGE
        // ════════════════════════════════════════════════
        obv_title:         { uz_lat: "Obyektivka AI",     uz_cyr: "Объективка AI",       en: 'CV Record AI',         ru: 'Объективка AI'        },
        obv_sub:           { uz_lat: "Ma'lumot kiriting, biz tuzib beramiz", uz_cyr: "Маълумот киритинг, биз тузиб берамиз", en: "Enter data, we'll generate", ru: 'Введите данные, мы составим' },
        obv_fullname:      { uz_lat: "F.I.Sh.",           uz_cyr: "Ф.И.Ш.",             en: 'Full Name',            ru: 'Ф.И.О.'               },
        obv_birth:         { uz_lat: "Tug'ilgan sana",   uz_cyr: "Туғилган сана",       en: 'Date of Birth',        ru: 'Дата рождения'        },
        obv_birthplace:    { uz_lat: "Tug'ilgan joyi",   uz_cyr: "Туғилган жойи",        en: 'Place of Birth',       ru: 'Место рождения'       },
        obv_nation:        { uz_lat: "Millati",           uz_cyr: "Миллати",             en: 'Nationality',          ru: 'Национальность'       },
        obv_party:         { uz_lat: "Partiyaviyligi",    uz_cyr: "Партиявийлиги",       en: 'Party membership',     ru: 'Партийность'          },
        obv_education:     { uz_lat: "Ma'lumoti",         uz_cyr: "Маълумоти",           en: 'Education',            ru: 'Образование'          },
        obv_graduated:     { uz_lat: "Tamomlagan joyi",  uz_cyr: "Тамомлаган жойи",     en: 'Graduated from',       ru: 'Окончил(а)'           },
        obv_specialty:     { uz_lat: "Mutaxassisligi",    uz_cyr: "Мутахассислиги",      en: 'Specialty',            ru: 'Специальность'        },
        obv_degree:        { uz_lat: "Ilmiy darajasi",   uz_cyr: "Илмий даражаси",      en: 'Academic degree',      ru: 'Учёная степень'       },
        obv_languages:     { uz_lat: "Chet tillari",     uz_cyr: "Чет тиллари",         en: 'Foreign languages',    ru: 'Иностранные языки'    },
        obv_awards:        { uz_lat: "Mukofotlari",      uz_cyr: "Мукофотлари",         en: 'Awards',               ru: 'Награды'              },
        obv_work:          { uz_lat: "Mehnat faoliyati", uz_cyr: "Меҳнат фаолияти",     en: 'Work experience',      ru: 'Трудовая деятельность'},
        obv_relatives:     { uz_lat: "Yaqin qarindoshlari", uz_cyr: "Яқин қариндошлари", en: 'Close relatives',     ru: 'Ближайшие родственники'},
        obv_add_work:      { uz_lat: "Ish joyi qo'shish", uz_cyr: "Иш жойи қўшиш",    en: 'Add workplace',        ru: 'Добавить место работы'},
        obv_add_rel:       { uz_lat: "Qarindosh qo'shish", uz_cyr: "Қариндош қўшиш",  en: 'Add relative',         ru: 'Добавить родственника'},
        obv_preview:       { uz_lat: "Oldindan ko'rish", uz_cyr: "Олдиндан кўриш",     en: 'Preview',              ru: 'Предпросмотр'         },
        obv_generate:      { uz_lat: "Hujjat yaratish",  uz_cyr: "Ҳужжат яратиш",      en: 'Generate document',    ru: 'Создать документ'     },

        // ════════════════════════════════════════════════
        // CV BUILDER
        // ════════════════════════════════════════════════
        cv_title:          { uz_lat: 'CV Builder',        uz_cyr: 'CV Builder',          en: 'CV Builder',           ru: 'Конструктор резюме'   },
        cv_sub:            { uz_lat: "Professional rezyume yarating", uz_cyr: "Professional резюме яратинг", en: 'Build a professional resume', ru: 'Создайте профессиональное резюме' },
        cv_template:       { uz_lat: "Shablon",           uz_cyr: "Шаблон",              en: 'Template',             ru: 'Шаблон'               },
        cv_tpl_minimal:    { uz_lat: "Minimal",           uz_cyr: "Минимал",             en: 'Minimal',              ru: 'Минимальный'          },
        cv_tpl_split:      { uz_lat: "Split",             uz_cyr: "Split",               en: 'Split',                ru: 'Разделённый'          },
        cv_tpl_modern:     { uz_lat: "Modern",            uz_cyr: "Замонавий",           en: 'Modern',               ru: 'Современный'          },
        cv_name:           { uz_lat: "Ism Familiya",      uz_cyr: "Исм Фамилия",         en: 'Full Name',            ru: 'Полное имя'           },
        cv_spec:           { uz_lat: "Mutaxassislik",     uz_cyr: "Мутахассислик",       en: 'Job title',            ru: 'Должность'            },
        cv_about:          { uz_lat: "O'zim haqimda",    uz_cyr: "Ўзим ҳақимда",        en: 'About me',             ru: 'О себе'               },
        cv_experience:     { uz_lat: "Ish tajribasi",     uz_cyr: "Иш тажрибаси",        en: 'Experience',           ru: 'Опыт работы'          },
        cv_education:      { uz_lat: "Ta'lim",            uz_cyr: "Таълим",              en: 'Education',            ru: 'Образование'          },
        cv_skills:         { uz_lat: "Ko'nikmalar",        uz_cyr: "Кўникмалар",          en: 'Skills',               ru: 'Навыки'               },
        cv_languages:      { uz_lat: "Tillar",             uz_cyr: "Тиллар",              en: 'Languages',            ru: 'Языки'                },
        cv_add_exp:        { uz_lat: "Tajriba qo'shish",  uz_cyr: "Тажриба қўшиш",      en: 'Add experience',       ru: 'Добавить опыт'        },
        cv_preview:        { uz_lat: "Ko'rish",            uz_cyr: "Кўриш",               en: 'Preview',              ru: 'Просмотр'             },

        // ════════════════════════════════════════════════
        // OCR PAGE
        // ════════════════════════════════════════════════
        ocr_title:         { uz_lat: "Rasm → Word AI",   uz_cyr: "Расм → Word AI",      en: 'Image → Word AI',      ru: 'Изображение → Word AI'},
        ocr_sub:           { uz_lat: "Rasmdan matnni ayirib Word hujjat yarating", uz_cyr: "Расмдан матнни айириб Word ҳужжат яратинг", en: 'Extract text from image into Word document', ru: 'Извлеките текст из изображения в Word' },
        ocr_drop:          { uz_lat: "Rasm tanlang yoki shu yerga tashlang", uz_cyr: "Расм танланг ёки шу ерга ташланг", en: 'Select image or drop here', ru: 'Выберите или перетащите изображение' },
        ocr_btn:           { uz_lat: "Word ga aylantirish", uz_cyr: "Word га айлантириш", en: 'Convert to Word',     ru: 'Конвертировать в Word'},
        ocr_processing:    { uz_lat: "AI matnni o'qimoqda...", uz_cyr: "AI матнни ўқимоқда...", en: 'AI is reading...', ru: 'ИИ читает...'     },
        ocr_success:       { uz_lat: "Word fayl tayyor!", uz_cyr: "Word файл тайёр!",   en: 'Word file ready!',     ru: 'Файл Word готов!'     },

        // ════════════════════════════════════════════════
        // IMAGE → PDF PAGE
        // ════════════════════════════════════════════════
        pdf_title:         { uz_lat: "Rasm → PDF",        uz_cyr: "Расм → PDF",          en: 'Image → PDF',          ru: 'Изображение → PDF'    },
        pdf_sub:           { uz_lat: "Bir nechta rasmni PDFga birlashtiring", uz_cyr: "Бир нечта расмни PDFга бирлаштиринг", en: 'Merge multiple images into PDF', ru: 'Объединить несколько изображений в PDF' },
        pdf_drop:          { uz_lat: "Rasmlarni tanlang",  uz_cyr: "Расмларни танланг",   en: 'Select images',        ru: 'Выберите изображения' },
        pdf_drop_sub:      { uz_lat: "Yoki bu yerga sudrab tashlang. Ko'pi bilan 20 ta rasm.", uz_cyr: "Ёки бу ерга судраб ташланг. Кўпи билан 20 та расм.", en: 'Or drag & drop here. Max 20 images.', ru: 'Или перетащите. Максимум 20 изображений.' },
        pdf_selected:      { uz_lat: "ta rasm tanlandi",  uz_cyr: "та расм танланди",    en: 'images selected',      ru: 'изображ. выбрано'     },
        pdf_add_more:      { uz_lat: "Rasm Qo'shish",     uz_cyr: "Расм Қўшиш",          en: 'Add Images',           ru: 'Добавить изображения' },
        pdf_btn:           { uz_lat: "PDF Yaratish",       uz_cyr: "PDF Яратиш",          en: 'Create PDF',           ru: 'Создать PDF'          },
        pdf_success:       { uz_lat: "PDF tayyor!",        uz_cyr: "PDF тайёр!",          en: 'PDF ready!',           ru: 'PDF готов!'           },

        // ════════════════════════════════════════════════
        // TRANSLATION PAGE
        // ════════════════════════════════════════════════
        tr_title:          { uz_lat: "Tarjima",            uz_cyr: "Таржима",             en: 'Translation',          ru: 'Перевод'              },
        tr_sub:            { uz_lat: "Sun'iy intellekt yordamida tarjima qiling", uz_cyr: "Сунъий интеллект ёрдамида таржима қилинг", en: 'Translate with AI assistance', ru: 'Переводите с помощью ИИ' },
        tr_from:           { uz_lat: "Manba tili",         uz_cyr: "Манба тили",          en: 'Source language',      ru: 'Исходный язык'        },
        tr_to:             { uz_lat: "Tarjima tili",       uz_cyr: "Таржима тили",        en: 'Target language',      ru: 'Язык перевода'        },
        tr_input_ph:       { uz_lat: "Tarjima qilinadigan matnni kiriting...", uz_cyr: "Таржима қилинадиган матнни киритинг...", en: 'Enter text to translate...', ru: 'Введите текст для перевода...' },
        tr_output_ph:      { uz_lat: "Tarjima bu yerda ko'rinadi...", uz_cyr: "Таржима бу ерда кўринади...", en: 'Translation appears here...', ru: 'Здесь появится перевод...' },
        tr_btn:            { uz_lat: "Tarjima qilish",     uz_cyr: "Таржима қилиш",       en: 'Translate',            ru: 'Перевести'            },
        tr_swap:           { uz_lat: "Almashtirish",       uz_cyr: "Алмаштириш",          en: 'Swap',                 ru: 'Поменять'             },
        tr_chars:          { uz_lat: "belgi",              uz_cyr: "белги",               en: 'chars',                ru: 'симв.'                },
        tr_error:          { uz_lat: "Tarjimada xatolik yuz berdi", uz_cyr: "Таржимада хатолик юз берди", en: 'Translation error occurred', ru: 'Ошибка при переводе' },
        tr_engine_ai:      { uz_lat: "AI Tarjima",         uz_cyr: "AI Таржима",          en: 'AI Translation',       ru: 'AI Перевод'           },
        tr_engine_google:  { uz_lat: "Google Tarjima",     uz_cyr: "Google Таржима",      en: 'Google Translate',     ru: 'Google Перевод'       },

        // ════════════════════════════════════════════════
        // TRANSLIT PAGE
        // ════════════════════════════════════════════════
        tl_title:          { uz_lat: "Krill ↔ Lotin",     uz_cyr: "Кирилл ↔ Лотин",     en: 'Cyrillic ↔ Latin',     ru: 'Кирилл ↔ Латин'       },
        tl_sub:            { uz_lat: "O'zbek matnini harf tizimlar orasida o'girish", uz_cyr: "Ўзбек матнини ҳарф тизимлар орасида ўгириш", en: 'Convert Uzbek text between alphabets', ru: 'Конвертировать узбекский текст' },
        tl_to_latin:       { uz_lat: "Kirillga → Lotinga", uz_cyr: "Кириллга → Лотинга", en: 'Cyrillic → Latin',     ru: 'Кирилл → Латиница'    },
        tl_to_cyrillic:    { uz_lat: "Lotinga → Kirillga", uz_cyr: "Лотинга → Кириллга", en: 'Latin → Cyrillic',     ru: 'Латиница → Кирилл'    },
        tl_input_ph:       { uz_lat: "Matn kiriting...",  uz_cyr: "Матн киритинг...",    en: 'Enter text...',        ru: 'Введите текст...'     },
        tl_output_ph:      { uz_lat: "Natija bu yerda ko'rinadi...", uz_cyr: "Натижа бу ерда кўринади...", en: 'Result appears here...', ru: 'Результат здесь...'   },
        tl_btn:            { uz_lat: "O'girish",           uz_cyr: "Ўгириш",              en: 'Convert',              ru: 'Конвертировать'       },

        // ════════════════════════════════════════════════
        // PREMIUM PAGE
        // ════════════════════════════════════════════════
        prem_title:        { uz_lat: "Premium Tarif",      uz_cyr: "Premium Тариф",       en: 'Premium Plan',         ru: 'Премиум тариф'        },
        prem_sub:          { uz_lat: "Chegaralarni kengaytiring", uz_cyr: "Чегараларни кенгайтиринг", en: 'Expand your limits', ru: 'Расширьте возможности' },
        prem_free:         { uz_lat: "Bepul",              uz_cyr: "Бепул",               en: 'Free',                 ru: 'Бесплатно'            },
        prem_monthly:      { uz_lat: "Premium Oylik",      uz_cyr: "Premium Ойлик",       en: 'Premium Monthly',      ru: 'Премиум Ежемесячный'  },
        prem_unlimited:    { uz_lat: "Cheksiz",            uz_cyr: "Чексиз",              en: 'Unlimited',            ru: 'Безлимитно'           },
        prem_docs:         { uz_lat: "hujjat/oy",          uz_cyr: "ҳужжат/ой",           en: 'docs/month',           ru: 'докум./мес.'          },
        prem_all_svc:      { uz_lat: "Barcha Pro xizmatlar", uz_cyr: "Барча Pro хизматлар", en: 'All Pro services',  ru: 'Все Pro услуги'       },
        prem_priority:     { uz_lat: "Ustuvor navbat",     uz_cyr: "Устувор навбат",       en: 'Priority queue',       ru: 'Приоритетная очередь' },
        prem_support:      { uz_lat: "yordam",             uz_cyr: "ёрдам",               en: 'support',              ru: 'поддержка'            },
        prem_btn_free:     { uz_lat: "Boshlash",           uz_cyr: "Бошлаш",              en: 'Start Free',           ru: 'Начать бесплатно'     },
        prem_btn_get:      { uz_lat: "Hozir olish",        uz_cyr: "Ҳозир олиш",          en: 'Get Now',              ru: 'Получить сейчас'      },
        prem_payment:      { uz_lat: "To'lov usullari",    uz_cyr: "Тўлов усуллари",       en: 'Payment methods',      ru: 'Способы оплаты'       },

        // ════════════════════════════════════════════════
        // LANGUAGE PICKER MODAL
        // ════════════════════════════════════════════════
        picker_title:      { uz_lat: "Tilni tanlang",      uz_cyr: "Тилни танланг",        en: 'Choose language',      ru: 'Выберите язык'        },
        picker_sub:        { uz_lat: "Siz istalgan vaqt sozlamalarda tilni o'zgartira olasiz", uz_cyr: "Сиз истаган вақт созламаларда тилни ўзгартира оласиз", en: 'You can change language anytime in settings', ru: 'Вы можете изменить язык в настройках' },
        picker_confirm:    { uz_lat: "Tasdiqlash",         uz_cyr: "Тасдиқлаш",           en: 'Confirm',              ru: 'Подтвердить'          },
    };

    // ─────────────────────────────────────────────────
    // State
    // ─────────────────────────────────────────────────
    const VALID_LANGS = ['uz_lat', 'uz_cyr', 'en', 'ru'];
    let _lang = localStorage.getItem(LS_KEY) || 'uz_lat';
    if (!VALID_LANGS.includes(_lang)) _lang = 'uz_lat';

    /** Translate a key in the current language. Falls back to uz_lat. */
    function t(key) {
        const entry = _dict[key];
        if (!entry) { console.warn(`[I18n] missing key: "${key}"`); return key; }
        return entry[_lang] ?? entry['uz_lat'] ?? key;
    }

    /** Change language, persist to localStorage, and re-apply to DOM. */
    function setLang(lang) {
        if (!VALID_LANGS.includes(lang)) {
            console.warn(`[I18n] unknown lang: ${lang}`); return;
        }
        _lang = lang;
        localStorage.setItem(LS_KEY, lang);
        apply();
        // Dispatch event so pages can react
        window.dispatchEvent(new CustomEvent('i18n:change', { detail: { lang } }));
    }

    /** Current language code. */
    function getLang() { return _lang; }

    /** All supported locales. */
    function getLangs() { return [...VALID_LANGS]; }

    /**
     * apply() — Scan the DOM for [data-i18n] and [data-i18n-ph] attributes
     * and replace textContent / placeholder with the current translation.
     *
     *  <span data-i18n="btn_generate"></span>
     *  <input data-i18n-ph="ph_text" />
     *  <button data-i18n="btn_generate" data-i18n-attr="title"></button>  ← sets title=
     */
    function apply(root = document) {
        root.querySelectorAll('[data-i18n]').forEach(el => {
            const key  = el.getAttribute('data-i18n');
            const attr = el.getAttribute('data-i18n-attr');
            const val  = t(key);
            if (attr) {
                el.setAttribute(attr, val);
            } else {
                // Preserve child elements (e.g. icons) — only update text nodes
                const textNode = [...el.childNodes].find(n => n.nodeType === Node.TEXT_NODE);
                if (textNode) {
                    textNode.nodeValue = val;
                } else {
                    el.textContent = val;
                }
            }
        });

        root.querySelectorAll('[data-i18n-ph]').forEach(el => {
            const key = el.getAttribute('data-i18n-ph');
            el.placeholder = t(key);
        });

        root.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = t(key);
        });

        // Update <html lang=""> attribute
        const langAttr = { uz_lat: 'uz', uz_cyr: 'uz', en: 'en', ru: 'ru' };
        document.documentElement.lang = langAttr[_lang] ?? 'uz';
    }

    // ─────────────────────────────────────────────────
    // Language Picker Modal
    // Injects a bottom-sheet modal if the user has never chosen a language.
    // ─────────────────────────────────────────────────
    function showPicker(force = false) {
        const alreadyChosen = localStorage.getItem(LS_KEY);
        if (alreadyChosen && !force) return;

        // Build modal HTML
        const modal = document.createElement('div');
        modal.id = 'i18n-picker';
        modal.style.cssText = `
            position:fixed;inset:0;z-index:9999;display:flex;align-items:flex-end;
            background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);
            animation:i18nFadeIn .25s ease;
        `;

        const langs = [
            { code: 'uz_lat', flag: '🇺🇿', label: "O'zbek (Lotin)" },
            { code: 'uz_cyr', flag: '🇺🇿', label: "Ўзбек (Кирилл)" },
            { code: 'en',     flag: '🇬🇧', label: 'English'         },
            { code: 'ru',     flag: '🇷🇺', label: 'Русский'          },
        ];

        modal.innerHTML = `
        <style>
          @keyframes i18nFadeIn{from{opacity:0}to{opacity:1}}
          @keyframes i18nSlideUp{from{transform:translateY(60px);opacity:0}to{transform:translateY(0);opacity:1}}
          #i18n-sheet{animation:i18nSlideUp .3s cubic-bezier(.16,1,.3,1)}
          .i18n-lang-btn{
            display:flex;align-items:center;gap:14px;width:100%;padding:16px 20px;
            background:none;border:none;cursor:pointer;border-radius:16px;
            font-size:15px;font-weight:600;font-family:inherit;transition:background .15s;
          }
          .dark .i18n-lang-btn{color:#f5f5f7}
          .i18n-lang-btn:hover{background:rgba(10,132,255,.1)}
          .i18n-lang-btn.selected{background:rgba(10,132,255,.15);color:#0A84FF}
          .i18n-confirm-btn{
            display:block;width:100%;padding:16px;background:#0A84FF;color:#fff;
            border:none;border-radius:20px;font-size:16px;font-weight:700;
            cursor:pointer;font-family:inherit;margin-top:8px;transition:filter .15s;
          }
          .i18n-confirm-btn:hover{filter:brightness(1.1)}
        </style>
        <div id="i18n-sheet" style="
            width:100%;max-width:480px;margin:0 auto;
            background:var(--i18n-bg,#fff);border-radius:32px 32px 0 0;
            padding:8px 20px 36px;box-shadow:0 -20px 60px rgba(0,0,0,.2);
        ">
          <div style="width:40px;height:4px;background:rgba(0,0,0,.15);border-radius:4px;margin:12px auto 20px"></div>
          <h2 style="font-size:22px;font-weight:800;margin-bottom:6px;text-align:center">${t('picker_title')}</h2>
          <p style="font-size:13px;color:#888;text-align:center;margin-bottom:20px">${t('picker_sub')}</p>
          <div id="i18n-lang-list">
            ${langs.map(l => `
              <button class="i18n-lang-btn ${l.code === _lang ? 'selected' : ''}"
                      data-lang="${l.code}" onclick="I18n._pickLang('${l.code}')">
                <span style="font-size:26px">${l.flag}</span>
                <span>${l.label}</span>
                ${l.code === _lang ? '<span style="margin-left:auto;color:#0A84FF;font-size:18px">✓</span>' : ''}
              </button>
            `).join('')}
          </div>
          <button class="i18n-confirm-btn" onclick="I18n._confirmPick()">${t('picker_confirm')}</button>
        </div>
        `;

        // Dark mode support for the sheet
        const isDark = document.documentElement.classList.contains('dark');
        modal.querySelector('#i18n-sheet').style.background = isDark ? '#151518' : '#fff';
        modal.querySelectorAll('.i18n-lang-btn').forEach(b => {
            b.style.color = isDark ? '#f5f5f7' : '#1d1d1f';
        });

        modal.addEventListener('click', e => { if (e.target === modal) _confirmPick(); });
        document.body.appendChild(modal);
    }

    // Called from picker buttons
    function _pickLang(code) {
        _lang = code;
        // Refresh button states
        document.querySelectorAll('.i18n-lang-btn').forEach(b => {
            const isSelected = b.dataset.lang === code;
            b.classList.toggle('selected', isSelected);
            b.innerHTML = b.innerHTML.replace(/<span[^>]*>✓<\/span>/g, '');
            if (isSelected) b.innerHTML += '<span style="margin-left:auto;color:#0A84FF;font-size:18px">✓</span>';
        });
    }

    function _confirmPick() {
        setLang(_lang);
        document.getElementById('i18n-picker')?.remove();
    }

    // ─────────────────────────────────────────────────
    // Public surface
    // ─────────────────────────────────────────────────
    return { t, setLang, getLang, getLangs, apply, showPicker, _pickLang, _confirmPick };
})();

// Auto-apply on load (runs immediately when script is parsed)
document.addEventListener('DOMContentLoaded', () => I18n.apply());
