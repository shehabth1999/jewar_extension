# -*- coding: utf-8 -*-
"""Background jobs for jewar_extension."""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='jewar_extension.run_group_build', bind=True)
def run_group_build(self, job_id, options):
    """Build one batch of WhatsApp contact groups.

    Model imports stay inside the body: the worker builds its model classes from
    the extension registry at startup, and importing at module level races that.
    """
    from django.utils import timezone

    from jewar_extension.models import GroupBuildJob
    from jewar_extension.services.group_builder import BuildOptions, build

    # Atomic claim — the button is also guarded, but a retried or duplicated
    # task must never build the same batch twice.
    claimed = GroupBuildJob.objects.filter(pk=job_id, status='pending').update(
        status='processing', started_at=timezone.now())
    if not claimed:
        logger.warning("group build job %s was already claimed, skipping", job_id)
        return {'skipped': True, 'job_id': job_id}

    job = GroupBuildJob.objects.get(pk=job_id)
    try:
        result = build(BuildOptions.from_dict(options), job=job)
    except Exception as exc:
        logger.exception("group build job %s failed", job_id)
        GroupBuildJob.objects.filter(pk=job_id).update(
            status='failed', completed_at=timezone.now(), result_message=str(exc)[:2000])
        raise

    plan = result['plan']
    GroupBuildJob.objects.filter(pk=job_id).update(
        status='completed',
        completed_at=timezone.now(),
        groups_created=result['groups'],
        processed_records=result['contacts'],
        result_message=plan.as_text())

    return {'job_id': job_id, 'groups': result['groups'], 'contacts': result['contacts']}
