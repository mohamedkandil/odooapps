from odoo import models, api

class Users(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def add_to_group_all_users(self, group_id):
        """إضافة جميع المستخدمين النشطين لمجموعة"""
        users = self.search([('active', '=', True)])
        group = self.env['res.groups'].browse(group_id)
        
        for user in users:
            if group not in user.groups_id:
                user.write({'groups_id': [(4, group.id)]})
        
        return True