from django.apps import AppConfig


class JewarExtensionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'

    # Derived, not hardcoded, because this package is imported under two
    # different names depending on where it is deployed:
    #
    #   modules/jewar_extension          -> "modules.jewar_extension"
    #   <app>/extensions/jewar_extension -> "jewar_extension"
    #
    # The fleet clones it into extensions/, which settings.py puts on sys.path,
    # so there it is a TOP-LEVEL package. A hardcoded name breaks whichever
    # layout it does not name, and it breaks it hard: Django raises
    # ImproperlyConfigured during django.setup(), so the entire application
    # fails to start rather than just this one module.
    name = __name__.rpartition('.')[0]

    def ready(self):
        # Register the `user.whatsapp_admin_contact_ids` special value used by the
        # access condition in security/access_conditions.py.
        # Relative import, for the same reason as `name` above.
        from .patches import apply_patches
        apply_patches()
