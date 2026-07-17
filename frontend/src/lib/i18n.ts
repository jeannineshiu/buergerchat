// UI strings for all supported answer languages. Official German terms
// (Bürgergeld, Kindergeld …) stay in German everywhere — users need to
// recognize them at the Amt; see backend/rag.py SYSTEM_PROMPT for the same
// rule on the answer side.

export interface StarterPrompt {
  topic: string;
  label: string;
  prompt: string;
}

export interface UIStrings {
  tagline: string;
  welcomeTitle: string;
  welcomeSubtitle: string;
  inputPlaceholder: string;
  send: string;
  typing: string;
  errorMessage: string;
  disclaimer: string;
  sources: string;
  buergergeldNotice: string;
  feedbackThanks: string;
  feedbackGood: string;
  feedbackBad: string;
  feedbackPlaceholder: string;
  feedbackSend: string;
  sessionQuestion: string;
  sessionPlaceholder: string;
  skip: string;
  submit: string;
  stars: string; // aria: "<n> {stars}"
  newChat: string;
  starters: StarterPrompt[];
}

export const RTL_LANGUAGES = new Set(["ar", "fa"]);

const de: UIStrings = {
  tagline: "Behördendeutsch in einfache Sprache — mit Quellenangabe",
  welcomeTitle: "Womit können wir helfen?",
  welcomeSubtitle:
    "Einfache Antworten mit offiziellen Quellen zu: Bürgergeld, Kindergeld & Familienleistungen, Rente, Wohngeld, Steuer-ID, Aufenthalt & Einbürgerung. Wir finden auch Ihre zuständige Behörde — nennen Sie dafür Ihre Postleitzahl.",
  inputPlaceholder: "Stellen Sie Ihre Frage …",
  send: "Senden",
  typing: "Antwort wird erstellt",
  errorMessage: "Die Anfrage ist fehlgeschlagen. Bitte versuchen Sie es erneut.",
  disclaimer: "BürgerChat erklärt amtliche Informationen, ersetzt aber keine Rechtsberatung.",
  sources: "Quellen",
  buergergeldNotice:
    "Seit dem 1. Juli 2026 heißt „Bürgergeld“ offiziell „Grundsicherungsgeld“ (Neue Grundsicherung). Es handelt sich um dieselbe Leistung.",
  feedbackThanks: "Danke für Ihr Feedback",
  feedbackGood: "Gute Antwort",
  feedbackBad: "Schlechte Antwort",
  feedbackPlaceholder: "Was war falsch? (optional)",
  feedbackSend: "Senden",
  sessionQuestion: "Wie hilfreich war dieses Gespräch?",
  sessionPlaceholder: "Möchten Sie uns mehr sagen? (optional)",
  skip: "Überspringen",
  submit: "Absenden",
  stars: "Sterne",
  newChat: "Neues Gespräch",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / Grundsicherung",
      prompt: "Habe ich Anspruch auf Bürgergeld (Grundsicherung) und wie beantrage ich es?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld",
      prompt: "Wer bekommt Kindergeld und wie beantrage ich es?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld & Familie",
      prompt: "Wie beantrage ich Elterngeld nach der Geburt meines Kindes?",
    },
    {
      topic: "rente",
      label: "Rente",
      prompt: "Wann kann ich in Rente gehen und wie stelle ich den Antrag?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld",
      prompt: "Habe ich Anspruch auf Wohngeld und wie beantrage ich es?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID",
      prompt: "Wie bekomme ich meine Steuer-Identifikationsnummer?",
    },
    {
      topic: "aufenthalt",
      label: "Aufenthalt & Einbürgerung",
      prompt: "Welche Voraussetzungen gelten für die deutsche Einbürgerung?",
    },
  ],
};

