from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class PartnerTerritory(models.Model):
    _name = "res.partner.territory"
    _description = "Partner Territory Information"

    name = fields.Char("Name", required=True)
    parent_id = fields.Many2one("res.partner.territory", "Parent", index=True, ondelete="cascade")

    @api.constrains("name")
    def _check_unique_name(self):
        if self.search([("name", "=", self.name), ("id", "!=", self.id)]):
            raise UserError(
                _(
                    "Territory names must be unique per Territory."
                )
            )

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True

    @api.multi
    def name_get(self):
        def get_names(territory):
            """ Return the list [territory.name, ...] """
            res = []
            while territory:
                res.append(territory.name)
                territory = territory.parent_id
            return res

        return [(territory.id, " / ".join(reversed(get_names(territory)))) for territory in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            territory_names = name.split(' / ')
            parents = list(territory_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
                territory_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    territorys = self.search([('id', 'not in', territory_ids)])
                    domain = expression.OR([[('parent_id', 'in', territory_ids.ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', territory_ids)], domain])
                for i in range(1, len(territory_names)):
                    domain = [[('name', operator, ' / '.join(territory_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            territorys = self.search(expression.AND([domain, args]), limit=limit)
        else:
            territorys = self.search(args, limit=limit)
        return territorys.name_get()
