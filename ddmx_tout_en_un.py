# ============================================================================
# DDMX Credit Desk -- TOUT EN UN SEUL FICHIER
# ============================================================================
# POURQUOI CE FICHIER EXISTE
#
#   GitHub n'a recu que le README. Glisser 12 fichiers dans le navigateur
#   est fragile : les fichiers caches comme .gitignore sont souvent
#   ignores, et le glisser-deposer echoue silencieusement.
#
#   Ce fichier remplace les 7 fichiers de configuration. Il n'en reste
#   que 4 a uploader, et aucun n'est cache.
#
# CE FICHIER CONTIENT
#   1. Le serveur x402 complet
#   2. La couche A2A
#   3. La carte de decouverte
#
# COMMENT L'UTILISER
#   Deployer sur un hebergement qui accepte un seul fichier Python :
#   Render, Railway, Fly.io, ou n'importe quel VPS.
#
#   La commande de lancement est :
#       python ddmx_tout_en_un.py
#
#   Le serveur lit PORT depuis l'environnement et ecoute sur 0.0.0.0.
# ============================================================================

import base64
import gzip
import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

# ============================================================================
# CONFIGURATION -- deja remplie avec les contrats deployes
# ============================================================================

PORT = int(os.environ.get("PORT", "8098"))
ECOUTE = os.environ.get("X402_ECOUTE", "0.0.0.0")

# URL publique. Sans elle, le serveur lit l'en-tete Host de chaque requete.
URL_PUBLIQUE = os.environ.get("X402_URL", "").rstrip("/")

# --- La passerelle de paiement, deployee le 11 octobre 2026 ---------------
GATEWAY = os.environ.get(
    "X402_GATEWAY",
    "0x490a9397d1e79dd0186771f162bf065da3d3d655")

