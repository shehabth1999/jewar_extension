# -*- coding: utf-8 -*-
"""
Runtime patch, kept inside jewar_extension so the whole feature stays local
(no core files edited).

Genie's filter/domain/condition resolver (``DjangoFilterConverter._process_special_values``)
only understands ``user`` / ``user.id`` / ``user.pk`` / dates / ``app.model``
content-type strings. It canNOT turn "me" into "the contacts of the WhatsApp
accounts I administer" — that link is a GenericForeignKey and needs a per-user
list. So we register ONE extra token used by security/access_conditions.py:

    user.whatsapp_admin_contact_ids
      -> distinct base.Partner ids that have a conversation on a WhatsApp account
         where the current user is an admin (empty if no user / admins nothing).

Resolving to a flat list of partner ids (instead of joining on the reverse
relation inside the condition) keeps the condition a simple ``id IN (...)`` — no
duplicate rows, no GFK traversal in the filter itself.
"""
import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def apply_patches():
    global _PATCHED
    if _PATCHED:
        return
    from modules.base.utils.filter_schema import DjangoFilterConverter

    _orig_process = DjangoFilterConverter._process_special_values  # bound classmethod

    def _process_special_values(cls, value):
        if value == "user.whatsapp_admin_contact_ids":
            return _whatsapp_admin_contact_ids()
        return _orig_process(value)  # delegate everything else, unchanged

    DjangoFilterConverter._process_special_values = classmethod(_process_special_values)
    _PATCHED = True
    logger.info(
        "jewar_extension: registered special value 'user.whatsapp_admin_contact_ids'"
    )


def _whatsapp_admin_contact_ids():
    from django.contrib.contenttypes.models import ContentType
    from modules.base.middleware import get_current_user
    from modules.base.models import Partner
    from modules.whatsapp.models.account import WhatsAppAccount

    user = get_current_user()
    if user is None or not getattr(user, "is_authenticated", False):
        return []  # secure default off-request / anonymous
    account_ids = list(user.admin_whatsapp_accounts.values_list("id", flat=True))
    if not account_ids:
        return []
    wa_ct = ContentType.objects.get_for_model(WhatsAppAccount)
    # Raw ORM (not the DRF layer) -> no recursion into access conditions.
    return list(
        Partner.objects.filter(
            social_conversations__social_account_content_type=wa_ct,
            social_conversations__social_account_object_id__in=account_ids,
        )
        .values_list("id", flat=True)
        .distinct()
    )
