import json

from lxml import etree

from odoo import api, models
from odoo.exceptions import AccessError


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _access_management_rules(self):
        if self.env.context.get("skip_access_management"):
            return self.env["access.management"]
        return self.env["access.management"]._rules_for_current_user()

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if not res.get("arch"):
            return res

        rules = self._access_management_rules()
        if not rules:
            return res

        doc = etree.fromstring(res["arch"])
        self._apply_model_access_to_view(doc, rules)
        self._apply_field_access_to_view(doc, rules)
        self._apply_button_tab_access_to_view(doc, rules)
        self._apply_filter_access_to_view(doc, rules)
        self._apply_global_access_to_view(doc, rules)
        res["arch"] = etree.tostring(doc, encoding="unicode")
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        rules = self._access_management_rules()
        if not rules:
            return result

        if any(rules.mapped("readonly_user")):
            for field_info in result.values():
                field_info["readonly"] = True

        for line in rules.mapped("field_access_ids").filtered(lambda item: item.model == self._name):
            if line.field_name in result:
                if line.readonly:
                    result[line.field_name]["readonly"] = True
                if line.invisible:
                    result[line.field_name]["invisible"] = True
                if line.required:
                    result[line.field_name]["required"] = True
        return result

    @api.model_create_multi
    def create(self, vals_list):
        self._check_access_management_readonly("create")
        return super().create(vals_list)

    def write(self, vals):
        self._check_access_management_readonly("write")
        if vals.get("active") is False:
            self._check_access_management_archive()
        return super().write(vals)

    def unlink(self):
        self._check_access_management_readonly("unlink")
        return super().unlink()

    def copy(self, default=None):
        self._check_access_management_duplicate()
        return super().copy(default=default)

    def _check_access_management_readonly(self, operation):
        if self.env.context.get("skip_access_management") or self.env.su:
            return
        if self._name.startswith(("access.management", "ir.rule", "res.groups")):
            return
        rules = self.env["access.management"]._rules_for_current_user()
        if any(rules.mapped("readonly_user")):
            raise AccessError("This user is read-only and cannot %s records." % operation)
        model_lines = rules.mapped("model_access_ids").filtered(lambda item: item.model == self._name)
        blocked = any(
            (operation == "create" and line.hide_create)
            or (operation == "write" and line.hide_edit)
            or (operation == "unlink" and line.hide_delete)
            for line in model_lines
        )
        if blocked:
            raise AccessError("This access rule does not allow you to %s records." % operation)

    def _check_access_management_duplicate(self):
        if self.env.context.get("skip_access_management") or self.env.su:
            return
        rules = self.env["access.management"]._rules_for_current_user()
        model_lines = rules.mapped("model_access_ids").filtered(lambda item: item.model == self._name)
        if any(model_lines.mapped("hide_duplicate")):
            raise AccessError("This access rule does not allow you to duplicate records.")

    def _check_access_management_archive(self):
        if self.env.context.get("skip_access_management") or self.env.su:
            return
        rules = self.env["access.management"]._rules_for_current_user()
        model_lines = rules.mapped("model_access_ids").filtered(lambda item: item.model == self._name)
        if any(model_lines.mapped("hide_archive")):
            raise AccessError("This access rule does not allow you to archive records.")

    @api.model
    def _apply_model_access_to_view(self, doc, rules):
        model_lines = rules.mapped("model_access_ids").filtered(lambda item: item.model == self._name)
        readonly_user = any(rules.mapped("readonly_user"))
        if readonly_user:
            for node in doc.xpath("//form|//tree|//kanban|//calendar|//pivot|//graph"):
                node.set("create", "false")
                node.set("edit", "false")
                node.set("delete", "false")
                node.set("duplicate", "false")
        for line in model_lines:
            for node in doc.xpath("//form|//tree|//kanban|//calendar|//pivot|//graph"):
                if line.hide_create:
                    node.set("create", "false")
                if line.hide_edit:
                    node.set("edit", "false")
                if line.hide_delete:
                    node.set("delete", "false")
                if line.hide_duplicate:
                    node.set("duplicate", "false")

    @api.model
    def _apply_field_access_to_view(self, doc, rules):
        field_lines = rules.mapped("field_access_ids").filtered(lambda item: item.model == self._name)
        readonly_user = any(rules.mapped("readonly_user"))
        for node in doc.xpath("//field"):
            field_name = node.get("name")
            if readonly_user:
                self._set_node_modifier(node, "readonly", True)
            for line in field_lines.filtered(lambda item: item.field_name == field_name):
                if line.readonly:
                    self._set_node_modifier(node, "readonly", True)
                if line.invisible:
                    self._set_node_modifier(node, "invisible", True)
                if line.required:
                    self._set_node_modifier(node, "required", True)

    @api.model
    def _apply_button_tab_access_to_view(self, doc, rules):
        lines = rules.mapped("button_access_ids").filtered(lambda item: item.model == self._name)
        for line in lines:
            if line.type == "button":
                xpath = "//button[@name='%s']" % line.technical_name
                if line.string:
                    xpath += "|//button[@string='%s']" % line.string
            else:
                xpath = "//page[@name='%s']" % line.technical_name
                if line.string:
                    xpath += "|//page[@string='%s']" % line.string
            for node in doc.xpath(xpath):
                self._set_node_modifier(node, "invisible", True)

    @api.model
    def _apply_global_access_to_view(self, doc, rules):
        if any(rules.mapped("hide_import")):
            for node in doc.xpath("//tree|//kanban"):
                node.set("import", "false")
        if any(rules.mapped("hide_export")):
            for node in doc.xpath("//tree|//pivot|//graph"):
                node.set("export_xlsx", "false")
        if any(rules.mapped("hide_chatter")):
            for node in doc.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' oe_chatter ')]"):
                self._set_node_modifier(node, "invisible", True)
        if any(rules.mapped("hide_send_message")):
            for node in doc.xpath("//button[contains(@class, 'o_ChatterTopbar_buttonSendMessage')]"):
                self._set_node_modifier(node, "invisible", True)
        if any(rules.mapped("hide_log_notes")):
            for node in doc.xpath("//button[contains(@class, 'o_ChatterTopbar_buttonLogNote')]"):
                self._set_node_modifier(node, "invisible", True)
        if any(rules.mapped("hide_schedule_activity")):
            for node in doc.xpath("//button[contains(@class, 'o_ChatterTopbar_buttonScheduleActivity')]"):
                self._set_node_modifier(node, "invisible", True)

    @api.model
    def _apply_filter_access_to_view(self, doc, rules):
        lines = rules.mapped("filter_access_ids").filtered(lambda item: item.model == self._name)
        for line in lines:
            for node in doc.xpath("//filter[@name='%s']|//separator[@name='%s']" % (line.filter_name, line.filter_name)):
                node.getparent().remove(node)

    @api.model
    def _set_node_modifier(self, node, key, value):
        node.set(key, "1" if value else "0")
        modifiers = json.loads(node.get("modifiers") or "{}")
        modifiers[key] = value
        node.set("modifiers", json.dumps(modifiers))