const en: UIStrings = {
  tagline: "German bureaucracy in plain language — with official sources",
  welcomeTitle: "How can we help?",
  welcomeSubtitle:
    "Simple answers with official sources about: Bürgergeld (basic income support), Kindergeld (child benefit) & family benefits, Rente (pension), Wohngeld (housing benefit), Steuer-ID (tax ID), residence & citizenship. We can also find your responsible authority — just include your postal code.",
  inputPlaceholder: "Ask your question …",
  send: "Send",
  typing: "Writing an answer",
  errorMessage: "The request failed. Please try again.",
  disclaimer: "BürgerChat explains official information; it is not legal advice.",
  sources: "Sources",
  buergergeldNotice:
    "Since 1 July 2026, “Bürgergeld” is officially called “Grundsicherungsgeld” (Neue Grundsicherung). It is the same benefit.",
  feedbackThanks: "Thanks for your feedback",
  feedbackGood: "Good answer",
  feedbackBad: "Bad answer",
  feedbackPlaceholder: "What was wrong? (optional)",
  feedbackSend: "Send",
  sessionQuestion: "How helpful was this conversation?",
  sessionPlaceholder: "Want to tell us more? (optional)",
  skip: "Skip",
  submit: "Submit",
  stars: "stars",
  newChat: "New chat",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (basic income support)",
      prompt: "Am I entitled to Bürgergeld (basic income support) and how do I apply?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (child benefit)",
      prompt: "Who gets Kindergeld and how do I apply for it?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (parental allowance) & family",
      prompt: "How do I apply for Elterngeld (parental allowance) after my child is born?",
    },
    {
      topic: "rente",
      label: "Rente (pension)",
      prompt: "When can I retire and how do I apply for my Rente (pension)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (housing benefit)",
      prompt: "Am I entitled to Wohngeld (housing benefit) and how do I apply?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (tax ID)",
      prompt: "How do I get my Steuer-Identifikationsnummer (tax ID)?",
    },
    {
      topic: "aufenthalt",
      label: "Residence & citizenship",
      prompt: "What are the requirements for German citizenship?",
    },
  ],
};

const tr: UIStrings = {
  tagline: "Alman resmi dili, sade bir dille — resmi kaynaklarla",
  welcomeTitle: "Size nasıl yardımcı olabiliriz?",
  welcomeSubtitle:
    "Şu konularda resmi kaynaklı, sade yanıtlar: Bürgergeld (temel güvence), Kindergeld (çocuk parası) ve aile yardımları, Rente (emeklilik), Wohngeld (kira yardımı), Steuer-ID (vergi kimlik numarası), oturum ve vatandaşlık. Posta kodunuzu yazarsanız yetkili daireyi de buluruz.",
  inputPlaceholder: "Sorunuzu yazın …",
  send: "Gönder",
  typing: "Yanıt hazırlanıyor",
  errorMessage: "İstek başarısız oldu. Lütfen tekrar deneyin.",
  disclaimer: "BürgerChat resmi bilgileri açıklar; hukuki danışmanlık yerine geçmez.",
  sources: "Kaynaklar",
  buergergeldNotice:
    "1 Temmuz 2026'dan beri „Bürgergeld“ resmi olarak „Grundsicherungsgeld“ (Neue Grundsicherung) olarak adlandırılıyor. Aynı yardımdır.",
  feedbackThanks: "Geri bildiriminiz için teşekkürler",
  feedbackGood: "İyi yanıt",
  feedbackBad: "Kötü yanıt",
  feedbackPlaceholder: "Ne yanlıştı? (isteğe bağlı)",
  feedbackSend: "Gönder",
  sessionQuestion: "Bu konuşma ne kadar yardımcı oldu?",
  sessionPlaceholder: "Daha fazlasını anlatmak ister misiniz? (isteğe bağlı)",
  skip: "Atla",
  submit: "Gönder",
  stars: "yıldız",
  newChat: "Yeni sohbet",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (temel güvence)",
      prompt: "Bürgergeld (temel güvence) alma hakkım var mı ve nasıl başvururum?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (çocuk parası)",
      prompt: "Kindergeld'i kim alır ve nasıl başvurabilirim?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (ebeveyn parası) ve aile",
      prompt: "Çocuğumun doğumundan sonra Elterngeld (ebeveyn parası) başvurusunu nasıl yaparım?",
    },
    {
      topic: "rente",
      label: "Rente (emeklilik)",
      prompt: "Ne zaman emekli olabilirim ve Rente (emeklilik) başvurusunu nasıl yaparım?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (kira yardımı)",
      prompt: "Wohngeld (kira yardımı) alma hakkım var mı ve nasıl başvururum?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (vergi kimlik numarası)",
      prompt: "Steuer-Identifikationsnummer'i (vergi kimlik numarası) nasıl alırım?",
    },
    {
      topic: "aufenthalt",
      label: "Oturum ve vatandaşlık",
      prompt: "Alman vatandaşlığı için hangi şartlar geçerli?",
    },
  ],
};

