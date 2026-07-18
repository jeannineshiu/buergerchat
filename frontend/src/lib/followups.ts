// Follow-up question suggestions shown under an answer, keyed by the
// answer's topic (backend/router.py topics). Content is modeled on the
// most-asked questions in the official FAQs (arbeitsagentur.de,
// familienportal.de, deutsche-rentenversicherung.de, bmwsb.bund.de,
// BAMF): (1) how much, (2) how/when to apply & documents, (3) which
// authority is responsible for me. The third question embeds the German
// authority name (Jobcenter, Familienkasse, …) on purpose — those names
// are authority-intent triggers in backend/router.py, so clicking it
// starts the Behörden-Finder flow in any language.
// German terms carry a parenthesized local translation, same rule as i18n.ts.

export type FollowUpMap = Record<string, string[]>;

const de: FollowUpMap = {
  buergergeld: [
    "Wie hoch ist das Grundsicherungsgeld für mich und meine Familie?",
    "Welche Unterlagen brauche ich für den Antrag?",
    "Wo ist mein zuständiges Jobcenter?",
  ],
  kindergeld: [
    "Wie hoch ist das Kindergeld pro Kind?",
    "Kann ich Kindergeld rückwirkend bekommen?",
    "Wo ist meine zuständige Familienkasse?",
  ],
  "familie-und-kinder": [
    "Wie hoch ist das Elterngeld?",
    "Bis wann muss ich Elterngeld beantragen?",
    "Wo ist meine zuständige Elterngeldstelle?",
  ],
  arbeitslos: [
    "Wie lange bekomme ich Arbeitslosengeld?",
    "Wann und wie muss ich mich arbeitslos melden?",
    "Wo ist meine Agentur für Arbeit?",
  ],
  rente: [
    "Mit wie viel Rente kann ich rechnen?",
    "Wann und wie sollte ich meine Rente beantragen?",
    "Wo ist eine Beratungsstelle der Rentenversicherung in meiner Nähe?",
  ],
  wohngeld: [
    "Wie viel Wohngeld kann ich bekommen?",
    "Welche Unterlagen brauche ich für den Wohngeld-Antrag?",
    "Wo ist meine zuständige Wohngeldstelle?",
  ],
  steuern: [
    "Wo finde ich meine Steuer-Identifikationsnummer?",
    "Ich bin neu in Deutschland — wie bekomme ich meine Steuer-ID?",
    "Wo ist mein zuständiges Finanzamt?",
  ],
  aufenthalt: [
    "Wie lange muss ich in Deutschland leben, um mich einbürgern zu lassen?",
    "Welche Sprachkenntnisse brauche ich für die Einbürgerung?",
    "Wo ist meine zuständige Ausländerbehörde?",
  ],
};

const en: FollowUpMap = {
  buergergeld: [
    "How much Grundsicherungsgeld (basic income support) would I get?",
    "Which documents do I need for the application?",
    "Where is my responsible Jobcenter?",
  ],
  kindergeld: [
    "How much Kindergeld (child benefit) is paid per child?",
    "Can I get Kindergeld (child benefit) retroactively?",
    "Where is my responsible Familienkasse (family benefits office)?",
  ],
  "familie-und-kinder": [
    "How much Elterngeld (parental allowance) would I get?",
    "What is the deadline for applying for Elterngeld (parental allowance)?",
    "Where is my responsible Elterngeldstelle (parental allowance office)?",
  ],
  arbeitslos: [
    "How long can I receive Arbeitslosengeld (unemployment benefit)?",
    "When and how do I have to register as unemployed?",
    "Where is my Agentur für Arbeit (employment agency)?",
  ],
  rente: [
    "How much Rente (pension) can I expect?",
    "When and how should I apply for my Rente (pension)?",
    "Where is a Rentenversicherung (pension insurance) advice office near me?",
  ],
  wohngeld: [
    "How much Wohngeld (housing benefit) could I get?",
    "Which documents do I need for the Wohngeld (housing benefit) application?",
    "Where is my responsible Wohngeldstelle (housing benefit office)?",
  ],
  steuern: [
    "Where can I find my Steuer-ID (tax ID)?",
    "I am new in Germany — how do I get my Steuer-ID (tax ID)?",
    "Where is my responsible Finanzamt (tax office)?",
  ],
  aufenthalt: [
    "How long do I need to live in Germany for Einbürgerung (naturalization)?",
    "Which language level do I need for Einbürgerung (naturalization)?",
    "Where is my responsible Ausländerbehörde (immigration office)?",
  ],
};

