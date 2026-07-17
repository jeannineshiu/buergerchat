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
      topic: "behoerde",
      label: "Die richtige Behörde finden",
      prompt: "Welches Amt ist für mein Anliegen zuständig?",
    },
  ],
};

const en: UIStrings = {
  tagline: "German bureaucracy in plain language — with official sources",
  welcomeTitle: "How can we help?",
  welcomeSubtitle:
    "Simple answers with official sources about: Bürgergeld, Kindergeld & family benefits, pension, Wohngeld, tax ID, residence & citizenship. We can also find your responsible authority — just include your postal code.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / basic income support",
      prompt: "Am I entitled to Bürgergeld (basic income support) and how do I apply?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (child benefit)",
      prompt: "Who gets Kindergeld and how do I apply for it?",
    },
    {
      topic: "behoerde",
      label: "Find the right authority",
      prompt: "Which office is responsible for my request?",
    },
  ],
};

const tr: UIStrings = {
  tagline: "Alman resmi dili, sade bir dille — resmi kaynaklarla",
  welcomeTitle: "Size nasıl yardımcı olabiliriz?",
  welcomeSubtitle:
    "Şu konularda resmi kaynaklı, sade yanıtlar: Bürgergeld, Kindergeld ve aile yardımları, emeklilik, Wohngeld, vergi kimlik numarası, oturum ve vatandaşlık. Posta kodunuzu yazarsanız yetkili daireyi de buluruz.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / temel güvence",
      prompt: "Bürgergeld (temel güvence) alma hakkım var mı ve nasıl başvururum?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (çocuk parası)",
      prompt: "Kindergeld'i kim alır ve nasıl başvurabilirim?",
    },
    {
      topic: "behoerde",
      label: "Doğru daireyi bulun",
      prompt: "Benim işim için hangi daire yetkili?",
    },
  ],
};

const ar: UIStrings = {
  tagline: "اللغة الرسمية الألمانية بلغة بسيطة — مع مصادر رسمية",
  welcomeTitle: "كيف يمكننا مساعدتك؟",
  welcomeSubtitle:
    "إجابات بسيطة بمصادر رسمية حول: Bürgergeld، وKindergeld والإعانات العائلية، والتقاعد، وWohngeld، والرقم الضريبي، والإقامة والتجنيس. يمكننا أيضًا إيجاد الجهة المختصة بك — اذكر الرمز البريدي فقط.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / الضمان الأساسي",
      prompt: "هل يحق لي الحصول على Bürgergeld (الضمان الأساسي) وكيف أقدم الطلب؟",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (إعانة الأطفال)",
      prompt: "من يحصل على Kindergeld وكيف أقدم الطلب؟",
    },
    {
      topic: "behoerde",
      label: "إيجاد الجهة المختصة",
      prompt: "أي مكتب مسؤول عن طلبي؟",
    },
  ],
};

const fa: UIStrings = {
  tagline: "زبان اداری آلمانی به زبان ساده — با منابع رسمی",
  welcomeTitle: "چطور می‌توانیم کمک کنیم؟",
  welcomeSubtitle:
    "پاسخ‌های ساده با منابع رسمی درباره: Bürgergeld، Kindergeld و مزایای خانواده، بازنشستگی، Wohngeld، شماره مالیاتی، اقامت و تابعیت. اداره مسئول شما را هم پیدا می‌کنیم — کافی است کد پستی خود را بنویسید.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / تأمین پایه",
      prompt: "آیا حق دریافت Bürgergeld (تأمین پایه) را دارم و چگونه درخواست بدهم؟",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (کمک‌هزینه فرزند)",
      prompt: "چه کسی Kindergeld می‌گیرد و چگونه درخواست بدهم؟",
    },
    {
      topic: "behoerde",
      label: "یافتن اداره مسئول",
      prompt: "کدام اداره مسئول کار من است؟",
    },
  ],
};

const uk: UIStrings = {
  tagline: "Німецька бюрократична мова — простими словами, з офіційними джерелами",
  welcomeTitle: "Чим можемо допомогти?",
  welcomeSubtitle:
    "Прості відповіді з офіційними джерелами про: Bürgergeld, Kindergeld та сімейні виплати, пенсію, Wohngeld, податковий номер, перебування та громадянство. Також знайдемо вашу відповідальну установу — просто вкажіть поштовий індекс.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / базове забезпечення",
      prompt: "Чи маю я право на Bürgergeld (базове забезпечення) і як його оформити?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (допомога на дітей)",
      prompt: "Хто отримує Kindergeld і як подати заяву?",
    },
    {
      topic: "behoerde",
      label: "Знайти потрібну установу",
      prompt: "Яка установа відповідає за моє питання?",
    },
  ],
};

const ru: UIStrings = {
  tagline: "Немецкий бюрократический язык — простыми словами, с официальными источниками",
  welcomeTitle: "Чем мы можем помочь?",
  welcomeSubtitle:
    "Простые ответы с официальными источниками о: Bürgergeld, Kindergeld и семейных выплатах, пенсии, Wohngeld, налоговом номере, пребывании и гражданстве. Также найдём вашу ответственную инстанцию — просто укажите почтовый индекс.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / базовое обеспечение",
      prompt: "Имею ли я право на Bürgergeld (базовое обеспечение) и как его оформить?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (пособие на детей)",
      prompt: "Кто получает Kindergeld и как подать заявление?",
    },
    {
      topic: "behoerde",
      label: "Найти нужное ведомство",
      prompt: "Какое ведомство отвечает за мой вопрос?",
    },
  ],
};