const ar: UIStrings = {
  tagline: "اللغة الرسمية الألمانية بلغة بسيطة — مع مصادر رسمية",
  welcomeTitle: "كيف يمكننا مساعدتك؟",
  welcomeSubtitle:
    "إجابات بسيطة بمصادر رسمية حول: Bürgergeld (الضمان الأساسي)، وKindergeld (إعانة الأطفال) والإعانات العائلية، وRente (التقاعد)، وWohngeld (إعانة السكن)، وSteuer-ID (الرقم الضريبي)، والإقامة والتجنيس. يمكننا أيضًا إيجاد الجهة المختصة بك — اذكر الرمز البريدي فقط.",
  inputPlaceholder: "اكتب سؤالك …",
  send: "إرسال",
  typing: "جارٍ كتابة الإجابة",
  errorMessage: "فشل الطلب. يرجى المحاولة مرة أخرى.",
  disclaimer: "يشرح BürgerChat المعلومات الرسمية، وهو ليس استشارة قانونية.",
  sources: "المصادر",
  buergergeldNotice:
    "منذ 1 يوليو 2026 أصبح اسم „Bürgergeld“ رسميًا „Grundsicherungsgeld“ (Neue Grundsicherung). إنها الإعانة نفسها.",
  feedbackThanks: "شكرًا على ملاحظاتك",
  feedbackGood: "إجابة جيدة",
  feedbackBad: "إجابة سيئة",
  feedbackPlaceholder: "ما الخطأ؟ (اختياري)",
  feedbackSend: "إرسال",
  sessionQuestion: "ما مدى فائدة هذه المحادثة؟",
  sessionPlaceholder: "هل تريد إخبارنا بالمزيد؟ (اختياري)",
  skip: "تخطي",
  submit: "إرسال",
  stars: "نجوم",
  newChat: "محادثة جديدة",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (الضمان الأساسي)",
      prompt: "هل يحق لي الحصول على Bürgergeld (الضمان الأساسي) وكيف أقدم الطلب؟",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (إعانة الأطفال)",
      prompt: "من يحصل على Kindergeld وكيف أقدم الطلب؟",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (إعانة الوالدين) والأسرة",
      prompt: "كيف أتقدم بطلب Elterngeld (إعانة الوالدين) بعد ولادة طفلي؟",
    },
    {
      topic: "rente",
      label: "Rente (التقاعد)",
      prompt: "متى يمكنني التقاعد وكيف أتقدم بطلب Rente (المعاش)؟",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (إعانة السكن)",
      prompt: "هل يحق لي الحصول على Wohngeld (إعانة السكن) وكيف أقدم الطلب؟",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (الرقم الضريبي)",
      prompt: "كيف أحصل على Steuer-Identifikationsnummer (الرقم الضريبي)؟",
    },
    {
      topic: "aufenthalt",
      label: "الإقامة والتجنيس",
      prompt: "ما هي شروط الحصول على الجنسية الألمانية؟",
    },
  ],
};

const fa: UIStrings = {
  tagline: "زبان اداری آلمانی به زبان ساده — با منابع رسمی",
  welcomeTitle: "چطور می‌توانیم کمک کنیم؟",
  welcomeSubtitle:
    "پاسخ‌های ساده با منابع رسمی درباره: Bürgergeld (تأمین پایه)، Kindergeld (کمک‌هزینه فرزند) و مزایای خانواده، Rente (بازنشستگی)، Wohngeld (کمک‌هزینه مسکن)، Steuer-ID (شماره مالیاتی)، اقامت و تابعیت. اداره مسئول شما را هم پیدا می‌کنیم — کافی است کد پستی خود را بنویسید.",
  inputPlaceholder: "سؤال خود را بنویسید …",
  send: "ارسال",
  typing: "در حال نوشتن پاسخ",
  errorMessage: "درخواست ناموفق بود. لطفاً دوباره تلاش کنید.",
  disclaimer: "BürgerChat اطلاعات رسمی را توضیح می‌دهد و جایگزین مشاوره حقوقی نیست.",
  sources: "منابع",
  buergergeldNotice:
    "از ۱ ژوئیه ۲۰۲۶ نام رسمی „Bürgergeld“ به „Grundsicherungsgeld“ (Neue Grundsicherung) تغییر کرده است. این همان مزایاست.",
  feedbackThanks: "از بازخورد شما متشکریم",
  feedbackGood: "پاسخ خوب",
  feedbackBad: "پاسخ بد",
  feedbackPlaceholder: "چه چیزی اشتباه بود؟ (اختیاری)",
  feedbackSend: "ارسال",
  sessionQuestion: "این گفتگو چقدر مفید بود؟",
  sessionPlaceholder: "می‌خواهید بیشتر بگویید؟ (اختیاری)",
  skip: "رد کردن",
  submit: "ثبت",
  stars: "ستاره",
  newChat: "گفتگوی جدید",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (تأمین پایه)",
      prompt: "آیا حق دریافت Bürgergeld (تأمین پایه) را دارم و چگونه درخواست بدهم؟",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (کمک‌هزینه فرزند)",
      prompt: "چه کسی Kindergeld می‌گیرد و چگونه درخواست بدهم؟",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (کمک‌هزینه والدین) و خانواده",
      prompt: "چگونه پس از تولد فرزندم برای Elterngeld (کمک‌هزینه والدین) درخواست بدهم؟",
    },
    {
      topic: "rente",
      label: "Rente (بازنشستگی)",
      prompt: "چه زمانی می‌توانم بازنشسته شوم و چگونه برای Rente (مستمری) درخواست بدهم؟",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (کمک‌هزینه مسکن)",
      prompt: "آیا حق دریافت Wohngeld (کمک‌هزینه مسکن) را دارم و چگونه درخواست بدهم؟",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (شماره شناسایی مالیاتی)",
      prompt: "چگونه Steuer-Identifikationsnummer (شماره شناسایی مالیاتی) را دریافت کنم؟",
    },
    {
      topic: "aufenthalt",
      label: "اقامت و تابعیت",
      prompt: "شرایط دریافت تابعیت آلمان چیست؟",
    },
  ],
};

