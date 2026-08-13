# -*- coding: utf-8 -*-
"""Build WhatsApp contact groups (chat.Campaign) in slices of N, one series per account.

One module, three callers: the @onchange preview, the celery task and the
management command. They must never disagree, so every number the user sees in
the wizard footer comes out of :func:`compute` — the same function the build runs.

Two things this solves that hand-built groups could not:

* **The same human is several contact rows.** ``UniqueConstraint(phone,
  whatsapp_account)`` (modules/whatsapp/extensions.py) makes a customer who
  messaged two of the company numbers two Partner rows *by design*. Left alone,
  that customer receives the same campaign from every number. 139,865 rows in
  this database are only 98,757 people.
* **Templates are account-bound.** A WhatsAppTemplate belongs to one account and
  send-time validation rejects the WHOLE batch if any recipient's account differs
  (modules/whatsapp/tasks.py). So a group must never mix accounts, and a handset
  cannot simply be moved to a less busy account — it has to already exist there.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Grouping key for "same handset". Digits only, last 10, so that a local
# ``01005101964`` and an international ``201005101964`` collapse to one person.
#
# This is deliberately NOT modules.whatsapp.utils.phone.normalize_phone: that
# helper runs `phonenumbers` per number, which costs ~7s over this table and
# would make the live wizard preview unusable (the whole scan is 0.9s with this
# key). It is also the same last-10-digit prefilter that
# modules/whatsapp/services/partner_linking.py already clusters on.
CANON = ("right(regexp_replace(coalesce(nullif(p.phone,''), p.mobile, ''), "
         "'[^0-9]', '', 'g'), 10)")

MIN_DIGITS = 8
TEMPLATE_SENT = ("m.direction = 'outbound' "
                 "and (m.type = 'template' or m.original_type = 'template') "
                 "and m.status in ('delivered', 'sent')")

# Meta failure codes that mean "do not send to this person again", and for how
# long. Codes 131042 / 131031 / 130403 are deliberately absent: those are OUR
# account's billing/restriction faults, and suppressing on them would poison
# ~1,500 perfectly good contacts for a problem on our side.
META_BLOCK_CODES = {
    '131026': None,   # not a WhatsApp user - permanent
    '131049': 30,     # Meta is rate-limiting marketing to this user
    '130472': 90,     # user is in Meta's marketing-limit experiment group
}


@dataclass(frozen=True)
class BuildOptions:
    batch_hint: str
    group_size: int = 250
    exclude_account_ids: tuple = ()
    exclude_suppliers: bool = True
    dedupe_handsets: bool = True
    exclude_meta_errors: bool = True
    exclude_templated_this_month: bool = False
    exclude_any_previous_batch: bool = False
    exclude_batch_hint: str = ''

    @classmethod
    def from_wizard(cls, record):
        # During @onchange the wizard row may not be saved yet, and an unsaved
        # instance cannot be asked for its m2m. The proxy stashes pending m2m
        # assignments on _m2m_data, so read that first and fall back to the
        # relation only once the row exists.
        pending = (getattr(record, '_m2m_data', None) or {}).get('excluded_accounts')
        if pending is not None:
            excluded = tuple(sorted(int(a.pk if hasattr(a, 'pk') else a) for a in pending))
        elif record.pk:
            excluded = tuple(sorted(record.excluded_accounts.values_list('id', flat=True)))
        else:
            excluded = ()
        return cls(
            batch_hint=(record.batch_hint or '').strip(),
            group_size=record.group_size or 250,
            exclude_account_ids=excluded,
            exclude_suppliers=bool(record.exclude_suppliers),
            dedupe_handsets=bool(record.dedupe_handsets),
            exclude_meta_errors=bool(record.exclude_meta_errors),
            exclude_templated_this_month=bool(record.exclude_templated_this_month),
            exclude_any_previous_batch=bool(record.exclude_any_previous_batch),
            exclude_batch_hint=(record.exclude_batch_hint or '').strip()
            if record.exclude_specific_batch else '',
        )

    @classmethod
    def from_values(cls, values):
        """Build from the raw form payload an @onchange receives."""
        values = values or {}

        def flag(key, default=False):
            raw = values.get(key, default)
            if isinstance(raw, str):
                return raw.lower() in ('1', 'true', 'yes', 'on')
            return bool(raw)

        accounts = values.get('excluded_accounts') or []
        if isinstance(accounts, (int, str)):
            accounts = [accounts]
        excluded = []
        for item in accounts:
            if isinstance(item, dict):
                item = item.get('id')
            try:
                excluded.append(int(item))
            except (TypeError, ValueError):
                continue

        try:
            size = int(values.get('group_size') or 250)
        except (TypeError, ValueError):
            size = 250

        return cls(
            batch_hint=str(values.get('batch_hint') or '').strip(),
            group_size=size,
            exclude_account_ids=tuple(sorted(excluded)),
            exclude_suppliers=flag('exclude_suppliers', True),
            dedupe_handsets=flag('dedupe_handsets', True),
            exclude_meta_errors=flag('exclude_meta_errors', True),
            exclude_templated_this_month=flag('exclude_templated_this_month'),
            exclude_any_previous_batch=flag('exclude_any_previous_batch'),
            exclude_batch_hint=(str(values.get('exclude_batch_hint') or '').strip()
                                if flag('exclude_specific_batch') else ''),
        )

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, data):
        data = dict(data or {})
        data['exclude_account_ids'] = tuple(data.get('exclude_account_ids') or ())
        return cls(**data)


@dataclass
class BuildPlan:
    """The funnel, in the order the wizard footer shows it.

    ``total_contacts - every removed_* == final_contacts`` always holds; the
    steps are applied in sequence so nothing is counted twice.
    """
    total_contacts: int = 0
    unique_phones: int = 0
    removed_excluded_accounts: int = 0
    removed_suppliers: int = 0
    removed_previous_batches: int = 0
    removed_sent_this_month: int = 0
    removed_meta_errors: int = 0
    removed_duplicates: int = 0
    final_contacts: int = 0
    group_count: int = 0
    per_account: dict = field(default_factory=dict)   # account_id -> [partner_id]
    account_names: dict = field(default_factory=dict)

    def footer_values(self):
        """The dict an @onchange returns to repaint the wizard footer."""
        return {
            'total_contacts': self.total_contacts,
            'unique_phones': self.unique_phones,
            'removed_excluded_accounts': self.removed_excluded_accounts,
            'removed_suppliers': self.removed_suppliers,
            'removed_previous_batches': self.removed_previous_batches,
            'removed_sent_this_month': self.removed_sent_this_month,
            'removed_meta_errors': self.removed_meta_errors,
            'removed_duplicates': self.removed_duplicates,
            'final_contacts': self.final_contacts,
            'group_count': self.group_count,
        }

    def as_text(self):
        lines = [
            f"Total contacts        {self.total_contacts:>10,}",
            f"Unique phones         {self.unique_phones:>10,}",
            "Removed:",
            f"  Excluded accounts   {self.removed_excluded_accounts:>10,}",
            f"  Suppliers           {self.removed_suppliers:>10,}",
            f"  Previous batches    {self.removed_previous_batches:>10,}",
            f"  Sent this month     {self.removed_sent_this_month:>10,}",
            f"  Meta errors         {self.removed_meta_errors:>10,}",
            f"  Duplicate phones    {self.removed_duplicates:>10,}",
            f"Final contacts        {self.final_contacts:>10,}",
            f"Groups                {self.group_count:>10,}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# exclusion sets
# ---------------------------------------------------------------------------

def _partner_ids_in_batches(cur, hint=None):
    """Partners already sitting in a generated batch (any, or one named hint)."""
    sql = ("select distinct g.partner_id from base_partner_groups g "
           "join chat_campaign c on c.id = g.campaign_id "
           "where c.batch_hint is not null and c.batch_hint <> ''")
    params = []
    if hint:
        sql += " and c.batch_hint = %s"
        params.append(hint)
    cur.execute(sql, params)
    return {r[0] for r in cur.fetchall()}


def _partner_ids_templated_since(cur, since):
    cur.execute(
        f"select distinct cv.social_partner_id from chat_message m "
        f"join chat_conversation cv on cv.id = m.conversation_id "
        f"where {TEMPLATE_SENT} and cv.social_partner_id is not null "
        f"and m.created_at >= %s", [since])
    return {r[0] for r in cur.fetchall()}


def _partner_ids_meta_blocked(cur):
    """Recipients Meta told us not to message again, per META_BLOCK_CODES."""
    now = timezone.now()
    blocked = set()
    for code, days in META_BLOCK_CODES.items():
        sql = ("select distinct cv.social_partner_id from chat_message m "
               "join chat_conversation cv on cv.id = m.conversation_id "
               "where m.status = 'refused' and m.direction = 'outbound' "
               "and (m.type = 'template' or m.original_type = 'template') "
               "and cv.social_partner_id is not null "
               "and m.reason like %s")
        params = [f'%Error code: {code}%']
        if days is not None:
            sql += " and m.created_at >= %s"
            params.append(now - timedelta(days=days))
        cur.execute(sql, params)
        blocked |= {r[0] for r in cur.fetchall()}
    return blocked


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------

def compute(options: BuildOptions) -> BuildPlan:
    """Read-only. Returns the funnel counts AND the exact per-account assignment.

    The assignment is computed here rather than in the build so that the number
    of groups shown in the preview is the number of groups actually created.
    Whole thing is ~0.9s over 160k rows.
    """
    plan = BuildPlan()
    excluded_accounts = set(options.exclude_account_ids or ())

    with connection.cursor() as cur:
        cur.execute(
            f"select p.id, p.whatsapp_account_id, {CANON}, coalesce(p.supplier, false) "
            f"from base_partner p "
            f'where p."system_user" = false and p.active = true '
            f"  and p.whatsapp_account_id is not null "
            f"  and length({CANON}) >= {MIN_DIGITS}")
        rows = cur.fetchall()

        cur.execute("select id, trim(coalesce(name, '')) from whatsapp_whatsappaccount")
        plan.account_names = dict(cur.fetchall())

        prev_ids = set()
        if options.exclude_any_previous_batch:
            prev_ids = _partner_ids_in_batches(cur)
        elif options.exclude_batch_hint:
            prev_ids = _partner_ids_in_batches(cur, options.exclude_batch_hint)

        month_ids = set()
        if options.exclude_templated_this_month:
            start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_ids = _partner_ids_templated_since(cur, start)

        meta_ids = _partner_ids_meta_blocked(cur) if options.exclude_meta_errors else set()

    plan.total_contacts = len(rows)

    # When we dedupe, an exclusion is about the PERSON, not the row: if any row
    # of a handset was templated this month, the handset is out everywhere. That
    # is the whole point - excluding only the row leaks the ad out of a
    # different account under a duplicate row.
    def promote(ids):
        if not options.dedupe_handsets or not ids:
            return ids
        phones = {ph for pid, _aid, ph, _sup in rows if pid in ids}
        return {pid for pid, _aid, ph, _sup in rows if ph in phones}

    prev_ids, month_ids, meta_ids = promote(prev_ids), promote(month_ids), promote(meta_ids)

    # Sequential funnel - each row is removed by the first rule that catches it,
    # so the counts add up to total_contacts exactly.
    kept = []
    for pid, aid, ph, supplier in rows:
        if aid in excluded_accounts:
            plan.removed_excluded_accounts += 1
        elif options.exclude_suppliers and supplier:
            plan.removed_suppliers += 1
        elif pid in prev_ids:
            plan.removed_previous_batches += 1
        elif pid in month_ids:
            plan.removed_sent_this_month += 1
        elif pid in meta_ids:
            plan.removed_meta_errors += 1
        else:
            kept.append((pid, aid, ph))

    plan.unique_phones = len({ph for _pid, _aid, ph in kept})

    if options.dedupe_handsets:
        assignment = _assign_balanced(kept)
        plan.removed_duplicates = len(kept) - len(assignment)
    else:
        assignment = [(pid, aid) for pid, aid, _ph in kept]
        plan.removed_duplicates = 0

    per_account = defaultdict(list)
    for pid, aid in assignment:
        per_account[aid].append(pid)
    for aid in per_account:
        per_account[aid].sort()

    plan.per_account = dict(per_account)
    plan.final_contacts = len(assignment)
    size = max(1, options.group_size)
    plan.group_count = sum(-(-len(ids) // size) for ids in per_account.values())
    return plan


def _assign_balanced(kept):
    """One row per handset, spreading the duplicates so the load evens out.

    A handset that exists on only one account is pinned there - nothing can move
    it, because a Partner row for it does not exist anywhere else. Only handsets
    that already exist on several accounts are free, and those get handed to
    whichever of *their own* accounts is currently lightest. Processing the most
    constrained handsets first, in sorted order, keeps the result identical
    across runs - re-running the wizard must not reshuffle everyone.
    """
    clusters = defaultdict(dict)          # phone -> {account_id: partner_id}
    for pid, aid, ph in kept:
        current = clusters[ph].get(aid)
        if current is None or pid < current:
            clusters[ph][aid] = pid       # lowest id wins within one account

    load = Counter()
    out = []
    movable = []
    for ph, by_account in clusters.items():
        if len(by_account) == 1:
            (aid, pid), = by_account.items()
            out.append((pid, aid))
            load[aid] += 1
        else:
            movable.append(ph)

    for ph in sorted(movable, key=lambda p: (len(clusters[p]), p)):
        by_account = clusters[ph]
        aid = min(by_account, key=lambda a: (load[a], a))
        out.append((by_account[aid], aid))
        load[aid] += 1

    return out


# ---------------------------------------------------------------------------
# the build
# ---------------------------------------------------------------------------

def build(options: BuildOptions, job=None) -> dict:
    """Create the groups. Never deletes or edits an existing group.

    Each run is a new batch tagged with ``batch_hint``, so a rebuild cannot
    cascade into whatsapp_whatsappcampaign rows the way deleting groups does.
    """
    from modules.chat.models import Campaign

    plan = compute(options)
    size = max(1, options.group_size)
    created = links = 0

    if job is not None:
        job.total_records = plan.final_contacts
        job.save(update_fields=['total_records'])

    with connection.cursor() as cur:
        for aid in sorted(plan.per_account, key=lambda a: -len(plan.per_account[a])):
            ids = plan.per_account[aid]
            account_name = plan.account_names.get(aid) or f'account {aid}'
            for start in range(0, len(ids), size):
                chunk = ids[start:start + size]
                name = f'{options.batch_hint} {account_name} {start + 1} / {start + len(chunk)}'
                with transaction.atomic():
                    cur.execute(
                        "insert into chat_campaign "
                        "(name, created_at, updated_at, active, batch_hint, whatsapp_account_id) "
                        "values (%s, now(), now(), true, %s, %s) returning id",
                        [name, options.batch_hint, aid])
                    campaign_id = cur.fetchone()[0]
                    for i in range(0, len(chunk), 1000):
                        part = chunk[i:i + 1000]
                        values = ','.join(['(%s,%s)'] * len(part))
                        params = [x for pid in part for x in (pid, campaign_id)]
                        cur.execute(
                            f"insert into base_partner_groups (partner_id, campaign_id) "
                            f"values {values} on conflict (partner_id, campaign_id) do nothing",
                            params)
                created += 1
                links += len(chunk)

            if job is not None:
                job.processed_records = links
                job.save(update_fields=['processed_records'])

    logger.info("jewar group build '%s': %s groups, %s memberships",
                options.batch_hint, created, links)
    return {'groups': created, 'contacts': links, 'plan': plan}


def preview(values):
    """The @onchange body, shared by both entry points.

    The wizard is opened as a slideover, and in that mode the frontend sends the
    *parent* screen's model (chat.campaign) on the onchange call rather than the
    wizard's own. Rather than bet on which one arrives, the method is registered
    on both models and both land here with the same raw payload.

    Returns an Odoo-style onchange result: {'value': ...} or {'errors': ...}.
    """
    from django.utils.translation import gettext as _

    values = values or {}
    if values.get('exclude_specific_batch') and not str(
            values.get('exclude_batch_hint') or '').strip():
        return {'errors': {'exclude_batch_hint': _("Enter the batch name to exclude.")}}

    size = values.get('group_size')
    if size not in (None, '') and not (10 <= int(size) <= 1000):
        return {'errors': {'group_size': _("Group size must be between 10 and 1000.")}}

    try:
        plan = compute(BuildOptions.from_values(values))
    except Exception:
        logger.exception("group build preview failed")
        return None
    return {'value': plan.footer_values()}


def running_job():
    """The build job currently occupying the queue, if any."""
    from jewar_extension.models import GroupBuildJob
    return GroupBuildJob.objects.filter(status__in=('pending', 'processing')).first()
