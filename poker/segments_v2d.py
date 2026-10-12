# Shimi Poker V2d — הפיצול של 10 הסצינות המקוריות (v2) ל-20 קטעי 81 פריימים (5.06 שנ'),
# מצב לבוש נעול בכל קטע, חברה במקום אח, מסתיים בהלבשה תחתונה.
ID_BASE = ("A pale goth woman, pale porcelain skin with freckles, sharp black winged eyeliner, dark plum lipstick, "
      "long straight jet-black hair with straight blunt bangs and one deep-purple streak, silver eyebrow piercing. "
      "LOCKED BODY: pronounced hourglass figure, very large full heavy natural bust, narrow small waist, wide full hips, "
      "soft rounded thighs, average height, same face and same proportions in every frame. ")
ID_CHOKER = "black velvet choker with silver ankh, "
CORE = ("Underground poker room, green felt table, warm brass lamp light overhead, chips and cards on the table. "
        "She plays poker against her best friend, a laughing dark-haired young woman in a red flannel shirt with rolled-up sleeves. ")
MOTION = ("Continuous full-body motion throughout, smooth natural movement, fabric and hair moving realistically. "
          "Handheld cinematic camera, film grain, photorealistic, realistic skin texture. ")
CONSISTENCY = ("Anatomically correct hands with exactly five fingers on each hand, natural bust that moves only slightly and keeps a consistent shape, consistent hourglass proportions in every frame, no warping or stretching of body parts, stable face. ")

# מצבי לבוש נעולים לפי סצינה (1-3 עם צ'וקר עד שהוא מוסר בסוף סצינה 3)
STATE = {
 1: "She wears a long dark wool coat over a black leather biker jacket over a short fitted black knit dress. ",
 2: "Her wool coat is tossed over the chair. She wears a black leather biker jacket over a short fitted black knit dress. ",
 3: "She wears a short fitted black knit dress with a thin dark scarf, black fingerless lace gloves, a black beanie and chunky black boots. ",
 4: "She wears a short fitted black knit dress. Beneath the dress she wears a black lace bra and matching black lace panties. ",
}
STATE_LACE = "She wears a black lace bra and matching black lace panties. "

ACTIONS = {
 "1a": "stands up from her chair and slowly unbuttons her long dark wool coat, one button at a time, then slides it off her right shoulder",
 "1b": "slides the wool coat off both shoulders one arm at a time and tosses it over the back of her chair, then sits back down laughing",
 "2a": "shrugs off her black leather biker jacket sliding it down her right arm, catching it with her other hand",
 "2b": "slides the leather jacket off her left arm and drops it on the coat pile on the chair",
 "3a": "in one playful sweep pulls off her thin dark scarf and black fingerless lace gloves, tugs off her black beanie and shakes her long black hair loose",
 "3b": "kicks off her chunky black boots under the table, peels off her socks, unclasps her black velvet choker and drops everything on the pile",
 "4a": "grabs the hem of her short fitted black knit dress with both hands and slowly pulls it up over her hips and waist, up past her bare midriff",
 "4b": "lifts the black knit dress over her head with both arms raised high, revealing her black lace bra and matching black lace panties, tosses the dress on the pile and puts her hands on her hips, smirking",
 "5a": "sits back down at the table in her black lace bra and matching black lace panties, laughing in amused disbelief and brushing her hair back",
 "5b": "shuffles the next hand of cards in her lace lingerie and deals them across the green felt, leaning on her elbows toward the table",
 "6a": "stands up from the table and starts a slow playful spin in her black lace lingerie, arms out to the sides",
 "6b": "completes the slow playful circle, her long black hair swinging around her, both women laughing",
 "7a": "stands beside her friend's chair and starts a playful teasing dance in her black lace lingerie, shifting her weight smoothly from one foot to the other, swaying her hips side to side in rhythm",
 "7b": "dances beside the chair, running her hands slowly through her long black hair with a teasing smile, her body flowing continuously",
 "8a": "dances between the poker table and the brass lamp in her black lace lingerie, swinging her hips in rhythm and starting a slow spin with her arms flowing above her head",
 "8b": "turns gracefully around the warm lamplight in her black lace lingerie while her friend claps and laughs at the table, camera circling slowly around her",
 "9a": "dances in her black lace lingerie with her arms raised above her head, hips rolling smoothly in rhythm, her whole body moving in one continuous flowing motion",
 "9b": "drops into a playful curtsy toward her friend in her black lace lingerie, laughing warmly",
 "10a": "leans over the poker table toward the camera, resting on her elbows in her black lace bra and matching black lace panties",
 "10b": "blows a playful kiss toward the camera and laughs warmly as her friend raises the winning hand of cards",
}

def prompt(seg):
    scene = int(seg[:-1])
    ident = ID_BASE + (ID_CHOKER if scene <= 3 else "")
    state = STATE.get(scene, STATE_LACE)
    return (ident + CORE + "She " + ACTIONS[seg] + ". "
            + "Her friend laughs and pulls the chips toward herself. " + state + MOTION + CONSISTENCY)

NEG = ("bright tones, overexposed, static, frozen, motionless, still picture, blurred details, subtitles, style of painting, "
       "overall gray, worst quality, low quality, ugly, incomplete, extra fingers, poorly drawn hands, deformed, disfigured, "
       "misshapen limbs, fused fingers, messy background, cartoon, anime, illustration, cgi, 3d render, nudity, topless, "
       "bare breasts, male figures, brother, man at the table")

SEGMENTS = sorted(ACTIONS.keys())
