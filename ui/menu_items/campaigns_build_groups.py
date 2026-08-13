# -*- coding: utf-8 -*-
# Adds the "Build WhatsApp Groups" button to the Groups screen.
#
# It has to go on the menu item, not the view: chat_campaigns_list_view has no
# `header` key, so appending to header.actions there resolves to nothing and the
# button silently never appears.
#
# selection_required is False on purpose — this builds from the whole contact
# base, it is not an operation on the rows the user ticked.
#
# "replace" rather than "append": append reads the target path first and raises
# if it is missing, and this menu item ships without an `actions` key at all.
# replace is the only operation that creates it. If chat ever adds its own
# actions here, this has to become an append.
from django.utils.translation import gettext as _


menu_dict = {
    "append_build_groups_chat_campaigns": {
        "_inherit": "chat_main_menu_omnichannel_campaigns",
        "inheritance_operations": [
            {
                "operation": "replace",
                "target": "actions",
                "content": [{
                    "string": _("Build WhatsApp Groups"),
                    "icon": "RefreshCw",
                    "name": "build_whatsapp_groups",
                    "type": "menu",
                    "menu_type": "slideover",
                    "view_key": "jewar_build_groups_form_view",
                    "model": "jewar_extension.buildgroupswizard",
                    "as": "button",
                    "view_type": ["list"],
                    "variant": "primary",
                    "selection_required": False,
                    "confirm_required": False,
                    "allowed_groups": ["chat.admins"],
                }],
            },
        ],
    },
}
