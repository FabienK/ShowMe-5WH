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
scripts/    Script d'installation de ComfyUI (macOS)
```

## Fonctionnement

- **Prompt libre global** : vous écrivez directement un prompt complet.
- **Tout générer pour moi** : tirage aléatoire d'une réponse par question (5 tirages).
- **Question par question** : pour chacune des 5 questions, trois choix possibles —
  liste numérotée de 20 propositions, réponse libre, ou "l'app décide" (tirage
  aléatoire sur cette question uniquement).
- Le script assemblé est **toujours affiché avant envoi** à ComfyUI.
- Le style choisi dans "What" détermine le **preset technique** (checkpoint,
  LoRA, sampler, steps, CFG, résolution) utilisé pour la génération — mapping
  statique dans `backend/presets/presets.json`, à éditer manuellement après vos
  propres essais dans ComfyUI (pas d'auto-sélection en V1).

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
2. Télécharger les checkpoints Stable Diffusion (et LoRA éventuels) pour les
   styles que vous comptez utiliser, dans `ComfyUI/models/checkpoints/`
   (et `models/loras/`).
3. Pour chaque style, régler manuellement sampler / steps / CFG / résolution
   dans l'interface ComfyUI jusqu'à obtenir un résultat satisfaisant.
4. Reporter ces réglages dans `backend/presets/presets.json`.
5. Démarrer ComfyUI, puis le backend (`uvicorn`), puis le frontend
   (`npm run dev`), et faire un passage complet : choisir un style avec un
   preset renseigné, parcourir le flux (question par question ou tirage
   global), valider l'écran de prévisualisation, lancer la génération,
   vérifier l'image, puis tester "Régénérer".
6. En cas d'erreur ComfyUI (graphe refusé, nœud manquant), ajuster
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