const tr: FollowUpMap = {
  buergergeld: [
    "Ne kadar Grundsicherungsgeld (temel güvence) alabilirim?",
    "Başvuru için hangi belgeler gerekli?",
    "Benim yetkili Jobcenter'im (iş merkezi) nerede?",
  ],
  kindergeld: [
    "Çocuk başına ne kadar Kindergeld (çocuk parası) ödeniyor?",
    "Kindergeld'i (çocuk parası) geriye dönük alabilir miyim?",
    "Benim yetkili Familienkasse'm (aile kasası) nerede?",
  ],
  "familie-und-kinder": [
    "Ne kadar Elterngeld (ebeveyn parası) alabilirim?",
    "Elterngeld (ebeveyn parası) başvurusu için son tarih ne?",
    "Benim yetkili Elterngeldstelle'm (ebeveyn parası dairesi) nerede?",
  ],
  arbeitslos: [
    "Ne kadar süre Arbeitslosengeld (işsizlik parası) alabilirim?",
    "İşsiz kaldığımda ne zaman ve nasıl kayıt yaptırmalıyım?",
    "Benim Agentur für Arbeit'ım (iş ajansı) nerede?",
  ],
  rente: [
    "Ne kadar Rente (emeklilik) bekleyebilirim?",
    "Rente (emeklilik) başvurusunu ne zaman ve nasıl yapmalıyım?",
    "Yakınımda bir Rentenversicherung (emeklilik sigortası) danışma bürosu nerede?",
  ],
  wohngeld: [
    "Ne kadar Wohngeld (kira yardımı) alabilirim?",
    "Wohngeld (kira yardımı) başvurusu için hangi belgeler gerekli?",
    "Benim yetkili Wohngeldstelle'm (kira yardımı dairesi) nerede?",
  ],
  steuern: [
    "Steuer-ID'mi (vergi kimlik numarası) nerede bulabilirim?",
    "Almanya'ya yeni geldim — Steuer-ID'mi (vergi kimlik numarası) nasıl alırım?",
    "Benim yetkili Finanzamt'ım (vergi dairesi) nerede?",
  ],
  aufenthalt: [
    "Einbürgerung (vatandaşlık) için Almanya'da kaç yıl yaşamış olmam gerekiyor?",
    "Einbürgerung (vatandaşlık) için hangi dil seviyesi gerekli?",
    "Benim yetkili Ausländerbehörde'm (yabancılar dairesi) nerede?",
  ],
};

const ar: FollowUpMap = {
  buergergeld: [
    "كم يبلغ Grundsicherungsgeld (الضمان الأساسي) الذي يمكنني الحصول عليه؟",
    "ما المستندات المطلوبة لتقديم الطلب؟",
    "أين يقع Jobcenter (مركز العمل) المختص بي؟",
  ],
  kindergeld: [
    "كم يبلغ Kindergeld (إعانة الأطفال) لكل طفل؟",
    "هل يمكنني الحصول على Kindergeld (إعانة الأطفال) بأثر رجعي؟",
    "أين تقع Familienkasse (صندوق الأسرة) المختصة بي؟",
  ],
  "familie-und-kinder": [
    "كم يبلغ Elterngeld (إعانة الوالدين) الذي يمكنني الحصول عليه؟",
    "ما آخر موعد لتقديم طلب Elterngeld (إعانة الوالدين)؟",
    "أين تقع Elterngeldstelle (مكتب إعانة الوالدين) المختصة بي؟",
  ],
  arbeitslos: [
    "ما مدة حصولي على Arbeitslosengeld (إعانة البطالة)؟",
    "متى وكيف يجب أن أسجل نفسي عاطلاً عن العمل؟",
    "أين تقع Agentur für Arbeit (وكالة العمل) الخاصة بي؟",
  ],
  rente: [
    "كم يبلغ Rente (معاش التقاعد) الذي يمكنني توقعه؟",
    "متى وكيف أقدم طلب Rente (معاش التقاعد)؟",
    "أين يوجد مكتب استشارة Rentenversicherung (تأمين التقاعد) بالقرب مني؟",
  ],
  wohngeld: [
    "كم يبلغ Wohngeld (إعانة السكن) الذي يمكنني الحصول عليه؟",
    "ما المستندات المطلوبة لطلب Wohngeld (إعانة السكن)؟",
    "أين تقع Wohngeldstelle (مكتب إعانة السكن) المختصة بي؟",
  ],
  steuern: [
    "أين أجد Steuer-ID (الرقم الضريبي) الخاص بي؟",
    "أنا جديد في ألمانيا — كيف أحصل على Steuer-ID (الرقم الضريبي)؟",
    "أين يقع Finanzamt (مكتب الضرائب) المختص بي؟",
  ],
  aufenthalt: [
    "كم سنة يجب أن أعيش في ألمانيا للحصول على Einbürgerung (التجنيس)؟",
    "ما مستوى اللغة المطلوب لـ Einbürgerung (التجنيس)؟",
    "أين تقع Ausländerbehörde (دائرة الأجانب) المختصة بي؟",
  ],
};

