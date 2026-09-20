# Générateur d'images 4W1H

Application locale (React + FastAPI) qui construit un script de génération d'image
en répondant à 5 questions — **What / Who / Where / When / How** — puis l'envoie
à [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (Stable Diffusion) exécuté
en local sur la machine.

Usage personnel, mono-utilisateur, pensé pour un Mac mini M4 (backend MPS
d'Apple, sans GPU CUDA).

## Structure du dépôt

```
backend/    API FastAPI (assemblage du script, presets, appel à ComfyUI)
frontend/   Application React + TypeScript (Vite)
scripts/    Scripts d'installation (ComfyUI, modèle de traduction) — macOS
```

## Fonctionnement

- **Prompt libre global** : vous écrivez directement un prompt complet.
- **Tout générer pour moi** : tirage aléatoire d'une réponse par question (5 tirages).
- **Question par question** : pour chacune des 5 questions, trois choix possibles —
  liste numérotée de 20 propositions, réponse libre, ou "l'app décide" (tirage
  aléatoire sur cette question uniquement).
- Le texte libre (réponse libre par question, ou prompt libre global) est
  saisi en français puis **traduit en anglais en local** avant envoi au
  modèle (Argos Translate — voir `backend/app/services/translation.py` et
  l'étape d'installation ci-dessous), les checkpoints Stable Diffusion étant
  entraînés très majoritairement sur des légendes anglaises.
- Le script assemblé (déjà traduit) est **toujours affiché avant envoi** à
  ComfyUI.
- Le style choisi dans "What" détermine le **preset technique** (checkpoint,
  LoRA, sampler, steps, CFG, résolution) utilisé pour la génération — mapping
  statique dans `backend/presets/presets.json`, à éditer manuellement après vos
  propres essais dans ComfyUI (pas d'auto-sélection en V1).
- **Plusieurs moteurs de génération** sont supportés (`engine_type` du
  modèle) : SDXL, Flux dev, Anima, Flux schnell (moteur MLX natif, rapide,
  via le custom node `Mflux-ComfyUI`) et Flux Kontext. Le dispatch vers le
  bon moteur est centralisé dans
  `backend/app/services/generation_dispatch.py`.
- **Image de référence (img2img)** : pour les modèles Flux Kontext, vous
  pouvez fournir une image de référence + une force de transformation
  (denoise) au lieu de partir d'un bruit aléatoire — utile pour retoucher
  ou décliner une image existante.

## Génération par lots (batch)

En plus de la génération unitaire, l'app permet de composer une **liste de
jobs indépendants** (chacun avec son propre script/style/modèle/image de
référence) et de les lancer d'un coup :

- Le batch tourne **côté serveur**, en tâche de fond — vous pouvez fermer
  l'onglet, la génération continue (utile pour lancer un batch le soir et
  récupérer les images le lendemain).
- Les items sont traités **strictement en série** (ComfyUI ne traite qu'un
  job à la fois) et **une erreur sur un item n'arrête pas le batch** : elle
  est consignée, et le batch continue avec l'item suivant.
- Les résultats (images + métadonnées) sont sauvegardés sur disque dans
  `backend/generated_batches/<batch_id>/` et consultables via l'onglet
  **Historique** de l'interface, qui affiche la progression en direct
  pendant qu'un batch tourne.
- Un batch interrompu par un redémarrage du backend est marqué
  `"interrupted"` dans l'Historique plutôt que de rester bloqué sur
  "en cours" — il n'y a pas de reprise automatique en V1.

## Accès depuis un autre appareil (iPad, téléphone…)

Le serveur de dev Vite écoute sur toutes les interfaces réseau
(`server.host: true` dans `frontend/vite.config.ts`), pas seulement
`localhost`. Depuis un appareil connecté au **même Wi-Fi** que le Mac,
ouvrez `http://<IP locale du Mac>:5173` dans un navigateur (IP visible via
`ipconfig getifaddr en0` ou dans Réglages réseau macOS). Les appels
`/api` et `/generated` passent par le proxy de Vite vers le backend local :
pas de configuration CORS supplémentaire nécessaire. Le frontend doit
rester lancé sur le Mac pour que ça fonctionne (pas un déploiement
permanent).

## Installation

### 1. ComfyUI (à faire une seule fois, sur le Mac mini)

ComfyUI n'est pas inclus dans ce dépôt et doit être installé séparément :

```bash
./scripts/install_comfyui.sh
```

Ce script clone ComfyUI, crée un environnement virtuel dédié et installe
PyTorch avec support MPS (Apple Silicon). Il affiche ensuite les étapes
suivantes : téléchargement des checkpoints Stable Diffusion, démarrage de
ComfyUI (`python main.py`), et vérification qu'il répond sur
`http://127.0.0.1:8188`.

**Important** : ce script doit être exécuté directement sur le Mac mini —
il ne peut pas être testé depuis un environnement cloud (pas de GPU/MPS).

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuster COMFYUI_HOST/PORT si besoin
uvicorn app.main:app --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrez ensuite `http://localhost:5173` — le serveur de dev proxifie les
appels `/api/*` vers le backend sur le port 8000.

### 4. Modèle de traduction (recommandé)

Le texte libre (voir ci-dessus) n'est traduit en anglais que si ce modèle est
installé — sans lui, l'app fonctionne quand même, mais envoie le texte libre
tel quel (français) au modèle d'image, avec un avertissement dans les logs
backend.

```bash
./scripts/install_translation_model.sh
```

Ce script installe les dépendances backend puis télécharge le modèle
français -> anglais Argos Translate (~50 Mo, une seule fois, connexion
Internet requise). La traduction s'exécute ensuite en local, sans appel
réseau.

## Configuration des presets (`backend/presets/presets.json`)

Le fichier est livré avec les 20 styles de "What" en placeholders
(`REPLACE_ME_...`), plus une entrée `default` utilisée en repli. Après avoir
testé un style dans l'interface ComfyUI et trouvé des réglages satisfaisants,
éditez l'entrée correspondante :

```json
"Anime": {
  "checkpoint": "mon_checkpoint_anime.safetensors",
  "lora": null,
  "sampler": "dpmpp_2m",
  "scheduler": "karras",
  "steps": 25,
  "cfg": 7.5,
  "width": 512,
  "height": 768,
  "negative_prompt": "low quality, blurry, bad anatomy, watermark"
}
```

- `checkpoint` / `lora` : noms de fichiers exacts, tels que présents dans
  `ComfyUI/models/checkpoints/` et `ComfyUI/models/loras/` (`lora: null` si
  aucun LoRA n'est utilisé pour ce style).
- Les styles non encore édités utilisent un nom de checkpoint invalide
  (`REPLACE_ME_...`) : ComfyUI refusera la génération plutôt que d'utiliser
  silencieusement un mauvais modèle.
- Un style sans entrée dédiée retombe automatiquement sur `default`.

## Checklist à faire vous-même sur le Mac mini (après cette livraison)

1. Lancer `./scripts/install_comfyui.sh` et vérifier que ComfyUI démarre
   (`http://127.0.0.1:8188/system_stats`).
2. Lancer `./scripts/install_translation_model.sh` pour que le texte libre
   saisi en français soit traduit en anglais avant envoi au modèle d'image.
3. Télécharger les checkpoints Stable Diffusion (et LoRA éventuels) pour les
   styles que vous comptez utiliser, dans `ComfyUI/models/checkpoints/`
   (et `models/loras/`).
4. Pour chaque style, régler manuellement sampler / steps / CFG / résolution
   dans l'interface ComfyUI jusqu'à obtenir un résultat satisfaisant.
5. Reporter ces réglages dans `backend/presets/presets.json`.
6. Démarrer ComfyUI, puis le backend (`uvicorn`), puis le frontend
   (`npm run dev`), et faire un passage complet : choisir un style avec un
   preset renseigné, parcourir le flux (question par question ou tirage
   global), valider l'écran de prévisualisation, lancer la génération,
   vérifier l'image, puis tester "Régénérer".
7. En cas d'erreur ComfyUI (graphe refusé, nœud manquant), ajuster
   `backend/app/workflows/base_workflow.json` et/ou l'entrée de preset
   concernée — ce réglage dépend de la version de ComfyUI installée et des
   nœuds disponibles, donc nécessairement itératif sur votre machine.

## Tests

```bash
# Backend
cd backend && source .venv/bin/activate && pytest

# Frontend
cd frontend && npm run test && npm run build
```

Les tests backend simulent ComfyUI (`httpx.MockTransport`) et ne nécessitent
pas d'installation réelle. La génération d'image réelle ne peut être
vérifiée qu'avec ComfyUI effectivement lancé sur la machine.

## Hors scope V1

Upload de fichiers pour préremplir les réponses, saisie vocale, stockage
cloud, auto-sélection intelligente des modules ComfyUI, génération vidéo,
entraînement de modèles — voir `backend.md` / `frontend.md` pour le détail.
