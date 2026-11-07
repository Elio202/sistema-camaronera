"""Ensamblaje de rutas HTTP con sus controladores."""

from app.controllers.base_controller import BaseController
from app.controllers.delete_controller import DeleteController
from app.controllers.get_controller import GetController
from app.controllers.patch_controller import PatchController
from app.controllers.post_controller import PostController


class App(GetController, PostController, DeleteController, PatchController, BaseController):
    """Manejador HTTP compuesto por controladores seg?n el m?todo solicitado."""

    pass
