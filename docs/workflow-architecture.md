# هيكلة سير العمل – الشركة الافتراضية (n8n Virtual Company)

> ملخص معماري للمشروع وبوابة الموافقة التنفيذية. مبني على الرسم المعرفي (Graphify) لسير عمل n8n الحالية.

## 1. فكرة الشركة الافتراضية

الشركة الافتراضية مجموعة من سير عمل n8n تعمل كـ«أقسام» مؤتمتة، ويتولى وكلاء ذكاء اصطناعي (AI Agents) التحليل واتخاذ القرارات التشغيلية. المدير التنفيذي (CEO) هو صاحب القرار النهائي في الإجراءات الحساسة.

## 2. سير العمل الرئيسية

### أ) قسم التداول والإشارات (Workflow `oISSqKWtxkFT98zK`)

مسار من عدة طبقات، كل طبقة بوابة (Gate) تصفّي الإشارات قبل الوصول للتنفيذ:

1. **جلب البيانات:** `MT5 Price Feed` + استخراج الصفقات المغلقة (`Extract Closed Deals` / `Save Closed Deal`).
2. **الفلترة بالقواعد:** `Rule Filter` ثم `Passes Filter` (رفض مبكر مع `Log Filter Reject`).
3. **حالة المخاطر:** `Load Risk State` (وفي حال عدم توفرها `Risk State Unavailable`).
4. **الفرز الأولي بالذكاء الاصطناعي:** `DeepSeek Screener` + `DeepSeek Gate` + `Is Flagged`.
5. **وكيل التحليل:** `AI Agent` (نموذج Claude، مع أداة أخبار `yahoo_news_mcp`).
6. **بوابة الأمان (Safety Gate) وفحص المخاطر:** `Risk Check`، `Decide Batch Risk`، `Batch Risk OK`.
7. **منع التكرار (Locks):** `Claim Send Lock` → `Get Send Locks` → `Decide Lock Winner` → `Is First Claim`، مع `Release Rejected Lock` عند الرفض.
8. **التنفيذ والإشعار:** `HTTP Request1` ثم `Log Sent Trade` و`Notify Trade` (Telegram).
9. **التنبيهات:** `Market Data Missing?` → `Alert Market Data Missing` (Telegram).

### ب) قسم البنية التحتية والنسخ الاحتياطي (Workflow `rvF54qkfmXin7Sv4`)

- مشغّل `Every 6 Hours`.
- `Backup Workflows & DB` و`Update Knowledge Graph` (Execute Command) لتحديث النسخ الاحتياطية والرسم المعرفي دورياً.

## 3. بوابة الموافقة التنفيذية (Executive Approval Gate)

أي إجراء حساس على GitHub يمر عبر موافقة المدير التنفيذي عبر Telegram قبل التنفيذ.

**الإجراءات الخاضعة للبوابة:**
- إنشاء أو تعديل ملفات على فرع `main`.
- فتح أو دمج أي Pull Request.

**آلية العمل:**
1. يستدعي الوكيل الأداة `request_ceo_approval` مع: `action_title`، `repository`، `branch`، `details`.
2. يُرسل Sub-workflow طلب الموافقة إلى المدير التنفيذي على Telegram ويتوقف مؤقتاً بانتظار الرد.
3. عند الانتظار يتوقف الوكيل ولا يكرر الطلب، ويُبلغ المستخدم بأن الطلب بانتظار التأكيد.
4. لا يُنفّذ الإجراء إلا بعد `status: APPROVED`. عند الرفض يُلغى الإجراء فوراً.

**تدفق التفرّع (Branching):**

```
تعديل على dev  ──►  request_ceo_approval (Telegram)  ──►  APPROVED؟  ──►  فتح PR: dev → main
                                                        └─ مرفوض ──►  إلغاء
```

- التعديلات الأولية تتم على `dev` (لا تتطلب موافقة).
- فتح PR نحو `main` يتطلب موافقة مسبقة.

## 4. ملاحظات

- الرسم المعرفي يُحدَّث كل 6 ساعات عبر قسم البنية التحتية.
- هذا المستند ملخص؛ المرجع الأدق هو تعريفات سير العمل نفسها في n8n.