const pl: UIStrings = {
  tagline: "Niemiecki język urzędowy — prostym językiem, z oficjalnymi źródłami",
  welcomeTitle: "W czym możemy pomóc?",
  welcomeSubtitle:
    "Proste odpowiedzi z oficjalnymi źródłami o: Bürgergeld, Kindergeld i świadczeniach rodzinnych, emeryturze, Wohngeld, numerze podatkowym, pobycie i obywatelstwie. Znajdziemy też właściwy urząd — wystarczy podać kod pocztowy.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / zabezpieczenie podstawowe",
      prompt: "Czy mam prawo do Bürgergeld (zabezpieczenia podstawowego) i jak je złożyć?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (zasiłek na dzieci)",
      prompt: "Kto dostaje Kindergeld i jak złożyć wniosek?",
    },
    {
      topic: "behoerde",
      label: "Znajdź właściwy urząd",
      prompt: "Który urząd jest właściwy dla mojej sprawy?",
    },
  ],
};

const zhHant: UIStrings = {
  tagline: "把德國公文翻成簡單語言 — 附官方來源",
  welcomeTitle: "需要什麼協助？",
  welcomeSubtitle:
    "提供有官方來源的簡單解答：Bürgergeld、Kindergeld 與家庭福利、退休金、Wohngeld、稅務識別號、居留與入籍。也能幫你找到主管機關 — 只要附上郵遞區號。",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / 基本生活保障",
      prompt: "我有資格領 Bürgergeld（基本生活保障）嗎？要怎麼申請？",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld（兒童金）",
      prompt: "誰可以領 Kindergeld？要怎麼申請？",
    },
    {
      topic: "behoerde",
      label: "找到對的機關",
      prompt: "我的事情該找哪個機關辦理？",
    },
  ],
};

const zhHans: UIStrings = {
  tagline: "把德国公文翻成简单语言 — 附官方来源",
  welcomeTitle: "需要什么帮助？",
  welcomeSubtitle:
    "提供有官方来源的简单解答：Bürgergeld、Kindergeld 与家庭福利、养老金、Wohngeld、税务识别号、居留与入籍。也能帮你找到主管机关 — 只要附上邮政编码。",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / 基本生活保障",
      prompt: "我有资格领 Bürgergeld（基本生活保障）吗？要怎么申请？",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld（儿童金）",
      prompt: "谁可以领 Kindergeld？要怎么申请？",
    },
    {
      topic: "behoerde",
      label: "找到对的机关",
      prompt: "我的事情该找哪个机关办理？",
    },
  ],
};

const vi: UIStrings = {
  tagline: "Ngôn ngữ hành chính Đức — bằng lời đơn giản, kèm nguồn chính thức",
  welcomeTitle: "Chúng tôi có thể giúp gì?",
  welcomeSubtitle:
    "Câu trả lời đơn giản với nguồn chính thức về: Bürgergeld, Kindergeld và trợ cấp gia đình, lương hưu, Wohngeld, mã số thuế, cư trú và nhập tịch. Chúng tôi cũng tìm được cơ quan phụ trách — chỉ cần ghi mã bưu điện của bạn.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / bảo đảm cơ bản",
      prompt: "Tôi có quyền nhận Bürgergeld (bảo đảm cơ bản) không và nộp đơn thế nào?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (tiền trẻ em)",
      prompt: "Ai được nhận Kindergeld và nộp đơn thế nào?",
    },
    {
      topic: "behoerde",
      label: "Tìm đúng cơ quan",
      prompt: "Cơ quan nào phụ trách việc của tôi?",
    },
  ],
};

const id: UIStrings = {
  tagline: "Bahasa birokrasi Jerman — dengan bahasa sederhana dan sumber resmi",
  welcomeTitle: "Apa yang bisa kami bantu?",
  welcomeSubtitle:
    "Jawaban sederhana dengan sumber resmi tentang: Bürgergeld, Kindergeld & tunjangan keluarga, pensiun, Wohngeld, nomor pajak, izin tinggal & kewarganegaraan. Kami juga bisa menemukan kantor yang berwenang — cukup sertakan kode pos Anda.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / jaminan dasar",
      prompt: "Apakah saya berhak atas Bürgergeld (jaminan dasar) dan bagaimana mengajukannya?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (tunjangan anak)",
      prompt: "Siapa yang mendapat Kindergeld dan bagaimana cara mengajukannya?",
    },
    {
      topic: "behoerde",
      label: "Temukan kantor yang tepat",
      prompt: "Kantor mana yang berwenang untuk urusan saya?",
    },
  ],
};

const ko: UIStrings = {
  tagline: "독일 행정 용어를 쉬운 말로 — 공식 출처와 함께",
  welcomeTitle: "무엇을 도와드릴까요?",
  welcomeSubtitle:
    "공식 출처가 있는 쉬운 답변: Bürgergeld, Kindergeld와 가족 수당, 연금, Wohngeld, 세금 ID, 체류와 귀화. 우편번호를 알려주시면 담당 관청도 찾아드립니다.",
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
  starters: [
    {
      topic: "buergergeld",
      label: "Bürgergeld / 기초 생활 보장",
      prompt: "저는 Bürgergeld(기초 생활 보장)를 받을 수 있나요? 어떻게 신청하나요?",
    },
    {
      topic: "kindergeld",
      label: "Kindergeld (아동 수당)",
      prompt: "Kindergeld는 누가 받을 수 있고 어떻게 신청하나요?",
    },
    {
      topic: "behoerde",
      label: "담당 관청 찾기",
      prompt: "제 용무는 어느 관청이 담당하나요?",
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
