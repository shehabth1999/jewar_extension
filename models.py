# -*- coding: utf-8 -*-
# Models for jewar_extension module
from django.db import models
from django.utils.translation import gettext_lazy as _

from modules.base.models.partner import Partner, PartnerManager


class JewarContactManager(PartnerManager):
    """
    Manager for the jewar contacts view.

    Scopes the (real) ``base.Partner`` records down to the contacts that belong
    to WhatsApp accounts where the CURRENT user is an *admin* (the account's
    ``admins`` M2M). A contact "belongs to" an account when it has a chat
    conversation on that account (``Partner.social_conversations`` ->
    ``Conversation.social_account`` GenericForeignKey).

    This scoping lives ONLY on this proxy model, so ``base.Partner`` everywhere
    else in the system (Contacts app, CRM, chat, ...) is completely unaffected.

    Rules:
      * no request/user in context  -> nothing (secure default)
      * superuser                   -> everything (bypass, like the rest of the app)
      * user admins no account       -> nothing
      * otherwise                    -> contacts of the user's admin accounts only
    """

    def get_queryset(self):
        from django.contrib.contenttypes.models import ContentType
        from modules.base.middleware import get_current_user
        from modules.whatsapp.models.account import WhatsAppAccount

        # Same base as the normal Partner list (excludes AI / system users).
        qs = super().get_queryset()

        user = get_current_user()
        if user is None or not getattr(user, "is_authenticated", False):
            return qs.none()

        # Superusers bypass the account scope, consistent with the rest of the app.
        if user.is_superuser:
            return qs

        admin_account_ids = list(
            user.admin_whatsapp_accounts.values_list("id", flat=True)
        )
        if not admin_account_ids:
            return qs.none()

        wa_ct = ContentType.objects.get_for_model(WhatsAppAccount)
        return qs.filter(
            social_conversations__social_account_content_type=wa_ct,
            social_conversations__social_account_object_id__in=admin_account_ids,
        ).distinct()


class JewarContact(Partner):
    """
    Proxy over ``base.Partner`` — these are the SAME real contact records, not a
    separate table. Only the read scope differs: list/form views built on this
    model show a user only the contacts of the WhatsApp accounts they administer.

    Permissions are independent from ``base.partner`` (Django gives a proxy its
    own content type + perms), so delete is gated separately via
    ``delete_jewarcontact`` (granted to ``contacts.admins`` only) — see
    ``security/model_permissions.py``.
    """

    objects = JewarContactManager()

    class Meta:
        proxy = True
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
