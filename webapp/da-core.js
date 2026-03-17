/* ═══════════════════════════════════════════════
   DASTYOR AI — da-core.js
   Barcha sahifalar uchun umumiy til & mavzu boshqaruvi
   Include: <script src="da-core.js"></script>
═══════════════════════════════════════════════ */

window.DA = (() => {

  /* ── Keys ── */
  const KEY_LANG  = 'language';
  const KEY_THEME = 'theme';
  const LEGACY_KEY_LANG = 'da_lang';
  const LEGACY_KEY_THEME = 'da_theme';

  /* ── Translations ── */
  const LANGS = {
    uz: {
      greeting:        "Xush kelibsiz,",
      activity:        "Aktivlik",
      requests:        "so'rovlar",
      trend:           "+12% bu hafta",
      apps:            "Ilovalar",
      app1t:           "Obyektivka AI",  app1d: "Rasmiy ma'lumotnoma tuzish",
      app2t:           "CV Builder",     app2d: "Zamonaviy rezyume tuzish",
      app3t:           "Tarjimon AI",    app3d: "Smart tarjima va tahlil",
      app4t:           "AI Tools",       app4d: "Tarjima, OCR va boshqa vositalar",
      settingsTitle:   "Sozlamalar",     settingsSub: "Ilovani o'zingizga moslashtiring",
      sectionAppear:   "Ko'rinish",      sectionSupport: "Yordam",   sectionAbout: "Ilova haqida",
      theme:           "Mavzu",          themeLight: "Yorug'",        themeDark: "Tungi",
      lang:            "Til",            langName: "O'zbekcha",
      support:         "Qo'llab-quvvatlash", supportSub: "Bot orqali xabar yuboring",
      contact:         "Aloqa",          version: "Versiya 1.0.0",
      tabHome:         "Bosh sahifa",    tabSettings: "Sozlamalar",
      toastSent:       "Xabar yuborildi ✓", toastErr: "Xatolik yuz berdi",
      promptMsg:       "Xabaringizni yozing:",
      /* more.html */
      servicesTitle:   "Xizmatlar",      servicesSub: "Barcha vositalar",
      secTextLang:     "Til va Matn",    secFiles: "Fayl vositalari",
      svc1t: "Tarjima AI",       svc1d: "Matn va hujjatlarni tarjima qilish",
      svc2t: "Krill / Lotin",    svc2d: "O'zbek alifbosini o'girish",
      svc3t: "Rasm → Word",      svc3d: "Rasmdan matnni Word ga aylantirish",
      svc4t: "Rasm → PDF",       svc4d: "Rasmlarni PDF ga birlashtirish",
      tabMore: "Xizmatlar",
      translate_input_placeholder: "Matnni bu yerga kiriting...",
      translate_output_placeholder: "Tarjima shu yerda chiqadi...",
      translate_action: "⚡ Tarjima qilish",
      translate_wait: "Kuting...",
      translate_loading_engine: "Yuklanmoqda...",
      translate_enter_text: "Matn kiriting!",
      translate_max_chars: "Max 5000 belgi.",
      translate_swap_langs: "Tillarni almashtiring.",
      translate_done: "Tarjima qilindi",
      quick_phrases: "Tezkor iboralar",
      translit_title: "Krill / Lotin",
      translit_input_placeholder: "Matnni bu yerga kiriting...",
      translit_output_placeholder: "Natija shu yerda chiqadi...",
      translit_action: "⚡ O'girish",
      translit_keyboard: "Klaviatura",
      translit_samples: "Namunalar",
      ocr_title: "Rasm → Word",
      ocr_ai_scanner: "AI skayner",
      ocr_ai_sub: "Rasmlar Word faylga aylantiriladi va bot orqali yuboriladi",
      ocr_upload_title: "Rasmlarni yuklang",
      ocr_upload_sub: "Yoki bu yerga bosing / sudrab tashlang",
      ocr_clear: "Tozalash",
      ocr_btn_convert: "Word faylga aylantirish",
      img2pdf_title: "Rasm → PDF",
      img2pdf_label_title: "PDF generatsiya",
      img2pdf_label_sub: "Natijalar qurilmangizga yuklanadi hamda bot orqali PDF holida jo'natiladi.",
      img2pdf_upload_title: "Rasmlarni tanlang",
      img2pdf_upload_sub: "Yoki bu yerga sudrab tashlang. Ko'pi bilan 20 ta rasm.",
      img2pdf_clear: "Tozalash",
      img2pdf_generated: "PDF yaratildi!",
      img2pdf_btn_create: "⚡ PDF yaratish",
      img2pdf_new: "🔄 Yangi PDF yaratish",
      spellcheck_title: "Imlo tekshirish",
      spellcheck_subtitle: "AI yordamida hujjatingizdagi imlo xatolarini aniqlang va tuzating",
      back_home: "← Bosh sahifa",
      spellcheck_send_tg: "Telegram orqali jo'natish",
      spellcheck_send_tg_sub: "Hujjatni to'g'ridan-to'g'ri botga yuborish",
      spellcheck_btn: "Telegram botda tekshirish",
      telegram_only_alert: "Faqat Telegram bot orqali ishlaydi!",
      prem_title: "Premium tarif",
      prem_sub: "Chegaralarni kengaytiring",
      prem_free: "Bepul",
      prem_docs: "hujjat/oy",
      prem_pro: "Pro xizmatlar",
      prem_fast: "Tezkor aloqa",
      prem_btn_free: "Boshlash",
      prem_pop: "TOP",
      prem_monthly: "Premium oylik",
      prem_unlimited: "Cheksiz",
      prem_docs2: "hujjatlar",
      prem_all_svc: "Barcha Pro xizmatlar",
      prem_priority: "Ustuvor navbat",
      prem_support: "yordam",
      prem_btn_get: "Hozir olish",
      prem_payment: "To'lov usullari",
      cv_btn_preview: "Ko'rish",
      cv_tpl_title: "Dizayn shablon",
      cv_upload_img: "Rasm yuklash",
      cv_rec_img: "Professional tasvir tavsiya etiladi",
      cv_experience: "Ish tajribasi",
      cv_add_exp: "+ Tajriba qo'shish",
      cv_education: "Ta'lim",
      cv_add_edu: "+ Ta'lim qo'shish",
      cv_skills: "Ko'nikmalar",
      ph_cv_name: "Ism Familiya (Masalan: Alisherov M.)",
      ph_cv_role: "Kasb (Masalan: UI/UX Designer)",
      ph_cv_phone: "Telefon (+998...)",
      ph_email: "Email",
      ph_cv_loc: "Manzil (Masalan: Toshkent Shahri)",
      ph_cv_about: "Haqingizda qisqacha ma'lumot (Summary)",
      ph_skill: "Ko'nikma yozib ENTER bosing...",
      obyektivka_form_title: "Ma'lumotnoma tayyorlash xizmati",
      nav_tools: "Asboblar",
      nav_translator: "Tarjimon",
      nav_settings: "Sozlamalar",
      language_changed_success: "Til muvaffaqiyatli o'zgartirildi",
      settings_language: "Til",
      objective_title: "Obyektivka Generator",
      objective_subtitle: "Kasb va tajribangizga mos obyektivka yarating",
      objective_role_label: "Kasbingizni kiriting",
      objective_role_placeholder: "Masalan: UI/UX Designer",
      objective_exp_label: "Tajriba darajasi",
      objective_exp_junior: "Boshlang'ich",
      objective_exp_middle: "O'rta",
      objective_exp_senior: "Katta mutaxassis",
      objective_exp_lead: "Rahbar",
      objective_extra_label: "Qo'shimcha ma'lumot",
      objective_extra_placeholder: "Qisqa yo'nalish yoki maqsad yozing",
      objective_generate: "Obyektivka yaratish",
      objective_result: "Natija",
      objective_copy: "Nusxa olish",
      objective_copied: "Matn nusxalandi",
      objective_error_role: "Kasbni kiriting",
      objective_back: "Bosh sahifa",
      objective_working: "AI ishlamoqda...",
      objective_ready: "Tayyor",
      copy_error: "Nusxalashda xatolik",
    },
    ru: {
      greeting:        "Добро пожаловать,",
      activity:        "Активность",
      requests:        "запросов",
      trend:           "+12% за неделю",
      apps:            "Приложения",
      app1t:           "Obyektivka AI",  app1d: "Создание официальных справок",
      app2t:           "CV Builder",     app2d: "Современное резюме",
      app3t:           "Переводчик AI",  app3d: "Умный перевод и анализ",
      app4t:           "AI Tools",       app4d: "Перевод, OCR и другие инструменты",
      settingsTitle:   "Настройки",      settingsSub: "Настройте приложение под себя",
      sectionAppear:   "Внешний вид",    sectionSupport: "Поддержка",   sectionAbout: "О приложении",
      theme:           "Тема",           themeLight: "Светлая",          themeDark: "Тёмная",
      lang:            "Язык",           langName: "Русский",
      support:         "Служба поддержки", supportSub: "Отправьте сообщение через бот",
      contact:         "Написать",       version: "Версия 1.0.0",
      tabHome:         "Главная",        tabSettings: "Настройки",
      toastSent:       "Сообщение отправлено ✓", toastErr: "Произошла ошибка",
      promptMsg:       "Напишите ваше сообщение:",
      servicesTitle:   "Услуги",         servicesSub: "Все инструменты",
      secTextLang:     "Текст и язык",   secFiles: "Файловые инструменты",
      svc1t: "Переводчик AI",    svc1d: "Перевод текстов и документов",
      svc2t: "Кирилл / Латин",   svc2d: "Конвертация узбекского алфавита",
      svc3t: "Фото → Word",      svc3d: "Извлечение текста из изображений",
      svc4t: "Фото → PDF",       svc4d: "Объединение изображений в PDF",
      tabMore: "Услуги",
      translate_input_placeholder: "Введите текст здесь...",
      translate_output_placeholder: "Перевод появится здесь...",
      translate_action: "⚡ Перевести",
      translate_wait: "Подождите...",
      translate_loading_engine: "Загрузка...",
      translate_enter_text: "Введите текст!",
      translate_max_chars: "Макс. 5000 символов.",
      translate_swap_langs: "Поменяйте языки местами.",
      translate_done: "Переведено",
      quick_phrases: "Быстрые фразы",
      translit_title: "Кирилл / Латиница",
      translit_input_placeholder: "Введите текст здесь...",
      translit_output_placeholder: "Результат появится здесь...",
      translit_action: "⚡ Конвертировать",
      translit_keyboard: "Клавиатура",
      translit_samples: "Примеры",
      ocr_title: "Фото → Word",
      ocr_ai_scanner: "AI сканер",
      ocr_ai_sub: "Изображения конвертируются в Word и отправляются через бот",
      ocr_upload_title: "Загрузите изображения",
      ocr_upload_sub: "Или нажмите / перетащите сюда",
      ocr_clear: "Очистить",
      ocr_btn_convert: "Конвертировать в Word",
      img2pdf_title: "Фото → PDF",
      img2pdf_label_title: "Генерация PDF",
      img2pdf_label_sub: "Результаты сохраняются на устройстве и отправляются через бота.",
      img2pdf_upload_title: "Выберите изображения",
      img2pdf_upload_sub: "Или перетащите сюда. До 20 изображений.",
      img2pdf_clear: "Очистить",
      img2pdf_generated: "PDF готов!",
      img2pdf_btn_create: "⚡ Создать PDF",
      img2pdf_new: "🔄 Создать новый PDF",
      spellcheck_title: "Проверка орфографии",
      spellcheck_subtitle: "ИИ найдет и исправит орфографические ошибки в документе",
      back_home: "← Главная",
      spellcheck_send_tg: "Отправить через Telegram",
      spellcheck_send_tg_sub: "Отправить документ напрямую боту",
      spellcheck_btn: "Проверить в Telegram-боте",
      telegram_only_alert: "Работает только через Telegram-бота!",
      prem_title: "Премиум тариф",
      prem_sub: "Расширьте возможности",
      prem_free: "Бесплатно",
      prem_docs: "док/мес",
      prem_pro: "Pro сервисы",
      prem_fast: "Быстрая связь",
      prem_btn_free: "Начать",
      prem_pop: "TOP",
      prem_monthly: "Премиум на месяц",
      prem_unlimited: "Безлимит",
      prem_docs2: "документов",
      prem_all_svc: "Все Pro сервисы",
      prem_priority: "Приоритетная очередь",
      prem_support: "поддержка",
      prem_btn_get: "Получить сейчас",
      prem_payment: "Способы оплаты",
      cv_btn_preview: "Просмотр",
      cv_tpl_title: "Шаблон дизайна",
      cv_upload_img: "Загрузить фото",
      cv_rec_img: "Рекомендуется профессиональное фото",
      cv_experience: "Опыт работы",
      cv_add_exp: "+ Добавить опыт",
      cv_education: "Образование",
      cv_add_edu: "+ Добавить образование",
      cv_skills: "Навыки",
      ph_cv_name: "Имя Фамилия (например: Ivanov I.)",
      ph_cv_role: "Профессия (например: UI/UX Designer)",
      ph_cv_phone: "Телефон (+998...)",
      ph_email: "Email",
      ph_cv_loc: "Адрес (например: Ташкент)",
      ph_cv_about: "Кратко о себе (Summary)",
      ph_skill: "Введите навык и нажмите ENTER...",
      obyektivka_form_title: "Сервис подготовки справки",
      nav_tools: "Инструменты",
      nav_translator: "Переводчик",
      nav_settings: "Настройки",
      language_changed_success: "Язык успешно изменён",
      settings_language: "Язык",
      objective_title: "Генератор цели",
      objective_subtitle: "Создайте цель под вашу должность и опыт",
      objective_role_label: "Укажите профессию",
      objective_role_placeholder: "Например: UI/UX Designer",
      objective_exp_label: "Уровень опыта",
      objective_exp_junior: "Начальный",
      objective_exp_middle: "Средний",
      objective_exp_senior: "Старший специалист",
      objective_exp_lead: "Руководитель",
      objective_extra_label: "Дополнительная информация",
      objective_extra_placeholder: "Кратко опишите направление или цель",
      objective_generate: "Создать цель",
      objective_result: "Результат",
      objective_copy: "Копировать",
      objective_copied: "Текст скопирован",
      objective_error_role: "Введите профессию",
      objective_back: "Главная",
      objective_working: "ИИ работает...",
      objective_ready: "Готово",
      copy_error: "Ошибка при копировании",
    },
    en: {
      greeting:        "Welcome,",
      activity:        "Activity",
      requests:        "requests",
      trend:           "+12% this week",
      apps:            "Applications",
      app1t:           "Obyektivka AI",  app1d: "Official document generation",
      app2t:           "CV Builder",     app2d: "Modern resume builder",
      app3t:           "Translator AI",  app3d: "Smart translation & analysis",
      app4t:           "AI Tools",       app4d: "Translation, OCR & more",
      settingsTitle:   "Settings",       settingsSub: "Customize the app to your liking",
      sectionAppear:   "Appearance",     sectionSupport: "Support",   sectionAbout: "About",
      theme:           "Theme",          themeLight: "Light",          themeDark: "Dark",
      lang:            "Language",       langName: "English",
      support:         "Help & Support", supportSub: "Send a message via bot",
      contact:         "Contact",        version: "Version 1.0.0",
      tabHome:         "Home",           tabSettings: "Settings",
      toastSent:       "Message sent ✓", toastErr: "Something went wrong",
      promptMsg:       "Write your message:",
      servicesTitle:   "Services",       servicesSub: "All tools",
      secTextLang:     "Text & Language",secFiles: "File Tools",
      svc1t: "Translator AI",    svc1d: "Translate texts & documents",
      svc2t: "Cyrillic / Latin", svc2d: "Convert Uzbek script",
      svc3t: "Image → Word",     svc3d: "Extract text from images",
      svc4t: "Image → PDF",      svc4d: "Combine images into PDF",
      tabMore: "Services",
      translate_input_placeholder: "Enter text here...",
      translate_output_placeholder: "Translation will appear here...",
      translate_action: "⚡ Translate",
      translate_wait: "Please wait...",
      translate_loading_engine: "Loading...",
      translate_enter_text: "Enter text!",
      translate_max_chars: "Max 5000 characters.",
      translate_swap_langs: "Swap the languages.",
      translate_done: "Translated",
      quick_phrases: "Quick phrases",
      translit_title: "Cyrillic / Latin",
      translit_input_placeholder: "Enter text here...",
      translit_output_placeholder: "Result will appear here...",
      translit_action: "⚡ Convert",
      translit_keyboard: "Keyboard",
      translit_samples: "Samples",
      ocr_title: "Image → Word",
      ocr_ai_scanner: "AI scanner",
      ocr_ai_sub: "Images are converted to Word and sent via bot",
      ocr_upload_title: "Upload images",
      ocr_upload_sub: "Or click / drag and drop here",
      ocr_clear: "Clear",
      ocr_btn_convert: "Convert to Word",
      img2pdf_title: "Image → PDF",
      img2pdf_label_title: "PDF generation",
      img2pdf_label_sub: "Results are saved on your device and sent via bot.",
      img2pdf_upload_title: "Select images",
      img2pdf_upload_sub: "Or drag and drop here. Up to 20 images.",
      img2pdf_clear: "Clear",
      img2pdf_generated: "PDF created!",
      img2pdf_btn_create: "⚡ Create PDF",
      img2pdf_new: "🔄 Create new PDF",
      spellcheck_title: "Spell checker",
      spellcheck_subtitle: "AI finds and fixes spelling errors in your document",
      back_home: "← Home",
      spellcheck_send_tg: "Send via Telegram",
      spellcheck_send_tg_sub: "Send document directly to the bot",
      spellcheck_btn: "Check in Telegram bot",
      telegram_only_alert: "Works only via Telegram bot!",
      prem_title: "Premium plan",
      prem_sub: "Unlock more limits",
      prem_free: "Free",
      prem_docs: "docs/month",
      prem_pro: "Pro services",
      prem_fast: "Fast support",
      prem_btn_free: "Start",
      prem_pop: "TOP",
      prem_monthly: "Premium monthly",
      prem_unlimited: "Unlimited",
      prem_docs2: "documents",
      prem_all_svc: "All Pro services",
      prem_priority: "Priority queue",
      prem_support: "support",
      prem_btn_get: "Get now",
      prem_payment: "Payment methods",
      cv_btn_preview: "Preview",
      cv_tpl_title: "Design template",
      cv_upload_img: "Upload image",
      cv_rec_img: "A professional image is recommended",
      cv_experience: "Work experience",
      cv_add_exp: "+ Add experience",
      cv_education: "Education",
      cv_add_edu: "+ Add education",
      cv_skills: "Skills",
      ph_cv_name: "Full name (e.g. John D.)",
      ph_cv_role: "Role (e.g. UI/UX Designer)",
      ph_cv_phone: "Phone (+998...)",
      ph_email: "Email",
      ph_cv_loc: "Location (e.g. Tashkent)",
      ph_cv_about: "Short about you (Summary)",
      ph_skill: "Type a skill and press ENTER...",
      obyektivka_form_title: "Certificate builder service",
      nav_tools: "Tools",
      nav_translator: "Translator",
      nav_settings: "Settings",
      language_changed_success: "Language changed successfully",
      settings_language: "Language",
      objective_title: "Objective Generator",
      objective_subtitle: "Generate a focused objective for your role",
      objective_role_label: "Enter your role",
      objective_role_placeholder: "Example: UI/UX Designer",
      objective_exp_label: "Experience level",
      objective_exp_junior: "Junior",
      objective_exp_middle: "Mid-level",
      objective_exp_senior: "Senior",
      objective_exp_lead: "Lead",
      objective_extra_label: "Additional details",
      objective_extra_placeholder: "Add a short focus or goal",
      objective_generate: "Generate Objective",
      objective_result: "Result",
      objective_copy: "Copy",
      objective_copied: "Text copied",
      objective_error_role: "Enter your role",
      objective_back: "Home",
      objective_working: "AI is working...",
      objective_ready: "Ready",
      copy_error: "Copy failed",
    }
  };

  /* ── State ── */
  function normalizeLang(v) {
    const s = String(v || "").toLowerCase();
    return s === "ru" || s === "en" ? s : "uz";
  }

  function normalizeTheme(v) {
    return String(v || "").toLowerCase() === "dark" ? "dark" : "light";
  }

  function readKey(primary, legacy, fallback) {
    return localStorage.getItem(primary) || localStorage.getItem(legacy) || fallback;
  }

  function persistLang(v) {
    localStorage.setItem(KEY_LANG, v);
    localStorage.setItem(LEGACY_KEY_LANG, v);
  }

  function persistTheme(v) {
    localStorage.setItem(KEY_THEME, v);
    localStorage.setItem(LEGACY_KEY_THEME, v);
  }

  let lang = normalizeLang(readKey(KEY_LANG, LEGACY_KEY_LANG, "uz"));
  let theme = normalizeTheme(readKey(KEY_THEME, LEGACY_KEY_THEME, "light"));

  /* ── Internal helpers ── */
  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function _applyThemeDom(t) {
    const root = document.documentElement;
    root.setAttribute('data-theme', t);
    root.classList.toggle("dark", t === "dark");
    root.classList.toggle("light", t === "light");
  }

  function _applyLangDom(l) {
    document.documentElement.lang = l;
    const t = LANGS[l] || LANGS.uz;
    // iterate all [data-i18n] elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (t[key] !== undefined) el.textContent = t[key];
    });
    // data-i18n-attr: e.g. placeholder
    document.querySelectorAll('[data-i18n-attr]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const attr = el.getAttribute('data-i18n-attr');
      if (key && attr && t[key] !== undefined) el.setAttribute(attr, t[key]);
    });
    // fire events so pages can do extra updates
    window.dispatchEvent(new CustomEvent('da:lang', { detail: { lang: l, t } }));
    window.dispatchEvent(new CustomEvent('app:language-changed', { detail: { language: l } }));
    window.dispatchEvent(new CustomEvent('app:language-applied', { detail: { language: l } }));
    refreshMobileNavLabels();
  }

  /* ── Public API ── */
  function getTheme() { return theme; }
  function getLang()  { return lang;  }
  function t(key)     { return (LANGS[lang] || LANGS.uz)[key] || key; }

  function setTheme(val) {
    theme = normalizeTheme(val);
    persistTheme(theme);
    _applyThemeDom(theme);
    window.dispatchEvent(new CustomEvent('da:theme', { detail: { theme } }));
    window.dispatchEvent(new CustomEvent('app:theme-changed', { detail: { theme } }));
  }

  function setLang(val) {
    lang = normalizeLang(val);
    persistLang(lang);
    _applyLangDom(lang);
  }

  /* ── Auto-init on DOMContentLoaded ── */
  function init() {
    persistTheme(theme);
    persistLang(lang);
    _applyThemeDom(theme);
    _applyLangDom(lang);
    setTimeout(enhanceMobileUI, 0);
  }

  function iconSvg(name) {
    const common = 'fill="none" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
    if (name === 'home') return `<svg ${common}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 10v10h14V10"/></svg>`;
    if (name === 'tools') return `<svg ${common}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`;
    if (name === 'translate') return `<svg ${common}><path d="M5 8h10"/><path d="M10 5v3c0 4-2.5 6.5-5 8"/><path d="M10 13l3 6 3-6"/><path d="M16 13h4"/></svg>`;
    if (name === 'settings') return `<svg ${common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5h.1a1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/></svg>`;
    return '';
  }

  function activeNavKey(path) {
    if (path.endsWith('/index.html') || path === '/' || path.endsWith('/')) return 'home';
    if (path.endsWith('/more.html')) return 'tools';
    if (path.endsWith('/translate.html')) return 'translate';
    return 'settings';
  }

  function enhanceMobileUI() {
    const body = document.body;
    if (!body || body.dataset.disableMobileNav === 'true') return;
    body.classList.add('da-mobile-shell');

    if (document.querySelector('.da-bottom-nav') || document.querySelector('.bottom-nav')) return;

    const path = location.pathname.toLowerCase();
    const active = activeNavKey(path);
    const nav = document.createElement('nav');
    nav.className = 'da-bottom-nav';
    nav.innerHTML = `
      <a class="da-nav-item ${active === 'home' ? 'active' : ''}" href="index.html">
        ${iconSvg('home')}
        <span>${t('tabHome')}</span>
      </a>
      <a class="da-nav-item ${active === 'tools' ? 'active' : ''}" href="more.html">
        ${iconSvg('tools')}
        <span>${t('nav_tools')}</span>
      </a>
      <a class="da-nav-item ${active === 'translate' ? 'active' : ''}" href="translate.html">
        ${iconSvg('translate')}
        <span>${t('nav_translator')}</span>
      </a>
      <a class="da-nav-item ${active === 'settings' ? 'active' : ''}" href="index.html?open=settings">
        ${iconSvg('settings')}
        <span>${t('nav_settings')}</span>
      </a>
    `;
    body.appendChild(nav);
  }

  function refreshMobileNavLabels() {
    const nav = document.querySelector('.da-bottom-nav');
    if (!nav) return;
    const labels = nav.querySelectorAll('span');
    if (labels[0]) labels[0].textContent = t('tabHome');
    if (labels[1]) labels[1].textContent = t('nav_tools');
    if (labels[2]) labels[2].textContent = t('nav_translator');
    if (labels[3]) labels[3].textContent = t('nav_settings');
  }

  window.addEventListener("storage", (e) => {
    if (e.key === KEY_THEME || e.key === LEGACY_KEY_THEME) {
      const next = normalizeTheme(readKey(KEY_THEME, LEGACY_KEY_THEME, "light"));
      if (next !== theme) {
        theme = next;
        _applyThemeDom(theme);
        window.dispatchEvent(new CustomEvent('da:theme', { detail: { theme } }));
        window.dispatchEvent(new CustomEvent('app:theme-changed', { detail: { theme } }));
      }
    }
    if (e.key === KEY_LANG || e.key === LEGACY_KEY_LANG) {
      const next = normalizeLang(readKey(KEY_LANG, LEGACY_KEY_LANG, "uz"));
      if (next !== lang) {
        lang = next;
        _applyLangDom(lang);
      }
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return { getTheme, getLang, setTheme, setLang, t, iconSvg };
})();