const uk: UIStrings = {
  tagline: "Німецька бюрократична мова — простими словами, з офіційними джерелами",
  welcomeTitle: "Чим можемо допомогти?",
  welcomeSubtitle:
    "Прості відповіді з офіційними джерелами про: Bürgergeld (базове забезпечення), Kindergeld (допомогу на дітей) та сімейні виплати, Rente (пенсію), Wohngeld (житлову допомогу), Steuer-ID (податковий номер), перебування та громадянство. Також знайдемо вашу відповідальну установу — просто вкажіть поштовий індекс.",
  inputPlaceholder: "Поставте своє запитання …",
  send: "Надіслати",
  typing: "Готуємо відповідь",
  errorMessage: "Запит не вдався. Спробуйте ще раз.",
  disclaimer: "BürgerChat пояснює офіційну інформацію і не замінює юридичну консультацію.",
  sources: "Джерела",
  buergergeldNotice:
    "З 1 липня 2026 року „Bürgergeld“ офіційно називається „Grundsicherungsgeld“ (Neue Grundsicherung). Це та сама виплата.",
  feedbackThanks: "Дякуємо за відгук",
  feedbackGood: "Хороша відповідь",
  feedbackBad: "Погана відповідь",
  feedbackPlaceholder: "Що було не так? (необов'язково)",
  feedbackSend: "Надіслати",
  sessionQuestion: "Наскільки корисною була ця розмова?",
  sessionPlaceholder: "Хочете розповісти більше? (необов'язково)",
  skip: "Пропустити",
  submit: "Надіслати",
  stars: "зірок",
  newChat: "Нова розмова",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (базове забезпечення)",
      prompt: "Чи маю я право на Bürgergeld (базове забезпечення) і як його оформити?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (допомога на дітей)",
      prompt: "Хто отримує Kindergeld і як подати заяву?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (батьківська допомога) і сім'я",
      prompt: "Як подати заяву на Elterngeld (батьківську допомогу) після народження дитини?",
    },
    {
      topic: "rente",
      label: "Rente (пенсія)",
      prompt: "Коли я можу вийти на пенсію і як подати заяву на Rente (пенсію)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (житлова допомога)",
      prompt: "Чи маю я право на Wohngeld (житлову допомогу) і як її оформити?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (податковий номер)",
      prompt: "Як отримати Steuer-Identifikationsnummer (податковий номер)?",
    },
    {
      topic: "aufenthalt",
      label: "Проживання та громадянство",
      prompt: "Які умови отримання німецького громадянства?",
    },
  ],
};

