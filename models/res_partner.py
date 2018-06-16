import re
import logging
import random
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, MissingError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger("Copia Partner")

_choice = [
    ("Y", "Yes"),
    ("N", "No")
]

_gender = [
    ("male", "Male"),
    ("female", "Female")
]

_age_range = [
    ("18-25", "Under 25"),
    ("25-39", "25-39"),
    ("40-54", "40-54"),
    ("55", "over 55")
]

_marital_status = [
    ("married", "Married"),
    ("single", "Single")
]

_partner_type = [
    ("customer", 'Customer'),
    ("agent", "Agent"),
    ("associate", "Associate")
]

_monthly_income = [
    ('<5000', 'Less than KES 5,000'),
    ('5,000 - 10,000', 'KES 5,000 - 10,000'),
    ('10,001 - 15,000', 'KES 10,001 - 15,000'),
    ('15,001 - 20,000', 'KES 15,001 - 20,000'),
    ('20,001 - 25,000', 'KES 20,001 - 25,000'),
    ('25,000 +', 'KES 25,000 +'),
]

_no_of_children = [
    ('0', '0'),
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
    ('10+', '10+'),
]

_child_age = [
    ('mdogo dana', 'Mdogo Sana'),
    ('nursery', 'Nursery'),
    ('primary', 'Primary'),
    ('secondary', 'Secondary'),
    ('university', 'University'),
    ('anafanya kazi', 'Anafanya kazi'),
]


class PartnerAgentType(models.Model):
    _name = "agent.type"

    name = fields.Char("Name", required=True)
    split_exempt = fields.Boolean("Exempt from Splits")
    default_sla_days = fields.Integer(
        "Default SLA Days", help="Default SLA Days per Agent Type", required=True, default=2
    )

    account_id = fields.Many2one("account.account", string="Account Receivable Type",
                                 domain=[('internal_type', '=', 'receivable'),
                                         ('deprecated', '=', False)])

    @api.constrains("name")
    @api.one
    def _check_name(self):
        if self.search_count([("name", "=", self.name), ("id", "!=", self.id)]):
            raise ValidationError(_(
                "Name must be unique per Agent Type"
            ))


