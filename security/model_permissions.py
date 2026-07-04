# -*- coding: utf-8 -*-
"""
Access rights for jewar_extension module.
Format: [view, add, change, delete] as [0/1, 0/1, 0/1, 0/1]

No model permissions here: the feature reuses base.partner, whose delete is
already restricted to contacts.admins + superusers by the contacts module.
"""

MODEL_PERMISSIONS = []
