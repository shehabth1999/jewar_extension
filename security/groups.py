# -*- coding: utf-8 -*-
"""
Security groups for jewar_extension module

This file defines all security groups for the jewar_extension module.
Groups are synced to the database using the sync_groups management command.
"""

GROUPS = [
    {
        'name': 'Jewar_extension Users',
        'technical_name': 'jewar_extension.users',
        'category': 'Jewar_extension',
        'description': 'Access jewar_extension module',
    },
    {
        'name': 'Jewar_extension Admins',
        'technical_name': 'jewar_extension.admins',
        'category': 'Jewar_extension',
        'implied_groups': ['jewar_extension.users'],
        'description': 'Manage all jewar_extension module',
    }
]