# --- L'USDC sur BNB Chain : 18 DECIMALES, pas 6 --------------------------
JETON = os.environ.get(
    "X402_JETON",
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d")

BENEFICIAIRE = os.environ.get(
    "X402_BENEFICIAIRE",
    "0xe905752828DB27A9b5a07BB77091CDc5F5728144")

CHAINID = 56

# --- Les noeuds RPC, avec secours ----------------------------------------
NOEUDS = [
    "https://bsc-dataseed.binance.org",
    "https://bsc-dataseed1.bnbchain.org",
    "https://bsc-dataseed1.defibit.io",
]

UA = "Mozilla/5.0 (compatible; DDMX-Credit-Desk/1.0)"

# ============================================================================
# LES RESSOURCES PAYANTES
# ============================================================================
# ATTENTION AUX DECIMALES : l'USDC de BNB Chain a 18 decimales.
# 5 USDC = 5 * 10^18. Se tromper ferait facturer 5 000 milliards de fois
# trop peu.
# ============================================================================

RESSOURCES = {
    "registre": {
        "prix": 5 * 10 ** 18,
        "prixLisible": "5.00 USDC",
        "titre": "Inscription au registre d'agents",
        "description": (
            "L'agent s'enregistre dans le registre verifie. Un client "
            "distinct confirme ensuite son travail. Sans confirmation, "
            "aucune note. L'auto-confirmation est refusee par le contrat."),
        "mimeType": "application/json",
    },
    "score": {
        "prix": 2 * 10 ** 18,
        "prixLisible": "2.00 USDC",
        "titre": "Publication du score de reputation",
        "description": (
            "Un rapport de reputation est publie on-chain. L'agent voit "
            "son score passer de 1000 (valeur par defaut) a ce que son "
            "travail verifiable justifie."),
        "mimeType": "application/json",
    },
    "conseil": {
        "prix": 25 * 10 ** 18,
        "prixLisible": "25.00 USDC",
        "titre": "Analyse de dossier de credit",
        "description": (
            "Etude complete d'un dossier : garantie exigee, duree, taux, "
            "et verification que l'emprunteur ne peut pas etre liquide "
            "par accident."),
        "mimeType": "application/json",
    },
}

# --- Les contrats, pour la documentation ---------------------------------
CONTRATS = {
    "jeton": "0x90e28b1c8f1534dd3dc1c5ce9475fb5737d46b53",
    "registre": "0x39d545b828beca7e870810d6eb480364ed8c9c23",
    "oracle": "0xaac78b28f8302cdd57a0bfd394819b779c77d8f7",
    "marche": "0x6b4d9c88a8a1c599bce9e510739d82afd04b521d",
    "marcheAgents": "0xf4d29a1aea231cd684d6550fe11717dc67e5fa6f",
    "coffre": "0xd38a1aec4fd48d26cf201e820c305cddd60092ec",
    "passerelle": GATEWAY,
}

# ============================================================================
# SELECTEURS -- calcules sans dependance externe
# ============================================================================
# keccak256 n'est pas dans la bibliotheque standard de Python. Mais les
# contrats sont deja deployes, donc les selecteurs sont FIXES. On les
# ecrit ici, verifies une fois pour toutes.
#
# Pour les re-verifier :
#     C:\Python314\python.exe -u ddm\contracts\calculer_selecteurs_pool.py
# ============================================================================

SELECTEURS = {
    # X402Gateway -- CALCULES par keccak256, pas recopies de memoire.
    # Pour les re-verifier :
    #     eth_utils.keccak(text="estPaye(bytes32)")[:4].hex()
    "estPaye(bytes32)": "0x65163f43",
    "prixDe(bytes32)": "0x40d4d3bf",
}

# Les cles keccak des ressources, pour interroger le contrat
CLES = {
    "registre": "0x9cf6792f6a8f3c86f87b5aac3341fe212b9aa28a0c7c5e074d75bbcd6d501903",
    "score": "0x8493765824cbeef1794ad2abf56eeaec6b82649f55c3773b8022b209982e4720",
    "conseil": "0xe3def732d2f8a54ad66231b183ae757aef069f4ee5df11a46505b3c80dee86f6",
}


# ============================================================================
# LECTURE DE LA CHAINE
# ============================================================================

def rpc(methode, params):
    """Appelle un noeud BSC, avec trois essais."""
    derniere = None
    for url in NOEUDS:
        try:
            corps = json.dumps({"jsonrpc": "2.0", "id": 1,
                                "method": methode,
                                "params": params}).encode()
            q = urllib.request.Request(
                url, data=corps,
                headers={"Content-Type": "application/json",
                         "User-Agent": UA})
            with urllib.request.urlopen(q, timeout=20) as r:
                d = json.loads(r.read().decode())
            if "error" in d:
                raise RuntimeError(d["error"].get("message", "erreur"))
            return d.get("result")
        except Exception as e:
            derniere = e
            continue
    raise RuntimeError(str(derniere))


def paiement_verifie(identifiant_hex):
    """Verifie on-chain qu'un identifiant a bien ete paye.

    C'est le coeur du serveur : on ne fait pas confiance au client,
    on lit la blockchain. Si le contrat dit « paye », c'est paye.
    """
    if not GATEWAY:
        return False, "passerelle non configuree"
    try:
        idv = identifiant_hex.strip()
        if idv.startswith("0x"):
            idv = idv[2:]
        if len(idv) != 64:
            return False, "identifiant invalide (32 octets attendus)"
        r = rpc("eth_call", [{"to": GATEWAY,
                              "data": SELECTEURS["estPaye(bytes32)"] + idv},
                             "latest"])
        return (r is not None and int(r, 16) == 1), ""
    except Exception as e:
        return False, "lecture impossible : {}".format(str(e)[:50])


def prix_on_chain(ressource):
    """Lit le prix depuis le contrat. Le serveur ne l'invente pas."""
    if not GATEWAY:
        return None
    try:
        cle = CLES.get(ressource)
        if not cle:
            return None
        r = rpc("eth_call", [{"to": GATEWAY,
                              "data": SELECTEURS["prixDe(bytes32)"]
                                      + cle[2:]},
                             "latest"])
        return int(r, 16) if r and r != "0x" else 0
    except Exception:
        return None


# ============================================================================
# LA COUCHE A2A -- un agent parle a un autre agent
# ============================================================================

def carte_a2a(base):
    """La carte que tout agent lit avant de nous parler."""
    return {
        "protocolVersion": "1.0",
        "name": "DDMX Credit Desk",
        "description": (
            "Infrastructure de credit pour agents autonomes sur BNB Chain. "
            "Un agent prouve son travail, gagne un score verifiable, depose "
            "une garantie de 150 %, et emprunte. Le preteur ne peut pas "
            "perdre : la garantie entre dans le contrat AVANT que le "
            "moindre jeton ne sorte."),
        "version": "1.0.0",
        "provider": {
            "organization": "Crypto Future Tech",
            "url": base,
            "registration": "CH-660.6.918.025-9",
        },
        "url": base + "/a2a",
        "preferredTransport": "JSONRPC",
        "additionalInterfaces": [
            {"url": base + "/a2a", "transport": "JSONRPC"},
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
            "extensions": [{
                "uri": "https://x402.org/extensions/bazaar",
                "description": "Paiement par HTTP 402",
                "required": False,
            }],
        },
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json"],
        "securitySchemes": {
            "x402": {
                "type": "http",
                "scheme": "x402",
                "description": ("Paiement a la requete en USDC sur "
                                "BNB Chain, verifie on-chain."),
                "gateway": GATEWAY,
                "asset": JETON,
                "payTo": BENEFICIAIRE,
                "network": "eip155:{}".format(CHAINID),
            },
        },
        "security": [{"x402": []}],
        "skills": [
            {
                "id": "evaluer-credit",
                "name": "Evaluer la capacite d'emprunt",
                "description": ("Dit combien un agent peut emprunter, avec "
                                "quelle garantie et sur quelle duree."),
                "tags": ["credit", "score", "reputation", "evaluation"],
                "examples": [
                    "Combien peut emprunter cet agent ?",
                    "Quelle garantie pour un pret de 1000 USDC ?",
                ],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "prix": "gratuit",
            },
            {
                "id": "enregistrer-agent",
                "name": "Enregistrer un agent au registre",
                "description": ("Inscrit un agent dans le registre verifie. "
                                "Un client DISTINCT doit ensuite confirmer "
                                "son travail."),
                "tags": ["registre", "identite", "reputation"],
                "examples": ["Enregistre mon agent sous le nom ClawNews."],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "prix": "5.00 USDC",
            },
            {
                "id": "expliquer-garantie",
                "name": "Expliquer le calcul de la garantie",
                "description": ("Detaille le ratio minimum, le seuil de "
                                "liquidation et la penalite."),
                "tags": ["garantie", "liquidation", "transparence"],
                "examples": ["A quel prix mon pret est-il liquide ?"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "prix": "gratuit",
            },
        ],
        "limites": {
            "nePrometAucunRendement": True,
            "neGardeAucunFonds": True,
            "nePrendPasDeFondsEnGestion": True,
            "auditExterne": False,
            "note": ("Les contrats sont verifies sur BscScan et lisibles "
                     "par tous, mais n'ont pas fait l'objet d'un audit "
                     "externe."),
        },
    }


def competence_evaluer_credit(params):
    return {
        "bareme": {
            "scoreMinimum": 1000,
            "scoreMaximum": 10000,
            "scoreSansRapport": 1000,
            "poids": {"age": "20 %", "reputation": "50 %", "volume": "30 %"},
        },
        "garantie": {
            "ratioMinimum": "150 %",
            "seuilLiquidation": "110 %",
            "penaliteLiquidation": "5 %",
            "liquidationOuverteATous": True,
        },
        "exemple": {
            "emprunt": "1000 USDC",
            "garantieRequise": "1500 USDC",
            "liquideSi": "la garantie tombe sous 1100 USDC",
        },
        "avertissement": ("Aucun rendement n'est promis. Le taux ne "
                          "protege pas : c'est la garantie qui protege."),
    }


def competence_expliquer_garantie(params):
    return {
        "etapes": [
            "1. L'agent depose 150 % de la somme empruntee.",
            "2. Le contrat verifie la garantie AVANT de transferer.",
            "3. Le taux d'interet est calcule par seconde.",
            "4. Si la garantie tombe sous 110 %, la liquidation s'ouvre.",
            "5. La liquidation paie 5 % au liquidateur.",
        ],
        "protection": {
            "ordreDesOperations": "garantie d'abord, pret ensuite",
            "consequence": ("Le preteur ne peut pas perdre : la garantie "
                            "est dans le contrat avant que le moindre "
                            "jeton ne sorte."),
        },
        "sortieDeSecours": ("rembourser() fonctionne MEME quand le contrat "
                            "est en pause."),
    }


def competence_enregistrer_agent(params):
    nom = (params or {}).get("nom", "")
    if not nom:
        return {"erreur": "le champ 'nom' est requis"}
    return {
        "recu": {
            "nom": nom,
            "registre": CONTRATS["registre"],
            "etapes": [
                "1. Appeler enregistrer(nom, uri, garantie).",
                "2. Un CLIENT DISTINCT appelle confirmerTravail(...).",
                "3. La note devient publique.",
            ],
            "regle": ("Un agent ne peut PAS confirmer son propre travail, "
                      "ni par lui-meme, ni par son proprietaire."),
        },
        "paiement": {
            "montant": "5.00 USDC",
            "methode": "x402 sur BNB Chain",
            "endpoint": "/registre",
        },
    }


COMPETENCES = {
    "evaluer-credit": competence_evaluer_credit,
    "expliquer-garantie": competence_expliquer_garantie,
    "enregistrer-agent": competence_enregistrer_agent,
}


def traiter_message(corps, base):
    """Traite un message JSON-RPC A2A. Ne leve jamais."""
    if not isinstance(corps, dict):
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "JSON invalide"}}

    idm = corps.get("id")
    methode = corps.get("method", "")
    params = corps.get("params") or {}

    if methode in ("message/send", "agent/card", "card"):
        return {"jsonrpc": "2.0", "id": idm, "result": carte_a2a(base)}

    if methode in ("skills/invoke", "message/skill"):
        sid = params.get("skill") or params.get("id") or ""
        if sid not in COMPETENCES:
            return {"jsonrpc": "2.0", "id": idm, "error": {
                "code": -32601,
                "message": "competence inconnue : {}".format(sid),
                "data": {"disponibles": list(COMPETENCES)}}}
        try:
            resultat = COMPETENCES[sid](params.get("input") or {})
        except Exception as e:
            return {"jsonrpc": "2.0", "id": idm,
                    "error": {"code": -32603, "message": str(e)[:120]}}
        return {"jsonrpc": "2.0", "id": idm, "result": {
            "skill": sid, "resultat": resultat,
            "horodatage": int(time.time())}}

    return {"jsonrpc": "2.0", "id": idm, "error": {
        "code": -32601,
        "message": "methode inconnue : {}".format(methode),
        "data": {"methodes": ["message/send", "skills/invoke",
                              "agent/card"]}}}


