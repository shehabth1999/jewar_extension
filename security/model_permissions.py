# -*- coding: utf-8 -*-
"""
Access rights for jewar_extension module.
Format: [view, add, change, delete] as [0/1, 0/1, 0/1, 0/1]
"""

MODEL_PERMISSIONS = [
    # jewar_extension.jewarcontact is a PROXY of base.partner, so it has its own
    # permissions independent from base.partner. The per-record scope (only
    # contacts of the accounts you administer) is enforced by the model manager;
    # these permissions only decide who can open the view and who can delete.
    #
    # Contacts Users: open the view + edit, but NOT delete.
    {
        'model': 'jewar_extension.jewarcontact',
        'group': 'contacts.users',
        'permissions': [1, 0, 1, 0],  # view, no add, change, no delete
    },
    # Contacts Admins: same, plus delete. (Superusers bypass perms entirely.)
    # This is the ONLY non-superuser group that can delete a contact here.
    {
        'model': 'jewar_extension.jewarcontact',
        'group': 'contacts.admins',
        'permissions': [1, 0, 1, 1],  # view, no add, change, delete
    },
]

# Permission patterns for convenience
PERMISSION_PATTERNS = {
    'NONE': [0, 0, 0, 0],           # No access
    'VIEW_ONLY': [1, 0, 0, 0],      # View only
    'MANAGE': [1, 1, 1, 0],         # Manage but no delete
    'FULL': [1, 1, 1, 1],           # Full access
}

# Example using patterns:
# {
#     'model': 'jewar_extension.modelname',
#     'group': 'jewar_extension.users',
#     'permissions': PERMISSION_PATTERNS['MANAGE'],
# }