const ru: UIStrings = {
  tagline: "Немецкий бюрократический язык — простыми словами, с официальными источниками",
  welcomeTitle: "Чем мы можем помочь?",
  welcomeSubtitle:
    "Простые ответы с официальными источниками о: Bürgergeld (базовое обеспечение), Kindergeld (пособие на детей) и семейных выплатах, Rente (пенсия), Wohngeld (жилищное пособие), Steuer-ID (налоговый номер), пребывании и гражданстве. Также найдём вашу ответственную инстанцию — просто укажите почтовый индекс.",
  inputPlaceholder: "Задайте свой вопрос …",
  send: "Отправить",
  typing: "Готовим ответ",
  errorMessage: "Запрос не удался. Попробуйте ещё раз.",
  disclaimer: "BürgerChat объясняет официальную информацию и не заменяет юридическую консультацию.",
  sources: "Источники",
  buergergeldNotice:
    "С 1 июля 2026 года „Bürgergeld“ официально называется „Grundsicherungsgeld“ (Neue Grundsicherung). Это та же выплата.",
  feedbackThanks: "Спасибо за отзыв",
  feedbackGood: "Хороший ответ",
  feedbackBad: "Плохой ответ",
  feedbackPlaceholder: "Что было не так? (необязательно)",
  feedbackSend: "Отправить",
  sessionQuestion: "Насколько полезным был этот разговор?",
  sessionPlaceholder: "Хотите рассказать больше? (необязательно)",
  skip: "Пропустить",
  submit: "Отправить",
  stars: "звёзд",
  newChat: "Новый разговор",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (базовое обеспечение)",
      prompt: "Имею ли я право на Bürgergeld (базовое обеспечение) и как его оформить?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (пособие на детей)",
      prompt: "Кто получает Kindergeld и как подать заявление?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (родительское пособие) и семья",
      prompt: "Как подать заявление на Elterngeld (родительское пособие) после рождения ребёнка?",
    },
    {
      topic: "rente",
      label: "Rente (пенсия)",
      prompt: "Когда я могу выйти на пенсию и как подать заявление на Rente (пенсию)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (жилищное пособие)",
      prompt: "Имею ли я право на Wohngeld (жилищное пособие) и как его оформить?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (налоговый номер)",
      prompt: "Как получить Steuer-Identifikationsnummer (налоговый номер)?",
    },
    {
      topic: "aufenthalt",
      label: "Пребывание и гражданство",
      prompt: "Каковы условия получения немецкого гражданства?",
    },
  ],
};

const pl: UIStrings = {
  tagline: "Niemiecki język urzędowy — prostym językiem, z oficjalnymi źródłami",
  welcomeTitle: "W czym możemy pomóc?",
  welcomeSubtitle:
    "Proste odpowiedzi z oficjalnymi źródłami o: Bürgergeld (zabezpieczenie podstawowe), Kindergeld (zasiłek na dzieci) i świadczeniach rodzinnych, Rente (emerytura), Wohngeld (dodatek mieszkaniowy), Steuer-ID (numer podatkowy), pobycie i obywatelstwie. Znajdziemy też właściwy urząd — wystarczy podać kod pocztowy.",
  inputPlaceholder: "Zadaj swoje pytanie …",
  send: "Wyślij",
  typing: "Przygotowujemy odpowiedź",
  errorMessage: "Żądanie nie powiodło się. Spróbuj ponownie.",
  disclaimer: "BürgerChat objaśnia oficjalne informacje i nie zastępuje porady prawnej.",
  sources: "Źródła",
  buergergeldNotice:
    "Od 1 lipca 2026 r. „Bürgergeld“ oficjalnie nazywa się „Grundsicherungsgeld“ (Neue Grundsicherung). To to samo świadczenie.",
  feedbackThanks: "Dziękujemy za opinię",
  feedbackGood: "Dobra odpowiedź",
  feedbackBad: "Zła odpowiedź",
  feedbackPlaceholder: "Co było nie tak? (opcjonalnie)",
  feedbackSend: "Wyślij",
  sessionQuestion: "Jak pomocna była ta rozmowa?",
  sessionPlaceholder: "Chcesz powiedzieć więcej? (opcjonalnie)",
  skip: "Pomiń",
  submit: "Wyślij",
  stars: "gwiazdek",
  newChat: "Nowa rozmowa",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (zabezpieczenie podstawowe)",
      prompt: "Czy mam prawo do Bürgergeld (zabezpieczenia podstawowego) i jak je złożyć?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (zasiłek na dzieci)",
      prompt: "Kto dostaje Kindergeld i jak złożyć wniosek?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (zasiłek rodzicielski) i rodzina",
      prompt: "Jak złożyć wniosek o Elterngeld (zasiłek rodzicielski) po narodzinach dziecka?",
    },
    {
      topic: "rente",
      label: "Rente (emerytura)",
      prompt: "Kiedy mogę przejść na emeryturę i jak złożyć wniosek o Rente (emeryturę)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (dodatek mieszkaniowy)",
      prompt: "Czy mam prawo do Wohngeld (dodatku mieszkaniowego) i jak go otrzymać?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (numer podatkowy)",
      prompt: "Jak otrzymać Steuer-Identifikationsnummer (numer identyfikacji podatkowej)?",
    },
    {
      topic: "aufenthalt",
      label: "Pobyt i obywatelstwo",
      prompt: "Jakie są warunki uzyskania niemieckiego obywatelstwa?",
    },
  ],
};

