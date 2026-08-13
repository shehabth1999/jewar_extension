# -*- coding: utf-8 -*-
# Wizard behind the "Build WhatsApp Groups" button on the Groups screen.
#
# The footer is the preview: every field in it is written by the @onchange on
# jewar_extension.buildgroupswizard, so the numbers repaint as the user toggles
# the filters. The footer only supports label -> value rows with the `number`
# widget, which is exactly the shape of this breakdown.
from django.utils.translation import gettext as _


def _readout(name, string, highlight=False):
    field = {"name": name, "string": string, "widget": "number", "readonly": True}
    if highlight:
        field["highlight"] = True
    return field


jewar_build_groups_form_view = {
    "key": "jewar_build_groups_form_view",
    "name": _("Build WhatsApp Groups"),
    "priority": 1,
    "module": "jewar_extension",
    "model": "jewar_extension.buildgroupswizard",
    "view_type": "form",
    "body": {
        "sheet": {
            "sections": [
                {
                    "title": _("Batch"),
                    "groups": [
                        {
                            "fields": [
                                {
                                    "name": "batch_hint",
                                    "string": _("Batch name"),
                                    "widget": "text",
                                    "required": True,
                                    "placeholder": _("e.g. xx1"),
                                    "help": _("Prefixes every group in this run, "
                                              "e.g. \"xx1 basmala 1 / 250\""),
                                },
                                {
                                    "name": "group_size",
                                    "string": _("Group size"),
                                    "widget": "number",
                                    "required": True,
                                    "onChange": True,
                                    "onChangeTrigger": "blur",
                                    "help": _("Contacts per group (10-1000)"),
                                },
                                {
                                    "name": "excluded_accounts",
                                    "string": _("Exclude accounts"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "multiSelect": True,
                                    "onChange": True,
                                    "help": _("These accounts get no groups at all"),
                                },
                            ]
                        }
                    ],
                },
                {
                    "title": _("Filters"),
                    "groups": [
                        {
                            "fields": [
                                {
                                    "name": "exclude_suppliers",
                                    "string": _("Exclude suppliers"),
                                    "widget": "switch",
                                    "onChange": True,
                                },
                                {
                                    "name": "dedupe_handsets",
                                    "string": _("Split repeated numbers"),
                                    "widget": "switch",
                                    "onChange": True,
                                    "help": _("The same person under several accounts is "
                                              "placed once, spread to balance the load"),
                                },
                                {
                                    "name": "exclude_meta_errors",
                                    "string": _("Exclude Meta errors"),
                                    "widget": "switch",
                                    "onChange": True,
                                    "help": _("Numbers Meta says cannot or should not "
                                              "receive marketing"),
                                },
                                {
                                    "name": "exclude_templated_this_month",
                                    "string": _("Exclude contacts sent a template this month"),
                                    "widget": "switch",
                                    "onChange": True,
                                },
                            ]
                        }
                    ],
                },
                {
                    "title": _("Previous batches"),
                    "groups": [
                        {
                            "fields": [
                                {
                                    "name": "exclude_any_previous_batch",
                                    "string": _("Exclude contacts in any previous batch"),
                                    "widget": "switch",
                                    "onChange": True,
                                },
                                {
                                    "name": "exclude_specific_batch",
                                    "string": _("Exclude contacts in a specific batch"),
                                    "widget": "switch",
                                    "onChange": True,
                                    "help": _("Use this to catch contacts added since a "
                                              "batch was built"),
                                },
                                {
                                    "name": "exclude_batch_hint",
                                    "string": _("Batch name to exclude"),
                                    "widget": "text",
                                    "placeholder": _("e.g. xx1"),
                                    "onChange": True,
                                    "invisible": {
                                        "field": "exclude_specific_batch",
                                        "operator": "eq",
                                        "value": False,
                                    },
                                },
                            ]
                        }
                    ],
                },
            ],
            "footer": {
                "position": "end",
                "fields": [
                    _readout("total_contacts", _("Total contacts")),
                    _readout("unique_phones", _("Unique phones")),
                    {"separator": "thin"},
                    _readout("removed_excluded_accounts", _("Removed — excluded accounts")),
                    _readout("removed_suppliers", _("Removed — suppliers")),
                    _readout("removed_previous_batches", _("Removed — previous batches")),
                    _readout("removed_sent_this_month", _("Removed — sent this month")),
                    _readout("removed_meta_errors", _("Removed — Meta errors")),
                    _readout("removed_duplicates", _("Removed — duplicate phones")),
                    {"separator": "bold"},
                    _readout("final_contacts", _("Final contacts"), highlight=True),
                    _readout("group_count", _("Groups"), highlight=True),
                ],
            },
        }
    },
}
