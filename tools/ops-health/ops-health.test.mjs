// Ops Health (PR-1) static + behavioural tests. Zero dependencies.
// Run from the repo root:  node --test tools/ops-health/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const FILES = {
  monitor: path.join(ROOT, 'workflows/ops/health-monitor.json'),
  handler: path.join(ROOT, 'workflows/ops/global-error-handler.json'),
  heartbeat: path.join(ROOT, 'workflows/heartbeat-check.json'),
};
const load = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const monitor = load(FILES.monitor);
const handler = load(FILES.handler);
const heartbeat = load(FILES.heartbeat);
const all = [monitor, handler];
const PLACEHOLDER_CHAT = 'REPLACE_WITH_TELEGRAM_CHAT_ID';
const EXPECTED = ['Heartbeat Check', 'GitHub AI Assistant', 'MCP server', 'Telegram Approval', 'Global Error Handler'];

const ALLOWED_TYPES = new Set([
  'n8n-nodes-base.scheduleTrigger',
  'n8n-nodes-base.errorTrigger',
  'n8n-nodes-base.set',
  'n8n-nodes-base.httpRequest',
  'n8n-nodes-base.code',
  'n8n-nodes-base.telegram',
]);
const LLM_TYPE = /langchain|openai|anthropic|gemini|mistral|ollama|groq|perplexity|deepseek|openrouter|cohere|huggingface|lmchat|agent/i;
const LLM_HOST = /api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|openrouter\.ai|api\.mistral\.ai|api\.groq\.com|api\.deepseek\.com|api\.cohere\.|api-inference\.huggingface\.co|\/v1\/chat\/completions|\/v1\/messages|\/v1\/completions/i;
const SECRET = /ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{16,}|\d{6,12}:[A-Za-z0-9_-]{30,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.|bearer\s+[A-Za-z0-9._~+\/=-]{16,}/i;

const node = (wf, name) => wf.nodes.find((n) => n.name === name);
const codeOf = (wf, name) => node(wf, name).parameters.jsCode;

// ---- Code-node harness (simulates the n8n sandbox helpers) ----
function runCode(code, { nodes = {}, input = [], executed = [], state = {}, now }) {
  const RealDate = Date;
  class FakeDate extends RealDate {
    constructor(...a) { super(...(a.length ? a : [now])); }
    static now() { return now; }
  }
  const $ = (name) => {
    if (!(name in nodes) && !executed.includes(name)) throw new Error('Node not executed: ' + name);
    return { first: () => (nodes[name] === undefined ? undefined : { json: nodes[name] }), isExecuted: executed.includes(name) };
  };
  const $input = { all: () => input.map((json) => ({ json })) };
  const fn = new Function('$', '$input', '$getWorkflowStaticData', 'Date', code);
  return fn($, $input, () => state, FakeDate).map((i) => i.json);
}

const T0 = Date.parse('2026-11-25T09:45:00Z');
const MIN = 60000;
const cfg = {
  n8n_base_url: 'http://127.0.0.1:5680',
  expected_workflows: ['Heartbeat Check', 'Telegram Approval'],
  heartbeat_workflow_name: 'Heartbeat Check',
  heartbeat_max_age_minutes: 30,
  failure_lookback_minutes: 15,
  suppress_hours: 2,
  telegram_chat_id: PLACEHOLDER_CHAT,
};
const okResp = (body) => ({ statusCode: 200, body });
// Production Config as exported (heartbeat check disabled until a heartbeat workflow exists).
const prodCfg = Object.fromEntries(node(monitor, 'Config').parameters.assignments.assignments.map((a) => [a.name, a.type === 'array' ? JSON.parse(a.value) : a.value]));
function signals(now, { hbAgeMin = 5, failures = [], apiDown = false, inactive = [], config = cfg, noHeartbeatWf = false, extraWfs = [] } = {}) {
  const wfs = [
    { id: 'hb1', name: 'Heartbeat Check', active: !inactive.includes('Heartbeat Check'), settings: { errorWorkflow: 'geh' } },
    { id: 'ta1', name: 'Telegram Approval', active: !inactive.includes('Telegram Approval'), settings: { errorWorkflow: 'geh' } },
    { id: 'u1', name: 'Uncovered', active: true, settings: {} },
    ...extraWfs.map((name, i) => ({ id: 'x' + i, name, active: !inactive.includes(name), settings: { errorWorkflow: 'geh' } })),
  ].filter((w) => !(noHeartbeatWf && w.id === 'hb1'));
  return {
    Config: config,
    'Check API Health': apiDown ? { error: { message: 'connect ECONNREFUSED' } } : okResp({ status: 'ok' }),
    'Get Workflows': apiDown ? { error: { message: 'connect ECONNREFUSED' } } : okResp({ data: wfs }),
    'Get Failed Executions': apiDown ? { error: { message: 'connect ECONNREFUSED' } } : okResp({ data: failures }),
    'Get Heartbeat Executions': apiDown ? { error: { message: 'connect ECONNREFUSED' } } : okResp({ data: [{ id: '1', workflowId: 'hb1', status: 'success', startedAt: new Date(now - hbAgeMin * MIN).toISOString(), stoppedAt: new Date(now - hbAgeMin * MIN).toISOString() }] }),
  };
}
const runMonitor = (now, opts, state, summary = false) =>
  runCode(codeOf(monitor, 'Evaluate Health'), { nodes: signals(now, opts), state, now, executed: summary ? ['Daily 08:00 Summary'] : ['Every 15 Minutes'] });

// ---------------- Static checks ----------------
test('both workflows are inactive on import ("active": false)', () => {
  for (const wf of all) assert.equal(wf.active, false, wf.name);
});

test('only allow-listed node types are used', () => {
  for (const wf of all) for (const n of wf.nodes) assert.ok(ALLOWED_TYPES.has(n.type), wf.name + ': ' + n.type);
});

test('T0: no LLM node and no LLM endpoint anywhere', () => {
  for (const wf of all) {
    for (const n of wf.nodes) assert.ok(!LLM_TYPE.test(n.type), wf.name + ': LLM node ' + n.type);
    assert.ok(!LLM_HOST.test(JSON.stringify(wf)), wf.name + ': LLM endpoint referenced');
  }
});

test('all HTTP requests are GET only', () => {
  const http = monitor.nodes.filter((n) => n.type === 'n8n-nodes-base.httpRequest');
  assert.ok(http.length >= 4);
  for (const wf of all) for (const n of wf.nodes.filter((x) => x.type === 'n8n-nodes-base.httpRequest')) {
    assert.equal(n.parameters.method, 'GET', n.name);
  }
});

test('n8n API calls use the n8nApi credential and never embed a key', () => {
  for (const n of monitor.nodes.filter((x) => x.type === 'n8n-nodes-base.httpRequest' && /\/api\/v1\//.test(x.parameters.url))) {
    assert.equal(n.parameters.nodeCredentialType, 'n8nApi', n.name);
    assert.ok(!n.parameters.sendHeaders, n.name + ' must not send manual headers');
  }
});

test('no secrets committed in workflow files', () => {
  for (const f of Object.values(FILES)) assert.ok(!SECRET.test(fs.readFileSync(f, 'utf8')), f);
});

test('Telegram chat id and credential id are placeholders in committed files', () => {
  assert.equal(node(handler, 'Send Error Alert').parameters.chatId, PLACEHOLDER_CHAT);
  assert.equal(prodCfg.telegram_chat_id, PLACEHOLDER_CHAT);
  for (const wf of all) for (const n of wf.nodes.filter((x) => x.credentials && x.credentials.telegramApi)) {
    assert.equal(n.credentials.telegramApi.id, 'REPLACE_ME', wf.name + ': ' + n.name);
  }
  assert.equal(prodCfg.n8n_base_url, 'http://127.0.0.1:5680');
});

test('every workflow file carries a Tier: T0 note in its description', () => {
  for (const wf of [monitor, handler, heartbeat]) assert.match(String(wf.description || ''), /^Tier: T0\b/, wf.name);
});

test('monitor schedules: every 15 minutes + daily 08:00 Asia/Riyadh', () => {
  assert.equal(monitor.settings.timezone, 'Asia/Riyadh');
  const every = node(monitor, 'Every 15 Minutes').parameters.rule.interval[0];
  assert.deepEqual([every.field, every.minutesInterval], ['minutes', 15]);
  const daily = node(monitor, 'Daily 08:00 Summary').parameters.rule.interval[0];
  assert.deepEqual([daily.field, daily.triggerAtHour, daily.triggerAtMinute ?? 0], ['days', 8, 0]);
});

// ---------------- Redaction ----------------
const SAMPLE_SECRETS = [
  'ghp_abcdefghijklmnopqrstuvwxyz0123456789',
  'github_pat_11ABCDEFG0123456789_abcdefghijklmnop',
  'sk-proj-abcdefghijklmnopqrstuvwx',
  '1234567890:AAHabcdefghijklmnopqrstuvwxyz012345',
  'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.abcdefghijk',
];

test('Global Error Handler redacts secrets and includes required fields', () => {
  const msg = 'Auth failed: Authorization: Bearer abcdefghijklmnop12345 api_key=SuperSecret123 ' + SAMPLE_SECRETS.join(' ') + ' https://user:pa55word@host/x <tag>';
  const [out] = runCode(codeOf(handler, 'Format Error Alert'), {
    now: T0,
    input: [{ execution: { id: '777', error: { message: msg }, lastNodeExecuted: 'HTTP Request', mode: 'trigger' }, workflow: { id: 'w1', name: 'Payments Sync' } }],
  });
  for (const s of SAMPLE_SECRETS.concat(['abcdefghijklmnop12345', 'SuperSecret123', 'pa55word'])) assert.ok(!out.text.includes(s), 'leaked: ' + s);
  assert.match(out.text, /Payments Sync/);
  assert.match(out.text, /#777/);
  assert.match(out.text, /2026-11-25 12:45 \(الرياض\)/);
  assert.match(out.text, /&lt;tag&gt;/);
});

test('Global Error Handler handles trigger failures without an execution id', () => {
  const [out] = runCode(codeOf(handler, 'Format Error Alert'), {
    now: T0,
    input: [{ trigger: { error: { message: 'token=abc123secret' } }, workflow: { id: 'w2', name: 'Poller' } }],
  });
  assert.match(out.text, /Poller/);
  assert.ok(!out.text.includes('abc123secret'));
});

// ---------------- Global Error Handler: 2h dedup + 6/hour cap ----------------
const gehErr = (wfId, nodeName, message, execId) => ({ execution: { id: String(execId || 1), error: { message }, lastNodeExecuted: nodeName, mode: 'trigger' }, workflow: { id: wfId, name: 'WF ' + wfId } });
const geh = (state, now, ...items) => runCode(codeOf(handler, 'Format Error Alert'), { now, state, input: items });

test('handler mutes the same error for 2 hours, then reports the repeat count', () => {
  const st = {};
  assert.equal(geh(st, T0, gehErr('w1', 'HTTP', 'timeout after 3000 ms', 11)).length, 1);
  assert.equal(geh(st, T0 + 10 * MIN, gehErr('w1', 'HTTP', 'timeout after 5000 ms', 12)).length, 0);
  assert.equal(geh(st, T0 + 119 * MIN, gehErr('w1', 'HTTP', 'timeout after 7000 ms', 13)).length, 0);
  const [again] = geh(st, T0 + 121 * MIN, gehErr('w1', 'HTTP', 'timeout after 9000 ms', 14));
  assert.match(again.text, /#14/);
  assert.match(again.text, /تكرر: 2 مرة/);
});

test('handler dedup key ignores numbers and long ids but not workflow, node or text', () => {
  const st = {};
  assert.equal(geh(st, T0, gehErr('w1', 'HTTP', 'record a1b2c3d4e5f6a7b8 not found (row 42)')).length, 1);
  assert.equal(geh(st, T0 + MIN, gehErr('w1', 'HTTP', 'record 9f8e7d6c5b4a3f2e not found (row 7)')).length, 0);
  assert.equal(geh(st, T0 + MIN, gehErr('w2', 'HTTP', 'record a1b2c3d4e5f6a7b8 not found (row 42)')).length, 1);
  assert.equal(geh(st, T0 + MIN, gehErr('w1', 'Code', 'record a1b2c3d4e5f6a7b8 not found (row 42)')).length, 1);
  assert.equal(geh(st, T0 + MIN, gehErr('w1', 'HTTP', 'permission denied')).length, 1);
});

test('handler caps alerts at 6 per hour, then reports how many were muted', () => {
  const st = {};
  let sent = 0;
  for (let i = 0; i < 9; i++) sent += geh(st, T0 + i * MIN, gehErr('w' + i, 'N', 'distinct failure ' + 'abcdefghi'[i])).length;
  assert.equal(sent, 6);
  const out = geh(st, T0 + 61 * MIN, gehErr('wz', 'N', 'another failure'));
  assert.equal(out.length, 2);
  assert.match(out[0].text, /^3 تنبيهات إضافية مكتومة/);
  assert.match(out[1].text, /WF wz/);
  assert.equal(geh(st, T0 + 62 * MIN, gehErr('wy', 'N', 'yet another')).length, 1, 'muted count resets after it is reported');
});

test('handler forgets dedup entries after 24 hours', () => {
  const st = {};
  geh(st, T0, gehErr('w1', 'HTTP', 'boom'));
  geh(st, T0 + 25 * 60 * MIN, gehErr('w9', 'HTTP', 'other'));
  assert.deepEqual(Object.keys(st.errors).filter((k) => k.startsWith('w1|')), []);
});

test('monitor redacts secrets in alert text', () => {
  const state = {};
  const out = runMonitor(T0, { apiDown: true }, state);
  // inject a secret through the API error message path
  const nodes = signals(T0, {});
  nodes['Check API Health'] = { error: { message: 'failed with ' + SAMPLE_SECRETS[0] } };
  const out2 = runCode(codeOf(monitor, 'Evaluate Health'), { nodes, state: {}, now: T0, executed: ['Every 15 Minutes'] });
  assert.equal(out.length, 1);
  assert.ok(!out2[0].text.includes(SAMPLE_SECRETS[0]));
});

// Telegram token embedded in a bot URL (no word boundary between "bot" and the digits).
const BOT_URL_TOKEN = '1234567890:AAHabcdefghijklmnopqrstuvwxyz012345';
const BOT_URL = 'https://api.telegram.org/bot' + BOT_URL_TOKEN + '/sendMessage';

test('handler redacts a Telegram token inside a bot<token> URL', () => {
  const [out] = runCode(codeOf(handler, 'Format Error Alert'), {
    now: T0,
    input: [{ execution: { id: '901', error: { message: 'request to ' + BOT_URL + ' failed' }, lastNodeExecuted: 'Send', mode: 'trigger' }, workflow: { id: 'wtok', name: 'Token URL' } }],
  });
  assert.ok(!out.text.includes(BOT_URL_TOKEN), 'token leaked');
  assert.ok(!out.text.includes('AAHabcdefghijklmnopqrstuvwxyz012345'), 'token secret part leaked');
  assert.match(out.text, /bot\[REDACTED_TELEGRAM_TOKEN\]/);
});

test('monitor redacts a Telegram token inside a bot<token> URL', () => {
  const nodes = signals(T0, {});
  nodes['Check API Health'] = { error: { message: 'request to ' + BOT_URL + ' failed' } };
  const out = runCode(codeOf(monitor, 'Evaluate Health'), { nodes, state: {}, now: T0, executed: ['Every 15 Minutes'] });
  assert.equal(out.length, 1);
  assert.ok(!out[0].text.includes(BOT_URL_TOKEN), 'token leaked');
  assert.match(out[0].text, /bot\[REDACTED_TELEGRAM_TOKEN\]/);
});

test('committed-secret scanner catches a token inside a bot<token> URL', () => {
  assert.ok(SECRET.test(BOT_URL));
});

// ---------------- Behaviour: alerts, 2h suppression, recovery ----------------
test('healthy system sends nothing on the 15-minute check', () => {
  assert.deepEqual(runMonitor(T0, {}, {}), []);
});

test('stale heartbeat, inactive workflow, uncovered failure and API outage raise alerts', () => {
  const fail = [{ id: '900', workflowId: 'u1', status: 'error', startedAt: new Date(T0 - 5 * MIN).toISOString() }];
  const covered = [{ id: '901', workflowId: 'hb1', status: 'error', startedAt: new Date(T0 - 5 * MIN).toISOString() }];
  const [a] = runMonitor(T0, { hbAgeMin: 45, failures: fail.concat(covered), inactive: ['Telegram Approval'] }, {});
  assert.equal(a.kind, 'alert');
  assert.match(a.text, /تأخرت النبضة/);
  assert.match(a.text, /غير مفعّل: Telegram Approval/);
  assert.match(a.text, /#900/);
  assert.ok(!a.text.includes('#901'), 'failure covered by an error workflow must not alert');
  const [b] = runMonitor(T0, { apiDown: true }, {});
  assert.match(b.text, /healthz/);
});

test('duplicate alerts are suppressed for 2 hours, then re-sent as a reminder', () => {
  const state = {};
  assert.equal(runMonitor(T0, { hbAgeMin: 45 }, state).length, 1);
  assert.deepEqual(runMonitor(T0 + 15 * MIN, { hbAgeMin: 60 }, state), []);
  assert.deepEqual(runMonitor(T0 + 119 * MIN, { hbAgeMin: 164 }, state), []);
  const [r] = runMonitor(T0 + 120 * MIN, { hbAgeMin: 165 }, state);
  assert.equal(r.kind, 'alert');
  assert.match(r.text, /تذكير/);
});

test('recovery message is sent once when the issue clears', () => {
  const state = {};
  runMonitor(T0, { hbAgeMin: 45 }, state);
  const [rec] = runMonitor(T0 + 15 * MIN, { hbAgeMin: 2 }, state);
  assert.equal(rec.kind, 'recovered');
  assert.match(rec.text, /تعافى/);
  assert.match(rec.text, /النبضة/);
  assert.deepEqual(runMonitor(T0 + 30 * MIN, { hbAgeMin: 2 }, state), []);
});

test('an API outage does not produce a false "recovered" for checks it could not run', () => {
  const state = {};
  runMonitor(T0, { hbAgeMin: 45 }, state);
  const out = runMonitor(T0 + 15 * MIN, { apiDown: true }, state);
  assert.ok(out.every((m) => m.kind !== 'recovered'));
  assert.ok(Object.keys(state.opsHealth.active).some((k) => k === 'hb:stale'));
});

test('approved Config: heartbeat check enabled on Heartbeat Check, five expected workflows', () => {
  assert.equal(prodCfg.heartbeat_workflow_name, 'Heartbeat Check');
  assert.deepEqual(prodCfg.expected_workflows, EXPECTED);
  assert.equal(Number(prodCfg.heartbeat_max_age_minutes), 30);
  assert.equal(Number(prodCfg.failure_lookback_minutes), 15);
  assert.equal(Number(prodCfg.suppress_hours), 2);
});

test('approved Config: no alert when all five workflows exist and are active, alert names a missing one', () => {
  const extra = EXPECTED.filter((n) => !['Heartbeat Check', 'Telegram Approval'].includes(n));
  assert.deepEqual(runMonitor(T0, { config: prodCfg, extraWfs: extra }, {}), []);
  const [a] = runMonitor(T0, { config: prodCfg, extraWfs: extra.filter((n) => n !== 'MCP server') }, {});
  assert.equal(a.kind, 'alert');
  assert.match(a.text, /MCP server/);
  const [b] = runMonitor(T0, { config: prodCfg, extraWfs: extra, hbAgeMin: 45 }, {});
  assert.match(b.text, /تأخرت النبضة/);
});

test('with heartbeat disabled (empty name): no heartbeat alert, summary says disabled', () => {
  const disabled = { ...prodCfg, heartbeat_workflow_name: '', expected_workflows: ['Telegram Approval'] };
  const opts = { config: disabled, noHeartbeatWf: true, hbAgeMin: 999 };
  assert.deepEqual(runMonitor(T0, opts, {}), []);
  const [s] = runMonitor(T0, opts, {}, true);
  assert.match(s.text, /كل الفحوصات سليمة/);
  assert.match(s.text, /النبضة: معطّلة/);
  assert.ok(!/Heartbeat Check/.test(s.text));
});

test('daily 08:00 summary is always sent and does not change suppression state', () => {
  const state = {};
  const [s1] = runMonitor(T0, {}, state, true);
  assert.equal(s1.kind, 'summary');
  assert.match(s1.text, /كل الفحوصات سليمة/);
  const [s2] = runMonitor(T0, { hbAgeMin: 45 }, state, true);
  assert.match(s2.text, /مشكلة قائمة/);
  assert.deepEqual(state, {});
});

// ---------------- Public-repo hygiene: no real IPs or Telegram chat ids in ANY file ----------------
// Pattern-based detection only: no real values and no fingerprints of real values are stored in this repo.
const SKIP_DIRS = new Set(['.git', 'node_modules']);
const TEXT_EXT = /\.(json|md|mjs|cjs|js|ts|mts|ya?ml|txt|env|ini|conf|cfg|toml|sh|html|csv|example)$/i;
const IPV4 = /(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])/g;
const IP_ALLOWED = (ip) => /^127\./.test(ip) || ip === '0.0.0.0' || /^(192\.0\.2|198\.51\.100|203\.0\.113)\./.test(ip);
const CHAT_KEY = /["']?(?:chat_?id|telegram_chat_id|chatId)["']?\s*[:=]\s*["']?-?\d{5,}/gi;

export function findLeaks(text) {
  const out = [];
  for (const m of text.matchAll(IPV4)) if (!IP_ALLOWED(m[0])) out.push('ipv4');
  for (const _ of text.matchAll(CHAT_KEY)) out.push('telegram-chat-id');
  return out;
}
function listFiles(dir) {
  const res = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) { if (!SKIP_DIRS.has(e.name)) res.push(...listFiles(path.join(dir, e.name))); }
    else if (TEXT_EXT.test(e.name) || !e.name.includes('.')) res.push(path.join(dir, e.name));
  }
  return res;
}

test('leak detector catches synthetic samples and ignores placeholders', () => {
  const ip = ['8', '8', '4', '4'].join('.');
  assert.deepEqual(findLeaks('url: http://' + ip + ':5680'), ['ipv4']);
  assert.ok(findLeaks('"chatId": "' + '9'.repeat(9) + '"').includes('telegram-chat-id'));
  assert.ok(findLeaks('chat_id=-' + '1'.repeat(12)).includes('telegram-chat-id'));
  assert.deepEqual(findLeaks('"chatId": "' + PLACEHOLDER_CHAT + '" http://localhost:5680 http://127.0.0.1:5680 typeVersion 1.2'), []);
});

test('no real IP address or Telegram chat id in any repository file', () => {
  const files = listFiles(ROOT);
  assert.ok(files.length >= 5);
  const bad = [];
  for (const f of files) {
    const kinds = findLeaks(fs.readFileSync(f, 'utf8'));
    if (kinds.length) bad.push(path.relative(ROOT, f) + ' -> ' + [...new Set(kinds)].join(','));
  }
  assert.deepEqual(bad, [], 'remove real values (reported by file and kind only):\n' + bad.join('\n'));
});
