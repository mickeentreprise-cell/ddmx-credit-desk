# COMMENT DEPLOYER — en 15 minutes

## Ce que tu as dans ce dossier

Neuf fichiers. Tu vas les glisser sur GitHub, puis connecter GitHub a
Render. Render fera le reste.

## Etape 1 — GitHub (5 minutes)

1. Va sur https://github.com et cree un compte si tu n'en as pas
2. Clique sur **New repository**
3. Nom : `ddmx-credit-desk`
4. Visibilite : **Public** (obligatoire pour l'offre gratuite de Render)
5. Clique **Create repository**
6. Sur la page qui s'ouvre, clique **uploading an existing file**
7. **Glisse les 9 fichiers** de ce dossier (PAS le dossier lui-meme)
8. Clique **Commit changes**

## Etape 2 — Render (5 minutes)

1. Va sur https://render.com
2. **Sign up** avec GitHub (le plus simple)
3. Clique **New** puis **Web Service**
4. Choisis le depot `ddmx-credit-desk`
5. Render detecte `render.yaml` tout seul — ne touche a rien
6. Clique **Create Web Service**
7. Attends 2 a 3 minutes

## Etape 3 — Verifier (1 minute)

Render te donne une adresse du type :

    https://ddmx-credit-desk.onrender.com

Ouvre ces trois liens :

    https://TON-ADRESSE.onrender.com/sante
    https://TON-ADRESSE.onrender.com/.well-known/agent-card.json
    https://TON-ADRESSE.onrender.com/discovery/resources

Si les trois repondent, **le service est en ligne**.

## Etape 4 — Remplir X402_URL (2 minutes)

1. Dans Render, va dans **Environment**
2. Ajoute une variable :
   - Nom : `X402_URL`
   - Valeur : `https://TON-ADRESSE.onrender.com`
3. Clique **Save Changes**

Cela garantit que les URL renvoyees aux agents sont les bonnes.

## Etape 5 — S'inscrire dans l'annuaire (5 minutes)

Va sur https://github.com/x402-index/x402-discovery-index/issues

Clique **New issue** et colle le texte de `CONTACTER-LA-TECHNOLOGIE.md`.

**Verifie et liste sous 24 heures.**

---

## ATTENTION — le plan gratuit de Render

Le service **s'endort apres 15 minutes sans trafic**. Le premier appel
apres une pause prend environ **30 secondes**.

Ce n'est pas bloquant : un agent qui recoit un 402 attend de toute facon.
Mais l'annuaire qui verifie ton endpoint pourrait tomber sur un reveil lent.

**Si c'est un probleme :**

| Hebergeur | Cout | Reveil |
|---|---|---|
| Render gratuit | 0 EUR | 30 s |
| Railway | ~5 $/mois | instantane |
| Fly.io | offre gratuite | instantane |

---

## Les variables d'environnement

| Nom | Valeur par defaut | Ce qu'elle fait |
|---|---|---|
| `PORT` | 8098 | impose par l'hebergeur |
| `X402_ECOUTE` | 0.0.0.0 | adresse d'ecoute |
| `X402_URL` | (vide) | URL publique |
| `X402_GATEWAY` | deja rempli | le contrat de paiement |
| `X402_JETON` | deja rempli | USDC sur BNB Chain |
| `X402_BENEFICIAIRE` | deja rempli | qui recoit l'argent |

**Les trois dernieres sont deja dans `render.yaml`. Tu n'as rien a faire.**
