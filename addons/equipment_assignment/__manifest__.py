{
    'name': 'Видача обладнання співробітникам',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Видача, повернення та історія використання основних засобів',
    'depends': ['hr_maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'security/equipment_assignment_security.xml',
        'wizard/equipment_issue_views.xml',
        'report/equipment_issue_report.xml',
        'views/equipment_assignment_views.xml',
        'views/maintenance_equipment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
