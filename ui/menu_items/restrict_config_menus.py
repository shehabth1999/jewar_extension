# -*- coding: utf-8 -*-
# Restrict CRM (Configuration, Orders & Billing) and Contacts (Features, Countries)
# grouping menus to their module admins only, via menu inheritance (no core edit).
menu_dict = {
    "restrict_crm_configuration_to_admins": {
        "_inherit": "crm_main_menu_configuration",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["crm.admins"]},
        ],
    },
    "restrict_crm_orders_to_admins": {
        "_inherit": "crm_main_menu_orders",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["crm.admins"]},
        ],
    },
    "restrict_contacts_features_to_admins": {
        "_inherit": "contacts_main_menu_features",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["contacts.admins"]},
        ],
    },
    "restrict_contacts_countries_to_admins": {
        "_inherit": "contacts_main_menu_features_country",
        "inheritance_operations": [
            {"operation": "replace", "target": "allowed_groups", "content": ["contacts.admins"]},
        ],
    },
}