const fa: FollowUpMap = {
  buergergeld: [
    "چقدر Grundsicherungsgeld (تأمین پایه) می‌توانم بگیرم؟",
    "برای درخواست چه مدارکی لازم است؟",
    "Jobcenter (مرکز کاریابی) مسئول من کجاست؟",
  ],
  kindergeld: [
    "برای هر فرزند چقدر Kindergeld (کمک‌هزینه فرزند) پرداخت می‌شود؟",
    "آیا می‌توانم Kindergeld (کمک‌هزینه فرزند) را به‌صورت گذشته بگیرم؟",
    "Familienkasse (صندوق خانواده) مسئول من کجاست؟",
  ],
  "familie-und-kinder": [
    "چقدر Elterngeld (کمک‌هزینه والدین) می‌توانم بگیرم؟",
    "مهلت درخواست Elterngeld (کمک‌هزینه والدین) تا کی است؟",
    "Elterngeldstelle (اداره کمک‌هزینه والدین) مسئول من کجاست؟",
  ],
  arbeitslos: [
    "چه مدت می‌توانم Arbeitslosengeld (کمک‌هزینه بیکاری) بگیرم؟",
    "چه زمانی و چگونه باید خودم را بیکار اعلام کنم؟",
    "Agentur für Arbeit (اداره کار) من کجاست؟",
  ],
  rente: [
    "چقدر Rente (مستمری) می‌توانم انتظار داشته باشم؟",
    "چه زمانی و چگونه باید برای Rente (مستمری) درخواست بدهم؟",
    "نزدیک‌ترین دفتر مشاوره Rentenversicherung (بیمه بازنشستگی) کجاست؟",
  ],
  wohngeld: [
    "چقدر Wohngeld (کمک‌هزینه مسکن) می‌توانم بگیرم؟",
    "برای درخواست Wohngeld (کمک‌هزینه مسکن) چه مدارکی لازم است؟",
    "Wohngeldstelle (اداره کمک‌هزینه مسکن) مسئول من کجاست؟",
  ],
  steuern: [
    "Steuer-ID (شماره مالیاتی) خود را کجا پیدا کنم؟",
    "تازه به آلمان آمده‌ام — چگونه Steuer-ID (شماره مالیاتی) بگیرم؟",
    "Finanzamt (اداره مالیات) مسئول من کجاست؟",
  ],
  aufenthalt: [
    "برای Einbürgerung (تابعیت) باید چند سال در آلمان زندگی کرده باشم؟",
    "برای Einbürgerung (تابعیت) چه سطح زبانی لازم است؟",
    "Ausländerbehörde (اداره اتباع خارجی) مسئول من کجاست؟",
  ],
};

