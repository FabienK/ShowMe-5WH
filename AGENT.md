# ShowMe-5WH — mode d'emploi pour un agent (usage depuis un autre projet)

> **Ce fichier suffit.** Il n'est pas nécessaire de lire `README.md`,
> `init/etat.md`, `frontend/`, `plans/` ni le code pour générer des images.
> Une seule source de vérité pour les `model_id` : `backend/presets/presets.json`
> (voir §4). Ne pas modifier ShowMe depuis un autre projet.

ShowMe-5WH est un générateur d'images **local** (FastAPI + ComfyUI sur le Mac)
piloté par une API REST. Dépôt :
`/Users/fabien_1/Documents/Projets Claude code/ShowMe-5WH`.
API : **`http://127.0.0.1:8540/api`** (port dédié — pas 8000, pas 8080).

---

## 1. Démarrer et vérifier (toujours en premier)

```bash
"/Users/fabien_1/Documents/Projets Claude code/ShowMe-5WH/scripts/start_showme.sh"
```

Idempotent : lance ComfyUI (8188) et le backend (8540) s'ils ne tournent pas,
ne touche à rien s'ils tournent déjà et sont sains, **refuse** (exit 1, message
explicite) si un port est occupé par un autre programme — dans ce cas, arrêter
ce programme ou le déplacer, ne jamais lancer ShowMe sur un autre port. Le
frontend web n'est pas nécessaire pour l'API (`--with-frontend` pour l'avoir).

ComfyUI est **partagé entre projets** et peut avoir été lancé d'ailleurs, ou
avant un déplacement de dossier : il répond alors sur le port mais ses chemins
de modèles sont périmés. Le script vérifie donc qu'il tourne depuis
`ShowMe-5WH/ComfyUI` **et** que `CheckpointLoaderSimple` voit
`sd_xl_base_1.0.safetensors` ; sinon il le remplace — sauf si une génération
est en cours (exit 1, relancer plus tard). `--restart-comfyui` force ce cycle.
Ne jamais lancer ComfyUI autrement que par ce script.

Vérification que l'on parle bien à ShowMe (et pas à un autre serveur) :

```bash
curl -s http://127.0.0.1:8540/api/health     # → {"status":"ok","app":"ShowMe-5WH"}
```

Arrêt : `scripts/stop_showme.sh` (backend + frontend), `--all` pour ComfyUI aussi.

## 2. ShowMe est-il déjà occupé ?

Une seule génération à la fois, tous appelants confondus (verrou côté
serveur). **Avant de générer** :

```bash
curl -s http://127.0.0.1:8540/api/status
# {"busy":false,"current":null,"waiting":0,"running_batches":[],"comfyui_reachable":true}
```

- `busy: true` → une image est en cours (`current` : `model_id`, `source`
  `generate`/`batch`, `batch_id`, `started_at`) ; `waiting` = appels déjà en
  file derrière.
- `comfyui_reachable: false` → ComfyUI n'est pas lancé : relancer §1.

Si occupé, deux options :
1. **Déposer un batch (§6) et repasser** — recommandé : `POST /api/batches`
   répond immédiatement (202), le serveur enchaîne quand la place se libère.
2. Attendre en sondant `/api/status` toutes les 30 s, puis générer.

Un `POST /api/generate` envoyé pendant que c'est occupé **n'échoue pas** : il
attend son tour, puis génère. Prévoir un timeout HTTP client ≥ temps des jobs
devant + le sien (compter large : 15 min pour du Flux schnell, plus si un
batch tourne). Ne jamais lancer deux `/api/generate` en parallèle.

## 3. Générer une image : 2 appels

### 3a. `POST /api/script` — traduire et détecter le style

Le prompt s'écrit en **français** ; il est traduit en anglais en local
(Argos Translate) et le style est détecté par mots-clés.

```bash
curl -s http://127.0.0.1:8540/api/script \
  -H 'Content-Type: application/json' \
  -d '{"mode":"free_prompt","prompt":"Photo réaliste d’une chaîne de dominos noirs sur une table en bois, le premier bascule, lumière douce de fin d’après-midi"}'
```

Réponse (extrait) :

```json
{"mode":"free_prompt","script":"Realistic photo of a chain of black dominoes on a wooden table, ...",
 "style":"Photoréaliste",
 "models":[{"id":"realistic_lexique_1216","label":"Realistic Vision Lexique","estimated_time":"~30s",...},
           {"id":"flux_schnell_photo","label":"Flux","version":"schnell","estimated_time":"~2 min 30",...}, ...]}
```

**Toujours relire `script` avant de générer.** Argos se trompe sur les mots
ambigus — cas réels : « pièce » (d'échecs) → *room*, « braise » → *braid*,
« lumière rasante » → *shaved lighting*, « filet d'eau » → *water net*.
Si la traduction est fausse : reformuler en français et rappeler `/api/script`,
**ou** écrire directement le `script` en anglais soi-même à l'étape 3b (l'API
n'impose pas de passer par `/api/script`).

`style` peut être `null` (aucun mot-clé reconnu) : la génération utilisera
alors les modèles `*_default`. Pour forcer un style, le passer explicitement
dans 3b (valeurs exactes en §4).

### 3b. `POST /api/generate` — produire l'image

```bash
curl -s --max-time 900 http://127.0.0.1:8540/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"script":"Realistic photo of a chain of black dominoes on a wooden table, the first one tipping over, soft late-afternoon light",
       "style":"Photoréaliste","model_id":"flux_schnell_photo","seed":null}' \
  > reponse.json
```

- `script` : texte **anglais** (sortie de 3a, ou écrit directement).
- `style` : une des 20 valeurs exactes de §4, ou omis.
- `model_id` : **obligatoire** en pratique (chaque style propose plusieurs
  modèles). Valeurs en §4.
- `seed` : entier pour reproduire une image, `null`/omis pour aléatoire.

Réponse : `{"status":"success","image_base64":"data:image/png;base64,....",
"prompt_id":"...","seed_used":123456,"preset_used":{...}}`.

Décodage — retirer le préfixe `data:image/png;base64,` :

```python
import base64, json
data = json.load(open("reponse.json"))
png = base64.b64decode(data["image_base64"].split(",", 1)[1])
open("photo.png", "wb").write(png)
```

Bonnes pratiques prompt : sujet + lieu + moment + technique/composition en une
phrase ; pas de texte à faire écrire dans l'image ; garder `seed_used` dans les
métadonnées de l'image (reproductibilité). Mentionner le modèle utilisé =
`preset_used.model_label` + `preset_used.model_version`.

## 4. Styles et `model_id` (généré depuis `backend/presets/presets.json`)

`style` doit être **exactement** l'une des 20 chaînes ci-dessous (accents
compris). Chaque style propose ses modèles calibrés **plus**, automatiquement,
`flux_<slug>` (~12 min), `flux_schnell_<slug>` (~2 min 30),
`flux_kontext_<slug>` (img2img uniquement) et `openai_<slug>` (payant, §7).
Si un `model_id` renvoie 422, la liste a changé : relire `presets.json` ou
lire `models[]` dans la réponse de `/api/script`.

| Style | `model_id` disponibles (temps mesuré sur le Mac mini M4) |
|---|---|
| *(aucun style)* | `sdxl_default` ~2 min · `flux_default` · `flux_schnell_default` · `openai_default` |
| Photoréaliste | `realistic_lexique_1216` ~30s · `realistic_vision_photo` ~20s · `flux_photo` ~12 min · **`flux_schnell_photo` ~2 min 30** · `openai_photorealiste` |
| Bande dessinée | `anima_bd` ~7 min · `counterfeit_bd` ~20s · `flux_bande_dessinee` · `flux_schnell_bande_dessinee` · `openai_bande_dessinee` |
| Anime | `counterfeit_anime` ~20s · `flux_anime` · `flux_schnell_anime` · `openai_anime` |
| Peinture à l'huile | `sdxl_huile` ~2 min · `flux_huile` · `flux_schnell_peinture_a_l_huile` · `openai_peinture_a_l_huile` |
| Aquarelle | `sdxl_aquarelle` ~2 min 30 · `flux_aquarelle` · `flux_schnell_aquarelle` · `openai_aquarelle` |
| Pixel art | `sdxl_pixelart` ~2 min · `flux_pixelart` · `flux_schnell_pixel_art` · `openai_pixel_art` |
| 3D render | `sdxl_3drender_lora` ~2 min · `flux_3d_render` · `flux_schnell_3d_render` · `openai_3d_render` |
| Croquis crayon | `sdxl_croquis_lexique` ~2 min · `sdxl_croquis` ~2 min · `flux_croquis_crayon` · `flux_schnell_croquis_crayon` · `openai_croquis_crayon` |
| Cyberpunk | `sdxl_cyberpunk` ~2 min · `flux_cyberpunk` · `flux_schnell_cyberpunk` · `openai_cyberpunk` |
| Fantasy médiéval | `sdxl_fantasy` ~2 min · `sdxl_fantasy_lora_art` ~2 min · `flux_fantasy_medieval` · `flux_schnell_fantasy_medieval` · `openai_fantasy_medieval` |
| Noir et blanc argentique | `sdxl_nb_argentique` ~2 min · `rv_nb_argentique_lora_film` ~20s · `flux_noir_et_blanc_argentique` · `flux_schnell_noir_et_blanc_argentique` · `openai_noir_et_blanc_argentique` |
| Pop art | `sdxl_popart` ~2 min · `counterfeit_popart` ~20s · `flux_pop_art` · `flux_schnell_pop_art` · `openai_pop_art` |
| Minimaliste vectoriel | `sdxl_minimaliste` ~2 min · `flux_minimaliste_vectoriel` · `flux_schnell_minimaliste_vectoriel` · `openai_minimaliste_vectoriel` |
| Surréaliste | `sdxl_surrealiste` ~2 min · `flux_surrealiste` · `flux_schnell_surrealiste` · `openai_surrealiste` |
| Steampunk | `sdxl_steampunk_lora` ~2 min · `flux_steampunk` · `flux_schnell_steampunk` · `openai_steampunk` |
| Gothique | `sdxl_gothique` ~2 min · `sdxl_gothique_lora_dark` ~2 min · `flux_gothique` · `flux_schnell_gothique` · `openai_gothique` |
| Art nouveau | `sdxl_art_nouveau` ~2 min · `flux_art_nouveau` · `flux_schnell_art_nouveau` · `openai_art_nouveau` |
| Cartoon | `sdxl_cartoon_lora` ~2 min · `flux_cartoon` · `flux_schnell_cartoon` · `openai_cartoon` |
| Isométrique | `sdxl_isometrique` ~2 min · `flux_isometrique` · `flux_schnell_isometrique` · `openai_isometrique` |
| Impressionniste | `sdxl_impressionniste_lora_monet` ~2 min · `flux_impressionniste` · `flux_schnell_impressionniste` · `openai_impressionniste` |

**Choix par défaut pour un usage programmatique** : `flux_schnell_*`
(~2 min 30, très fidèle au prompt, 1216×832). Pour itérer vite sur une idée :
un modèle `~20s`/`~30s` (512 px ou 1216×832 selon l'entrée). `flux_*` (dev,
~12 min) seulement si la qualité schnell ne suffit pas.

## 5. Autres modes de `/api/script`

- `{"mode":"global_random"}` : tirage aléatoire des 5 réponses (What/Who/Where/When/How).
- `{"mode":"per_question","answers":{"what":{"source":"list","index":2},
  "who":{"source":"free_text","text":"un vieux pêcheur"},"where":{"source":"random"},
  "when":{"source":"random"},"how":{"source":"random"}}}` : `index` 1-20 dans
  la liste de la question (`GET /api/questions` pour les listes).

## 6. Batch : plusieurs images, ou « je dépose et je repasse »

```bash
curl -s http://127.0.0.1:8540/api/batches -H 'Content-Type: application/json' \
  -d '{"items":[{"script":"...","style":"Photoréaliste","model_id":"flux_schnell_photo"},
                {"script":"...","style":"Aquarelle","model_id":"sdxl_aquarelle"}]}'
# → 202 {"batch_id":"20260920T160200_1f1f5906"}
curl -s http://127.0.0.1:8540/api/batches/<batch_id>
# → {"status":"running"|"completed"|"interrupted","items":[{"index":0,"status":"success",
#     "image_path":"<batch_id>/0.png","seed_used":...,"preset_used":{...}}, ...]}
```

Image d'un item : `http://127.0.0.1:8540/generated/<image_path>` (PNG direct,
pas de base64) ; sur disque : `backend/generated_batches/<batch_id>/<index>.png`.
Les items s'exécutent en série ; une erreur sur un item n'arrête pas le batch
(`status:"error"` + `error_type`). Un backend redémarré marque le batch
`interrupted` (pas de reprise) : relancer les items manquants.
À préférer dès ≥ 3 images, ou quand `/api/status` dit `busy`.

