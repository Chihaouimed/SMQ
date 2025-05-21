import requests
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FicheRisque(models.Model):
    _name = 'fiche.risque'
    _description = 'Fiche de risque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    # Déclarations de champs
    name = fields.Char(string='Référence', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))
    proposition_ia = fields.Text("Proposition IA")
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    declencheur = fields.Text(string='Déclencheur', required=True, tracking=True)
    liste_concernee_ids = fields.Many2many('res.partner', string='Liste concernée', tracking=True)
    type_risque = fields.Selection([('menace', 'Menace'), ('opportunite', 'Opportunité')],
                                   string='Type de risque', required=True, default='menace', tracking=True)
    niveau_cout = fields.Selection([('faible', 'Faible'), ('moyen', 'Moyen'), ('eleve', 'Élevé')],
                                   string="Niveau de Coût")
    niveau_qualite = fields.Selection([('faible', 'Faible'), ('moyen', 'Moyen'), ('eleve', 'Élevé')],
                                      string="Niveau de Qualité")
    niveau_delai = fields.Selection([('faible', 'Faible'), ('moyen', 'Moyen'), ('eleve', 'Élevé')],
                                    string="Niveau de Délai")
    methode_calcul = fields.Selection(
        [('moyenne', 'Moyenne'), ('max', 'Maximum'), ('min', 'Minimum'), ('autre', 'Autre')],
        string='Méthode de calcul', required=True, default='moyenne', tracking=True)
    frequence = fields.Selection([('1', '1'), ('3', '3'), ('5', '5')], string="Fréquence", required=True)
    gravite = fields.Selection([('1', '1'), ('3', '3'), ('5', '5')], string="Gravité", required=True)
    detectabilite = fields.Selection([('1', '1'), ('3', '3'), ('5', '5')], string="Détectabilité", required=True)
    critere_ids = fields.One2many('fiche.risque.critere', 'fiche_risque_id', string='Critères d\'évaluation')
    note_globale = fields.Float(string='Note globale', compute='_compute_note_globale', store=True, readonly=True)
    recommandation_ia = fields.Text(string='Recommandation IA', compute='_compute_recommandation_ia', store=True)
    niveau_risque = fields.Selection(
        [('faible', 'Faible'), ('moyen', 'Moyen'), ('eleve', 'Élevé'), ('critique', 'Critique')],
        string='Niveau de risque', compute='_compute_niveau_risque', store=True)
    state = fields.Selection([('brouillon', 'Brouillon'), ('valide', 'Validé'), ('traite', 'Traité'), ('clos', 'Clos')],
                             string='État', default='brouillon', tracking=True)
    responsable_id = fields.Many2one('res.users', string='Responsable', tracking=True)
    action_ids = fields.One2many('action', 'fiche_risque_id', string='Actions')
    action_count = fields.Integer(string='Nombre d\'actions', compute='_compute_action_count')
    niveau_risque_val = fields.Integer(string="Valeur Niveau de Risque", compute="_compute_niveau_risque_val",
                                       store=True)

    # Dépendances et calculs des champs
    @api.depends('niveau_risque')
    def _compute_niveau_risque_val(self):
        for rec in self:
            mapping = {'faible': 1, 'moyen': 2, 'eleve': 3, 'critique': 4}
            rec.niveau_risque_val = mapping.get(rec.niveau_risque, 0)

    def _compute_action_count(self):
        for record in self:
            record.action_count = len(record.action_ids)

    def action_view_actions(self):
        self.ensure_one()
        return {
            'name': _('Actions'),
            'type': 'ir.actions.act_window',
            'res_model': 'action',
            'view_mode': 'tree,form',
            'domain': [('fiche_risque_id', '=', self.id)],
            'context': {'default_fiche_risque_id': self.id}
        }

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouveau')) == _('Nouveau'):
            vals['name'] = self.env['ir.sequence'].next_by_code('fiche.risque') or _('Nouveau')
        return super(FicheRisque, self).create(vals)

    @api.depends('critere_ids.note', 'methode_calcul')
    def _compute_note_globale(self):
        for record in self:
            # Filtrer les critères qui ont une note (puisque c'est un champ Selection requis, on vérifie juste qu'il existe)
            criteres = record.critere_ids.filtered(lambda c: c.note)

            if not criteres:
                record.note_globale = 0
                continue

            # Convertir les notes string en float pour les calculs
            notes = [float(c.note) for c in criteres]

            if record.methode_calcul == 'moyenne':
                record.note_globale = sum(notes) / len(notes)
            elif record.methode_calcul == 'max':
                record.note_globale = max(notes)
            elif record.methode_calcul == 'min':
                record.note_globale = min(notes)
            else:
                record.note_globale = sum(notes) / len(notes)

    @api.depends('frequence', 'gravite', 'detectabilite')
    def _compute_niveau_risque(self):
        for rec in self:
            if rec.frequence and rec.gravite and rec.detectabilite:
                score = int(rec.frequence) * int(rec.gravite) * int(rec.detectabilite)
                if score <= 20:
                    rec.niveau_risque = 'faible'
                elif score <= 40:
                    rec.niveau_risque = 'moyen'
                elif score <= 75:
                    rec.niveau_risque = 'eleve'
                else:
                    rec.niveau_risque = 'critique'
            else:
                rec.niveau_risque = False

    def action_creer_action(self):
        self.ensure_one()
        if not self.id:
            raise ValidationError(_("La fiche de risque n'existe pas ou n'est pas enregistrée."))
        return {
            'name': _('Créer une action'),
            'type': 'ir.actions.act_window',
            'res_model': 'action',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_fiche_risque_id': self.id}
        }

    def action_valider(self):
        for record in self:
            if not record.critere_ids:
                raise ValidationError(_("Vous devez ajouter au moins un critère d'évaluation."))
            record.state = 'valide'

    def action_traiter(self):
        for record in self:
            record.state = 'traite'

    def action_clore(self):
        for record in self:
            record.state = 'clos'

    def action_reset(self):
        for record in self:
            record.state = 'brouillon'

    def check_internet_connection(self):
        try:
            socket.gethostbyname("api.deepai.org")
            return True
        except socket.gaierror:
            return False

    def action_generer_recommandation_ia(self):
        for rec in self:
            if not rec.niveau_risque:
                rec.recommandation_ia = "Aucune recommandation possible sans niveau de risque."
                rec.proposition_ia = "Aucune proposition possible sans évaluation du risque."
                continue

            prompt = (
                f"Voici une fiche de risque à analyser pour générer un plan d'action et des propositions :\n\n"
                f"- Référence : {rec.name}\n"
                f"- Date : {rec.date}\n"
                f"- Déclencheur : {rec.declencheur}\n"
                f"- Type de risque : {rec.type_risque}\n"
                f"- Niveau de risque : {rec.niveau_risque}\n"
                f"- Fréquence : {rec.frequence}\n"
                f"- Gravité : {rec.gravite}\n"
                f"- Détectabilité : {rec.detectabilite}\n"
                f"- Liste concernée : {', '.join(rec.liste_concernee_ids.mapped('name'))}\n"
                f"- Critères d'évaluation : {', '.join([f'{c.critere}: {c.note}' for c in rec.critere_ids])}\n"
                f"- Méthode de calcul de la note : {rec.methode_calcul}"
            )

            headers = {
                'api-key': '2ac0b0e4-eb18-422b-bc1f-0c9c627cbc46',  # Remplace par ta clé API DeepAI
            }

            data = {
                'text': prompt
            }

            # Envoie de la requête à l'API
            try:
                response = requests.post('https://api.deepai.org/api/text-generator', headers=headers, data=data)

                # Log de la réponse pour débogage
                if response.status_code == 200:
                    response_data = response.json()
                    rec.proposition_ia = response_data.get('output', 'Aucune réponse générée.')
                    rec.recommandation_ia = f"Recommandation IA : {rec.proposition_ia}"
                else:
                    rec.proposition_ia = f"Erreur API : {response.status_code} - {response.text}"
                    rec.recommandation_ia = "Erreur lors de la génération des recommandations."

            except Exception as e:
                rec.proposition_ia = f"Erreur lors de l'appel API : {str(e)}"
                rec.recommandation_ia = "Erreur lors de la génération des recommandations."


class FicheRisqueCritere(models.Model):
    _name = 'fiche.risque.critere'
    _description = 'Critère d\'évaluation d\'une fiche de risque'

    name = fields.Char(string="Nom du critère", required=True)
    fiche_risque_id = fields.Many2one('fiche.risque', string='Fiche de risque', required=True, ondelete='cascade')
    critere = fields.Char(string='Critère', required=True)
    note = fields.Selection([('1', '1'), ('3', '3'), ('5', '5')],
                            string="Note", required=True)

    @api.constrains('note')
    def _check_note_validity(self):
        for record in self:
            if record.note not in ['1', '3', '5']:
                raise ValidationError(_('La note doit être 1, 3 ou 5.'))