const uk: FollowUpMap = {
  buergergeld: [
    "Скільки Grundsicherungsgeld (базового забезпечення) я можу отримати?",
    "Які документи потрібні для заяви?",
    "Де мій відповідальний Jobcenter (центр зайнятості)?",
  ],
  kindergeld: [
    "Скільки Kindergeld (допомоги на дітей) платять на дитину?",
    "Чи можна отримати Kindergeld (допомогу на дітей) заднім числом?",
    "Де моя відповідальна Familienkasse (сімейна каса)?",
  ],
  "familie-und-kinder": [
    "Скільки Elterngeld (батьківської допомоги) я можу отримати?",
    "До якого строку треба подати заяву на Elterngeld (батьківську допомогу)?",
    "Де моя відповідальна Elterngeldstelle (відділ батьківської допомоги)?",
  ],
  arbeitslos: [
    "Як довго я можу отримувати Arbeitslosengeld (допомогу з безробіття)?",
    "Коли та як я маю зареєструватися безробітним?",
    "Де моя Agentur für Arbeit (агентство зайнятості)?",
  ],
  rente: [
    "На яку Rente (пенсію) я можу розраховувати?",
    "Коли та як подати заяву на Rente (пенсію)?",
    "Де поблизу є консультація Rentenversicherung (пенсійного страхування)?",
  ],
  wohngeld: [
    "Скільки Wohngeld (житлової допомоги) я можу отримати?",
    "Які документи потрібні для заяви на Wohngeld (житлову допомогу)?",
    "Де моя відповідальна Wohngeldstelle (відділ житлової допомоги)?",
  ],
  steuern: [
    "Де знайти мій Steuer-ID (податковий номер)?",
    "Я нещодавно в Німеччині — як отримати Steuer-ID (податковий номер)?",
    "Де мій відповідальний Finanzamt (податкова служба)?",
  ],
  aufenthalt: [
    "Скільки років треба прожити в Німеччині для Einbürgerung (набуття громадянства)?",
    "Який рівень мови потрібен для Einbürgerung (набуття громадянства)?",
    "Де моя відповідальна Ausländerbehörde (відомство у справах іноземців)?",
  ],
};

const ru: FollowUpMap = {
  buergergeld: [
    "Сколько Grundsicherungsgeld (базового обеспечения) я могу получить?",
    "Какие документы нужны для заявления?",
    "Где мой ответственный Jobcenter (центр занятости)?",
  ],
  kindergeld: [
    "Сколько Kindergeld (пособия на детей) платят на ребёнка?",
    "Можно ли получить Kindergeld (пособие на детей) задним числом?",
    "Где моя ответственная Familienkasse (семейная касса)?",
  ],
  "familie-und-kinder": [
    "Сколько Elterngeld (родительского пособия) я могу получить?",
    "До какого срока нужно подать заявление на Elterngeld (родительское пособие)?",
    "Где моя ответственная Elterngeldstelle (отдел родительского пособия)?",
  ],
  arbeitslos: [
    "Как долго я могу получать Arbeitslosengeld (пособие по безработице)?",
    "Когда и как я должен зарегистрироваться безработным?",
    "Где моя Agentur für Arbeit (агентство занятости)?",
  ],
  rente: [
    "На какую Rente (пенсию) я могу рассчитывать?",
    "Когда и как подать заявление на Rente (пенсию)?",
    "Где поблизости консультация Rentenversicherung (пенсионного страхования)?",
  ],
  wohngeld: [
    "Сколько Wohngeld (жилищного пособия) я могу получить?",
    "Какие документы нужны для заявления на Wohngeld (жилищное пособие)?",
    "Где моя ответственная Wohngeldstelle (отдел жилищного пособия)?",
  ],
  steuern: [
    "Где найти мой Steuer-ID (налоговый номер)?",
    "Я недавно в Германии — как получить Steuer-ID (налоговый номер)?",
    "Где мой ответственный Finanzamt (налоговая служба)?",
  ],
  aufenthalt: [
    "Сколько лет нужно прожить в Германии для Einbürgerung (получения гражданства)?",
    "Какой уровень языка нужен для Einbürgerung (получения гражданства)?",
    "Где моя ответственная Ausländerbehörde (ведомство по делам иностранцев)?",
  ],
};

