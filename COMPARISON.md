# ShimiStudio — השוואה כוללת ותוכנית מיזוג v2.0

## מקורות מידע

1. **ShimiStudio v1.0** — המערכת הנוכחית שלנו (24 קבצים, 6437 שורות, GitHub: sunraz/ShimiStudio)
2. **FantasyForge AI** (ai-content-creator repo) — אפליקציית web מלאה שנבנתה עם Manus (180 קבצים, React + TypeScript + tRPC + MySQL)
3. **xmode.ai** — פלטפורמת יצירת תוכן AI מסחרית (ניתוח דרך browser automation)

---

## השוואה מלאה

### 1. ארכיטקטורה

| פיצ'ר | ShimiStudio v1.0 | FantasyForge AI | xmode.ai |
|-------|-------------------|-----------------|---------|
| סוג | Local-first (CLI + Worker) | Web app (React + tRPC) | Web app (Next.js) |
| Backend | Base44 entities + Worker.py | Node.js + tRPC + Drizzle ORM | קניינית |
| DB | Base44 (MongoDB) + RenderJob | MySQL (Drizzle ORM) | קניינית |
| מודלים | Wan 2.2, LTX-Video, Flux.1 (open-source) | LucyDream API + free APIs | xSD, xSD Pro (קניינית) |
| NSFW | ✅ מלא (מודלים open-source) | ✅ (LucyDream xxx mode) | ✅ מלא |
| GPU | מקומי / Colab / Kaggle | ענן (API) | ענן (קניינית) |

### 2. יכולות יצירה

| יכולת | ShimiStudio v1.0 | FantasyForge AI | xmode.ai |
|-------|-------------------|-----------------|---------|
| Text→Image | ✅ (Flux.1 + ComfyUI) | ✅ (LucyDream API) | ✅ (xSD) |
| Text→Video | ✅ (Wan 2.2 + LTX) | ⚠️ UI קיים, לא עובד | ✅ (xWRS Pro) |
| Image→Video | ✅ (Wan 2.2 I2V) | ❌ | ✅ |
| Face ID | ✅ (IP-Adapter FaceID + InsightFace) | ❌ | ✅ (קניינית) |
| Face Swap | ✅ (ReActor) | ❌ | ✅ |
| TTS + LipSync | ✅ | ❌ | ❌ |
| Bulk Generation | ❌ | ❌ | ✅ |
| Scene Composition | ❌ | ❌ | ✅ (face + outfit + location) |

### 3. ממשק משתמש

| רכיב | ShimiStudio v1.0 | FantasyForge AI | xmode.ai |
|------|-------------------|-----------------|---------|
| Web UI | ❌ (CLI בלבד) | ✅ מלא (React) | ✅ מלא |
| Dashboard | ❌ | ✅ | ✅ |
| Gallery | ❌ | ✅ | ✅ |
| History | ❌ | ✅ | ✅ |
| Settings | ❌ | ✅ | ✅ |
| Favorites | ❌ | ❌ | ✅ |
| Public Feed | ❌ | ❌ | ✅ |
| API Vault | ❌ | ✅ | ❌ |
| Character Chat | ❌ | ✅ (UI בלבד) | ❌ |
| Mac Control Panel | ✅ | ❌ | ❌ |

### 4. סטיילים וטונים

#### FantasyForge AI — סטיילים:
- Photorealistic, Anime, Oil Painting, Watercolor, Cinematic, Fantasy, Artistic, Sketch

#### FantasyForge AI — מודים (Moods):
- Sensual, Romantic, Bold, Ethereal, Dark, Playful, Intimate, Passionate

#### xmode.ai — קטגוריות:
- **Styles** — סטיילים רגילים (פורטרטים, סצנות)
- **XXX** — תוכן מפורש (נעול, דורש קרדיטים)
- **Video** — סטיילי וידאו (pool, gym, dance, etc.)
- **XXX Video** — וידאו מפורש

#### xmode.ai — מודלים:
- **xSD** — סטנדרטי
- **xSD Pro** — איכות גבוהה

#### xmode.ai — מבנה Prompt (החשוב ביותר!):
כל סטייל מכיל **שני prompts נפרדים**:

**Image Prompt** — תיאור התמונה:
```
"iphone shot of a woman, medium closeup wearing a bikini, she is facing the viewer 
wearing a leather collar, amateur exposure and lighting, dark room background, 
neutral pose with arms by her side"
```

**Video Prompt** — תיאור הוידאו המפורט:
```
"Use the person from the reference image as the only character. Keep their face, 
body, and identity consistent with the reference. Do not change their appearance.

Single continuous 5-second take, photoreal, candid voyeur holiday footage, 16:9, no cuts.

Long-lens telephoto from a distance across a busy public hotel pool, shot from 
behind a white balcony rail and an out-of-focus potted palm. Harsh midday sun, 
heat haze, mild handheld iPhone wobble. She never looks at the camera.

[0–5s] She climbs the pool ladder in the shallow end, water sheeting off her, 
then takes two steps onto the hot stone toward a white sunlounger. 
Slow clumsy zoom. End as she reaches the chair.

Audio: distant splashes, muffled pool chatter, no music, no captions.
Candid only — no posing, no slow-mo, no beauty light."
```

