import { createClientFromRequest } from 'npm:@base44/sdk@0.8.31';

// ═══════════════════════════════════════════════════════════════════
// MINI-SHIMI CHAT v2.0 — Real AI (Google Gemini) + Lead Collection
// ═══════════════════════════════════════════════════════════════════
// מיני-שימי הוא החבר הכי טוב של הלקוח. חם, אמיתי, מקשיב.
// מופעל על ידי Google Gemini AI — תגובות אמיתיות, לא מוגדרות מראש.
// ═══════════════════════════════════════════════════════════════════

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Content-Type': 'application/json'
};

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY") || "YOUR_GEMINI_API_KEY_HERE";
const GEMINI_MODEL = "gemini-flash-lite-latest";

// ── מערכת הפרומפט של מיני-שימי ─────────────────────────────────────
const SYSTEM_PROMPT = `אתה מיני-שימי — הגרסה הקטנה של שימי שחי באתר. אתה החבר הכי טוב של הלקוח לענייני כסף.

## מי אתה
- שמך שימי. אתה החבר הכי טוב של הלקוח.
- חם, אמיתי, מקשיב, לא שיפוטי.
- מדבר כמו חבר — לא כמו יועץ או בנקאי.
- עברית טבעית, חמה, עם אופי. לא רשמי מדי. אבל גם לא סלנג כבד.

## מה אתה כן עושה
- מקשיב למצב הכלכלי של הלקוח
- מעודד, מכיל, מבין
- שואל שאלות פתוחות כדי להבין את המצב
- נותן תחושת "אתה לא לבד"
- מכווין להוריד את שימי ל-WhatsApp (למספר הטלפון)

## מה אתה לא עושה
- לא נותן עצות השקעות (מניות, קריפטו, נדל"ן, ביטקוין)
- לא נותן ייעוץ מס
- לא ממליץ על מוצרים פיננסיים ספציפיים
- לא מתחייב על תוצאות
- לא נותן מספרים מדויקים או חישובים מדויקים

## חוקי ברזל
1. עונה קצר — 1-3 משפטים בלבד. לא טקסטים ארוכים.
2. כשמישהו מספר על משכנתא/הלוואות → תגיד שיש מומחים שיכולים לעזור ותבקש מספר טלפון.
3. כשמישהו מספר על ניהול כלכלי/תקציב/חובות/מינוס → תציע להמשיך ב-WhatsApp ותבקש מספר טלפון.
4. אם מבקשים משהו שאתה לא יכול (השקעות, מס, ביטוח) → תגיד בכנות שאתה לא יכול, תבטיח להעביר ליוצרים ולעדכן תוך כמה ימים.
5. תוך 3-5 הודעות שיחה → תבקש מספר טלפון באופן טבעי.
6. אחרי שקיבלת טלפון → תבקש שם.
7. אחרי שקיבלת שם + טלפון → תגיד תודה חמה וסיים.
8. אם מסרבים לתת מספר → "אין בעיה בכלל, אני פה" ותמשיך שיחה רגילה.
9. אל תגיד שאתה AI או בוט. אתה שימי, החבר.
10. לא מציג את עצמך מחדש בכל הודעה — רק בהודעה הראשונה.

## דוגמאות
משתמש: "היי"
שימי: "היי! אני שימי 👋 נעים להכיר. מה שלומך? מה מטריד אותך?"

משתמש: "יש לי מינוס של 5000 שקל"
שימי: "אני שומע אותך. זה לא קל, ואתה לא לבד בזה. כמה זמן אתה במצב הזה?"

משתמש: "כמה חודשים כבר"
שימי: "מבין. שמע, יש שיטות לצאת מזה, אבל לפני שיטות צריך להבין לאן הכסף הולך. אני יכול לעזור לך עם זה באמת ב-WhatsApp — שם אני יכול ללוות אותך. מה המספר שלך?"

משתמש: "0521234567"
שימי: "מעולה! איך קוראים לך?"

משתמש: "דני"
שימי: "דני, תודה רבה! מישהו יחזור אליך בהקדם. אתה תצליח 💪"

משתמש: "איך להשקיע בביטקוין?"
שימי: "תשמע, את זה אני עדיין לא יכול לעזור — אני לא נותן עצות השקעות. אבל הבאת רעיון מעניין! אני אעביר את זה ליוצרים שלי ומבטיח לך שיבדקו את זה. יש משהו אחר שאוכל לעזור בו?"`;