class Partner(models.Model):
    _inherit = "res.partner"

    @api.one
    def _compute_has_partner_data(self):
        self.has_partner_data = False
        if self.partner_data:
            self.has_partner_data = True

    @api.one
    def _compute_sms_count(self):
        self.sms_count = self.env["sms.message"].search([("partner_id", "=", self.id)]).__len__()

    is_agent = fields.Boolean(string="Is Agent", help="Whether the partner is an Agent")
    agent_type_id = fields.Many2one("agent.type", string="Agent Type")
    can_purchase = fields.Boolean("Can Purchase")
    partner_data = fields.One2many("res.partner.data", "partner_id", string="Partner Data", ondelete="cascade")
    has_partner_data = fields.Boolean("Has Partner Data", compute="_compute_has_partner_data")
    sms_count = fields.Integer("Inbox/Outbox", compute="_compute_sms_count")
    active_agent = fields.Boolean(
        "Agent Activation", track_visibility="onchange", default=False, help="Whether the Agent is activated"
    )
    sale_associate_id = fields.Many2one("res.partner", string="Salesperson")
    is_sale_associate = fields.Boolean("Is Sales Associate", help="Whether the partner is a Sales Associate")
    partner_type = fields.Selection(_partner_type, string="Partner Type", store=True, track_visibility="onchange")
    credit_days = fields.Integer('Credit Days')
    agent_id = fields.Many2one('res.partner', "Agent Assigned To", domain=[('is_agent', '=', True)])

    @api.model
    def create(self, vals):
        if 'partner_type' in vals and 'agent_type_id' in vals:
            vals['active_agent'] = True
        return super(Partner, self).create(vals)

    @api.onchange("partner_type")
    def onchange_partner_type(self):
        self.is_agent = (self.partner_type == "agent")
        self.is_sale_associate = (self.partner_type == "associate")
        self.customer = (self.partner_type == "agent" or self.partner_type == "customer")
        self.can_purchase = (self.partner_type == "agent")

    @api.onchange("agent_type_id")
    def onchange_agent_type(self):
        '''
        ON agent changed change the account receivable account depending on the agent account assigned if no account is assigne
        assign the defaulf account receivable account
        :return: None
        '''
        if self.agent_type_id['account_id']:
            self.property_account_receivable_id = self.agent_type_id['account_id']
        else:
            self.property_account_receivable_id = \
                self.env['account.account'].search([('internal_type', '=', 'receivable'),
                                                    ('deprecated', '=', False)])[0]['id']

    @api.one
    @api.constrains("phone")
    def _check_phone(self):
        if self.phone:
            # TODO - replace the first \d{3} with res_partner.country_id.phone_code
            if re.match(r"^\+\d{3}\d{9}$", self.phone) is None:
                raise ValidationError("Phone Number MUST be in the format +2547xxxxxxxx, Not (%s)" % self.phone)

            if self.phone == self.mobile:
                raise ValidationError("Phone Number (%s) cannot be the same as mobile number." % self.phone)

            if self.search_count([("phone", "=", self.phone)]) > 1:
                raise ValidationError("Phone Number (%s) must be unique per Partner." % self.phone)

            elif self.search_count([("mobile", "=", self.phone)]) > 1:
                raise ValidationError("Mobile Number (%s) must be unique per Partner." % self.phone)

        else:
            pass

    @api.one
    @api.constrains("mobile")
    def _check_mobile(self):
        if self.mobile:
            # TODO - replace the first \d{3} with res_partner.country_id.phone_code
            if re.match(r"^\+\d{3}\d{9}$", self.mobile) is None:
                raise ValidationError("Mobile Number MUST be in the format +2547xxxxxxxx, Not (%s)" % self.mobile)
            if self.phone == self.mobile:
                raise ValidationError("Mobile Number (%s) cannot be the same as phone number." % self.phone)

            elif self.search_count([("mobile", "=", self.mobile)]) > 1:
                raise ValidationError("Mobile Number (%s) must be unique per Partner." % self.mobile)
            elif self.search_count([("phone", "=", self.mobile)]) > 1:
                raise ValidationError("Phone Number (%s) must be unique per Partner." % self.phone)
        else:
            pass

    @api.multi
    def get_partner_data(self):
        res_partner_data = [i.id for i in self.partner_data]
        form_view_id = self.env.ref("copia_partner.res_partner_data_view_form")

        if res_partner_data:
            return {
                "view_type": "form",
                "view_mode": "form",
                "view_id": form_view_id.id,
                "res_model": "res.partner.data",
                "target": "current",
                "res_id": res_partner_data[0],
                "context": {
                    "default_partner_id": self.id
                },
                "type": "ir.actions.act_window"
            }
        else:
            return {
                "view_type": "form",
                "view_mode": "form",
                "view_id": form_view_id.id,
                "res_model": "res.partner.data",
                "target": "current",
                "type": "ir.actions.act_window",
                "context": {
                    "default_partner_id": self.id,
                    "default_pin": "1234"
                }
            }

    @api.multi
    def action_view_sms(self):
        sms_ids = self.env["sms.message"].search([("partner_id", "=", self.id)]).ids
        action = self.env.ref("copia_sale.action_sms_message_all").read()[0]
        if len(sms_ids) > 1:
            action["domain"] = [("id", "in", sms_ids)]
        elif len(sms_ids) == 1:
            action["views"] = [(self.env.ref("copia_sale.view_sms_message_form").id, "form")]
            action["res_id"] = sms_ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        result = []
        if not args:
            args = []
        if operator not in ("ilike", "like", "=", "=like", "=ilike"):
            return super(Partner, self).name_search(name, args, operator, limit)

        if name:
            search_domain = ["|"] + [["phone", operator, name]] + [["name", operator, name]] + args
            result = self.search(search_domain, limit=limit)
        else:
            result = self.search(args, limit=limit)

        return result.name_get()

    @api.multi
    def action_toggle_active_agent(self):
        if self.active_agent:
            self.active_agent = False
            self.can_purchase = False
        else:
            self.active_agent = True
            self.can_purchase = True

    @api.multi
    def action_sms_new_agent(self):
        # FIXME: Move hard-coded SMS messages to ERP
        res, sms = list([]), self.env["sms.message"]

        if not self._context.get("date_from", False) and not self._context.get("date_to", False):
            _now = fields.datetime.now()
            to_time = _now.replace(hour=10, minute=59, second=59)
            from_time = (_now - datetime.timedelta(days=1)).replace(hour=11, minute=0, second=0)
        else:
            from_time = fields.datetime.strptime(
                self._context.get("date_from", False), DEFAULT_SERVER_DATETIME_FORMAT
            )
            to_time = fields.datetime.strptime(
                self._context.get("date_to", False), DEFAULT_SERVER_DATETIME_FORMAT
            )
        msg = self._context.get(
            "message", "Heko kwa kukubaliwa kama Ajenti wa Copia. Tafadhali weka order yako ya kwanza tayari. "
                       "Mwakilishi wako wa Copia atakutembelea hivi karibuni kukusaidia kuagiza."
        )

        for partner in self.search([
            ("create_date", ">=", from_time.__str__()), ("create_date", "<=", to_time.__str__()),
            ("partner_type", "=", "agent")
        ]):
            if not partner.phone or partner.phone is None or partner.phone.__len__() == 0:
                _queue = False
            else:
                _queue = self._context.get("add_to_queue", True)

            sms.with_context(add_to_queue=_queue).create({
                "partner_id": partner.id,
                "type": "outbox",
                "from_num": "Copia",
                "to_num": partner.phone,
                "date": datetime.datetime.today().isoformat(),
                "text": msg,
                "note": _queue and "Copia New Agent" or "Copia New Agent Failure (No Number)"
            })
            res.append({
                "partner": partner.name_get(),
                "phone": partner.phone,
                "message": msg,
                "queued": _queue
            })

        return res

    @api.multi
    def action_sms_night_to_pay(self):
        # FIXME: Move hard-coded SMS messages to ERP
        res = list([])
        msg = self._context.get(
            "message", "Asante kwa kuagiza bidhaa na Copia. Bidhaa zitakazoletwa leo ni ya thamani ya "
                       "KSHS {:0,.2f}. Tafadhali lipa kwa njia ya MPESA kabla ya madereva wetu kuwasili."
        )

        date_invoice = self._context.get("date_invoice", fields.date.today())

        self._cr.execute("""
        SELECT
            r.id,
            r.name,
            r.phone,
            -- SUM(i.residual) residual,
            SUM(i.amount_total) amount_total
        FROM account_invoice i
        JOIN res_partner r ON r.id = i.partner_id
        WHERE i.date_invoice = %s
        AND i.state != 'cancel' AND i.type = 'out_invoice'
        GROUP BY r.id HAVING SUM(i.residual) > 0;
       """, (date_invoice,))

        sms = self.env["sms.message"]
        for inv in self._cr.dictfetchall():
            if not inv.get("phone", False) or inv.get("phone", "").__len__() == 0:
                _queue = False
            else:
                _queue = self._context.get("add_to_queue", True)

            sms.with_context(add_to_queue=_queue).create({
                "partner_id": inv.get("id"),
                "type": "outbox",
                "from_num": "Copia",
                "to_num": inv.get("phone"),
                "date": datetime.datetime.today().isoformat(),
                # "text": msg.format(inv.get("residual", 0)),
                "text": msg.format(inv.get("amount_total", 0)),
                "note": _queue and "Copia SMS Night-to-Pay" or "Copia SMS Night-to-Pay Failure (No Number)"
            })
            res.append({
                "partner": inv.get("name"),
                "phone": inv.get("phone"),
                # "message": msg.format(inv.get("residual", 0)),
                "message": msg.format(inv.get("amount_total", 0)),
                "queued": _queue
            })

        return res

    def _track_subtype(self, init_values):
        """
        Track a Partner's partner_type changes with agent_type_id included.
        i.e customer -> agent, also note agent_type

        :param init_values:
        :return:
        """
        self.ensure_one()
        if "partner_type" in init_values and self.partner_type == "agent" and self.customer:
            return "copia_partner.mt_customer_to_agent"

        return super(Partner, self)._track_subtype(init_values)