const zhHant: UIStrings = {
  tagline: "把德國公文翻成簡單語言 — 附官方來源",
  welcomeTitle: "需要什麼協助？",
  welcomeSubtitle:
    "提供有官方來源的簡單解答：Bürgergeld（基本生活保障）、Kindergeld（兒童金）與家庭福利、Rente（退休金）、Wohngeld（住房補貼）、Steuer-ID（稅務識別號）、居留與入籍。也能幫你找到主管機關 — 只要附上郵遞區號。",
  inputPlaceholder: "輸入你的問題 …",
  send: "送出",
  typing: "回答準備中",
  errorMessage: "請求失敗，請再試一次。",
  disclaimer: "BürgerChat 解釋官方資訊，不能取代法律諮詢。",
  sources: "來源",
  buergergeldNotice:
    "自 2026 年 7 月 1 日起，„Bürgergeld“ 正式更名為 „Grundsicherungsgeld“（Neue Grundsicherung），是同一項福利。",
  feedbackThanks: "感謝你的回饋",
  feedbackGood: "回答得好",
  feedbackBad: "回答不好",
  feedbackPlaceholder: "哪裡有問題？（選填）",
  feedbackSend: "送出",
  sessionQuestion: "這次對話對你有幫助嗎？",
  sessionPlaceholder: "想多說一點嗎？（選填）",
  skip: "略過",
  submit: "送出",
  stars: "顆星",
  newChat: "新對話",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld（基本生活保障）",
      prompt: "我有資格領 Bürgergeld（基本生活保障）嗎？要怎麼申請？",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld（兒童金）",
      prompt: "誰可以領 Kindergeld？要怎麼申請？",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld（父母金）與家庭福利",
      prompt: "孩子出生後，我要怎麼申請 Elterngeld（父母金）？",
    },
    {
      topic: "rente",
      label: "Rente（退休金）",
      prompt: "我什麼時候可以退休？要怎麼申請 Rente（退休金）？",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld（住房補貼）",
      prompt: "我有資格領 Wohngeld（住房補貼）嗎？要怎麼申請？",
    },
    {
      topic: "steuern",
      label: "Steuer-ID（稅務識別號）",
      prompt: "我要怎麼取得 Steuer-Identifikationsnummer（稅務識別號）？",
    },
    {
      topic: "aufenthalt",
      label: "居留與入籍",
      prompt: "申請德國入籍需要符合哪些條件？",
    },
  ],
};

const zhHans: UIStrings = {
  tagline: "把德国公文翻成简单语言 — 附官方来源",
  welcomeTitle: "需要什么帮助？",
  welcomeSubtitle:
    "提供有官方来源的简单解答：Bürgergeld（基本生活保障）、Kindergeld（儿童金）与家庭福利、Rente（养老金）、Wohngeld（住房补贴）、Steuer-ID（税务识别号）、居留与入籍。也能帮你找到主管机关 — 只要附上邮政编码。",
  inputPlaceholder: "输入你的问题 …",
  send: "发送",
  typing: "回答准备中",
  errorMessage: "请求失败，请再试一次。",
  disclaimer: "BürgerChat 解释官方信息，不能取代法律咨询。",
  sources: "来源",
  buergergeldNotice:
    "自 2026 年 7 月 1 日起，„Bürgergeld“ 正式更名为 „Grundsicherungsgeld“（Neue Grundsicherung），是同一项福利。",
  feedbackThanks: "感谢你的反馈",
  feedbackGood: "回答得好",
  feedbackBad: "回答不好",
  feedbackPlaceholder: "哪里有问题？（选填）",
  feedbackSend: "发送",
  sessionQuestion: "这次对话对你有帮助吗？",
  sessionPlaceholder: "想多说一点吗？（选填）",
  skip: "跳过",
  submit: "提交",
  stars: "颗星",
  newChat: "新对话",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld（基本生活保障）",
      prompt: "我有资格领 Bürgergeld（基本生活保障）吗？要怎么申请？",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld（儿童金）",
      prompt: "谁可以领 Kindergeld？要怎么申请？",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld（父母金）与家庭福利",
      prompt: "孩子出生后，我要怎么申请 Elterngeld（父母金）？",
    },
    {
      topic: "rente",
      label: "Rente（养老金）",
      prompt: "我什么时候可以退休？要怎么申请 Rente（养老金）？",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld（住房补贴）",
      prompt: "我有资格领 Wohngeld（住房补贴）吗？要怎么申请？",
    },
    {
      topic: "steuern",
      label: "Steuer-ID（税务识别号）",
      prompt: "我要怎么取得 Steuer-Identifikationsnummer（税务识别号）？",
    },
    {
      topic: "aufenthalt",
      label: "居留与入籍",
      prompt: "申请德国入籍需要符合哪些条件？",
    },
  ],
};

