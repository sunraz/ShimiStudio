# -*- coding: utf-8 -*-
ID_BASE = ("A pale goth woman, pale porcelain skin with freckles, sharp black winged eyeliner, dark plum lipstick, "
      "long straight jet-black hair with straight blunt bangs and one deep-purple streak, silver eyebrow piercing. "
      "LOCKED BODY: pronounced hourglass figure, full large natural bust, very narrow small waist, wide full hips, "
      "soft rounded thighs, average height, same proportions in every frame. ")
ID_CHOKER = "black velvet choker with silver ankh, "
CORE = ("Underground poker room, green felt table, warm brass lamp light overhead, chips and cards on the table. "
        "She sits playing poker against her dark-haired young male friend, tall lean, rolled-up sleeves, forearm tattoos. ")
TAIL = ("Her friend laughs and pulls the chips toward himself. Continuous full-body motion throughout, hips swaying, "
        "hair swinging with her movements, fabric moving realistically. Handheld cinematic camera, film grain, "
        "photorealistic, realistic skin texture. ")
NEG = ("bright tones, overexposed, static, still, frozen, no motion, motionless, blurred details, subtitles, style of painting, paintings, "
       "overall gray, worst quality, low quality, ugly, incomplete, extra fingers, poorly drawn hands, deformed, disfigured, "
       "misshapen limbs, fused fingers, bad anatomy, distorted breasts, warped torso, warped body shape, mutated hands, extra limbs, sagging, unrealistic proportions, still picture, messy background, cartoon, anime, illustration, cgi, 3d render")
STATE = {
 1: "She wears a long dark wool coat over a black leather biker jacket over a short fitted black knit dress, thin dark scarf, black fingerless lace gloves, black beanie.",
 2: "She wears a black leather biker jacket over a short fitted black knit dress, thin dark scarf, black fingerless lace gloves, black beanie.",
 3: "She wears a short fitted black knit dress, thin dark scarf, black fingerless lace gloves, black beanie, chunky black boots.",
 4: "She wears her short fitted black knit dress, chunky black boots.",
 5: "She wears only her black lace bra and matching black lace panties, barefoot.",
 6: "She wears only her black lace bra and matching black lace panties.",
 7: "She wears only her black lace bra and matching black lace panties.",
 8: "She wears only her black lace bra and matching black lace panties.",
 9: "She wears only her black lace bra and matching black lace panties.",
 10: "She wears only her black lace bra and matching black lace panties.",
}
ACTIONS = {
 1: "loses the hand and bursts out laughing in disbelief, then stands up from her chair, unbuttons her long dark wool coat and slides it off her shoulders one arm at a time, tossing it over the back of her chair, then sits back down and deals the next hand",
 2: "shrugs off her black leather biker jacket, letting it slide slowly down her arms, and drops it on the coat pile",
 3: "unwinds her thin dark scarf from her neck, pulls off her black fingerless lace gloves one finger at a time, tugs off her black beanie and shakes her hair loose, tossing everything playfully onto the pile",
 4: "stands up, grabs the hem of her short fitted black knit dress with both hands and slowly pulls it up over her hips and waist, up past her bare midriff, then lifts it over her head with both arms raised high, the dress sliding off completely and smoothly, revealing her black lace bra and matching black lace panties, and tosses the dress onto the pile",
 5: "kicks off her chunky black boots under the table with a playful clatter, sits on the edge of her chair and peels off her socks one by one, dropping them onto the clothes pile, laughing at her losing streak",
 6: "unclasps her black velvet choker, drops it and her remaining jewelry onto the pile, then stands with her hands on her hips wearing only her black lace bra and matching black lace panties, smirking down at her friend",
 7: "stands up and begins a slow sensual dance beside his chair, swaying her hips side to side, running her hands through her hair with a teasing smile",
 8: "dances between his knees, leaning close over him, her hands sliding down his shoulders, moving to the music",
 9: "turns away from him and bends forward at the waist, hands sliding slowly down her thighs, glancing back over her shoulder with a teasing smile",
 10: "spins back around, hops up to sit on the edge of the poker table in her black lace lingerie, laughing, and flicks a poker chip playfully at her friend",
}
def prompt(n):
    ident = ID_BASE + (ID_CHOKER if n <= 5 else "")
    return ident + CORE + STATE[n] + " She " + ACTIONS[n] + ". " + TAIL
ANCHOR_A = "https://media.base44.com/images/public/6a901f55a4d9a9b76a095a77/b81004041_generated_image.png"
ANCHOR_B = ANCHOR_A
