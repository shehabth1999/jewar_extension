# -*- coding: utf-8 -*-
# Wizard behind the "Build WhatsApp Groups" button on the Groups screen.
#
# Layout note: FormGroup renders its own fields `grid-cols-1` — always one per
# line — and only *groups* sit side by side (FormRow is `@3xl:grid-cols-2`, a
# container query on the <form>). The slideover opens at size xl = 900px, which
# clears @3xl, so every section here carries TWO groups to get two real columns.
# One group per section is what makes this form a single tall stack.
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


# The wizard is a TransientModel, so the form always opens in create mode and the
# frontend seeds it from `defaultValue` alone — the backend does not inject model
# defaults into the schema. Without these the switches render OFF while the model
# (and BuildOptions) say True, and the build silently filters nothing.
_ONLY_SPECIFIC_BATCH = {
    "field": "exclude_specific_batch",
    "operator": "eq",
    "value": False,
}


jewar_build_groups_form_view = {
    "key": "jewar_build_groups_form_view",
    "name": _("Build WhatsApp Groups"),
    "priority": 1,
    "module": "jewar_extension",
    "model": "jewar_extension.buildgroupswizard",
    "view_type": "form",
    "body": {
        "sheet": {
            "title": {
                "title": _("New batch"),
                "fields": [
                    {
                        "name": "batch_hint",
                        "string": _("Batch name"),
                        "widget": "text",
                        "required": True,
                        "maxLength": 64,
                        "placeholder": _("e.g. xx1"),
                        # Kept on one line: collect_translations matches the
                        # gettext call with a regex, so a string split across
                        # lines by implicit concatenation is never extracted
                        # and can never be translated.
                        "help": _('Prefixes every group in this run, e.g. "xx1 basmala 1 / 250"'),
                    },
                ],
            },
            "sections": [
                {
                    "title": _("Batch"),
                    "groups": [
                        {
                            "title": _("Sizing"),
                            "fields": [
                                {
                                    "name": "group_size",
                                    "string": _("Group size"),
                                    "widget": "number",
                                    "required": True,
                                    "min": 10,
                                    "max": 1000,
                                    "step": 10,
                                    "defaultValue": 250,
                                    "onChange": True,
                                    "onChangeTrigger": "blur",
                                    "help": _("Contacts per group (10-1000)"),
                                },
                            ],
                        },
                        {
                            "title": _("Accounts"),
                            "fields": [
                                {
                                    "name": "excluded_accounts",
                                    "string": _("Exclude accounts"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "multiSelect": True,
                                    "onChange": True,
                                    "placeholder": _("All accounts included"),
                                    "help": _("These accounts get no groups at all"),
                                    "domain": {
                                        "filters": {
                                            "operator": "and",
                                            "filters": [
                                                {"field": "active", "operator": "eq",
                                                 "value": True},
                                            ],
                                        }
                                    },
                                    "context": {"default_fields": {"active": True}},
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": _("Filters"),
                    "groups": [
                        {
                            "title": _("Skip these contacts"),
                            "fields": [
                                {
                                    "name": "exclude_suppliers",
                                    "string": _("Suppliers"),
                                    "widget": "switch",
                                    "defaultValue": True,
                                    "onChange": True,
                                    "help": _("Contacts flagged as suppliers never receive a marketing group"),
                                },
                                {
                                    "name": "exclude_meta_errors",
                                    "string": _("Meta errors"),
                                    "widget": "switch",
                                    "defaultValue": True,
                                    "onChange": True,
                                    "help": _("Numbers Meta says cannot or should not receive marketing"),
                                },
                            ],
                        },
                        {
                            "title": _("Repeats & recent sends"),
                            "fields": [
                                {
                                    "name": "dedupe_handsets",
                                    "string": _("Split repeated numbers"),
                                    "widget": "switch",
                                    "defaultValue": True,
                                    "onChange": True,
                                    "help": _("The same person under several accounts is placed once, spread to balance the load"),
                                },
                                {
                                    "name": "exclude_templated_this_month",
                                    "string": _("Sent a template this month"),
                                    "widget": "switch",
                                    "onChange": True,
                                    "help": _("Leaves out anyone who already got a template message this calendar month"),
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": _("Previous batches"),
                    "groups": [
                        {
                            "title": _("Skip contacts already grouped"),
                            "fields": [
                                {
                                    "name": "exclude_any_previous_batch",
                                    "string": _("In any previous batch"),
                                    "widget": "switch",
                                    "onChange": True,
                                },
                                {
                                    "name": "exclude_specific_batch",
                                    "string": _("In one specific batch"),
                                    "widget": "switch",
                                    "onChange": True,
                                    "help": _("Use this to catch contacts added since a batch was built"),
                                },
                            ],
                        },
                        {
                            # Hidden as a whole so the column title does not sit
                            # above an empty slot while the toggle is off.
                            "title": _("Which batch"),
                            "invisible": _ONLY_SPECIFIC_BATCH,
                            "fields": [
                                {
                                    "name": "exclude_batch_hint",
                                    "string": _("Batch name to exclude"),
                                    "widget": "text",
                                    "maxLength": 64,
                                    "placeholder": _("e.g. xx1"),
                                    "onChange": True,
                                    "invisible": _ONLY_SPECIFIC_BATCH,
                                },
                            ],
                        },
                    ],
                },
                {
                    # Targeting, not suppression: leaving both empty means every
                    # contact qualifies. Picking anything here narrows the build
                    # to the contacts that match.
                    "title": _("Targeting"),
                    "groups": [
                        {
                            "title": _("Tags"),
                            "fields": [
                                {
                                    "name": "tags",
                                    "string": _("Only contacts with these tags"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "multiSelect": True,
                                    "onChange": True,
                                    "placeholder": _("Any tag"),
                                    "help": _("Leave empty to include contacts regardless of their tags"),
                                },
                            ],
                        },
                        {
                            "title": _("CRM"),
                            "fields": [
                                {
                                    "name": "lead_stages",
                                    "string": _("Only contacts whose latest lead is in these stages"),
                                    "widget": "relation",
                                    "displayField": "name",
                                    "multiSelect": True,
                                    "onChange": True,
                                    "placeholder": _("Any stage"),
                                    "help": _("Uses the most recent lead per contact, not every lead they ever had"),
                                },
                            ],
                        },
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
                    _readout("removed_no_tag_match", _("Removed — tag mismatch")),
                    _readout("removed_no_stage_match", _("Removed — lead stage mismatch")),
                    _readout("removed_duplicates", _("Removed — duplicate phones")),
                    {"separator": "bold"},
                    _readout("final_contacts", _("Final contacts"), highlight=True),
                    _readout("group_count", _("Groups"), highlight=True),
                ],
            },
        }
    },
}