const vi: UIStrings = {
  tagline: "Ngôn ngữ hành chính Đức — bằng lời đơn giản, kèm nguồn chính thức",
  welcomeTitle: "Chúng tôi có thể giúp gì?",
  welcomeSubtitle:
    "Câu trả lời đơn giản với nguồn chính thức về: Bürgergeld (bảo đảm cơ bản), Kindergeld (tiền trẻ em) và trợ cấp gia đình, Rente (lương hưu), Wohngeld (trợ cấp nhà ở), Steuer-ID (mã số thuế), cư trú và nhập tịch. Chúng tôi cũng tìm được cơ quan phụ trách — chỉ cần ghi mã bưu điện của bạn.",
  inputPlaceholder: "Đặt câu hỏi của bạn …",
  send: "Gửi",
  typing: "Đang soạn câu trả lời",
  errorMessage: "Yêu cầu thất bại. Vui lòng thử lại.",
  disclaimer: "BürgerChat giải thích thông tin chính thức, không thay thế tư vấn pháp lý.",
  sources: "Nguồn",
  buergergeldNotice:
    "Từ ngày 1/7/2026, „Bürgergeld“ chính thức đổi tên thành „Grundsicherungsgeld“ (Neue Grundsicherung). Đây là cùng một khoản trợ cấp.",
  feedbackThanks: "Cảm ơn phản hồi của bạn",
  feedbackGood: "Câu trả lời tốt",
  feedbackBad: "Câu trả lời chưa tốt",
  feedbackPlaceholder: "Có gì chưa đúng? (không bắt buộc)",
  feedbackSend: "Gửi",
  sessionQuestion: "Cuộc trò chuyện này hữu ích thế nào?",
  sessionPlaceholder: "Bạn muốn chia sẻ thêm? (không bắt buộc)",
  skip: "Bỏ qua",
  submit: "Gửi",
  stars: "sao",
  newChat: "Cuộc trò chuyện mới",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (bảo đảm cơ bản)",
      prompt: "Tôi có quyền nhận Bürgergeld (bảo đảm cơ bản) không và nộp đơn thế nào?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (tiền trẻ em)",
      prompt: "Ai được nhận Kindergeld và nộp đơn thế nào?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (trợ cấp cha mẹ) và gia đình",
      prompt: "Làm sao để xin Elterngeld (trợ cấp cha mẹ) sau khi con tôi chào đời?",
    },
    {
      topic: "rente",
      label: "Rente (lương hưu)",
      prompt: "Khi nào tôi có thể nghỉ hưu và làm sao để xin Rente (lương hưu)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (trợ cấp nhà ở)",
      prompt: "Tôi có được nhận Wohngeld (trợ cấp nhà ở) không và xin như thế nào?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (mã số thuế)",
      prompt: "Làm sao để nhận Steuer-Identifikationsnummer (mã số thuế)?",
    },
    {
      topic: "aufenthalt",
      label: "Cư trú và nhập quốc tịch",
      prompt: "Điều kiện để nhập quốc tịch Đức là gì?",
    },
  ],
};

const id: UIStrings = {
  tagline: "Bahasa birokrasi Jerman — dengan bahasa sederhana dan sumber resmi",
  welcomeTitle: "Apa yang bisa kami bantu?",
  welcomeSubtitle:
    "Jawaban sederhana dengan sumber resmi tentang: Bürgergeld (jaminan dasar), Kindergeld (tunjangan anak) & tunjangan keluarga, Rente (pensiun), Wohngeld (tunjangan perumahan), Steuer-ID (nomor pajak), izin tinggal & kewarganegaraan. Kami juga bisa menemukan kantor yang berwenang — cukup sertakan kode pos Anda.",
  inputPlaceholder: "Tulis pertanyaan Anda …",
  send: "Kirim",
  typing: "Sedang menyiapkan jawaban",
  errorMessage: "Permintaan gagal. Silakan coba lagi.",
  disclaimer: "BürgerChat menjelaskan informasi resmi dan bukan nasihat hukum.",
  sources: "Sumber",
  buergergeldNotice:
    "Sejak 1 Juli 2026, „Bürgergeld“ resmi bernama „Grundsicherungsgeld“ (Neue Grundsicherung). Ini tunjangan yang sama.",
  feedbackThanks: "Terima kasih atas masukan Anda",
  feedbackGood: "Jawaban bagus",
  feedbackBad: "Jawaban kurang baik",
  feedbackPlaceholder: "Apa yang salah? (opsional)",
  feedbackSend: "Kirim",
  sessionQuestion: "Seberapa membantu percakapan ini?",
  sessionPlaceholder: "Ingin bercerita lebih banyak? (opsional)",
  skip: "Lewati",
  submit: "Kirim",
  stars: "bintang",
  newChat: "Percakapan baru",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld (jaminan dasar)",
      prompt: "Apakah saya berhak atas Bürgergeld (jaminan dasar) dan bagaimana mengajukannya?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (tunjangan anak)",
      prompt: "Siapa yang mendapat Kindergeld dan bagaimana cara mengajukannya?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld (tunjangan orang tua) & keluarga",
      prompt: "Bagaimana cara mengajukan Elterngeld (tunjangan orang tua) setelah anak saya lahir?",
    },
    {
      topic: "rente",
      label: "Rente (pensiun)",
      prompt: "Kapan saya bisa pensiun dan bagaimana cara mengajukan Rente (pensiun)?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld (tunjangan perumahan)",
      prompt: "Apakah saya berhak atas Wohngeld (tunjangan perumahan) dan bagaimana mengajukannya?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID (nomor pajak)",
      prompt: "Bagaimana cara mendapatkan Steuer-Identifikationsnummer (nomor identifikasi pajak)?",
    },
    {
      topic: "aufenthalt",
      label: "Izin tinggal & kewarganegaraan",
      prompt: "Apa saja syarat untuk menjadi warga negara Jerman?",
    },
  ],
};