const pl: FollowUpMap = {
  buergergeld: [
    "Ile Grundsicherungsgeld (zabezpieczenia podstawowego) mogę dostać?",
    "Jakie dokumenty są potrzebne do wniosku?",
    "Gdzie jest mój właściwy Jobcenter (urząd pracy)?",
  ],
  kindergeld: [
    "Ile wynosi Kindergeld (zasiłek na dzieci) na dziecko?",
    "Czy mogę dostać Kindergeld (zasiłek na dzieci) wstecz?",
    "Gdzie jest moja właściwa Familienkasse (kasa rodzinna)?",
  ],
  "familie-und-kinder": [
    "Ile Elterngeld (zasiłku rodzicielskiego) mogę dostać?",
    "Do kiedy trzeba złożyć wniosek o Elterngeld (zasiłek rodzicielski)?",
    "Gdzie jest moja właściwa Elterngeldstelle (urząd zasiłku rodzicielskiego)?",
  ],
  arbeitslos: [
    "Jak długo mogę pobierać Arbeitslosengeld (zasiłek dla bezrobotnych)?",
    "Kiedy i jak muszę zarejestrować się jako bezrobotny?",
    "Gdzie jest moja Agentur für Arbeit (agencja pracy)?",
  ],
  rente: [
    "Na jaką Rente (emeryturę) mogę liczyć?",
    "Kiedy i jak złożyć wniosek o Rente (emeryturę)?",
    "Gdzie w pobliżu jest punkt doradczy Rentenversicherung (ubezpieczenia emerytalnego)?",
  ],
  wohngeld: [
    "Ile Wohngeld (dodatku mieszkaniowego) mogę dostać?",
    "Jakie dokumenty są potrzebne do wniosku o Wohngeld (dodatek mieszkaniowy)?",
    "Gdzie jest moja właściwa Wohngeldstelle (urząd dodatku mieszkaniowego)?",
  ],
  steuern: [
    "Gdzie znajdę mój Steuer-ID (numer podatkowy)?",
    "Jestem nowy w Niemczech — jak dostać Steuer-ID (numer podatkowy)?",
    "Gdzie jest mój właściwy Finanzamt (urząd skarbowy)?",
  ],
  aufenthalt: [
    "Ile lat trzeba mieszkać w Niemczech, by uzyskać Einbürgerung (obywatelstwo)?",
    "Jaki poziom języka jest potrzebny do Einbürgerung (obywatelstwa)?",
    "Gdzie jest moja właściwa Ausländerbehörde (urząd ds. cudzoziemców)?",
  ],
};

const zhHant: FollowUpMap = {
  buergergeld: [
    "Grundsicherungsgeld（基本生活保障金）每月可以領多少？",
    "申請需要準備哪些文件？",
    "我的 Jobcenter（就業中心）在哪裡？",
  ],
  kindergeld: [
    "Kindergeld（兒童金）每個孩子每月多少錢？",
    "Kindergeld（兒童金）可以補領嗎？",
    "我的 Familienkasse（家庭金辦公室）在哪裡？",
  ],
  "familie-und-kinder": [
    "Elterngeld（父母金）可以領多少？",
    "Elterngeld（父母金）最晚什麼時候要申請？",
    "我的 Elterngeldstelle（父母金辦公室）在哪裡？",
  ],
  arbeitslos: [
    "Arbeitslosengeld（失業金）可以領多久？",
    "失業後什麼時候、要怎麼登記？",
    "我的 Agentur für Arbeit（就業局）在哪裡？",
  ],
  rente: [
    "我的 Rente（退休金）大概會有多少？",
    "Rente（退休金）要什麼時候、怎麼申請？",
    "我附近的 Rentenversicherung（退休保險）諮詢處在哪裡？",
  ],
  wohngeld: [
    "我可以領多少 Wohngeld（住房補貼）？",
    "申請 Wohngeld（住房補貼）需要哪些文件？",
    "我的 Wohngeldstelle（住房補貼辦公室）在哪裡？",
  ],
  steuern: [
    "我的 Steuer-ID（稅務識別號）在哪裡可以找到？",
    "我剛到德國，要怎麼拿到 Steuer-ID（稅務識別號）？",
    "我的 Finanzamt（稅務局）在哪裡？",
  ],
  aufenthalt: [
    "Einbürgerung（入籍）需要在德國住滿幾年？",
    "Einbürgerung（入籍）需要什麼語言程度？",
    "我的 Ausländerbehörde（外國人管理局）在哪裡？",
  ],
};

