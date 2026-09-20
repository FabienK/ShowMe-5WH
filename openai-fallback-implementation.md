# Implémentation : génération via OpenAI (GPT Image 2) comme option à part entière dans ShowMe5WH

## Contexte

ShowMe5WH génère des images via ComfyUI/Stable Diffusion en local (Mac mini M4), à partir d'un script assemblé selon le protocole 4W1H (What/Who/Where/When/How).

**Objectif** : ajouter la génération via l'API OpenAI (GPT Image 2) comme **option de génération à part entière**, au même niveau que le générateur local — pas un fallback caché. L'utilisateur choisit sa source de génération avant de lancer, et le bouton correspondant affiche le crédit restant estimé et le coût d'une génération.

## Ce qu'il ne faut PAS faire

- Ne pas passer par ComfyUI Cloud (abonnement GPU distant) — inutile, on génère déjà en local.
- Ne pas passer par les Partner Nodes ComfyUI (clé API comfy.org) — dépendance à un compte tiers non justifiée.
- Ne pas essayer de récupérer le solde de crédit OpenAI via un appel API : **il n'existe aucun endpoint officiel et documenté pour ça**. L'endpoint `/v1/dashboard/billing/credit_grants` est non officiel, non garanti dans le temps, et ne doit pas être utilisé comme source de vérité pour l'affichage du bouton.

## Principe retenu pour l'affichage du crédit

Le coût par génération OpenAI est fixe et connu à l'avance (tarif par résolution). Le solde affiché sur le bouton est donc **calculé localement par l'app**, pas interrogé en direct auprès d'OpenAI :

1. L'utilisateur renseigne manuellement le montant crédité sur son compte OpenAI au moment où il recharge (un champ dans les paramètres de l'app, ex. "Solde OpenAI actuel : 25,00 $").
2. À chaque génération réussie via OpenAI, l'app décrémente ce solde localement du coût de la génération effectuée (selon la résolution utilisée).
3. Le solde est stocké côté backend (fichier local ou base légère existante du projet), pas recalculé à la volée.

Cette valeur est une estimation qui se désynchronise si le compte OpenAI est crédité ou utilisé ailleurs que par cette app — l'utilisateur doit resynchroniser manuellement le champ après un rechargement.

## Ce que Claude Code doit implémenter

### 1. Dépendance

```
pip install openai
```
Ajouter au fichier de dépendances existant du projet (`requirements.txt` ou équivalent).

### 2. Stockage du solde et des tarifs

Ajouter une structure de config/état persistant (au format déjà utilisé ailleurs dans le projet — fichier JSON local si c'est la convention existante) :

```json
{
  "openai_credit_balance_usd": 25.00,
  "openai_pricing": {
    "1024x1024": 0.03,
    "1536x1024": 0.05,
    "1024x1536": 0.05
  }
}
```
Vérifier les tarifs exacts en vigueur au moment de l'implémentation (ils évoluent) plutôt que de recopier ces chiffres sans validation.

Un endpoint (ou une entrée dans les paramètres existants) pour que l'utilisateur édite manuellement `openai_credit_balance_usd`.

### 3. Module de génération OpenAI

`backend/generators/openai_generator.py` :

```python
from openai import OpenAI
import base64

client = OpenAI()  # lit OPENAI_API_KEY depuis l'environnement

def generate_via_openai(prompt: str, resolution: str = "1024x1024") -> bytes:
    """
    Génère une image via GPT Image 2 à partir du script 4W1H assemblé.
    Retourne les bytes de l'image (décodés depuis base64).
    """
    result = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size=resolution,
        n=1,
    )
    image_base64 = result.data[0].b64_json
    return base64.b64decode(image_base64)
```

Adapter le nom du modèle et les paramètres à la version de SDK/API réellement disponible au moment de l'implémentation.

### 4. Décrément du solde après génération réussie

Après un appel `generate_via_openai()` réussi, soustraire le coût correspondant à la résolution utilisée de `openai_credit_balance_usd` et persister la nouvelle valeur. Ne décrémenter qu'en cas de succès confirmé (pas en cas d'erreur API).

### 5. Frontend (React)

Sur l'écran de choix de génération, deux options au même niveau (pas de hiérarchie "principal vs secours") :
- Bouton génération locale (comportement existant, inchangé)
- Bouton "GPT Image 2" affichant : `GPT Image 2 (0,03 $ / génération) — Solde estimé : 24,97 $`

Le libellé se met à jour après chaque génération OpenAI réussie, à partir de la valeur persistée côté backend.

Prévoir un état visuel si le solde estimé passe sous le coût d'une génération (bouton désactivé ou message d'alerte), pour éviter un appel voué à échouer côté OpenAI — étant donné que ce solde est une estimation, ça n'empêche pas un éventuel refus réel de l'API si le compte a été utilisé ailleurs entre-temps ; gérer ce cas comme une erreur d'appel classique (voir point suivant).

### 6. Gestion des erreurs

- `OPENAI_API_KEY` absente de l'environnement : échec explicite et lisible, pas de plantage silencieux.
- Échec d'appel API (quota réellement épuisé malgré le solde estimé positif, réseau, contenu refusé par la modération OpenAI) : erreur claire remontée au frontend, solde local non décrémenté.

## Ce qu'il ne faut PAS ajouter en V1

- Pas de tentative de synchronisation automatique du solde avec OpenAI (aucun endpoint fiable pour ça, cf. plus haut).
- Pas de gestion multi-fournisseurs (Flux, Kling, etc.) — uniquement OpenAI pour l'instant.
- Pas de sélection automatique entre local et OpenAI — le choix reste manuel, fait par l'utilisateur avant génération.

## Point de vigilance pour Claude Code

Avant d'écrire le code, vérifier dans le projet existant :
- Le nom exact et l'emplacement de l'écran/endpoint FastAPI qui déclenche la génération actuelle, pour y ajouter l'option OpenAI au même niveau que l'option locale.
- Le format du script assemblé par le protocole 4W1H (texte brut ? structuré ?) pour s'assurer qu'il est compatible tel quel avec le paramètre `prompt` de l'API OpenAI.
- La convention de stockage d'état/config déjà utilisée dans le projet, pour y intégrer `openai_credit_balance_usd` de façon cohérente plutôt que d'introduire un nouveau mécanisme de persistance.
- La convention de nommage/emplacement des fichiers images générés en local, pour répliquer le même comportement de sauvegarde côté OpenAI.
