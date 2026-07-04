# -*- coding: utf-8 -*-
{
    'name': 'Jewar Contacts',
    'technical_name': 'jewar_extension',
    'type': 'app',
    'summary': 'WhatsApp-account-scoped contacts view',
    'description': """
Adds a Contacts view that shows each user only the contacts belonging to the
WhatsApp accounts where they are an admin. Delete is restricted to Contacts
Admins and superusers.
""",
    'author': "Genie ERP",
    'website': "https://www.aigeniecrm.com",
    'category': 'Jewar_extension',
    'version': '0.0.1',
    'depends': ['base', 'contacts', 'whatsapp', 'chat'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