const zhHans: FollowUpMap = {
  buergergeld: [
    "Grundsicherungsgeld（基本生活保障金）每月可以领多少？",
    "申请需要准备哪些文件？",
    "我的 Jobcenter（就业中心）在哪里？",
  ],
  kindergeld: [
    "Kindergeld（儿童金）每个孩子每月多少钱？",
    "Kindergeld（儿童金）可以补领吗？",
    "我的 Familienkasse（家庭金办公室）在哪里？",
  ],
  "familie-und-kinder": [
    "Elterngeld（父母金）可以领多少？",
    "Elterngeld（父母金）最晚什么时候要申请？",
    "我的 Elterngeldstelle（父母金办公室）在哪里？",
  ],
  arbeitslos: [
    "Arbeitslosengeld（失业金）可以领多久？",
    "失业后什么时候、要怎么登记？",
    "我的 Agentur für Arbeit（就业局）在哪里？",
  ],
  rente: [
    "我的 Rente（养老金）大概会有多少？",
    "Rente（养老金）要什么时候、怎么申请？",
    "我附近的 Rentenversicherung（养老保险）咨询处在哪里？",
  ],
  wohngeld: [
    "我可以领多少 Wohngeld（住房补贴）？",
    "申请 Wohngeld（住房补贴）需要哪些文件？",
    "我的 Wohngeldstelle（住房补贴办公室）在哪里？",
  ],
  steuern: [
    "我的 Steuer-ID（税务识别号）在哪里可以找到？",
    "我刚到德国，要怎么拿到 Steuer-ID（税务识别号）？",
    "我的 Finanzamt（税务局）在哪里？",
  ],
  aufenthalt: [
    "Einbürgerung（入籍）需要在德国住满几年？",
    "Einbürgerung（入籍）需要什么语言程度？",
    "我的 Ausländerbehörde（外国人管理局）在哪里？",
  ],
};

const vi: FollowUpMap = {
  buergergeld: [
    "Tôi có thể nhận bao nhiêu Grundsicherungsgeld (tiền bảo đảm cơ bản)?",
    "Cần những giấy tờ gì để nộp đơn?",
    "Jobcenter (trung tâm việc làm) phụ trách tôi ở đâu?",
  ],
  kindergeld: [
    "Kindergeld (tiền trẻ em) mỗi con được bao nhiêu?",
    "Tôi có thể nhận Kindergeld (tiền trẻ em) truy lĩnh không?",
    "Familienkasse (quỹ gia đình) phụ trách tôi ở đâu?",
  ],
  "familie-und-kinder": [
    "Tôi có thể nhận bao nhiêu Elterngeld (trợ cấp cha mẹ)?",
    "Hạn chót nộp đơn Elterngeld (trợ cấp cha mẹ) là khi nào?",
    "Elterngeldstelle (văn phòng trợ cấp cha mẹ) phụ trách tôi ở đâu?",
  ],
  arbeitslos: [
    "Tôi được nhận Arbeitslosengeld (trợ cấp thất nghiệp) trong bao lâu?",
    "Khi nào và làm sao tôi phải đăng ký thất nghiệp?",
    "Agentur für Arbeit (sở lao động) của tôi ở đâu?",
  ],
  rente: [
    "Tôi có thể mong đợi bao nhiêu Rente (lương hưu)?",
    "Khi nào và làm sao để nộp đơn xin Rente (lương hưu)?",
    "Văn phòng tư vấn Rentenversicherung (bảo hiểm hưu trí) gần tôi ở đâu?",
  ],
  wohngeld: [
    "Tôi có thể nhận bao nhiêu Wohngeld (trợ cấp nhà ở)?",
    "Cần những giấy tờ gì để xin Wohngeld (trợ cấp nhà ở)?",
    "Wohngeldstelle (văn phòng trợ cấp nhà ở) phụ trách tôi ở đâu?",
  ],
  steuern: [
    "Tôi tìm Steuer-ID (mã số thuế) của mình ở đâu?",
    "Tôi mới đến Đức — làm sao để nhận Steuer-ID (mã số thuế)?",
    "Finanzamt (sở thuế) phụ trách tôi ở đâu?",
  ],
  aufenthalt: [
    "Tôi phải sống ở Đức bao nhiêu năm để được Einbürgerung (nhập quốc tịch)?",
    "Cần trình độ tiếng Đức nào cho Einbürgerung (nhập quốc tịch)?",
    "Ausländerbehörde (sở ngoại kiều) phụ trách tôi ở đâu?",
  ],
};

