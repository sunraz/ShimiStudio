# Shimi Dev — v2c: פיצול לקטעים של 81 פריימים (5.06 שניות ב-16fps), תנועה אחת לקטע
# חזה מחוזק לפי דרישת סאן 12/10; מצב לבוש נעול טקסטואלית בכל קטע.

ID = ("A pale goth woman, pale porcelain skin with freckles, sharp black winged eyeliner, dark plum lipstick, "
      "long straight jet-black hair with straight blunt bangs and one deep-purple streak, silver eyebrow piercing, "
      "extreme hourglass figure, very large full heavy natural bust, deep cleavage, narrow small waist, wide full hips, "
      "average height. ")
FRIEND = "Her best friend, a laughing dark-haired young woman in a red flannel shirt with rolled-up sleeves, sits at the table. "
SET = ("Underground poker room, green felt poker table with chips and playing cards, warm brass lamp light overhead. "
       "Photorealistic cinematic video, realistic skin texture, stable camera, natural motion. ")
LING = "wearing a black lace bra and matching black lace panties "

NEG = ("bright tones, overexposed, static, frozen, motionless, still picture, blurred details, subtitles, style of painting, "
       "overall gray, worst quality, low quality, ugly, incomplete, extra fingers, poorly drawn hands, deformed, disfigured, "
       "misshapen limbs, fused fingers, messy background, cartoon, anime, illustration, cgi, 3d render, nudity, topless, "
       "bare breasts, male figures, brother, man at the table, flat chest, small chest, breast distortion, inconsistent breast size")

SEGS = {
 1:  "She wears a long black wool coat over her short black knit dress and a black leather jacket. She slides the coat off her shoulders and hands it to her laughing friend.",
 2:  "She wears a short black knit dress with a black leather jacket over it. She pulls the jacket off, one shoulder at a time, and tosses it onto the chair beside the table.",
 3:  "She wears a short black knit dress with a black scarf around her neck and black gloves. She pulls the scarf loose with one hand and lets it fall onto the clothes pile.",
 4:  "She wears a short black knit dress and black gloves. She pulls the gloves off her hands one finger at a time and drops them onto the clothes pile.",
 5:  "She wears a short black knit dress. She grabs the hem of the dress with both hands and starts pulling it upward, laughing playfully.",
 6:  "Standing " + LING + "she tosses her balled-up black dress onto the clothes pile and laughs at her friend.",
 7:  LING + "she sits at the poker table and shuffles a deck of playing cards with a teasing smile.",
 8:  LING + "she deals playing cards across the green felt table toward her friend.",
 9:  LING + "she stands up from her chair and stretches her arms above her head playfully.",
 10: LING + "she spins in one full circle beside the table, her long black hair swinging, both women laughing.",
 11: LING + "she dances slowly, swaying her hips side to side in rhythm.",
 12: LING + "she sways in rhythm and runs both hands slowly through her long black hair with a teasing smile.",
 13: LING + "she turns slowly in the warm lamp light, her arms flowing gracefully.",
 14: LING + "she dances with her arms raised above her head, hips rolling smoothly in rhythm.",
 15: LING + "she drops into a playful curtsy toward her laughing friend and rises back up laughing.",
 16: LING + "she leans over the poker table on her elbows toward the camera and blows a playful kiss, as her friend raises the winning hand of cards.",
}

def prompt(n):
    return ID + SEGS[n] + " " + FRIEND + SET
