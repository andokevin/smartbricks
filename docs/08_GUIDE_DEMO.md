# 08 — Guide de démonstration (parcours client complet, avec Claude)

À suivre pendant la démo. Durée : 8 à 10 minutes. Le copilote utilise **Claude** (`LLM_PROVIDER=claude`, modèle `claude-haiku-5-5`) ; un parcours complet coûte environ **0,005 $** (plafond : 4 $).

---

## A. Avant la démo (5 minutes)

**1. Lancer l'application** (deux terminaux WSL) :

```bash
# Terminal 1 — base + API
cd ~/projets/smartbricks && docker compose up -d
cd backend && .venv/bin/uvicorn app.main:app --port 8000

# Terminal 2 — interface
cd ~/projets/smartbricks/frontend && pnpm dev
```

**2. Vérifier** <http://localhost:8000/api/v1/health> : il doit afficher `"llm_provider":"claude"`.

**3. Repartir d'une base propre** : ouvrir <http://localhost:5173>, se connecter en **Administrateur** (bouton de démo), puis **Réinitialiser la démo** sur le tableau de bord. Cela recrée Boutique Soa et les 25 freelances. La consommation de Claude est conservée.

**4. Préparer le texte à coller dans le copilote** :

> Boutique Soa veut un site e-commerce avec paiement MVola, une application mobile de suivi des commandes, et l'installation du réseau dans ses agences de Tana, Antsirabe, Toamasina et Fianarantsoa. Budget 6 000 000 Ar, livraison dans 8 semaines.

**5. Garder le plan B en tête** (§ D).

---

## B. Le scénario, écran par écran

| Min. | Écran | Action | Ce qu'on voit et ce qu'on dit |
|---|---|---|---|
| 0:00 | Connexion | Bouton **« Cliente — Soa »**, ou **« Pas encore de compte ? Créer un compte client »** (nom, organisation, email, mot de passe d'au moins 8 caractères) | Tableau de bord du client. Un compte neuf n'a aucun projet : passer directement par **Nouveau projet**. |
| 0:30 | **Copilote** (n°33) | Menu **Nouveau projet**, coller le texte, envoyer | Claude reformule et pose **une seule question** (souvent : ville de base, livraison, heures). Le badge indique **Claude**. |
| 1:00 | Copilote | Répondre simplement, par exemple : « La ville de base est Antananarivo, avec la livraison à domicile, 200 heures pour le sprint 1. » | Après 1 ou 2 réponses, le **brouillon** apparaît à droite : fonctionnalités, tâches, sites. Dire : « l'IA a structuré le besoin ; un programme a vérifié les compétences, les villes et les cycles de dépendances ». |
| 2:00 | Copilote | Modifier une valeur ou des heures dans le brouillon, puis **Valider le brouillon** | Le projet est créé et l'écran Périmètre s'ouvre. |
| 2:30 | **Périmètre** (sac à dos n°29) | **Calculer le périmètre** | Jauges budget et heures, fonctionnalités retenues ou reportées **avec la raison chiffrée**, encart **« Et si ? »**, badge « Optimum prouvé ». |
| 3:30 | **Équipe** (n°22 et n°21) | Passer de **Économique** à **Rapide** | Le classement change. Montrer le **nuage de Pareto** et l'étoile du meilleur compromis. |
| 4:00 | Équipe | **Équipe suggérée**, puis **Confirmer l'équipe** | La plateforme propose l'équipe : le client valide. |
| 4:30 | **Planning** (CSP n°3) | **Calculer le planning** | Gantt avec **flèches de dépendance**, chemin critique entouré, **8/8 contraintes** vérifiées, ordre des visites sur site. |
| 5:15 | Planning | **Scénario impossible (3 semaines)** | Diagnostic chiffré (chemin critique ou charge), le vrai planning reste intact. |
| 5:45 | Planning | **Signaler un retard** : une tâche du chemin critique, 8 h, **Réparer le planning** | Min-Conflict (n°11) : « N tâches déplacées, aucun changement de freelance », avec la comparaison à une replanification complète. |
| 6:30 | **Tournée** (n°30) | Ouvrir l'écran, **Valider la tournée** | Carte et itinéraire numéroté, **≈ 1 286 km**, gain par rapport à l'ordre saisi, Held-Karp. |
| 7:15 | **Synthèse** (n°33) | Ouvrir l'écran | Claude explique le plan en français simple, avec le badge **« Chaque chiffre vérifié dans les données »**. Poser une question, par exemple : « Pourquoi le paiement Orange Money n'est-il pas dans le sprint 1 ? » |
| 8:00 | Synthèse | **Cahier des charges (PDF)** | Le PDF de 4 pages est téléchargé : exigences, raisons, planning vérifié, tournée. |
| 8:30 | *(bonus)* Espace freelance | Se déconnecter, bouton **« Freelance — Hasina »** | Ses tâches, ce qu'elle attend, ses indisponibilités. Elle déclare un jour d'absence sur une tâche ; côté client, l'écran Planning affiche une alerte « recalculez le planning ». |

**Phrases clés :**
- « L'IA comprend et explique ; les algorithmes décident, et une fonction indépendante vérifie chaque résultat. »
- « Si l'IA cite un chiffre qui n'est pas dans les résultats, son texte est remplacé. »

---

## C. Ce qui peut varier avec Claude (normal)

- **Les questions et le brouillon changent d'une fois à l'autre.** Lors de l'essai de 14 h, Claude a produit 8 fonctionnalités et 18 tâches, et le sprint 1 retenait le paiement MVola. Les chiffres du diaporama viennent du projet de démonstration préchargé : ils ne seront pas identiques. C'est attendu, puisque les estimations viennent de l'IA.
- **Si Claude pose une question de trop**, répondre : « C'est tout, vous pouvez préparer le projet. »
- **Le premier brouillon prend environ 10 à 15 s** : c'est l'extraction structurée. Le dire pendant l'attente.
- **Si Claude n'a pas reçu d'heures pour le sprint 1**, il laisse le champ vide. Le brouillon propose alors une valeur par défaut (jours ouvrés × 6 h × 2 personnes), modifiable avant validation.

---

## D. Plan B (moins d'une minute)

- **Claude ne répond pas (réseau, clé) ou trop lentement** : dans `.env`, mettre `LLM_PROVIDER=mock`, puis arrêter (Ctrl+C) et relancer l'API (terminal 1). Le copilote simulé rejoue Boutique Soa à l'identique, sans réseau, et les chiffres du diaporama correspondent alors exactement.
- **Pas le temps de passer par le copilote** : utiliser le projet préchargé **« Boutique Soa »** depuis le tableau de bord (bouton « Continuer »).
- **La carte ne s'affiche pas (pas d'internet)** : l'écran Tournée bascule tout seul sur le **schéma hors ligne**.
- **Coût consommé** : en Administrateur, <http://localhost:8000/docs> → `GET /admin/llm-usage`.
