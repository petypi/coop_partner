from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class PartnerLocation(models.Model):
    _name = "res.partner.location"
    _description = "Partner Location Information"


    @api.multi
    @api.depends('partner_ids','agent_count')
    def _compute_agent_count(self):
        '''
        Computes the number of agents in a location
        :return:
        '''

        #Get the location id and sort in ascending order
        ids = self.ids
        ids.sort()
        size = len(ids)
        #Begin getting agents from last location in the list
        location_list = self._get_list(self.env['res.partner.location'].search([('id', '=', ids[size - 1])]))
        agent_list = []
        #populate agents from location
        while len(location_list) > 0:
            if self.env['res.partner.data'].search([('location_id', 'in', location_list)]):
                agent_list = agent_list + self._get_list(
                    self.env['res.partner.data'].search([('location_id', 'in', location_list)]))
            location_list = self._get_list(
                self.env['res.partner.location'].search([('parent_id', 'in', location_list)]))

        #Add agents to list
        loc = self.env['res.partner.location'].search([('id','=', ids[size-1])])
        loc.partner_ids = str(agent_list)
        #Saves agent_count to variable
        loc.agent_count = len(agent_list)

        return True

    @api.multi
    def get_agents(self):
        """
        Returns a view with all agents in that location
        :return:
        """
        import json
        partner_ids = json.loads(self.partner_ids)
        if len(partner_ids) > 0:
            return {
                'name': _('Agents'),
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'res.partner.data',
                'type': 'ir.actions.act_window',
                'context': {},
                'domain': [('id', 'in', partner_ids)],
            }


    def _get_list(self, collection):
        """
        Get a list of ID when given a list of objects
        :param collection:
        :return: list of ids
        """
        collection_list = []
        for data in collection:
            collection_list.append(data.id)
        return collection_list

    name = fields.Char("Name", required=True)
    parent_id = fields.Many2one("res.partner.location", "Parent", index=True, ondelete="cascade")
    active = fields.Boolean("active")
    location_ids = fields.One2many('res.partner.data', 'location_id', string='Locations')
    agent_count = fields.Integer("Agent Count", compute='_compute_agent_count', store=False)
    partner_ids = fields.Char("Agent Count", compute='_compute_agent_count', store=False)
    location_name = fields.Char("Display Name")

    @api.constrains("name")
    def _check_unique_name(self):
        if self.search([("name", "=", self.name), ("id", "!=", self.id)]):
            raise UserError(
                _(
                    "Location names must be unique per Location."
                )
            )

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))
        return True

    @api.onchange('parent_id', 'name')
    @api.one
    def update_display_name(self):
        """
        Update display name on change of parent_id or name
        :return:
        """
        self.generate_dispaly_name(self)

    def generate_display_name(self, location):
        """
        Generates the display name and update to database
        :return:
        """
        res = []
        # Hold inital location
        tmp_loc = location
        while location:
            res.append(location.name)
            location = location.parent_id

        # Generate display name
        location_name = " / ".join(reversed(res))

        # Generate dispaly name
        tmp_loc.write({'location_name': location_name})
        return tmp_loc.location_name

    @api.multi
    def name_get(self):
        return [(location.id, self.generate_display_name(location)) for location in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            location_names = name.split(' / ')
            parents = list(location_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args, operator='ilike', limit=limit)
                location_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    locations = self.search([('id', 'not in', location_ids)])
                    domain = expression.OR([[('parent_id', 'in', location_ids.ids)], domain])
                else:
                    domain = expression.AND([[('parent_id', 'in', location_ids)], domain])
                for i in range(1, len(location_names)):
                    domain = [[('name', operator, ' / '.join(location_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            locations = self.search(expression.AND([domain, args]), limit=limit)
        else:
            locations = self.search(args, limit=limit)
        return locations.name_get()


class LocationType(models.Model):
    _name = "res.partner.location.type"
    _description = "Location Type"

    name = fields.Char("Name", required=True)

    @api.constrains("name")
    def _check_unique_name(self):
        if self.search([("name", "=", self.name), ("id", "!=", self.id)]):
            raise UserError(
                _(
                    "Location Type names must be unique."
                )
            )