#### xmode.ai — מבנה FaceID:
```
<faceid:4995297:1.0> - High-angle amateur photo of her sitting on the floor...
```
- פורמט: `<faceid:ID:weight>` בתחילת ה-prompt
- weight: 0.0-1.0 (1.0 = התאמה מלאה)

#### xmode.ai — סצנות מורכבות:
```
Face ID + Outfit ID + Location ID → Final Generated Scene
```
- אפשר לשלב מספר FaceIDs בסצנה אחת
- כל ID מייצג אלמנט אחר (פנים, בגדים, מיקום, תאורה)

### 5. דמויות (FantasyForge AI)

6 דמויות מוכנות עם אישיות מלאה:

| דמות | תואר | סטייל | מוד | אישיות |
|------|------|--------|-----|---------|
| Luna | Mystical Dreamer | Ethereal | Sensual | Dreamy, romantic, mystical |
| Scarlett | Bold & Passionate | Cinematic | Playful | Bold, passionate, uninhibited |
| Jade | Artistic Visionary | Fantasy | Bold | Artistic, experimental |
| Aria | Sensual Enchantress | Photorealistic | Romantic | Seductive, enchanting |
| Nova | (TBD) | (TBD) | (TBD) | (TBD) |
| Venus | (TBD) | (TBD) | (TBD) | (TBD) |

### 6. מערכת תשלומים

| פלטפורמה | מודל | מחירים |
|----------|------|---------|
| ShimiStudio v1.0 | ❌ אין | — |
| FantasyForge AI | Credits (Stripe) | 10/$2.99, 100/$24.99, 500/$99.99, 1000/$179.99 |
| xmode.ai | Credits (pay-as-you-go) | 50/$11, 300/$45, 600/$80, 1200/$140 |
| Shimi (שלנו) | Multi-Tenant (A-D) | free 5/day → unlimited |

### 7. API Providers חינמיים (FantasyForge AI)

| ספק | סוג | הגבלה יומית | NSFW | איכות |
|------|------|-------------|------|--------|
| Airforce | Image | 1000 | ✅ | High |
| Pollinations | Image | 100 | ✅ | Medium |
| HuggingFace | Image | 50 | ✅ | Medium |
| DeepAI | Image | 5 | ✅ | High |
| Runway | Video | 5 | ✅ | High |
| Pika | Video | 10 | ✅ | High |
| Synthesia | Video | 3 | ❌ | High |
| LucyDream | Image | בתשלום | ✅ | High |

---

## תוכנית מיזוג — ShimiStudio v2.0

### מה משלבים מכל מקור:

#### מ-FantasyForge AI:
1. ✅ **סטיילים** (Photorealistic, Anime, Cinematic, etc.) → prompt templates
2. ✅ **מודים** (Sensual, Romantic, Bold, etc.) → prompt modifiers
3. ✅ **Aspect ratios** + **durations** → workflow parameters
4. ✅ **דמויות** (Luna, Scarlett, Jade, Aria) → persona system
5. ✅ **Free API rotation** → fallback כשאין GPU מקומי
6. ✅ **API Vault** → ניהול מפתחות API

#### מ-xmode.ai:
1. ✅ **Dual prompt structure** (Image prompt → Video prompt) → הפרדה ברורה
2. ✅ **קטגוריות סטיילים** (Styles, XXX, Video, XXX Video) → ארגון
3. ✅ **FaceID composition** (face + outfit + location) → scene system
4. ✅ **Video prompt template** (identity lock + camera + lighting + action + audio)
5. ✅ **Bulk generation** → batch processing
6. ✅ **Prompt packs** → curated templates מוכנים

#### מה שנשאר מ-ShimiStudio v1.0:
1. ✅ ComfyUI engine (Wan 2.2, LTX, Flux.1)
2. ✅ Worker architecture (Base44 → local)
3. ✅ IP-Adapter FaceID + ReActor
4. ✅ TTS + LipSync
5. ✅ Phone camera bridge
6. ✅ CivitAI model downloader
7. ✅ Colab/Kaggle cloud option

### סדר עדיפויות לבנייה:

1. **ספריית סטיילים + טונים** — prompt templates עם מערכת קטגוריות
2. **Dual prompt system** — Image prompt + Video prompt (במבנה xmode)
3. **FaceID composition** — שילוב מספר IDs בסצנה
4. **Bulk generation** — batch processing דרך Worker
5. **Free API fallback** — Airforce/Pollinations כשאין GPU
6. **דמויות/Personas** — system prompts ליצירה מותאמת
