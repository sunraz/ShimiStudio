"""
ShimiStudio — No-Filter Policy (permanent)
איפוס פילטרים קבוע בכל מנועי הסטודיו — הוראת סאן, 18/10/2026.

מדיניות: שום פייפליין דיפיוזיה של הסטודיו לא מריץ בודק בטיחות (safety checker).
הקוד קבוע וחל על כל נקודו� הבנייה: לוקאלי, קולאב, קגל, לורות ואימון.

חריג אחד והצהרה מלאה: המנוע המתארח של בייס44 מסנן בצד השרת —
אי אפשר לאפס אותו מקוד לקוח (נבדק חי 18/10: פרומפט מפורש נדחה שם).
לכן הרוטציה (free_api.py) קיימת: בסינון/כשל היא נופלת אוטומטית
לספקים ללא סינון. האחריות על התוצר — על המפעיל.
"""

from typing import Any


def apply_no_filter(pipe: Any) -> Any:
    """מאפס בודק בטיחות בכל פייפליין diffusers, בבטחה (רק אם השדה קיים)."""
    for attr, val in (
        ("safety_checker", None),
        ("requires_safety_checker", False),
        ("feature_extractor", None),
    ):
        if hasattr(pipe, attr):
            try:
                setattr(pipe, attr, val)
            except Exception:
                pass
    return pipe


def build_pipeline(loader, model_id: str, **kwargs):
    """בונה פייפליין עם איפוס מובנה מראש — לשימוש בכל from_pretrained."""
    kwargs.setdefault("safety_checker", None)
    kwargs.setdefault("requires_safety_checker", False)
    pipe = loader(model_id, **kwargs)
    return apply_no_filter(pipe)
