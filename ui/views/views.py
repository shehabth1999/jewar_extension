# -*- coding: utf-8 -*-
# UI Views for jewar_extension module
#
# Views are built on the ``jewar_extension.jewarcontact`` proxy model, whose
# manager scopes rows to the WhatsApp accounts where the current user is an
# admin (see ``models.py``). base.partner elsewhere (Contacts app, CRM, chat)
# is unaffected — the scope lives only on this proxy model / these views.
from django.utils.translation import gettext as _

jewar_contact_list_view = {
    "key": "jewar_contact_list_view",
    "name": _("Contacts"),
    "model": "jewar_extension.jewarcontact",
    "menu_item": "jewar_extension_contacts_menu",
    "view_type": "list",
    "priority": 10,
    "module": "jewar_extension",
    "body": {
        "tree": {
            "fields": [
                {
                    "name": "name",
                    "widget": "text",
                    "string": _("Name"),
                    "help": _("Contact name"),
                    "width": 260,
                },
                {
                    "name": "phone",
                    "widget": "text",
                    "string": _("Phone"),
                    "help": _("Primary phone contact"),
                },
                {
                    "name": "mobile",
                    "widget": "text",
                    "string": _("Mobile"),
                    "help": _("Mobile phone contact"),
                },
                {
                    "name": "email",
                    "widget": "text",
                    "string": _("Email Address"),
                    "help": _("Primary email contact"),
                },
                {
                    "name": "created_at",
                    "widget": "datetime",
                    "string": _("Created On"),
                    "help": _("When the contact was created"),
                },
            ]
        },
    },
}


jewar_contact_form_view = {
    "key": "jewar_contact_form_view",
    "name": _("Contact"),
    "model": "jewar_extension.jewarcontact",
    "menu_item": "jewar_extension_contacts_menu",
    "view_type": "form",
    "priority": 10,
    "module": "jewar_extension",
    "body": {
        "header": {
            "actions": [],
            "actions_list": [],
        },
        "sheet": {
            "title": {
                "fields": [
                    {
                        "name": "name",
                        "string": _("Name"),
                        "widget": "text",
                        "required": True,
                        "readonly": False,
                        "placeholder": _("Enter name"),
                    },
                ]
            },
            "sections": [
                {
                    "title": "",
                    "groups": [
                        {
                            "fields": [
                                {
                                    "name": "phone",
                                    "string": _("Phone"),
                                    "widget": "phone",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Phone number"),
                                    "placeholder": _("Enter phone number"),
                                },
                                {
                                    "name": "mobile",
                                    "string": _("Mobile"),
                                    "widget": "phone",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Mobile phone number"),
                                    "placeholder": _("Enter mobile number"),
                                },
                                {
                                    "name": "email",
                                    "string": _("Email"),
                                    "widget": "email",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Email address"),
                                    "placeholder": _("Enter email address"),
                                },
                                {
                                    "name": "website",
                                    "string": _("Website"),
                                    "widget": "url",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Website URL"),
                                    "placeholder": _("https://..."),
                                },
                            ],
                        },
                        {
                            "fields": [
                                {
                                    "name": "country_id",
                                    "string": _("Country"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Select country"),
                                    "placeholder": _("Search..."),
                                    "multiSelect": False,
                                },
                                {
                                    "name": "city",
                                    "string": _("City"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "creatable": True,
                                    "multiSelect": False,
                                    "required": False,
                                    "readonly": False,
                                    "help": _("City"),
                                },
                                {
                                    "name": "street",
                                    "string": _("Street"),
                                    "widget": "text",
                                    "required": False,
                                    "readonly": False,
                                    "help": _("Street address"),
                                    "placeholder": _("Enter street address"),
                                },
                            ],
                        },
                    ],
                }
            ],
        },
    },
}