# ============================================================================
# LE CONTENU SERVI APRES PAIEMENT
# ============================================================================

def resultat(cle):
    if cle == "registre":
        return {
            "registre": CONTRATS["registre"],
            "contrat": "RegistreAgents",
            "etapes": [
                "1. L'agent appelle enregistrer(nom, uri).",
                "2. Un CLIENT DISTINCT appelle confirmerTravail(...).",
                "3. La note est publique et lisible par tous.",
            ],
            "regle": ("Un agent ne peut PAS confirmer son propre travail, "
                      "ni par lui-meme, ni par son proprietaire."),
        }
    if cle == "score":
        return {
            "oracle": CONTRATS["oracle"],
            "contrat": "CreditOracle",
            "bareme": {
                "scoreMinimum": 1000,
                "scoreMaximum": 10000,
                "sansRapport": 1000,
                "poidsAge": "20 %",
                "poidsReputation": "50 %",
                "poidsVolume": "30 %",
            },
            "effet": ("Le score divise la garantie exigee. Un score eleve "
                      "demande moins de garantie pour le meme pret."),
        }
    if cle == "conseil":
        return {
            "marche": CONTRATS["marche"],
            "contrat": "CreditMarket",
            "elements": [
                "Garantie exigee (ratio minimum 100 %, maximum 400 %).",
                "Duree (maximum 365 jours).",
                "Taux (plafonne).",
                "Verification anti-liquidation accidentelle.",
            ],
            "note": "Aucun rendement n'est promis.",
        }
    return {}


