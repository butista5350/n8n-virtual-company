# دليل تشغيل مولّد Word Search (KDP)

**المقعد:** مؤلف الكتب ومدقق الجودة | **المستوى:** T0 (بلا نموذج ولا شبكة) | **الكلفة:** 0$

## 1. المتطلبات
- Python 3.9 أو أحدث، و`pip install reportlab pypdf` (pypdf للاختبارات فقط).
- نسخة من `tools/wordsearch/data/book.gardening.json` (الكتاب 1) خارج المستودع، تُعبَّأ فيها بيانات الناشر الحقيقية (اسم الناشر). لا تُرفع إلى المستودع.

## 2. التوليد
```bash
python3 tools/wordsearch/generate_book.py  --config <ملفك>.json --out output/interior.pdf   # 132 صفحة للكتاب 1
python3 tools/wordsearch/generate_cover.py --config <ملفك>.json --pages <عدد الصفحات المطبوع> --out output/cover.pdf
```
الناتج: `interior.pdf` (الداخل) و`cover.pdf` (غلاف كامل بعرض يحسب الكعب تلقائياً).

## 3. قبل الرفع (فحص بشري، 5 دقائق)
1. افتح `interior.pdf`: صفحة العنوان، صفحة الحقوق (اسم الناشر صحيح)، 3 ألغاز عشوائية، صفحتا حلول.
2. تأكد أن عدد صفحات الغلاف = عدد الصفحات المطبوع.
3. ارفع الملفين في KDP وانتظر المعاين (Previewer). يجب ألا تظهر تحذيرات هوامش أو bleed.
4. إن ظهر تحذير فسجّله وأخبر المدير التنفيذي. لا ترفع.

## 4. الرفع اليدوي على KDP (قرارك)
عنوان وكلمات مفتاحية ووصف: `docs/kdp/listing-draft-vol1.md`. التسعير بحاسبة KDP نفسها. الرفع والنشر قرار المدير العام وحده.

## 5. إضافة ألغاز أو أجزاء
- أضف قوائم في ملف المواضيع (`data/themes_gardening.json`: لكل موضوع 12 كلمة ونصيحة `fact` أصلية) ثم `python3 -m unittest discover -s tools/wordsearch/tests`.
- كتاب جديد بموضوع آخر (مثل Backyard Birds): انسخ `book.gardening.json` و`themes_gardening.json`، وغيّر `themes_file` و`cover` (العبارات والألوان وكلمات الشبكة التجريبية) و`fact_label`.

## 6. استكشاف الأعطال
| العَرَض | السبب | الحل |
|---|---|---|
| `could not build puzzle` | كلمات كثيرة طويلة | قلّل طول الكلمات أو غيّرها |
| تحذير هوامش في KDP | عدد الصفحات خارج 24–150 | عدّل `puzzle_count` |
| ModuleNotFoundError reportlab | غير مثبت | `pip install reportlab` |