// ── עזרים ──────────────────────────────────────────────────────────

function extractPhone(text) {
  // Israeli phone: 05X-XXXXXXX, 05XXXXXXXX, 972-5X-XXXXXXX, etc.
  const patterns = [
    /(\b0[5]\d[\-\s]?\d{3}[\-\s]?\d{4}\b)/,
    /(\b0[5]\d{8}\b)/,
    /(\b972[\-\s]?5\d[\-\s]?\d{3}[\-\s]?\d{4}\b)/,
    /(\b05\d[\-\s]?\d{3}[\-\s]?\d{4}\b)/
  ];
  for (const p of patterns) {
    const m = text.match(p);
    if (m) return m[1].replace(/[\-\s]/g, '');
  }
  return null;
}

function extractName(text) {
  // Hebrew names: 2-15 Hebrew letters, maybe with spaces
  // Only try if the message is short (likely a name response)
  if (text.length > 30) return null;
  const nameMatch = text.match(/^(?:קוראים לי\s+|שמי\s+|אני\s+)?([א-ת]{2,15}(?:\s+[א-ת]{2,15})?)$/);
  if (nameMatch) return nameMatch[1].trim();
  return null;
}

function isDecline(text) {
  return /לא|לא תודה|לא רוצה|לא מעוניין|עדיף לא|בסדר|אין צורך|אולי אחר כך|לא עכשיו/i.test(text.trim());
}

function isGreeting(text) {
  return /^(היי|הי|שלום|הלו|הילו|צאו|מה קורה|מה נשמע|בוקר טוב|ערב טוב|היי שימי)/i.test(text.trim());
}

// ── קריאה ל-Gemini API ─────────────────────────────────────────────