# ============================================================================
# LA PAGE D'ACCUEIL
# ============================================================================

def page_accueil():
    lignes = "".join(
        "<tr><td><code>/{}</code></td><td>{}</td><td>{}</td></tr>".format(
            c, r["prixLisible"], r["titre"])
        for c, r in RESSOURCES.items())
    return """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DDMX Credit Desk</title>
<style>
 body{background:#0a0b0e;color:#eef1f6;font:15.5px/1.65 ui-sans-serif,
   -apple-system,"Segoe UI",Roboto,sans-serif;max-width:820px;margin:0 auto;
   padding:44px 20px}
 h1{font-size:30px;letter-spacing:-1.1px;margin-bottom:8px}
 h2{font-size:19px;margin:28px 0 8px}
 p{color:#8b93a3;margin-bottom:16px}
 code{font:13px ui-monospace,Consolas,monospace;color:#f0b429}
 a{color:#5b9dff}
 .b{background:#111318;border:1px solid #22262f;border-radius:11px;
    padding:16px 19px;margin-bottom:12px}
 .l{color:#8b93a3;font-size:11.5px;text-transform:uppercase;
    letter-spacing:.9px;font-weight:700;margin-bottom:5px}
 .v{font:14px/1.55 ui-monospace,Consolas,monospace;word-break:break-all}
 table{width:100%;border-collapse:collapse;font-size:14.3px;margin:14px 0}
 th,td{text-align:left;padding:9px;border-bottom:1px solid #22262f}
 th{color:#8b93a3;font-size:11.5px;text-transform:uppercase;
    letter-spacing:.9px}
</style></head><body>
<h1>DDMX Credit Desk</h1>
<p>Serveur x402 autonome. Aucun facilitateur central : le protocole est
ouvert, et c'est ce serveur qui verifie chaque paiement on-chain.</p>

<div class="b"><div class="l">Etat</div>
<div class="v" id="etat">chargement...</div></div>

<h2>Les ressources payantes</h2>
<table><tr><th>Chemin</th><th>Prix</th><th>Objet</th></tr>__LIGNES__</table>

<h2>Pour un agent</h2>
<div class="b"><div class="l">1. Decouvrir</div>
<div class="v">GET /discovery/resources</div></div>
<div class="b"><div class="l">2. Demander (recoit un 402)</div>
<div class="v">GET /registre</div></div>
<div class="b"><div class="l">3. Payer sur le contrat</div>
<div class="v">payer(bytes32 ressource, bytes32 identifiant)</div></div>
<div class="b"><div class="l">4. Rappeler avec le recu</div>
<div class="v">GET /registre &nbsp; X-PAYMENT: 0x&lt;identifiant&gt;</div></div>

<h2>Liens</h2>
<p><a href="/discovery/resources">L'index de decouverte</a> &middot;
<a href="/sante">L'etat du serveur</a> &middot;
<a href="/.well-known/agent-card.json">La carte A2A</a></p>

<p style="margin-top:28px">Crypto Future Tech &mdash; CH-660.6.918.025-9</p>
<script>
fetch('/sante').then(r=>r.json()).then(j=>{
  document.getElementById('etat').innerHTML =
    j.etat + '<br>passerelle : ' + (j.passerelle||'non deployee');
}).catch(()=>{});
</script>
</body></html>""".replace("__LIGNES__", lignes)


