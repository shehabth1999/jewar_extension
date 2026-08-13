# -*- coding: utf-8 -*-
"""Background jobs for jewar_extension."""
import logging

from celery import shared_task
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def _notify(user_id, job, subject, body):
    """Tell the user the build finished.

    post_notification rather than a raw websocket push: the build runs for
    minutes, by which time the user has almost certainly left the Groups screen,
    and a websocket frame reaches nobody if they are not connected. This writes
    a real inbox row that is still there when they come back.

    Best effort — a notification problem must never fail a build that succeeded.
    """
    if not user_id:
        return
    try:
        from modules.base.models import User
        from modules.notifications.services.post_notification import post_notification

        partner_id = User.objects.filter(pk=user_id).values_list('partner_id', flat=True).first()
        if not partner_id:
            logger.info("group build: user %s has no partner, cannot notify", user_id)
            return

        post_notification(
            partner_ids=[partner_id],
            subject=subject,
            body=body,
            message_type='system',
            notification_type='inbox',
            record=job,
            # Registered category (group "System"). An invented key would sit
            # outside the user's notification preferences entirely.
            category='system',
        )
    except Exception as exc:
        logger.warning("group build: notification failed for user %s: %s", user_id, exc)


@shared_task(name='jewar_extension.run_group_build', bind=True)
def run_group_build(self, job_id, options, user_id=None):
    """Build one batch of WhatsApp contact groups.

    Model imports stay inside the body: the worker builds its model classes from
    the extension registry at startup, and importing at module level races that.
    """
    from django.utils import timezone

    from .models import GroupBuildJob
    from .services.group_builder import BuildOptions, build

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
        job.refresh_from_db()
        _notify(user_id, job,
                _('WhatsApp groups — build failed'),
                _('Batch "%(hint)s" failed: %(error)s') % {'hint': job.batch_hint, 'error': exc})
        raise

    plan = result['plan']
    GroupBuildJob.objects.filter(pk=job_id).update(
        status='completed',
        completed_at=timezone.now(),
        groups_created=result['groups'],
        processed_records=result['contacts'],
        result_message=plan.as_text())

    job.refresh_from_db()
    _notify(user_id, job,
            _('WhatsApp groups are ready'),
            _('Batch "%(hint)s": %(groups)s groups built for %(contacts)s contacts.') % {
                'hint': job.batch_hint,
                'groups': f"{result['groups']:,}",
                'contacts': f"{result['contacts']:,}",
            })

    return {'job_id': job_id, 'groups': result['groups'], 'contacts': result['contacts']}
