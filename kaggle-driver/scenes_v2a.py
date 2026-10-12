# Shimi Poker V2 — גרסה מאושרת סאן 12/10: חברה במקום אח, 10 סצינות × 121 פריימים (7.5 שנ'),
# מסתיים בהלבשה תחתונה. כל פעולה כוריאוגרפיה מלאה במצלמה.
ID_BASE = ("A pale goth woman, pale porcelain skin with freckles, sharp black winged eyeliner, dark plum lipstick, "
      "long straight jet-black hair with straight blunt bangs and one deep-purple streak, silver eyebrow piercing. "
      "LOCKED BODY: pronounced hourglass figure, full natural bust, narrow small waist, wide full hips, "
      "soft rounded thighs, average height, same face and same proportions in every frame. ")
ID_CHOKER = "black velvet choker with silver ankh, "
CORE = ("Underground poker room, green felt table, warm brass lamp light overhead, chips and cards on the table. "
        "She plays poker against her best friend, a laughing dark-haired young woman in a red flannel shirt with rolled-up sleeves. ")
MOTION = ("Continuous full-body motion throughout, smooth natural movement, fabric and hair moving realistically. "
          "Handheld cinematic camera, film grain, photorealistic, realistic skin texture. ")
ACTIONS = {
 1: "stands up from her chair, slowly unbuttons her long dark wool coat, slides it off her shoulders one arm at a time "
    "and tosses it over the back of her chair, then sits back down laughing",
 2: "shrugs off her black leather biker jacket, sliding it down her arms one at a time, and drops it on the coat pile",
 3: "in one playful sweep pulls off her thin dark scarf and black fingerless lace gloves, tugs off her black beanie and shakes "
    "her long black hair loose, kicks off her chunky black boots under the table, peels off her socks, unclasps her black velvet "
    "choker and drops everything on the pile",
 4: "grabs the hem of her short fitted black knit dress with both hands, slowly pulls it up over her hips and waist, up past "
    "her bare midriff, then lifts it over her head with both arms raised high, revealing her black lace bra and matching black "
    "lace panties, and tosses the dress on the pile, hands on her hips, smirking",
 5: "sits back down at the table in her black lace bra and panties, laughing in disbelief, shuffles and deals the next hand "
    "of cards, leaning on her elbows toward the green felt",
 6: "stands up and spins in a slow playful circle in her black lace lingerie, arms out to the sides, hair swinging, showing "
    "off playfully while both women laugh",
 7: "in her black lace bra and matching black lace panties stands and starts a playful teasing dance beside her friend's "
    "chair, shifting her weight smoothly from one foot to the other, swaying her hips side to side in rhythm, running her "
    "hands slowly through her long black hair with a teasing smile, her body flowing continuously",
 8: "dances in her black lace lingerie between the poker table and the brass lamp, swinging her hips in rhythm, spinning "
    "slowly with her arms flowing above her head, turning gracefully around the warm lamplight while her friend claps and "
    "laughs at the table, camera circling slowly around her",
 9: "dances in her black lace lingerie with her arms raised above her head, hips rolling smoothly in rhythm, her whole body "
    "moving in one continuous flowing motion, then drops into a playful curtsy toward her friend, laughing",
 10: "leans over the poker table toward the camera, resting on her elbows in her black lace bra and matching black lace "
     "panties, blows a playful kiss toward the camera and laughs warmly as her friend raises the winning hand of cards",
}
NEG = ("bright tones, overexposed, static, frozen, motionless, still picture, blurred details, subtitles, style of painting, "
       "overall gray, worst quality, low quality, ugly, incomplete, extra fingers, poorly drawn hands, deformed, disfigured, "
       "misshapen limbs, fused fingers, messy background, cartoon, anime, illustration, cgi, 3d render, nudity, topless, "
       "bare breasts, male figures, brother, man at the table")
def prompt(n):
    ident = ID_BASE + (ID_CHOKER if n <= 3 else "")
    state = ("Under all her clothes she wears a short fitted black knit dress. " if n <= 3 else
             "Beneath the dress she wears a black lace bra and matching black lace panties. " if n == 4 else
             "She wears a black lace bra and matching black lace panties. ")
    dance = DANCE_CONSISTENCY if n >= 7 else ""
    return (ident + CORE + "She loses the hand, reacts in amused disbelief, then she " + ACTIONS[n] + ". "
            + "Her friend laughs and pulls the chips toward herself. " + state + MOTION + dance)
DANCE_CONSISTENCY = ("Anatomically correct hands with exactly five fingers on each hand, natural bust that moves only slightly and keeps a consistent shape, consistent hourglass proportions in every frame, no warping or stretching of body parts, stable face. ")
ANCHOR_A = "https://media.base44.com/images/public/6a901f55a4d9a9b76a095a77/f7d19d8bd_generated_image.png"
ANCHOR_B = "https://media.base44.com/images/public/6a901f55a4d9a9b76a095a77/e8383ce46_generated_image.png"
