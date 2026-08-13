# extensions/jewar_extension/management/commands/build_whatsapp_groups.py
"""Same builder as the UI button, for the terminal or a cron job."""
import traceback

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Build a batch of WhatsApp contact groups (250 per group, one series per account)'

    def add_arguments(self, parser):
        parser.add_argument('--hint', required=True,
                            help='Batch name, prefixes every group (e.g. xx1)')
        parser.add_argument('--size', type=int, default=250, help='Contacts per group')
        parser.add_argument('--exclude-account', type=int, action='append', default=[],
                            dest='exclude_accounts', help='WhatsApp account id to skip (repeatable)')
        parser.add_argument('--include-suppliers', action='store_true',
                            help='Do not filter out suppliers')
        parser.add_argument('--no-dedupe', action='store_true',
                            help='Keep every duplicate contact row for the same phone')
        parser.add_argument('--include-meta-errors', action='store_true',
                            help='Do not filter out numbers Meta refused')
        parser.add_argument('--exclude-templated-this-month', action='store_true')
        parser.add_argument('--exclude-any-previous-batch', action='store_true')
        parser.add_argument('--exclude-batch', default='',
                            help='Skip contacts already in this batch')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show the breakdown but do not create anything')

    def handle(self, *args, **options):
        from jewar_extension.services.group_builder import BuildOptions, build, compute, running_job

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        build_options = BuildOptions(
            batch_hint=options['hint'].strip(),
            group_size=options['size'],
            exclude_account_ids=tuple(sorted(options['exclude_accounts'])),
            exclude_suppliers=not options['include_suppliers'],
            dedupe_handsets=not options['no_dedupe'],
            exclude_meta_errors=not options['include_meta_errors'],
            exclude_templated_this_month=options['exclude_templated_this_month'],
            exclude_any_previous_batch=options['exclude_any_previous_batch'],
            exclude_batch_hint=options['exclude_batch'].strip(),
        )

        self.stdout.write(self.style.NOTICE(f"Planning batch '{build_options.batch_hint}'..."))
        plan = compute(build_options)
        self.stdout.write(plan.as_text())
        self.stdout.write('')
        for account_id, ids in sorted(plan.per_account.items(), key=lambda kv: -len(kv[1])):
            name = plan.account_names.get(account_id) or f'account {account_id}'
            groups = -(-len(ids) // max(1, build_options.group_size))
            self.stdout.write(f'  {name[:28]:<28} {len(ids):>7,} -> {groups:>4} groups')

        if not plan.final_contacts:
            self.stdout.write(self.style.WARNING('\nNo contacts match these filters.'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - nothing written.'))
            return

        busy = running_job()
        if busy is not None:
            self.stdout.write(self.style.ERROR(
                f'\nAnother WhatsApp group build is currently running (job #{busy.id}).'))
            return

        # A job row here as well as in the button path, so a CLI run and a UI
        # run block each other rather than both building the same batch.
        from django.utils import timezone

        from jewar_extension.models import GroupBuildJob

        job = GroupBuildJob.objects.create(
            batch_hint=build_options.batch_hint, status='processing',
            options=build_options.to_dict(), total_records=plan.final_contacts,
            started_at=timezone.now())

        try:
            result = build(build_options, job=job)
        except Exception as exc:
            GroupBuildJob.objects.filter(pk=job.pk).update(
                status='failed', completed_at=timezone.now(), result_message=str(exc)[:2000])
            self.stdout.write(self.style.ERROR(f'\nBuild failed: {exc}'))
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return

        GroupBuildJob.objects.filter(pk=job.pk).update(
            status='completed', completed_at=timezone.now(),
            groups_created=result['groups'], processed_records=result['contacts'],
            result_message=result['plan'].as_text())

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('EXECUTION SUMMARY'))
        self.stdout.write('=' * 50)
        self.stdout.write(f"Batch: {build_options.batch_hint}")
        self.stdout.write(f"Groups created: {result['groups']:,}")
        self.stdout.write(f"Contacts placed: {result['contacts']:,}")
        self.stdout.write(self.style.SUCCESS('Completed successfully'))