const id: FollowUpMap = {
  buergergeld: [
    "Berapa Grundsicherungsgeld (jaminan dasar) yang bisa saya dapat?",
    "Dokumen apa saja yang diperlukan untuk pengajuan?",
    "Di mana Jobcenter (pusat kerja) yang berwenang untuk saya?",
  ],
  kindergeld: [
    "Berapa Kindergeld (tunjangan anak) per anak?",
    "Bisakah saya mendapat Kindergeld (tunjangan anak) secara surut?",
    "Di mana Familienkasse (kas keluarga) yang berwenang untuk saya?",
  ],
  "familie-und-kinder": [
    "Berapa Elterngeld (tunjangan orang tua) yang bisa saya dapat?",
    "Kapan batas waktu pengajuan Elterngeld (tunjangan orang tua)?",
    "Di mana Elterngeldstelle (kantor tunjangan orang tua) yang berwenang untuk saya?",
  ],
  arbeitslos: [
    "Berapa lama saya bisa menerima Arbeitslosengeld (tunjangan pengangguran)?",
    "Kapan dan bagaimana saya harus mendaftar sebagai pengangguran?",
    "Di mana Agentur für Arbeit (kantor tenaga kerja) saya?",
  ],
  rente: [
    "Berapa Rente (pensiun) yang bisa saya harapkan?",
    "Kapan dan bagaimana saya mengajukan Rente (pensiun)?",
    "Di mana kantor konsultasi Rentenversicherung (asuransi pensiun) terdekat?",
  ],
  wohngeld: [
    "Berapa Wohngeld (tunjangan perumahan) yang bisa saya dapat?",
    "Dokumen apa saja untuk pengajuan Wohngeld (tunjangan perumahan)?",
    "Di mana Wohngeldstelle (kantor tunjangan perumahan) yang berwenang untuk saya?",
  ],
  steuern: [
    "Di mana saya menemukan Steuer-ID (nomor pajak) saya?",
    "Saya baru di Jerman — bagaimana mendapatkan Steuer-ID (nomor pajak)?",
    "Di mana Finanzamt (kantor pajak) yang berwenang untuk saya?",
  ],
  aufenthalt: [
    "Berapa tahun saya harus tinggal di Jerman untuk Einbürgerung (kewarganegaraan)?",
    "Tingkat bahasa apa yang diperlukan untuk Einbürgerung (kewarganegaraan)?",
    "Di mana Ausländerbehörde (kantor imigrasi) yang berwenang untuk saya?",
  ],
};

const ko: FollowUpMap = {
  buergergeld: [
    "Grundsicherungsgeld(기초 생활 보장금)는 얼마나 받을 수 있나요?",
    "신청에는 어떤 서류가 필요한가요?",
    "제 담당 Jobcenter(고용 센터)는 어디에 있나요?",
  ],
  kindergeld: [
    "Kindergeld(아동 수당)는 아이 한 명당 얼마인가요?",
    "Kindergeld(아동 수당)를 소급해서 받을 수 있나요?",
    "제 담당 Familienkasse(가족 수당 사무소)는 어디에 있나요?",
  ],
  "familie-und-kinder": [
    "Elterngeld(부모 수당)는 얼마나 받을 수 있나요?",
    "Elterngeld(부모 수당)는 언제까지 신청해야 하나요?",
    "제 담당 Elterngeldstelle(부모 수당 사무소)는 어디에 있나요?",
  ],
  arbeitslos: [
    "Arbeitslosengeld(실업 급여)는 얼마나 오래 받을 수 있나요?",
    "실업 상태가 되면 언제, 어떻게 등록해야 하나요?",
    "제 Agentur für Arbeit(고용청)는 어디에 있나요?",
  ],
  rente: [
    "제 Rente(연금)는 얼마나 될까요?",
    "Rente(연금)는 언제, 어떻게 신청해야 하나요?",
    "근처의 Rentenversicherung(연금 보험) 상담소는 어디에 있나요?",
  ],
  wohngeld: [
    "Wohngeld(주거 보조금)는 얼마나 받을 수 있나요?",
    "Wohngeld(주거 보조금) 신청에는 어떤 서류가 필요한가요?",
    "제 담당 Wohngeldstelle(주거 보조금 사무소)는 어디에 있나요?",
  ],
  steuern: [
    "제 Steuer-ID(세금 식별 번호)는 어디에서 찾을 수 있나요?",
    "독일에 처음 왔는데 Steuer-ID(세금 식별 번호)는 어떻게 받나요?",
    "제 담당 Finanzamt(세무서)는 어디에 있나요?",
  ],
  aufenthalt: [
    "Einbürgerung(귀화)을 위해 독일에 몇 년 살아야 하나요?",
    "Einbürgerung(귀화)에는 어떤 어학 수준이 필요한가요?",
    "제 담당 Ausländerbehörde(외국인청)는 어디에 있나요?",
  ],
};

export const FOLLOW_UPS: Record<string, FollowUpMap> = {
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

export function getFollowUps(language: string, topic: string): string[] {
  const map = FOLLOW_UPS[language] ?? FOLLOW_UPS.de;
  return map[topic] ?? [];
}
