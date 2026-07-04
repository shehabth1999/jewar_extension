# -*- coding: utf-8 -*-
"""
Access conditions for jewar_extension module.

Record rule on the REAL contact (base.partner): every non-superuser sees only the
contacts of the WhatsApp accounts where they are an admin. This applies wherever
base.partner is queried (Contacts app, pickers, etc.) — access conditions are
model-wide, not per-view.

`user.whatsapp_admin_contact_ids` is resolved to the distinct partner ids by the
patch in ../patches.py (registered from apps.py `ready()`).

Delete is NOT handled here — base.partner already restricts delete to
contacts.admins + superusers via the contacts module's model permissions.
"""

ACCESS_CONDITIONS = [
    {
        "name": "own whatsapp account contacts",
        "model": "base.partner",
        "condition": {
            "filters": {
                "operator": "and",
                "filters": [
                    {
                        "field": "id",
                        "operator": "in",
                        "value": "user.whatsapp_admin_contact_ids",
                    },
                ],
            }
        },
        # [view, add, change, delete] — 1 = this rule is ENFORCED for that op.
        # Scope view + change (can't edit what you can't see); add/delete untouched
        # (delete stays gated by base.partner model perms).
        "permissions": [1, 0, 1, 0],
        "groups": [],  # global: applies to all non-superusers
    },
]
