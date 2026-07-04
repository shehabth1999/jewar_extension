# -*- coding: utf-8 -*-
"""
Runtime patch, kept inside jewar_extension so the whole feature stays local
(no core files edited).

The access condition in security/access_conditions.py filters base.partner by
``id IN <the contacts of the WhatsApp accounts I administer>``. That list is
per-user and can't be expressed by Genie's condition resolver (the account link
is a GenericForeignKey; the resolver only knows user.id / dates / content types).

We therefore register ONE token, ``user.whatsapp_admin_contact_ids``, and resolve
it to a concrete list of partner ids **before** the condition is handed to
``apply_dict_filters`` — because the pydantic layer validates that the ``in``
operator has a real list at parse time (a raw token string fails validation).

So we wrap ``AccessCondition.apply_to_queryset``: if a condition contains our
token, substitute the resolved list into a copy of the condition, then delegate
to the original method. Conditions without the token are passed through untouched.
"""
import logging

logger = logging.getLogger(__name__)

TOKEN = "user.whatsapp_admin_contact_ids"
_PATCHED = False


def apply_patches():
    global _PATCHED
    if _PATCHED:
        return
    from modules.base.models.access_conditions import AccessCondition

    _orig_apply = AccessCondition.apply_to_queryset

    def apply_to_queryset(self, queryset, permission_type="view", user=None):
        if _contains_token(self.condition):
            saved = self.condition
            try:
                # instances come fresh from get_conditions_for_model() per call,
                # so swapping self.condition here is request-local and safe.
                self.condition = _resolve_tokens(saved)
                return _orig_apply(self, queryset, permission_type, user)
            finally:
                self.condition = saved
        return _orig_apply(self, queryset, permission_type, user)

    AccessCondition.apply_to_queryset = apply_to_queryset
    _PATCHED = True
    logger.info(
        "jewar_extension: patched AccessCondition.apply_to_queryset for "
        "'%s'", TOKEN,
    )


def _contains_token(node):
    if isinstance(node, dict):
        return any(_contains_token(v) for v in node.values())
    if isinstance(node, list):
        return any(_contains_token(v) for v in node)
    return node == TOKEN


def _resolve_tokens(node):
    if isinstance(node, dict):
        return {k: _resolve_tokens(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_tokens(v) for v in node]
    if node == TOKEN:
        return _whatsapp_admin_contact_ids()
    return node


# Sentinel returned when the user should see nothing. `id IN (-1)` matches no
# partner (ids are positive) and keeps the `in` operator non-empty, which the
# pydantic filter layer requires — cleaner than letting an empty list raise.
_MATCH_NOTHING = [-1]


def _whatsapp_admin_contact_ids():
    from django.contrib.contenttypes.models import ContentType
    from modules.base.middleware import get_current_user
    from modules.base.models import Partner
    from modules.whatsapp.models.account import WhatsAppAccount

    user = get_current_user()
    if user is None or not getattr(user, "is_authenticated", False):
        return _MATCH_NOTHING  # secure default off-request / anonymous
    account_ids = list(user.admin_whatsapp_accounts.values_list("id", flat=True))
    if not account_ids:
        return _MATCH_NOTHING
    wa_ct = ContentType.objects.get_for_model(WhatsAppAccount)
    # Raw ORM (not the DRF layer) -> no recursion into access conditions.
    ids = list(
        Partner.objects.filter(
            social_conversations__social_account_content_type=wa_ct,
            social_conversations__social_account_object_id__in=account_ids,
        )
        .values_list("id", flat=True)
        .distinct()
    )
    return ids or _MATCH_NOTHING
