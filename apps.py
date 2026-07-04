from django.apps import AppConfig


class JewarExtensionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.jewar_extension'

    def ready(self):
        # Register the `user.whatsapp_admin_contact_ids` special value used by the
        # access condition in security/access_conditions.py.
        from modules.jewar_extension.patches import apply_patches
        apply_patches()
