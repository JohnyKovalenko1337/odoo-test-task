from odoo import fields, models


class EquipmentIssueWizard(models.TransientModel):
    _name = 'equipment.issue.wizard'
    _description = 'Видача обладнання'
    _check_company_auto = True

    equipment_id = fields.Many2one(
        'maintenance.equipment', string='Основний засіб', required=True,
        check_company=True,
    )
    company_id = fields.Many2one('res.company', related='equipment_id.company_id')
    employee_id = fields.Many2one(
        'hr.employee', string='Співробітник', required=True, check_company=True,
    )
    issue_date = fields.Date(
        string='Дата видачі', required=True, default=fields.Date.context_today,
    )

    def action_issue(self):
        self.ensure_one()
        self.check_access('read')
        assignment = self.env['equipment.assignment'].create({
            'equipment_id': self.equipment_id.id,
            'employee_id': self.employee_id.id,
            'issue_date': self.issue_date,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'equipment.assignment',
            'res_id': assignment.id,
            'view_mode': 'form',
            'target': 'current',
        }
