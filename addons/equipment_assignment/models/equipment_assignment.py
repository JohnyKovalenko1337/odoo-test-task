from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EquipmentAssignment(models.Model):
    _name = 'equipment.assignment'
    _description = 'Історія видачі обладнання'
    _order = 'issue_date desc, id desc'
    _rec_name = 'equipment_id'
    _check_company_auto = True

    equipment_id = fields.Many2one(
        'maintenance.equipment', string='Основний засіб', required=True,
        ondelete='restrict', check_company=True, index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Співробітник', required=True,
        ondelete='restrict', check_company=True, index=True,
    )
    company_id = fields.Many2one(
        'res.company', related='equipment_id.company_id', store=True, precompute=True,
        string='Компанія', required=True,
    )
    issue_date = fields.Date(
        string='Дата видачі', required=True, default=fields.Date.context_today,
    )
    return_date = fields.Date(string='Дата повернення', readonly=True, copy=False)
    issued_by = fields.Many2one('res.users', string='Видав', readonly=True)
    returned_by = fields.Many2one('res.users', string='Повернення прийняв', readonly=True)
    days_held = fields.Integer(string='Кількість днів', compute='_compute_days_held')
    state = fields.Selection(
        [('issued', 'Видано'), ('returned', 'Повернуто')],
        string='Статус', compute='_compute_state', store=True, precompute=True,
    )
    active_equipment_id = fields.Many2one(
        'maintenance.equipment', compute='_compute_state', store=True, precompute=True, copy=False,
        ondelete='restrict',
    )

    _sql_constraints = [
        ('one_active_assignment', 'unique(active_equipment_id)',
         'Це обладнання вже видано співробітнику.'),
        ('return_after_issue', 'CHECK(return_date IS NULL OR return_date >= issue_date)',
         'Дата повернення не може бути раніше дати видачі.'),
    ]

    @api.depends('return_date', 'equipment_id')
    def _compute_state(self):
        for assignment in self:
            assignment.state = 'returned' if assignment.return_date else 'issued'
            assignment.active_equipment_id = (
                False if assignment.return_date else assignment.equipment_id
            )

    @api.depends('issue_date', 'return_date')
    def _compute_days_held(self):
        today = fields.Date.context_today(self)
        for assignment in self:
            end = assignment.return_date or today
            assignment.days_held = (end - assignment.issue_date).days if assignment.issue_date else 0

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access('create')
        protected_fields = {'state', 'active_equipment_id', 'issued_by', 'returned_by', 'company_id'}
        defaults = self.default_get(
            ['equipment_id', 'employee_id', 'issue_date', 'return_date'] + sorted(protected_fields),
        )
        values = [dict(defaults, **vals) for vals in vals_list]
        equipment = self.env['maintenance.equipment'].browse([
            vals.get('equipment_id') for vals in values if vals.get('equipment_id')
        ])
        if not equipment:
            raise ValidationError(_('Оберіть обладнання.'))
        equipment._lock_for_assignment()
        for vals in values:
            if vals.get('return_date') or protected_fields & vals.keys():
                raise UserError(_('Історія створюється під час видачі обладнання.'))
            item = equipment.browse(vals.get('equipment_id')).exists()
            employee = self.env['hr.employee'].browse(vals.get('employee_id')).exists()
            employee.check_access('read')
            if not item or not employee:
                raise ValidationError(_('Оберіть обладнання та співробітника.'))
            if not item.active or not employee.active:
                raise ValidationError(_(
                    'Не можна видати архівне обладнання або видати його архівному співробітнику.',
                ))
            if item.employee_id or item.department_id:
                raise UserError(_('Обладнання вже призначене. Спочатку поверніть його.'))
            if not item.company_id or item.company_id != employee.company_id:
                raise ValidationError(_('Обладнання та співробітник повинні належати одній компанії.'))
            issue_date = fields.Date.to_date(vals.get('issue_date'))
            if not issue_date or issue_date > fields.Date.context_today(self):
                raise ValidationError(_('Дата видачі не може бути порожньою або майбутньою.'))
            last_return = self.search([
                ('equipment_id', '=', item.id), ('return_date', '!=', False),
            ], order='return_date desc', limit=1)
            if last_return and issue_date < last_return.return_date:
                raise ValidationError(_('Дата нової видачі не може бути раніше останнього повернення.'))
            vals['issued_by'] = self.env.uid
            vals['returned_by'] = False
        assignments = super().create(values)
        for assignment in assignments:
            assignment.equipment_id._set_employee_assignment(
                assignment.employee_id, assignment.issue_date,
            )
        return assignments

    def write(self, vals):
        self.check_access('write')
        if set(vals) != {'return_date'} or not vals['return_date']:
            raise UserError(_('Історію видачі змінювати не можна. Дозволене лише повернення.'))
        self.equipment_id._lock_for_assignment()
        self.invalidate_recordset()
        return_date = fields.Date.to_date(vals['return_date'])
        for assignment in self:
            if assignment.return_date:
                raise UserError(_('Обладнання вже повернуто.'))
            if return_date < assignment.issue_date or return_date > fields.Date.context_today(self):
                raise ValidationError(_('Дата повернення має бути між датою видачі та сьогодні.'))
        result = super().write(dict(vals, returned_by=self.env.uid))
        for assignment in self:
            assignment.equipment_id._set_employee_assignment(False, False)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise UserError(_('Історію видачі видаляти не можна.'))

    def copy(self, default=None):
        raise UserError(_('Для повторної видачі використовуйте картку обладнання.'))

    def action_return(self):
        self.write({'return_date': fields.Date.context_today(self)})
        return True

    def action_print_issue(self):
        self.check_access('read')
        return self.env.ref('equipment_assignment.action_report_equipment_issue').report_action(self)