class PartnerBusinessType(models.Model):
    _name = "res.partner.business.type"
    _description = "Partner Business Type"

    name = fields.Char("Name", required=True)


class PartnerData(models.Model):
    _name = "res.partner.data"
    _description = "Partner Extra Data"

    @api.one
    def _compute_agent_type(self):
        for partner in self:
            partner.agent_type_id = self.partner_id.agent_type_id
            partner.agent_type_name = self.partner_id.agent_type_id['name']

    @api.one
    def _compute_no_children(self):
        for partner in self:
            partner.no_of_children = len(self.customer_children)

    # Sales & Basic
    name = fields.Char(default="New")
    partner_id = fields.Many2one(
        "res.partner", "Partner",
        auto_join=True, index=True, ondelete="cascade", required=True
    )
    alternate_contact_name = fields.Char("Alternate Contact Name")
    alternate_contact_phone = fields.Char("Alternate Contact Phone")
    partner_dob = fields.Date("Date of Birth")
    id_number = fields.Char("National ID")
    can_earn_commission = fields.Boolean(
        "Can Earn Commission", track_visibility="onchange", store=True, compute="_compute_can_earn_commission"
    )
    credit_days = fields.Integer("Credit Days")
    prepayments_exempted = fields.Boolean("Exempt from High Value")

    # Info
    # TODO: Move warehouse_id to copia_stock
    pin = fields.Char(string="PIN", defualt='0000')
    # pin = fields.Char("PIN", compute="_generate_pin")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    till_number = fields.Char("MPESA Till Number")
    kra_pin = fields.Char("KRA Pin Number")
    social_media_ids = fields.Many2many(
        "res.partner.data.social.media", "res_partner_data_social_media_rel", "partner_data_id", "social_media_id"
    )
    phone_type = fields.Selection(
        [("smart", "Smart Phone"), ("regular", "Regular Phone")]
    )
    electricty_connection = fields.Selection(_choice, string="Electricity Connection")
    monthly_net_income = fields.Selection(_monthly_income, string="Monthly Net Income",
                                          help="Excludes Copia Commissions")

    notes = fields.Text()

    # Business
    net_income = fields.Integer("Monthly Net Income")
    business_name = fields.Char("Business Name")
    business_type = fields.Many2many(
        "res.partner.business.type", "partner_business_type", "business_type_id",
        "partner_id", string="Business Type"
    )
    orders_per_month = fields.Integer(string="Orders Per Month")
    number_of_permanent_workers = fields.Char(string="Number of Permanent Workers")
    number_of_casual_works = fields.Char(string="Number of Casual Workers")
    job_position = fields.Char(string="Job Position")
    agent_photo = fields.Binary("Agent Photo")
    pay_per_kilo = fields.Float("Pay per Kilo", default=0.0)

    # Customer
    customer_married = fields.Selection(_marital_status, string="Marital Status")
    customer_spouse_id = fields.Many2one(
        "res.partner", "Spouse"
    )
    customer_spouse_involved = fields.Boolean("Spouse involved in Copia?")
    customer_has_children = fields.Selection(_choice, string="Has Children?")
    customer_children = fields.One2many("res.partner.data.children", "res_partner_data_id", string="Children")
    customer_age_range = fields.Selection(_age_range, string="Customer Age Range")
    customer_occupation = fields.Char(string="Occupation")
    customer_has_email = fields.Boolean("Has Email")

    # Location
    latitude = fields.Float("Latitude", digits=(3, 5))
    longitude = fields.Float("Longitude", digits=(3, 5))
    location_id = fields.Many2one("res.partner.location", "Location")
    territory_id = fields.Many2one("res.partner.territory", "Territory")
    location_type_id = fields.Many2one("res.partner.location.type", string="Location Type")
    directions = fields.Text()

    # Assets
    asset_ids = fields.One2many("res.partner.data.asset", "res_partner_data_id", string="Assets")
    is_agent = fields.Boolean("Is Agent", related="partner_id.is_agent")
    is_sale_associate = fields.Boolean("Is Sale Associate", related="partner_id.is_sale_associate")
    # agent_type_id = fields.Many2one("Agent type", related="partner_id.agent_type_id")
    agent_type_id = fields.Many2one("agent.type", string="Agent Type", compute='_compute_agent_type')
    company_type = fields.Selection("Company Type", related="partner_id.company_type")
    chama_member_ids = fields.Many2many('res.partner', 'chama_members', 'chama_id', 'member_id')
    gender = fields.Selection(_gender, string="Gender")
    agent_type_name = fields.Char("Agent Type", store=False, compute='_compute_agent_type')
    no_of_children = fields.Selection(_no_of_children, string="No. of children", store=True)
    geo_code_valid = fields.Boolean("Validated GEO coded")

    @api.one
    @api.constrains("latitude", "longitude")
    def _check_latitude(self):
        if not self.latitude:
            raise ValidationError(_("Invalid latitude"))
        if not self.longitude:
            raise ValidationError(_("Invalid longitude"))

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            p = self.env["res.partner"].browse(self.env.context.get("active_id", False))
            vals.update({
                "name": p and p.name or "New"
            })

        '''
        Assign agents a random 4-digit PIN and send message with the PIN
        '''
        pin = 0000
        partner = False
        if self.env.context.get('default_partner_id'):
            partner = self.env['res.partner'].browse(self.env.context.get('default_partner_id'))
            if partner and partner.is_agent:
                while True:
                    r = random.randint(1111, 9999)
                    if r not in [1234, 0000]:
                        pin = "%04d" % r
                        vals.update({"pin": pin})
                        break

        partner_data_id = super(PartnerData, self).create(vals)
        if partner_data_id.id and partner:
            if partner.phone and partner.is_agent:
                msg = "Your Copia PIN is %s . PIN yako, SIRI yako." % pin
                # _logger.info('%s--%s' % (partner.phone, msg))
                self.env["sms.message"].with_context(add_to_queue=True).create({
                    "type": "outbox",
                    "from_num": "Copia",
                    "to_num": partner.phone,
                    "date": datetime.datetime.today().isoformat(),
                    "text": msg,
                    "note": "Copia PIN generation"
                })
        return partner_data_id

    @api.one
    @api.constrains("alternate_contact_phone")
    def _check_phone(self):
        if self.alternate_contact_phone:
            if re.match(r"^\+\d{3}\d{9}$", self.alternate_contact_phone) is None:
                raise ValidationError(
                    "Phone Number MUST be in the format +2547xxxxxxxx, Not (%s)" % self.alternate_contact_phone)

    @api.one
    @api.constrains("number_of_permanent_workers", "number_of_casual_works")
    def _no_of_workers(self):
        if self.partner_id.agent_type_id.name == 'Institution':
            if not self.number_of_permanent_workers or not self.number_of_casual_works:
                raise ValidationError("Enter number of permanent and casual works")

    @api.one
    @api.constrains("business_name", "business_type")
    def _no_business(self):
        if self.partner_id.agent_type_id.name == 'Field':
            if not self.business_name or not self.business_type:
                raise ValidationError("Enter Agent Business Name or Agent Business Type")

    @api.one
    @api.depends("partner_id")
    def _compute_can_earn_commission(self):
        self.can_earn_commission = False
        if (self.partner_id.is_agent and self.partner_id.active_agent and self.partner_id.can_purchase):
            self.can_earn_commission = True

    # TODO: Perhaps check res.partner.data.alt_contact_phone
    # @api.one
    # def _compute_is_chama(self):
    #     chama_type = self.env.ref("copia_partner.conf_t_chama")
    #     if (
    #             (self.partner_id.agent_type_id and self.partner_id.agent_type_id.name) or ""
    #     ).__eq__((chama_type and chama_type.name) or "Not"):
    #         self.is_chama = True
    #     else:
    #         self.is_chama = False

    @api.multi
    def action_toggle_can_earn_commission(self):
        if self.can_earn_commission:
            self.can_earn_commission = False
        else:
            self.can_earn_commission = True

    @api.multi
    def write(self, vals):
        '''
        Every time the PIN is changed we need to keep a log
        '''
        _logger.info('In copia_partner partner write. vals are %s', vals)
        pin_vals = []
        if 'pin' in vals:
            browse_ids = self.ids
            for partner in self.browse(browse_ids):
                pin_vals.append({'partner_id': partner.id, 'old_pin': partner.pin, 'new_pin': vals['pin']})
        pin_log_obj = self.env['pin.log']
        for v in pin_vals:
            pin_log_obj.create(v)
        res = super(PartnerData, self).write(vals)
        return res


class PartnerDataChildren(models.Model):
    _name = "res.partner.data.children"

    name = fields.Char("Name", required=True)
    age = fields.Selection(_child_age, string="Age")
    gender = fields.Selection(_gender, string="Gender")
    res_partner_data_id = fields.Many2one("res.partner.data", string="Partner Data")


class PartnerDataAsset(models.Model):
    _name = "res.partner.data.asset"

    name = fields.Char("Name", required=True)
    quantity = fields.Integer("Amount", help="What count of items of the asset were given", required=True, default=1)
    res_partner_data_id = fields.Many2one("res.partner.data", string="Partner Data")


class PartnerDataSocialMedia(models.Model):
    _name = "res.partner.data.social.media"

    name = fields.Char("Name", required=True)