## 7. Cas particuliers

- **img2img (Flux Kontext)** : `model_id:"flux_kontext_<slug>"`,
  `reference_image` = PNG/JPEG en base64 (avec ou sans préfixe data:), et
  `script` = instruction de transformation. Très lent (~26 min, jusqu'à 40 min
  au premier chargement). `denoise_strength` (0.1-1.0) ne s'applique qu'aux
  autres moteurs quand on leur donne une `reference_image` (sauf `flux_schnell`
  et `openai`, qui la refusent).
- **OpenAI GPT Image 2** (`openai_<slug>`) : service cloud **payant**,
  nécessite `OPENAI_API_KEY` dans `backend/.env`. Ne pas l'utiliser sans accord
  explicite de l'auteur dans le projet appelant.

## 8. Contraintes et erreurs

- Un seul job à la fois (§2). Changer de moteur entre deux images recharge un
  gros modèle : grouper les images par `model_id` dans un batch.
- Timeouts serveur : SDXL 300 s · Flux schnell 600 s · Anima 900 s ·
  Flux dev 1200 s · Flux Kontext 2400 s.
- Erreurs (`{"detail":{"status":"error","error_type":...,"detail":...}}`) :
  `invalid_model_id` 422 · `reference_image_required_for_model` /
  `img2img_not_supported_for_model` 422 · `invalid_reference_image` 422 ·
  `comfyui_unreachable` 503 (relancer §1) · `comfyui_timeout` 504 ·
  `comfyui_generation_failed` 502 · `openai_api_key_missing` 503.
- `comfyui_generation_failed` avec « No such file or directory » ou « value not
  in list » dans `ComfyUI/comfyui_run.log` alors que le fichier modèle existe :
  ComfyUI a été lancé depuis un ancien chemin (ou par un autre projet) →
  relancer §1, qui le détecte et le remplace.
- Sorties hors batch : ComfyUI écrit aussi chaque image dans
  `ShowMe-5WH/ComfyUI/output/` (utile si la réponse HTTP a été perdue).
