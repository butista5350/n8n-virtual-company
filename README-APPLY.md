# حزمة PR-0 وPR-1: خطوات التطبيق

**المستودع:** `butista5350/n8n-virtual-company` | **الفرع:** `dev` | **التاريخ:** 2026-11-25

```
pr-package/
├── README-APPLY.md                       هذا الملف
├── PR-0/
│   ├── PR-0.md                           وصف الـPR (يُلصق عند فتحه)
│   ├── org/company-structure-and-rbac.md ← v1.2 (53 مقعداً، 12 مفعّلاً، سياسة توجيه النماذج)
│   └── docs/runbooks/README.md
└── PR-1/
    ├── PR-1.md                           وصف الـPR
    ├── workflows/ops/health-monitor.json
    ├── workflows/ops/global-error-handler.json
    ├── docs/runbooks/health-monitor.md
    └── tools/ops-health/                 (مصادر، بناء، 36 اختباراً)
```

القاعدة: **لا إنشاء ولا رفع ولا فتح PR إلا بعد موافقتك عبر `request_ceo_approval`.** لكل حزمة طلب موافقة مستقل.

---

## الخطوة 0: متطلبات قبل أي رفع

| # | المتطلب | لـ |
|---|---|---|
| 1 | Fine-grained Token + حماية `main` (القسم 11 من ملف الهيكل) | PR-0 |
| 2 | اعتماد `n8n API (monitor)` (Header Auth: `X-N8N-API-KEY`) | PR-1 |
| 3 | اعتماد Telegram ومعرّف محادثتك | PR-1 |
| 4 | التحقق من عنوان n8n من داخل n8n (Docker؟) | PR-1 |

تنفيذ (1) يفضَّل **قبل** PR-0 لتُطبَّق الحماية من أول دمج.

---

## الخطوة 1: PR-0

### 1.1 طلب الموافقة (الصيغة المعتمدة)

```
🔒 طلب موافقة #PR-0
الموظف: مهندس مسارات n8n (بتكليف من مدير العمليات)
الإجراء: إنشاء ملفين على فرع dev ثم فتح PR إلى main
الأصل: org/company-structure-and-rbac.md ، docs/runbooks/README.md (فرع dev)
الأثر: ملف سياسة ومرجع فقط، بلا أثر تشغيلي على أي مسار
الكلفة: 0$
قابل للتراجع: نعم (حذف الملفين أو git revert)
معاينة: PR-0/PR-0.md
المهلة: 24 ساعة، وبعدها يُرفض تلقائياً
```

### 1.2 الأوامر (من جذر نسخة المستودع المحلية)

```bash
git fetch origin
git checkout dev && git pull origin dev

# انسخ محتوى PR-0 إلى جذر المستودع (بدون PR-0.md)
cp -r <مسار pr-package>/PR-0/org  <مسار pr-package>/PR-0/docs  .

git add org docs
git commit -F - <<'EOF'
docs(org): add company structure and RBAC v1.2

53 seats, 12 activated in phase 1, RBAC matrix, model routing policy,
spending and approval policy, KDP phase-1 decisions, and repository
hardening (fine-grained token and main protection).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fs5NxpHk9Nkuf9V8KqmLHP
EOF
git push origin dev
```

### 1.3 فتح الـPR وإغلاق الخطوة

1. افتح PR من `dev` إلى `main` والصق محتوى `PR-0.md` في الوصف.
2. ادمج بطريقة **Create a merge commit** (وليس Squash).
3. نفّذ اختبارات الإغلاق (القسم 11.3 من الملف) وسجّل نتيجتها.

---

## الخطوة 2: PR-1

### 2.1 طلب الموافقة

```
🔒 طلب موافقة #PR-1
الموظف: مهندس مسارات n8n ومراقب الصحة والتنبيهات
الإجراء: إضافة مساري Ops Health Monitor وGlobal Error Handler (غير فعّالين عند الاستيراد)، وتوثيقهما وأدوات اختبارهما، على فرع dev ثم فتح PR
الأصل: workflows/ops/*.json ، docs/runbooks/health-monitor.md ، tools/ops-health/** (فرع dev)
الأثر: مسارا مراقبة للقراءة فقط (GET). لا تغيير على Heartbeat Check أو أي مسار قائم
الكلفة: 0$
قابل للتراجع: نعم (تعطيل المسارين ثم git revert)
معاينة: PR-1/PR-1.md
المهلة: 24 ساعة، وبعدها يُرفض تلقائياً
```

### 2.2 رفع الملفات على `dev`

```bash
git checkout dev && git pull origin dev
cp -r <مسار pr-package>/PR-1/workflows  <مسار pr-package>/PR-1/docs  <مسار pr-package>/PR-1/tools  .

# تحقق قبل الـcommit: يجب أن تنتهي بـ pass 36 / fail 0
node tools/ops-health/tests/run-tests.mjs 2>&1 | grep -E "^# (pass|fail)"

git add workflows docs tools
git commit -F - <<'EOF'
feat(ops): add Ops Health Monitor and Global Error Handler workflows

Read-only health checks every 15 minutes plus an 08:00 Riyadh summary,
and an immediate error alert workflow. Secrets redacted, repeats muted
for 2h, recovery notices, 33 automated tests.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Fs5NxpHk9Nkuf9V8KqmLHP
EOF
git push origin dev
```

### 2.3 التطبيق على n8n

اتبع `docs/runbooks/health-monitor.md` بالترتيب: القسم 2 (المتطلبات)، ثم 3 (التفعيل: استيراد، ربط الاعتمادات، ضبط `Config`، اختبار الملخص، التفعيل، ربط المعالج)، ثم 4 (اختبارات القبول 1 إلى 10).

### 2.4 الدمج

بعد نجاح اختبارات القبول ومراجعة مسؤول الأمن: افتح PR من `dev` إلى `main` بوصف `PR-1.md`، وادمج بـ**Create a merge commit**.

---

## ما لم يُتحقق منه (بصراحة)

- **استيراد JSON داخل n8n لم يُجرَّ**، فبيئة البناء بلا n8n. المنطق (كود العقد) والبنية مُختبران آلياً، لكن توافق `typeVersion` مع نسختك يظهر عند الاستيراد. إن ظهر خطأ فهو تعديل سطر واحد في `tools/ops-health/build.mjs` ثم إعادة `node tools/ops-health/build.mjs`.
- **إرسال Telegram الفعلي** وسلوك Static Data في الإنتاج يظهران في اختبارات القبول 1 إلى 5.

## بعد PR-1

PR-2 (`sub-approval-gate`) ثم PR-3: **مولّد Word Search** (تغيّر عن سودوكو بقرارك)، ثم PR-4 وPR-5 بحسب خطة العمل. سأحدّث خطة العمل بقراراتك الخمسة قبل PR-2. **كل مسار لاحق يلتزم بسياسة توجيه النماذج**: عقد T0 افتراضياً، وأي عقدة نموذج تعلن `Tier` وسقف الاستدعاءات وتُضبط أسماء النماذج في `Config` فقط.
