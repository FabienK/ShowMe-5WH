# Backend — App génération d'images (4W1H)

## Stack
- **Backend** : Python + FastAPI
- **Frontend** : React (web local)
- **Moteur de génération** : Stable Diffusion via ComfyUI (à installer — pas encore présent sur la machine)
- **Communication backend ↔ ComfyUI** : API HTTP/WebSocket exposée par défaut par ComfyUI (`localhost:8188`)
- **Environnement** : 100% local, Mac mini M4 (pas de GPU CUDA — backend MPS d'Apple, temps de génération plus longs qu'avec une carte NVIDIA, accepté)

## Responsabilités du backend
1. Recevoir soit un prompt libre global, soit les réponses aux 5 questions (What/Who/Where/When/How) depuis le frontend
2. Chaque question dispose d'une **liste fixe et numérotée** de propositions (référentiel à définir par l'utilisateur, style inclus pour "What")
3. Pour le mode "app décide" (question isolée) ou "tout générer pour moi" (global) : tirage d'un nombre aléatoire par question concernée, correspondance directe avec l'entrée numérotée dans la liste de cette question — un seul algorithme de tirage, réutilisé dans les deux cas
4. Assembler le script final à partir des 5 réponses (ou utiliser directement le prompt libre global)
5. Résoudre le **preset technique** à utiliser à partir du style choisi dans "What" (mapping statique style → checkpoint/LoRA/paramètres, construit manuellement par l'utilisateur après ses propres tests — pas d'inférence automatique en V1)
6. Envoyer la requête de génération à ComfyUI via son API
7. Récupérer l'image générée et la transmettre au frontend

## Presets (V1)
- Table de correspondance statique : `style → {checkpoint, LoRA, sampler, steps, CFG, résolution, ...}`
- Alimentée manuellement par l'utilisateur au fur et à mesure de ses essais dans ComfyUI
- Pas de logique d'auto-sélection ou d'inférence à partir du contenu du script en V1

## Prérequis d'installation
- ComfyUI n'est pas encore installé — fait partie du périmètre projet (installation + configuration initiale sur Mac mini M4)
- Modèles Stable Diffusion à télécharger selon les styles retenus par l'utilisateur après ses tests

## Hors scope V1 (backlog V2+)
- Parsing de fichiers texte/image uploadés pour préremplir les réponses (l'image nécessite des précisions techniques supplémentaires à définir avant implémentation)
- Speech-to-text pour saisie vocale
- Stockage cloud (upload des images générées vers un service externe)
- Auto-sélection intelligente des modules ComfyUI (règles ou modèle qui infère les bons paramètres depuis le script)
- Génération vidéo (AnimateDiff / Stable Video Diffusion — charge GPU nettement supérieure, impact fort sur temps de génération en local sur M4)
- Entraînement de modèles (LoRA custom, Dreambooth) — écarté, pas de jeu de données disponible

## Points d'attention techniques
- Pas de GPU CUDA sur M4 : temps de génération à valider empiriquement avant de juger la V1 utilisable en pratique
- Le mapping style → preset ComfyUI est un artefact à maintenir manuellement (fichier de config ou base légère), pas une fonctionnalité "intelligente"
