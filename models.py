# -*- coding: utf-8 -*-
# Models for jewar_extension module
#
# Contact scoping is done via a global access condition on the real base.partner
# (see security/access_conditions.py), so no proxy model is needed.
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from modules.base.decorators import onchange
from modules.base.models.base import BaseModel  # noqa: F401
from modules.base.models.mixins import TransientModel

logger = logging.getLogger(__name__)


class GroupBuildJob(BaseModel):
    """One run of the WhatsApp group builder.

    Exists for two reasons: it is the single-flight lock (only one build may be
    in flight, claimed atomically), and it is the audit trail — these groups have
    been rebuilt by hand several times with no record of which filters produced
    which batch.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    batch_hint = models.CharField(_("Batch name"), max_length=64)
    status = models.CharField(_("Status"), max_length=16, choices=STATUS_CHOICES,
                              default='pending', db_index=True)
    options = models.JSONField(_("Options"), default=dict, blank=True)
    total_records = models.IntegerField(_("Total contacts"), default=0)
    processed_records = models.IntegerField(_("Processed"), default=0)
    groups_created = models.IntegerField(_("Groups created"), default=0)
    result_message = models.TextField(_("Result"), blank=True, default='')
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("WhatsApp Group Build")
        verbose_name_plural = _("WhatsApp Group Builds")
        ordering = ['-id']

    def __str__(self):
        return f'{self.batch_hint} ({self.status})'


class BuildGroupsWizard(TransientModel):
    """The slideover form behind the "Build WhatsApp Groups" button.

    The ``preview_*`` fields are not settings — they are written by the
    @onchange in extensions.py and rendered in the form footer, so the user sees
    the real counts before committing.
    """
    batch_hint = models.CharField(_("Batch name"), max_length=64)
    group_size = models.PositiveIntegerField(_("Group size"), default=250)
    excluded_accounts = models.ManyToManyField(
        'whatsapp.WhatsAppAccount', blank=True, related_name='+',
        verbose_name=_("Exclude accounts"))

    exclude_suppliers = models.BooleanField(_("Exclude suppliers"), default=True)
    dedupe_handsets = models.BooleanField(_("Split repeated numbers"), default=True)
    exclude_meta_errors = models.BooleanField(_("Exclude Meta errors"), default=True)
    exclude_templated_this_month = models.BooleanField(
        _("Exclude contacts already sent a template this month"), default=False)
    exclude_any_previous_batch = models.BooleanField(
        _("Exclude contacts in any previous batch"), default=False)
    exclude_specific_batch = models.BooleanField(
        _("Exclude contacts in a specific batch"), default=False)
    exclude_batch_hint = models.CharField(_("Batch name to exclude"), max_length=64,
                                          blank=True, default='')

    # --- footer preview (read-only, recomputed on every change) -------------
    total_contacts = models.IntegerField(default=0)
    unique_phones = models.IntegerField(default=0)
    removed_excluded_accounts = models.IntegerField(default=0)
    removed_suppliers = models.IntegerField(default=0)
    removed_previous_batches = models.IntegerField(default=0)
    removed_sent_this_month = models.IntegerField(default=0)
    removed_meta_errors = models.IntegerField(default=0)
    removed_duplicates = models.IntegerField(default=0)
    final_contacts = models.IntegerField(default=0)
    group_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = _("Build WhatsApp Groups")
        verbose_name_plural = _("Build WhatsApp Groups")

    def __str__(self):
        return self.batch_hint or 'build groups'

    @onchange('group_size', 'excluded_accounts', 'exclude_suppliers', 'dedupe_handsets',
              'exclude_meta_errors', 'exclude_templated_this_month',
              'exclude_any_previous_batch', 'exclude_specific_batch', 'exclude_batch_hint')
    def _onchange_preview(self):
        """Repaint the footer with the real numbers for the current settings.

        The whole scan is ~1.5s over 160k rows, so this runs inline rather than
        making the user press a preview button.
        """
        from jewar_extension.services.group_builder import preview

        return preview(getattr(self, '_original_data', None) or {})
