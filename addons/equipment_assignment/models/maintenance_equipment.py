from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    assignment_ids = fields.One2many(
        'equipment.assignment', 'equipment_id', string='Історія видачі', copy=False,
    )
    assignment_count = fields.Integer(
        string='Видачі', compute='_compute_assignment_count', compute_sudo=True,
    )
    assignment_days = fields.Integer(
        string='Днів у співробітника', compute='_compute_assignment_days',
    )

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for equipment in self:
            equipment.assignment_count = len(equipment.assignment_ids)

    @api.depends('employee_id', 'assign_date')
    def _compute_assignment_days(self):
        today = fields.Date.context_today(self)
        for equipment in self:
            equipment.assignment_days = (
                max((today - equipment.assign_date).days, 0)
                if equipment.employee_id and equipment.assign_date else 0
            )

    def _lock_for_assignment(self):
        self.check_access('write')
        if not self:
            return
        self.flush_recordset()
        # Serialize issue/return operations for the same physical item.
        self.env.cr.execute(SQL(
            'SELECT id FROM maintenance_equipment WHERE id IN %s ORDER BY id FOR UPDATE',
            tuple(self.ids),
        ))
        self.invalidate_recordset()

    def _set_employee_assignment(self, employee, issue_date):
        self.ensure_one()
        # Private helper: no context flag that an RPC caller could forge.
        return super().write({
            'equipment_assign_to': 'employee',
            'employee_id': employee.id if employee else False,
            'assign_date': issue_date,
        })

    @api.model_create_multi
    def create(self, vals_list):
        equipment = super().create(vals_list)
        if equipment.filtered('employee_id'):
            raise UserError(_('Спочатку створіть обладнання, потім натисніть «Видано».'))
        return equipment

    def write(self, vals):
        if {'employee_id', 'assign_date'} & vals.keys():
            raise UserError(_('Використовуйте кнопки «Видано» та «Повернути».'))
        if {'company_id', 'active', 'equipment_assign_to', 'department_id'} & vals.keys():
            self._lock_for_assignment()
            if self.filtered('employee_id'):
                raise UserError(_('Спочатку поверніть обладнання зі співробітника.'))
            if 'company_id' in vals and self.assignment_ids:
                raise UserError(_('Компанію обладнання з історією видачі змінювати не можна.'))
        return super().write(vals)

    def copy(self, default=None):
        default = dict(default or {}, employee_id=False, assign_date=False)
        return super().copy(default)

    def action_issue(self):
        self.ensure_one()
        self.check_access('write')
        self.env['equipment.assignment'].check_access('create')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Видача обладнання'),
            'res_model': 'equipment.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_equipment_id': self.id},
        }

    def action_return(self):
        self.ensure_one()
        self._lock_for_assignment()
        assignment = self.env['equipment.assignment'].search([
            ('equipment_id', '=', self.id), ('return_date', '=', False),
        ])
        if not assignment:
            raise UserError(_('Немає активної видачі для повернення.'))
        return assignment.action_return()

    def action_view_assignments(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'equipment_assignment.action_equipment_assignment',
        )
        action['domain'] = [('equipment_id', '=', self.id)]
        action['context'] = {}
        return action