async function callGemini(message, history) {
  // Build conversation contents for Gemini
  const contents = [];

  for (const msg of history) {
    contents.push({
      role: msg.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: msg.content || msg.text || '' }]
    });
  }

  // Add current message
  contents.push({
    role: 'user',
    parts: [{ text: message }]
  });

  const body = {
    systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
    contents: contents,
    generationConfig: {
      temperature: 0.85,
      maxOutputTokens: 300,
      topP: 0.9
    }
  };

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Gemini API error: ${response.status} - ${error.substring(0, 200)}`);
  }

  const data = await response.json();

  if (!data.candidates || !data.candidates[0]) {
    throw new Error('No response from Gemini');
  }

  const text = data.candidates[0].content?.parts?.[0]?.text || '';
  if (!text) {
    // Maybe thinking tokens consumed everything - try again with higher limit
    throw new Error('Empty response from Gemini');
  }

  return text.trim();
}

// ── שמירת ליד ──────────────────────────────────────────────────────

async function saveLead(base44, name, phone, allUserMessages) {
  const summary = allUserMessages.slice(0, 3).join(' | ').substring(0, 500);

  // Determine lead type from conversation
  const allText = allUserMessages.join(' ');
  const isMortgageOrLoans = /משכנתא|הלווא|ריבית|בנק|איחוד הלוואות/i.test(allText);
  const leadType = isMortgageOrLoans ? 'am_financials' : 'shimi';
  const source = isMortgageOrLoans ? 'landing_page_am' : 'landing_page_shimi';
  const notes = 'ליד מצ׳את באתר. סוג: ' + (isMortgageOrLoans ? 'משכנתא/הלוואות (א.מ. פיננסים)' : 'ניהול כלכלי (שימי)') + '. תוכן: ' + summary;

  try {
    return await base44.asServiceRole.entities.Lead.create({
      name: name,
      phone: phone,
      source: source,
      stage: 'new_lead',
      notes: notes,
      client_choice: isMortgageOrLoans ? 'משכנתא/הלוואות' : 'ניהול כלכלי'
    });
  } catch (e) {
    try {
      return await base44.asServiceRole.entities.Lead.create({
        data: {
          name: name,
          phone: phone,
          source: source,
          stage: 'new_lead',
          notes: notes,
          client_choice: isMortgageOrLoans ? 'משכנתא/הלוואות' : 'ניהול כלכלי'
        }
      });
    } catch (e2) {
      throw e2;
    }
  }
}

// ── שמירת בקשת יכולת ──────────────────────────────────────────────

async function saveCapabilityRequest(base44, requestText, allUserMessages) {
  const summary = allUserMessages.slice(0, 3).join(' | ').substring(0, 500);
  try {
    return await base44.asServiceRole.entities.SystemSettings.create({
      key: 'capability_request_' + Date.now(),
      value: requestText.substring(0, 500),
      description: 'בקשת יכולת חדשה ממיני-שימי באתר. תוכן: ' + summary
    });
  } catch (e) {
    console.log('Capability request save failed:', e.message);
  }
}

// ── זיהוי בקשת יכולת שלא קיימת ──────────────────────────────────────

function isCapabilityRequest(text) {
  return /השקע|מניות|ביטקוין|קריפטו|נדלן|תיק השקעות|קרנות|אג.ח|בורסה|סחר|מס |החזר מס|דו.ח מס|מס הכנסה|ביטוח לאומי|חשבונאות|רואה חשבון|מאזן|דוח רווח|פטור ממע.ם|רישום עסק|מע.ם|פתיחת תיק|עורך דין|ייעוץ משפטי|גירושין|צוואה|ביטוח|פוליסה|פיצויים|מטבע חוץ|פורקס|forex/i.test(text);
}

// ═══════════════════════════════════════════════════════════════════
// MAIN HANDLER
// ═══════════════════════════════════════════════════════════════════

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }

  try {
    const body = await req.json();
    const { message = '', history = [], sessionId = '' } = body;

    if (!message.trim()) {
      // Initial load - send greeting
      const greeting = await callGemini("היי", []);
      return new Response(JSON.stringify({
        reply: greeting,
        action: 'greeted',
        leadCaptured: false,
        leadSaved: false,
        leadType: '',
        capabilityRequest: false,
        capabilitySaved: false,
        collectedInfo: { hasPhone: false, hasName: false }
      }), { headers: CORS_HEADERS });
    }

    // Call Gemini with real AI
    let aiReply;
    try {
      aiReply = await callGemini(message, history);
    } catch (geminiError) {
      console.log('Gemini error:', geminiError.message);
      // Fallback to a warm message
      aiReply = "מצטער, יש בעיה טכנית רגעית. אפשר לנסות שוב? 🙏";
    }

    // Check for phone and name in user messages
    const allUserMessages = [...(history || []).filter(m => m.role === 'user').map(m => m.content || m.text || ''), message];
    const allPhones = allUserMessages.map(m => extractPhone(m)).filter(Boolean);
    const lastPhone = allPhones[allPhones.length - 1] || null;

    // Check if this message looks like a name (short Hebrew text after phone was given)
    let detectedName = null;
    if (lastPhone && allUserMessages.length > 0) {
      const lastMsg = message.trim();
      detectedName = extractName(lastMsg);
    }

    // Determine action
    let action = 'chat';
    let leadSaved = false;
    let capabilitySaved = false;
    let leadType = '';

    // Check if we collected both phone and name
    if (lastPhone && detectedName) {
      action = 'lead_captured';
      try {
        const base44 = createClientFromRequest(req);
        await saveLead(base44, detectedName, lastPhone, allUserMessages);
        leadSaved = true;
        leadType = /משכנתא|הלווא|ריבית/i.test(allUserMessages.join(' ')) ? 'am_financials' : 'shimi';
      } catch (e) {
        console.log('Lead save error:', e.message);
      }
    }

    // Check for capability requests
    if (isCapabilityRequest(message)) {
      action = 'capability_request';
      try {
        const base44 = createClientFromRequest(req);
        await saveCapabilityRequest(base44, message, allUserMessages);
        capabilitySaved = true;
      } catch (e) {
        console.log('Capability save error:', e.message);
      }
    }

    return new Response(JSON.stringify({
      reply: aiReply,
      action: action,
      leadCaptured: action === 'lead_captured',
      leadSaved: leadSaved,
      leadType: leadType,
      capabilityRequest: action === 'capability_request',
      capabilitySaved: capabilitySaved,
      collectedInfo: {
        hasPhone: !!lastPhone,
        hasName: !!detectedName
      }
    }), { headers: CORS_HEADERS });

  } catch (error) {
    return new Response(JSON.stringify({
      reply: "מצטער, יש בעיה טכנית רגעית. אפשר לנסות שוב? 🙏",
      error: error.message,
      action: 'error'
    }), { headers: CORS_HEADERS });
  }
});
