# -*- coding: utf-8 -*-
"""Model extensions for jewar_extension.

Everything here lives outside `modules/` on purpose — this is customer-specific
behaviour and must survive a core upgrade untouched.
"""
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from modules.base.decorators import action, onchange
from modules.base.model_inheritance import ModelExtension

logger = logging.getLogger(__name__)


class CampaignExtension(ModelExtension):
    """Marks a chat.Campaign as belonging to a generated batch.

    The batch is stored, not parsed out of the group name: "exclude anyone in
    batch xx1" has to keep working after somebody renames a group in the UI.
    """

    _inherit = 'chat.campaign'
    _depends = ['chat', 'whatsapp']

    batch_hint = models.CharField(_("Batch"), max_length=64, blank=True, null=True,
                                  db_index=True)
    whatsapp_account = models.ForeignKey(
        'whatsapp.WhatsAppAccount', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contact_groups', verbose_name=_("WhatsApp Account"))

    @onchange('group_size', 'excluded_accounts', 'exclude_suppliers', 'dedupe_handsets',
              'exclude_meta_errors', 'exclude_templated_this_month',
              'exclude_any_previous_batch', 'exclude_specific_batch', 'exclude_batch_hint')
    def _onchange_build_groups_preview(self):
        """Footer preview for the build wizard, registered on this model too.

        The wizard opens as a slideover, and in that mode the frontend sends the
        list screen's model — this one — on the onchange call instead of the
        wizard's. None of these fields exist on a Campaign, so the values come
        from the posted payload rather than from self.
        """
        # Relative: this package is imported as "modules.jewar_extension" in-repo
        # and as top-level "jewar_extension" when the fleet clones it into
        # extensions/. An absolute import names one layout and breaks the other.
        from .services.group_builder import preview

        return preview(getattr(self, '_original_data', None) or {})

    @action
    def build_whatsapp_groups(self, record):
        """Build a new batch of WhatsApp contact groups."""
        from django.utils import timezone

        from .models import GroupBuildJob
        from .services.group_builder import BuildOptions, compute, running_job
        from .tasks import run_group_build

        hint = (record.batch_hint or '').strip()
        if not hint:
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("Enter a batch name first.")}

        if record.exclude_specific_batch and not (record.exclude_batch_hint or '').strip():
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("Enter the batch name you want to exclude.")}

        if record.group_size and not (10 <= record.group_size <= 1000):
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("Group size must be between 10 and 1000.")}

        busy = running_job()
        if busy is not None:
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("Another WhatsApp group build is currently running.")}

        options = BuildOptions.from_wizard(record)
        plan = compute(options)
        if not plan.final_contacts:
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("No contacts match these filters — nothing to build.")}

        job = GroupBuildJob.objects.create(
            batch_hint=hint, status='pending', options=options.to_dict(),
            total_records=plan.final_contacts, started_at=timezone.now())

        # The row is written before the enqueue so a task that starts instantly
        # still finds it. That ordering means a failed enqueue leaves a 'pending'
        # row behind — and because running_job() counts 'pending' as live, that
        # one row would answer "another build is currently running" to every
        # later attempt, forever. Fail it explicitly instead.
        try:
            async_result = run_group_build.delay(job.id, options.to_dict())
        except Exception as exc:
            logger.exception("could not queue group build job %s", job.id)
            GroupBuildJob.objects.filter(pk=job.pk).update(
                status='failed', completed_at=timezone.now(),
                result_message=f'could not reach the task queue: {exc}'[:2000])
            return {'status': False, 'open_mode': 'message', 'data': {},
                    'message': _("Could not queue the build — the task queue is unreachable. Nothing was created.")}

        GroupBuildJob.objects.filter(pk=job.pk).update(celery_task_id=async_result.id or '')

        return {
            'status': True,
            'open_mode': 'message',
            'data': {'job_id': job.id},
            'message': _('Building "%(hint)s" in the background — %(contacts)s contacts into %(groups)s groups. Job #%(job)s.'
                         ) % {'hint': hint, 'contacts': f'{plan.final_contacts:,}',
                 'groups': plan.group_count, 'job': job.id},
            'on_success': {'type': 'refresh'},
        }