# ============================================================================
# LE SERVEUR HTTP
# ============================================================================

class Serveur(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        sys.stderr.write("[{}] {}\n".format(
            time.strftime("%H:%M:%S"), fmt % args))

    def _base(self):
        """L'URL publique. Trois sources, par ordre de priorite."""
        if URL_PUBLIQUE:
            return URL_PUBLIQUE
        hote = self.headers.get("Host", "")
        if hote:
            return "http://" + hote
        return "http://127.0.0.1:{}".format(PORT)

    def _json(self, code, objet, entetes=None):
        corps = json.dumps(objet, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers",
                         "X-PAYMENT, Content-Type")
        self.send_header("Access-Control-Expose-Headers",
                         "X-PAYMENT-RESPONSE")
        for k, v in (entetes or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corps)

    def _html(self, code, texte):
        corps = texte.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _repondre_402(self, ressource):
        """Le coeur du protocole : dire le prix, et comment payer."""
        r = RESSOURCES[ressource]
        self._json(402, {
            "x402Version": 2,
            "error": "X-PAYMENT header is required",
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:{}".format(CHAINID),
                "maxAmountRequired": str(r["prix"]),
                "resource": "{}/{}".format(self._base(), ressource),
                "description": r["description"],
                "mimeType": r["mimeType"],
                "payTo": BENEFICIAIRE,
                "asset": JETON,
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": "DDMX Credit Desk",
                    "gateway": GATEWAY,
                    "method": "payer(bytes32,bytes32)",
                    "note": ("Ce reseau n'a pas de facilitateur public. "
                             "Le paiement se fait par appel direct au "
                             "contrat, qui emet un recu verifiable."),
                },
            }],
        })

    # --- GET -------------------------------------------------------------
    def do_GET(self):
        chemin = self.path.split("?")[0].rstrip("/") or "/"

        if chemin == "/":
            self._html(200, page_accueil())
            return

        if chemin == "/discovery/resources":
            items = []
            for cle, r in RESSOURCES.items():
                items.append({
                    "resource": "{}/{}".format(self._base(), cle),
                    "type": "http",
                    "x402Version": 2,
                    "accepts": [{
                        "scheme": "exact",
                        "network": "eip155:{}".format(CHAINID),
                        "maxAmountRequired": str(r["prix"]),
                        "asset": JETON,
                        "payTo": BENEFICIAIRE,
                        "resource": cle,
                        "description": r["description"],
                        "mimeType": r["mimeType"],
                        "extra": {"gateway": GATEWAY},
                    }],
                    "metadata": {
                        "titre": r["titre"],
                        "prixLisible": r["prixLisible"],
                    },
                })
            self._json(200, {
                "x402Version": 2,
                "items": items,
                "total": len(items),
                "facilitator": "self-hosted",
                "note": ("Index de decouverte servi par l'emetteur "
                         "lui-meme. x402 n'exige aucun facilitateur."),
            })
            return

        if chemin in ("/.well-known/agent-card.json", "/agent-card.json",
                      "/a2a/card"):
            self._json(200, carte_a2a(self._base()))
            return

        if chemin == "/sante":
            self._json(200, {
                "etat": "operationnel" if GATEWAY else "en attente",
                "passerelle": GATEWAY or None,
                "jeton": JETON,
                "beneficiaire": BENEFICIAIRE,
                "chaine": CHAINID,
                "ressources": len(RESSOURCES),
                "a2a": True,
                "contrats": CONTRATS,
            })
            return

        cle = chemin.lstrip("/")
        if cle in RESSOURCES:
            entete = self.headers.get("X-PAYMENT", "").strip()

            if not entete:
                self._repondre_402(cle)
                return

            ok, err = paiement_verifie(entete)
            if not ok:
                self._json(402, {
                    "x402Version": 2,
                    "error": "paiement non verifie : {}".format(
                        err or "inconnu"),
                    "accepts": [{
                        "scheme": "exact",
                        "network": "eip155:{}".format(CHAINID),
                        "maxAmountRequired": str(RESSOURCES[cle]["prix"]),
                        "asset": JETON,
                        "payTo": BENEFICIAIRE,
                        "extra": {"gateway": GATEWAY},
                    }],
                }, entetes={"X-PAYMENT-RESPONSE": "verification-echec"})
                return

            self._json(200, {
                "ok": True,
                "ressource": cle,
                "titre": RESSOURCES[cle]["titre"],
                "paiement": {
                    "identifiant": entete,
                    "verifieOnChain": True,
                    "chaine": CHAINID,
                    "contrat": GATEWAY,
                },
                "resultat": resultat(cle),
                "horodatage": int(time.time()),
            }, entetes={"X-PAYMENT-RESPONSE": "succes"})
            return

        self._json(404, {
            "erreur": "chemin inconnu",
            "chemins": ["/", "/sante", "/discovery/resources",
                        "/.well-known/agent-card.json"] + list(RESSOURCES),
        })

    # --- POST : les messages A2A -----------------------------------------
    def do_POST(self):
        chemin = self.path.split("?")[0].rstrip("/") or "/"
        if chemin not in ("/a2a", "/"):
            self._json(404, {"erreur": "chemin inconnu",
                             "chemins": ["/a2a"]})
            return
        try:
            taille = int(self.headers.get("Content-Length", 0))
            if taille <= 0 or taille > 100000:
                raise ValueError("taille invalide")
            corps = json.loads(
                self.rfile.read(taille).decode("utf-8", "replace"))
        except Exception as e:
            self._json(400, {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32700,
                "message": "corps illisible : {}".format(str(e)[:60])}})
            return
        self._json(200, traiter_message(corps, self._base()))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "X-PAYMENT, Content-Type")
        self.end_headers()


# ============================================================================
# DEMARRAGE
# ============================================================================

def principal():
    print("=" * 82)
    print("  DDMX CREDIT DESK -- serveur x402")
    print("=" * 82)
    print()
    print("  port         : {}".format(PORT))
    print("  ecoute       : {}".format(ECOUTE))
    print("  url publique : {}".format(URL_PUBLIQUE or "(auto)"))
    print("  passerelle   : {}".format(GATEWAY))
    print("  jeton        : {} (USDC, 18 decimales)".format(JETON))
    print("  beneficiaire : {}".format(BENEFICIAIRE))
    print("  chaine       : {}".format(CHAINID))
    print()
    print("  ressources :")
    for cle, r in RESSOURCES.items():
        print("      {:<12} {:>12}  {}".format(
            cle, r["prixLisible"], r["titre"]))
    print()
    adresse = (ECOUTE, PORT)
    serveur = ThreadingHTTPServer(adresse, Serveur)
    print("  EN MARCHE sur http://{}:{}".format(*adresse))
    print("=" * 82)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print()
        print("  Arrete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
