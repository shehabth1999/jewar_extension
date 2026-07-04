# -*- coding: utf-8 -*-
# Menu items for jewar_extension module
from django.utils.translation import gettext as _

# The leaf "jewar_extension_contacts_menu" carries the model and is the key the
# list/form views reference via their "menu_item". `allowed_groups` controls who
# SEES the menu (the record scope itself is enforced by the JewarContact manager).
menu_dict = {
    "jewar_extension_main_menu": {
        "name": _("Jewar"),
        "icon": "Contact",
        "module": "jewar_extension",
        "sequence": 50,
        "allowed_groups": ["contacts.users"],
        "children": {
            "jewar_extension_contacts_menu": {
                "name": _("Contacts"),
                "icon": "Users",
                "module": "jewar_extension",
                "model": "jewar_extension.jewarcontact",
                "sequence": 1,
                "allowed_groups": ["contacts.users"],
                "view_types": "list,form",
            },
        },
    },
}
