from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class AccessManagement(models.Model):
    _name = "access.management"
    _description = "Access Management"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    user_ids = fields.Many2many("res.users", string="Users", required=True)
    company_ids = fields.Many2many("res.company", string="Companies")
    group_id = fields.Many2one("res.groups", string="Technical Group", copy=False, readonly=True)
    readonly_user = fields.Boolean(string="Read-only")
    disable_developer_mode = fields.Boolean(string="Disable Developer Mode")

    hide_chatter = fields.Boolean()
    hide_send_message = fields.Boolean()
    hide_log_notes = fields.Boolean()
    hide_schedule_activity = fields.Boolean()

    hide_import = fields.Boolean()
    hide_export = fields.Boolean()
    hide_spreadsheet = fields.Boolean()
    hide_add_property = fields.Boolean()

    menu_ids = fields.Many2many("ir.ui.menu", string="Hidden Menus")
    model_access_ids = fields.One2many("access.management.model.line", "access_id", string="Model Access")
    field_access_ids = fields.One2many("access.management.field.line", "access_id", string="Field Access")
    domain_access_ids = fields.One2many("access.management.domain.line", "access_id", string="Domain Access")
    button_access_ids = fields.One2many("access.management.button.line", "access_id", string="Button/Tab Access")
    filter_access_ids = fields.One2many("access.management.filter.line", "access_id", string="Hide Filter/Group By")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_security()
        records._clear_menu_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_security()
        self._clear_menu_cache()
        return res

    def unlink(self):
        groups = self.mapped("group_id")
        rules = self.mapped("domain_access_ids.rule_id")
        res = super().unlink()
        rules.unlink()
        groups.unlink()
        self._clear_menu_cache()
        return res

    def _clear_menu_cache(self):
        self.env.registry.clear_cache()

    def _sync_security(self):
        for access in self:
            access._sync_group()
            access.domain_access_ids._sync_ir_rules()

    def _sync_group(self):
        self.ensure_one()
        if not self.group_id:
            self.group_id = self.env["res.groups"].sudo().create({
                "name": "Access Management: %s" % self.name,
                "category_id": self.env.ref("base.module_category_hidden").id,
            })
        self.group_id.sudo().write({
            "name": "Access Management: %s" % self.name,
            "users": [(6, 0, self.user_ids.ids)],
        })

    @api.model
    def _rules_for_current_user(self):
        user = self.env.user
        domain = [
            ("active", "=", True),
            ("user_ids", "in", [user.id]),
            "|",
            ("company_ids", "=", False),
            ("company_ids", "in", [self.env.company.id]),
        ]
        return self.with_context(skip_access_management=True).sudo().search(domain)


class AccessManagementModelLine(models.Model):
    _name = "access.management.model.line"
    _description = "Access Management Model Line"

    access_id = fields.Many2one("access.management", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    hide_create = fields.Boolean()
    hide_edit = fields.Boolean()
    hide_delete = fields.Boolean()
    hide_duplicate = fields.Boolean()
    hide_archive = fields.Boolean()


class AccessManagementFieldLine(models.Model):
    _name = "access.management.field.line"
    _description = "Access Management Field Line"

    access_id = fields.Many2one("access.management", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade")
    field_id = fields.Many2one("ir.model.fields", string="Field", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    field_name = fields.Char(related="field_id.name", store=True, readonly=True)
    readonly = fields.Boolean()
    invisible = fields.Boolean()
    required = fields.Boolean()

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_id = False
        return {"domain": {"field_id": [("model_id", "=", self.model_id.id)]}}


class AccessManagementDomainLine(models.Model):
    _name = "access.management.domain.line"
    _description = "Access Management Domain Line"

    access_id = fields.Many2one("access.management", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    name = fields.Char(required=True, default="Domain Rule")
    domain_force = fields.Text(default="[]", required=True)
    perm_read = fields.Boolean(default=True)
    perm_write = fields.Boolean(default=True)
    perm_create = fields.Boolean(default=True)
    perm_unlink = fields.Boolean(default=True)
    rule_id = fields.Many2one("ir.rule", string="Generated Rule", copy=False, readonly=True)

    @api.constrains("domain_force")
    def _check_domain_force(self):
        for line in self:
            try:
                domain = safe_eval(line.domain_force or "[]", {"user": self.env.user})
                expression.normalize_domain(domain)
            except Exception as error:
                raise ValidationError(_("Invalid domain: %s") % error) from error

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_ir_rules()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_ir_rules()
        return res

    def unlink(self):
        rules = self.mapped("rule_id")
        res = super().unlink()
        rules.unlink()
        return res

    def _sync_ir_rules(self):
        for line in self:
            if not line.access_id.group_id:
                line.access_id._sync_group()
            vals = {
                "name": "%s / %s" % (line.access_id.name, line.name),
                "model_id": line.model_id.id,
                "domain_force": line.domain_force,
                "perm_read": line.perm_read,
                "perm_write": line.perm_write,
                "perm_create": line.perm_create,
                "perm_unlink": line.perm_unlink,
                "groups": [(6, 0, [line.access_id.group_id.id])],
                "active": line.access_id.active,
            }
            if line.rule_id:
                line.rule_id.sudo().write(vals)
            else:
                line.rule_id = self.env["ir.rule"].sudo().create(vals)


class AccessManagementButtonLine(models.Model):
    _name = "access.management.button.line"
    _description = "Access Management Button and Tab Line"

    access_id = fields.Many2one("access.management", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    type = fields.Selection([("button", "Button"), ("tab", "Tab")], required=True, default="button")
    technical_name = fields.Char(required=True, help="Button name or page technical name.")
    string = fields.Char(help="Optional visible label/string to match.")


class AccessManagementFilterLine(models.Model):
    _name = "access.management.filter.line"
    _description = "Access Management Filter Line"

    access_id = fields.Many2one("access.management", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", store=True, readonly=True)
    filter_name = fields.Char(required=True, help="Search filter/group technical name.")
