# -*- coding: utf-8 -*-
# Restrict chat Config menu items (Tags / Teams / Groups) to Chat Admins only,
# via menu inheritance (no chat core edit).
menu_dict = {
    "restrict_chat_tags_to_admins": {
        "_inherit": "chat_main_menu_omnichannel_tags",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["chat.admins"]},
        ],
    },
    "restrict_chat_teams_to_admins": {
        "_inherit": "chat_main_menu_omnichannel_teams",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["chat.admins"]},
        ],
    },
    "restrict_chat_groups_to_admins": {
        "_inherit": "chat_main_menu_omnichannel_campaigns",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["chat.admins"]},
        ],
    },
}
