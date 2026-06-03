import logging

from odoo import api, models, tools


_logger = logging.getLogger(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _access_management_hidden_menu_ids(self):
        rules = self.env["access.management"].with_context(skip_access_management=True)._rules_for_current_user()
        hidden_roots = rules.mapped("menu_ids")
        if not hidden_roots:
            return set()
        return set(
            self.with_context(skip_access_management=True, **{"ir.ui.menu.full_list": True})
            .sudo()
            .search([("id", "child_of", hidden_roots.ids)])
            .ids
        )

    def _load_menus_blacklist(self):
        blacklist = set(super()._load_menus_blacklist())
        try:
            blacklist.update(self._access_management_hidden_menu_ids())
        except Exception:
            _logger.exception("Failed to apply Access Management menu blacklist.")
        return list(blacklist)

    def _access_management_prune_loaded_menus(self, menus):
        hidden_menu_ids = self._access_management_hidden_menu_ids()
        if not hidden_menu_ids or not isinstance(menus, dict):
            return menus

        pruned = {}
        for menu_id, menu_data in menus.items():
            if menu_id in hidden_menu_ids:
                continue
            if isinstance(menu_data, dict):
                menu_data = dict(menu_data)
                children = menu_data.get("children")
                if isinstance(children, list):
                    if children and isinstance(children[0], dict):
                        menu_data["children"] = [
                            child for child in children if child.get("id") not in hidden_menu_ids
                        ]
                    else:
                        menu_data["children"] = [
                            child_id for child_id in children if child_id not in hidden_menu_ids
                        ]
                all_menu_ids = menu_data.get("all_menu_ids")
                if isinstance(all_menu_ids, list):
                    menu_data["all_menu_ids"] = [
                        menu_id for menu_id in all_menu_ids if menu_id not in hidden_menu_ids
                    ]
            pruned[menu_id] = menu_data
        return pruned

    @api.model
    def load_menus_root(self):
        menus = super().load_menus_root()
        try:
            return self._access_management_prune_loaded_menus(menus)
        except Exception:
            _logger.exception("Failed to prune Access Management root menus.")
            return menus

    @api.model
    def load_menus(self, debug):
        menus = super().load_menus(debug)
        try:
            return self._access_management_prune_loaded_menus(menus)
        except Exception:
            _logger.exception("Failed to prune Access Management loaded menus.")
            return menus

    @api.model
    def load_web_menus(self, debug):
        load_web_menus = getattr(super(), "load_web_menus", None)
        menus = load_web_menus(debug) if load_web_menus else self.load_menus(debug)
        try:
            return self._access_management_prune_loaded_menus(menus)
        except Exception:
            _logger.exception("Failed to prune Access Management web menus.")
            return menus

    @api.model
    @tools.ormcache("self.env.uid", "frozenset(self.env.user.groups_id.ids)", "debug")
    def _visible_menu_ids(self, debug=False):
        menu_ids = super()._visible_menu_ids(debug=debug)
        try:
            hidden_menu_ids = self._access_management_hidden_menu_ids()
            if hidden_menu_ids:
                menu_ids = set(menu_ids) - hidden_menu_ids
        except Exception:
            _logger.exception("Failed to apply Access Management hidden menus.")
        return menu_ids