const ko: UIStrings = {
  tagline: "독일 행정 용어를 쉬운 말로 — 공식 출처와 함께",
  welcomeTitle: "무엇을 도와드릴까요?",
  welcomeSubtitle:
    "공식 출처가 있는 쉬운 답변: Bürgergeld(기초 생활 보장), Kindergeld(아동 수당)와 가족 수당, Rente(연금), Wohngeld(주거 보조금), Steuer-ID(세금 식별 번호), 체류와 귀화. 우편번호를 알려주시면 담당 관청도 찾아드립니다.",
  inputPlaceholder: "질문을 입력하세요 …",
  send: "보내기",
  typing: "답변 작성 중",
  errorMessage: "요청이 실패했습니다. 다시 시도해 주세요.",
  disclaimer: "BürgerChat은 공식 정보를 설명하며 법률 자문을 대신하지 않습니다.",
  sources: "출처",
  buergergeldNotice:
    "2026년 7월 1일부터 „Bürgergeld“의 공식 명칭이 „Grundsicherungsgeld“(Neue Grundsicherung)로 바뀌었습니다. 같은 수당입니다.",
  feedbackThanks: "피드백 감사합니다",
  feedbackGood: "좋은 답변",
  feedbackBad: "아쉬운 답변",
  feedbackPlaceholder: "무엇이 잘못되었나요? (선택)",
  feedbackSend: "보내기",
  sessionQuestion: "이 대화가 얼마나 도움이 되었나요?",
  sessionPlaceholder: "더 알려주시겠어요? (선택)",
  skip: "건너뛰기",
  submit: "제출",
  stars: "점",
  newChat: "새 대화",
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld(기초 생활 보장)",
      prompt: "저는 Bürgergeld(기초 생활 보장)를 받을 수 있나요? 어떻게 신청하나요?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (아동 수당)",
      prompt: "Kindergeld는 누가 받을 수 있고 어떻게 신청하나요?",
    },
    {
      topic: "familie-und-kinder",
      label: "Elterngeld(부모 수당)와 가족",
      prompt: "아이가 태어난 후 Elterngeld(부모 수당)는 어떻게 신청하나요?",
    },
    {
      topic: "rente",
      label: "Rente(연금)",
      prompt: "언제 은퇴할 수 있고 Rente(연금)는 어떻게 신청하나요?",
    },
    {
      topic: "wohngeld",
      label: "Wohngeld(주거 보조금)",
      prompt: "저는 Wohngeld(주거 보조금)를 받을 수 있나요? 어떻게 신청하나요?",
    },
    {
      topic: "steuern",
      label: "Steuer-ID(세금 식별 번호)",
      prompt: "Steuer-Identifikationsnummer(세금 식별 번호)는 어떻게 발급받나요?",
    },
    {
      topic: "aufenthalt",
      label: "체류와 귀화",
      prompt: "독일 귀화 조건은 무엇인가요?",
    },
  ],
};

export const UI_STRINGS: Record<string, UIStrings> = {
  de,
  en,
  tr,
  ar,
  fa,
  uk,
  ru,
  pl,
  "zh-Hant": zhHant,
  "zh-Hans": zhHans,
  vi,
  id,
  ko,
};

export function getStrings(language: string): UIStrings {
  return UI_STRINGS[language] ?? de;
}
