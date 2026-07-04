# -*- coding: utf-8 -*-
# Models for jewar_extension module
#
# No models. The WhatsApp-account contact scoping is done via a global access
# condition on the real base.partner (see security/access_conditions.py), so no
# proxy model is needed.
from modules.base.models.base import BaseModel  # noqa: F401
