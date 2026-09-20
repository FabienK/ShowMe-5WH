# Mapping style → modèle(s) — suivi de calibration

Objectif : pour chacun des 20 styles de la question "What", déterminer le(s)
modèle(s) adapté(s), avec leurs caractéristiques. Un style peut avoir 1
modèle (auto-sélection) ou plusieurs (l'app propose le choix à l'utilisateur
avec leurs caractéristiques).

## Protocole d'affichage des modèles (validé le 2026-08-10)

Chaque `ModelOption` a 4 champs texte destinés à l'UI, à toujours renseigner
selon ce format pour rester lisible :

- `label` : nom technique du modèle seul (ex. "SDXL", "Flux", "Realistic
  Vision", "Counterfeit", "Anima") — jamais de registre du style "Rapide"/
  "Qualité supérieure"/"Standard", le temps affiché à côté rend ça inutile.
- `version` : ce qui distingue cette entrée d'une autre du même `label` pour
  ce style — "base 1.0", "dev", "schnell", "V2.5", "base v1.0", ou
  "+ LoRA <Nom Lisible>" quand un LoRA est appliqué.
- `estimated_time` : temps normalisé, toujours `~Xs` sous 60s ou `~X min`/
  `~X min 30` au-dessus. Jamais "~X minutes", jamais de virgule.
- `description` : une phrase courte (≤15 mots) qui répond à "pourquoi choisir
  celui-ci", sans jargon technique (pas de "steps", "GGUF", "backend MLX" —
  ça reste dans ce document, pas dans l'UI) et sans répéter le temps.

Le frontend (`ModelSelector.tsx`, `ResultPage.tsx`) affiche
`{label} · {version} · {estimated_time}` en titre puis `{description}`
en dessous. Toute nouvelle entrée ajoutée à `presets.json` doit suivre ce
format.

## Logique de l'app (validée le 2026-08-08)

```
CAS 1 — style issu du "What" (choix utilisateur ou tirage aléatoire) :
    SI plusieurs modèles conviennent à ce style :
        → proposer le choix, avec les caractéristiques de chaque modèle
    SINON (un seul modèle convient) :
        → générer automatiquement avec ce modèle

CAS 2 — prompt libre :
    SI aucun style identifiable (pas de mot-clé détecté) :
        → utiliser LE modèle généraliste
    SINON (mot-clé de style détecté) :
        → retombe dans la logique du CAS 1
```

- Détection de style dans le prompt libre : par **mots-clés** (pas d'appel LLM,
  app 100% locale). **Implémentée le 2026-08-10** :
  `backend/app/data/style_keywords.py` (mots-clés par style, alimentés par
  la colonne "Mots-clés déclencheurs" ci-dessous) +
  `backend/app/services/style_detection.py` (`detect_style()`, le mot-clé
  le plus long/spécifique l'emporte en cas d'ambiguïté). Branchée dans
  `backend/app/routers/script.py` pour le mode `free_prompt` et pour la
  question "What" répondue en texte libre (ce dernier cas plantait
  auparavant avec une erreur 422 "Style inconnu" côté `/generate` — corrigé
  au passage : le style est désormais résolu par mots-clés *avant* d'être
  transmis, plutôt que rejeté par le validateur strict).
- Modèle généraliste (cas 2.1) : **décidé le 2026-08-10** — SDXL base
  (1024×1024), cohérent avec le choix retenu pour la grande majorité des
  20 styles. Preset `default` de `presets.json` mis à jour en conséquence
  (`sdxl_default`, remplace l'ancien repli SD1.5 512×512).
- Prompt négatif par modèle vs. intention utilisateur : **implémenté le
  2026-08-10**. Chaque `ModelOption` porte déjà son propre `negative_prompt`
  (spécifique par modèle). Avant chaque génération, si le prompt positif de
  l'utilisateur demande explicitement un effet couvert par ce négatif (ex.
  "flou artistique", "filigrane") sans le nier ("sans flou"), le terme
  correspondant est retiré du négatif pour cette génération.
  `backend/app/data/negative_prompt_triggers.py` (déclencheurs français par
  terme, ~5 chacun, + marqueurs de négation français) +
  `backend/app/services/negative_prompt.py`
  (`strip_negative_conflicts(positive, negative)`, fenêtre de 30 caractères
  avant le déclencheur pour détecter une négation). Branché dans
  `backend/app/routers/generate.py` (moteurs `sd_checkpoint` et `anima` ;
  Flux n'a pas de négatif dans son graphe). Limite connue : la fenêtre de
  négation est un heuristique simple (pas d'analyse grammaticale), donc une
  négation formulée loin du déclencheur (ex. "je ne veux vraiment pas, sous
  aucun prétexte, de flou") peut ne pas être détectée.

## Prérequis

Chaque style doit avoir au moins un modèle associé, ou retomber sur le
modèle généraliste (une fois désigné).

## Inventaire des modèles disponibles

| Modèle | Type | Moteur ComfyUI | Vitesse constatée (Mac mini M4) |
|---|---|---|---|
| Realistic_Vision_V6.0_NV_B1_fp16 | Checkpoint SD1.5 | fast | ~20s / 512×512 / 20 steps (test du 2026-08-08) |
| Counterfeit-V2.5_fp16 | Checkpoint SD1.5 | fast | ~20s / 512×512 / 20 steps (test du 2026-08-08) |
| v1-5-pruned-emaonly | Checkpoint SD1.5 (base neutre) | fast | rapide (non re-mesuré) — **supprimé du disque le 2026-08-10** (plus référencé par aucun style depuis le passage du généraliste et d'"Art nouveau" à SDXL) |
| sd_xl_base_1.0 | Checkpoint SDXL (base neutre) | fast | ~2min04s / 1024×1024 / 20 steps (test du 2026-08-08) |
| anima-base-v1.0 | Diffusion model dédié | anima | ~7min13s / 1024×1024 / 30 steps (test du 2026-08-08) |
| flux1-krea-dev-Q5_K_M | Diffusion model (Flux.1) | flux | ~12min23s / 1024×1024 / 20 steps (test du 2026-08-08) |
| anima-turbo-lora-v0.2 | LoRA (accélération) | à câbler (non branché actuellement) | inconnu — **supprimé du disque le 2026-08-10** (jamais câblé dans le code) |
| 3d_render_style_xl (goofyai) | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024 (même vitesse que SDXL seul) |
| pixar_style_sdxl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024 — pas gardée (voir style "3D render"), **supprimée du disque le 2026-08-10** |
| fantasy_art_xl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024 — gardée (voir style "Fantasy médiéval") |
| medieval_memories_sdxl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024 — pas gardée (voir style "Fantasy médiéval"), **supprimée du disque le 2026-08-10** |
| film_lora_analog | LoRA SD1.5 | fast | testée 2026-08-10, ~20s/512×512, strength 0.7 — gardée (voir style "Noir et blanc argentique") |
| bw_1920s_style | LoRA SD1.5 | fast | testée 2026-08-10, ~20s/512×512 — pas gardée (artefacts/couleur qui perce), voir style "Noir et blanc argentique", **supprimée du disque le 2026-08-10** |
| steampunk_xl_v2 | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024, strength 0.8 — gardée seule (voir style "Steampunk") |
| dark_gothic_fantasy_xl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024, strength 1.0 — gardée (voir style "Gothique") |
| inspired_by_mucha | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024, strength 1.0 — pas gardée (voir style "Art nouveau"), **supprimée du disque le 2026-08-10** |
| animated_concept_sdxl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024, strength 0.75 — gardée seule (voir style "Cartoon") |
| monet_painting_style_xl | LoRA SDXL | fast | testée 2026-08-10, ~2min/1024×1024, strength 0.9 — gardée seule (voir style "Impressionniste") |
| pencil_sketch_style_sd15 | LoRA SD1.5 | fast | testée 2026-08-10, ~20s/512×512 — pas gardée (artefacts de hachures, voir style "Croquis crayon"), **supprimée du disque le 2026-08-10** |

## Suivi style par style

Statuts possibles : `à tester` / `en cours` / `validé` / `modèle à installer`

| # | Style | Statut | Modèle(s) retenu(s) | Mots-clés déclencheurs (prompt libre) | Notes |
|---|---|---|---|---|---|
| 1 | Bande dessinée | validé | Anima (comics occidental, encrage épais + trames) et Counterfeit-V2.5 (manga/anime) — 2 modèles, choix proposé à l'utilisateur | bande dessinée, comics, bd, planche (→ Anima) / manga, anime (→ Counterfeit-V2.5) | Test du 2026-08-08 avec prompt "superhero landing on rooftop, bold ink outlines, comic book panel style" : Anima colle nettement mieux au rendu "comics" (traits encrés, halftones, ~7min). Counterfeit-V2.5 reste un bon manga (~20s) mais ne correspond pas à "bande dessinée" occidentale. Anima reproduit des éléments visuels proches de super-héros connus (S-shield, cagoule) — normal vu l'entraînement, à surveiller pour usage perso |
| 2 | Photoréaliste | validé | Realistic Vision (rapide, bon pour itérer) + Flux dev (qualité/fidélité supérieure, lent) + **Flux schnell (rapide, ~2min30, ajouté 2026-08-10)** — 3 modèles, choix proposé à l'utilisateur | photo réaliste, réaliste, photographie | Test du 2026-08-08, prompt portrait pluie/néons (seed 42) : Flux dev respecte le prompt presque parfaitement (couleur veste, nuit, néons) en ~12min39s/1024px. Realistic Vision dérive un peu (veste rouge au lieu de verte, ambiance plus diurne que nocturne) mais reste net et rapide (~20s/512px) — bon pour itérer vite, moins fiable au prompt exact. Flux schnell (2026-08-10, via MLX/mflux, 4 steps) : reste fidèle au prompt (veste verte, cadrage portrait, pluie/néons) à un niveau proche de dev, en ~2min28s au lieu de ~11-12min — ajouté comme 3ème choix |
| 3 | Anime | validé | Counterfeit-V2.5 — modèle unique, auto-sélection (pas de choix à proposer) | anime, manga | Test du 2026-08-08, même prompt que Photoréaliste sans mot-clé "anime" (seed 42) : le style anime s'impose naturellement (biais du checkpoint), contenu bien respecté (veste verte correcte, scène nocturne pluvieuse). ~22s/512px. Un seul modèle dédié → CAS 1.2 (auto) |
| 4 | Peinture à l'huile | validé | SDXL base (rapide, ~2min) + Flux (plus riche, ~13min) — 2 modèles, choix proposé à l'utilisateur, PAS de téléchargement nécessaire | huile, peinture | Test du 2026-08-08, prompt "oil painting... visible brush strokes, impasto texture" (seed 42) : les deux modèles génériques rendent un vrai style peinture à l'huile convaincant sans modèle dédié. SDXL ~2min04s/1024px, Flux ~12min50s/1024px (plus riche en détails/couleurs mais 6x plus lent) |
| 5 | Aquarelle | validé | SDXL base (rapide, ~2min30s) + Flux (texture papier plus authentique, ~13min) — 2 modèles, choix proposé à l'utilisateur, PAS de téléchargement nécessaire | aquarelle, watercolor | Test du 2026-08-08, prompt "watercolor painting... soft washes, paper texture, bleeding effect" (seed 42) : les deux modèles génériques rendent une aquarelle convaincante. SDXL ~2min30s, Flux ~12min43s (texture papier/bords fondus plus fins, meilleur respect du contenu) |
| 6 | Pixel art | validé | SDXL base (rapide, ~2min) + Flux (le plus riche/détaillé, ~12min) — 2 modèles, choix proposé à l'utilisateur, PAS de téléchargement nécessaire | pixel art, 8-bit | Aucun modèle dédié installé — modèles bien adaptés mais non installés : *PixelArt XL* (LoRA/checkpoint SDXL) et *All-In-One-Pixel-Model* (checkpoint SD1.5), disponibles sur Civitai si le générique ne suffit plus |
| 7 | 3D render | validé | SDXL base + LoRA "3D Render Style XL" (rapide, ~2min, modèle unique retenu) — Flux et LoRA "Pixar Style" testés mais écartés | 3D, render, pixar | LoRA "3D Render Style XL" (goofyai) installée le 2026-08-10 |
| 8 | Croquis crayon | validé | SDXL base — modèle unique, auto-sélection. SD1.5 générique évoqué comme alternative "ébauche" mais jamais câblé dans `presets.json` ; son checkpoint (v1-5-pruned-emaonly) a été supprimé du disque le 2026-08-10 (inutilisé) | croquis, crayon, sketch | LoRA "Pencil Sketch Style" (SD1.5, civitai.com/models/103495) testée et écartée — artefacts de hachures, LoRA supprimée du disque le 2026-08-10 |
| 9 | Cyberpunk | validé | SDXL base (rapide, ~2min) + Flux dev (le plus cinématique, ~12min) + **Flux schnell (rapide, ~2min30, ajouté 2026-08-10)** — 3 modèles, choix proposé à l'utilisateur | cyberpunk | Realistic Vision (préréglage initial) testé et écarté — bonne qualité mais tenue trop suggestive pour ce prompt. Flux schnell (2026-08-10, via MLX/mflux, 4 steps, seed 42) : rendu cyborg très littéral (visage/crâne métallique, implants lumineux), enseignes néon bien rendues — interprétation différente de SDXL (silhouette humaine augmentée, vue de dos) mais tout aussi fidèle au prompt, en ~2min21s (comparable à SDXL ~2min10s) — ajouté comme 3ème choix |
| 10 | Fantasy médiéval | validé | SDXL base + LoRA "Fantasy Art XL" (style peinture classique) — 2 modèles, choix proposé à l'utilisateur | fantasy, médiéval | LoRA "Fantasy Art XL" (civitai.com/models/122806) installée le 2026-08-10 ; Flux et LoRA "Medieval Memories" testés mais pas gardés |
| 11 | Noir et blanc argentique | validé | SDXL base (riche/détaillé) + Realistic Vision + LoRA "Analog Film Photography" (grain naturel, strength 0.7) — 2 modèles, choix proposé à l'utilisateur | noir et blanc, argentique | LoRA "Analog Film Photography" installée le 2026-08-10 ; LoRA "Black & White 1920s Style" testée mais écartée (artefacts) |
| 12 | Pop art | validé | SDXL base (vrai style Warhol, trame de points) + Counterfeit-V2.5 (illustration colorée) — 2 modèles, choix proposé à l'utilisateur | pop art | Aucun modèle dédié installé actuellement |
| 13 | Minimaliste vectoriel | validé | SDXL base — modèle unique, auto-sélection | minimaliste, vectoriel | Aucun modèle dédié installé actuellement |
| 14 | Surréaliste | validé | SDXL base — modèle unique, auto-sélection | surréaliste | Aucun modèle dédié installé actuellement |
| 15 | Steampunk | validé | SDXL base + LoRA "Steampunk Style XL" (strength 0.8) — modèle unique retenu | steampunk | LoRA "Steampunk [Style] LoRA XL" (civitai.com/models/135168) installée le 2026-08-10 |
| 16 | Gothique | validé | SDXL base (architecture réaliste) + SDXL/LoRA "Dark Gothic Fantasy" (rendu peint/sombre) — 2 modèles, choix proposé à l'utilisateur | gothique, gothic | LoRA "Dark Gothic Fantasy" (civitai.com/models/293532) installée le 2026-08-10 |
| 17 | Art nouveau | validé | SDXL base — modèle unique, auto-sélection (SD1.5 écarté le 2026-08-10 pour cohérence avec le nouveau généraliste SDXL) | art nouveau | LoRA "Inspired by Mucha" (civitai.com/models/142990) testée mais pas gardée |
| 18 | Cartoon | validé | SDXL base + LoRA "Animated Concept" (strength 0.75) — modèle unique retenu | cartoon | LoRA "Animated Concept SDXL" (civitai.com/models/187625) installée le 2026-08-10 |
| 19 | Isométrique | validé | SDXL base — modèle unique, auto-sélection | isométrique, isometric | Aucun modèle dédié installé actuellement |
| 20 | Impressionniste | validé | SDXL base + LoRA "Monet Painting Style" (strength 0.9) — modèle unique retenu | impressionniste | LoRA "Monet Painting Style" (civitai.com/models/460366) installée le 2026-08-10 |

## Journal

- 2026-08-08 : logique de résolution style→modèle validée avec l'utilisateur.
  Checkpoints déplacés dans `ComfyUI/models/checkpoints` (plus de dépendance
  à l'installation Automatic1111, désormais dans la Corbeille macOS).
- 2026-08-08 : style "Bande dessinée" calibré. Anima = comics occidental,
  Counterfeit-V2.5 = manga/anime. Les deux gardés, choix proposé à
  l'utilisateur avec mots-clés de détection distincts.
- 2026-08-08 : style "Photoréaliste" calibré. Flux = très fidèle au prompt
  mais lent (~12min39s). Realistic Vision = rapide (~20s) mais peut dériver
  du prompt (couleur/ambiance). Les deux gardés, choix proposé à
  l'utilisateur.
- 2026-08-08 : style "Anime" calibré. Counterfeit-V2.5 confirmé comme
  modèle unique (auto-sélection, CAS 1.2), style anime intrinsèque au
  checkpoint même sans mot-clé dans le prompt.
- 2026-08-08 : style "Peinture à l'huile" calibré. SDXL base et Flux
  produisent tous les deux un excellent rendu peinture à l'huile avec un
  bon prompt — aucun modèle dédié à télécharger. Les deux gardés au choix.
- 2026-08-08 : style "Aquarelle" calibré. Même constat que peinture à
  l'huile : SDXL base et Flux rendent tous les deux une aquarelle
  convaincante sans modèle dédié. Les deux gardés au choix.
- 2026-08-10 : style "Pixel art" calibré. Prompt "pixel art, retro video
  game sprite, warrior standing in a medieval village at sunset, 16-bit
  style, limited color palette, crisp pixels, dithering shading" (seed 42) :
  SD1.5 générique (v1-5-pruned-emaonly) ignore la scène (pas de village,
  pas de coucher de soleil) et reste faible. SDXL base (~2min04s/1024px)
  respecte toute la scène avec un bon rendu pixel art. Flux (~12min/1024px)
  encore plus riche/détaillé (arrière-plan château, dithering plus fin)
  mais 6x plus lent pour un gain modéré. SDXL + Flux gardés au choix,
  SD1.5 générique écarté. Checkpoint "fast" du preset mis à jour vers
  sd_xl_base_1.0 (1024×1024, au lieu de v1-5-pruned-emaonly 512×512).
- 2026-08-10 : style "3D render" calibré. Prompt "3D render, pixar style,
  cute round robot character standing on a futuristic city street at
  night, neon signs, wet reflective pavement, octane render, soft global
  illumination, subsurface scattering, highly detailed" (seed 42) : SDXL
  base seul est bon mais un peu plat. Flux dérive vers du photoréaliste et
  perd le côté "rendu 3D/jouet". Téléchargement de deux LoRA SDXL pour
  comparaison : "Pixar Style (SDXL)" (civitai.com/models/188525) et
  "3D Render Style XL" de goofyai (huggingface.co/goofyai/3d_render_style_xl).
  LoRA Pixar Style : dérive vers du semi-réaliste, pas de plus-value nette,
  écartée. LoRA "3D Render Style XL" : nettement le meilleur résultat,
  rendu glossy/CGI cohérent — retenue comme modèle unique pour le preset
  "fast" (SDXL base + cette LoRA, strength 1.0/1.0). Flux écarté (dérive
  photoréaliste, ne correspond pas au rendu "3D/jouet" recherché) : un
  seul modèle proposé pour ce style (auto-sélection, CAS 1.2).
- 2026-08-10 : style "Croquis crayon" calibré. Prompt "pencil sketch,
  graphite drawing, portrait of an elderly wizard with a long beard,
  cross-hatching shading, paper texture, detailed line art, black and
  white" (seed 42) : SD1.5 générique déjà très propre (hachures fines,
  ~20s/512px). SDXL encore plus détaillé/riche (~2min/1024px, ajoute
  chapeau/lunettes). LoRA dédiée "Pencil Sketch Style" (SD1.5) testée :
  rendu plus brut mais avec artefacts de hachures sur le front, écartée.
  Décision utilisateur (2026-08-10) : SDXL = rendu "fini", retenu comme
  checkpoint par défaut du preset ; SD1.5 = rendu "ébauche" plus rapide,
  jugé complémentaire mais pas encore exposé dans l'UI (pas de bouton
  dédié pour un 2e choix propre au style — architecture actuelle limitée
  à fast/flux/anima). À revisiter si ce cas se répète sur d'autres styles.
- 2026-08-10 : style "Cyberpunk" calibré. Prompt "cyberpunk style, cyborg
  character with glowing neon implants, standing in a rain-slicked
  futuristic city street at night, neon signs, dystopian atmosphere,
  highly detailed" (seed 42) : Realistic Vision (préréglage initial,
  ~20s/512px) rend bien l'ambiance néon mais avec une tenue trop
  suggestive pour ce prompt — écarté. SDXL (~2min/1024px) très bon,
  atmosphérique et bien composé. Flux (~12min/1024px) le plus
  impressionnant, cinématique, détails d'armure/pluie excellents.
  SDXL + Flux gardés au choix, checkpoint "fast" du preset changé vers
  sd_xl_base_1.0 (1024×1024, au lieu de Realistic_Vision_V6.0_NV_B1_fp16
  512×512).
- 2026-08-10 : style "Fantasy médiéval" calibré. Prompt "epic fantasy
  medieval knight in ornate armor, standing in an ancient castle
  courtyard, dramatic lighting, highly detailed digital painting" (seed
  42) : SDXL générique très bon mais rendu assez CGI. Flux excellent,
  peinture classique soignée. Téléchargement de deux LoRA SDXL pour
  comparaison : "Fantasy Art XL" (civitai.com/models/122806, entraînée
  sur des artistes fantasy classiques type Boris Vallejo) et "Medieval
  Memories" (civitai.com/models/656224, substituée à "Medieval Scenery
  XL" initialement visée — téléchargement de cette dernière bloqué par
  Civitai, 401 nécessitant une connexion). SDXL + LoRA "Fantasy Art XL" :
  excellent, style peinture chaude/texturée. SDXL + LoRA "Medieval
  Memories" : très bon aussi, ambiance brumeuse/cinématique. Décision
  utilisateur : garder **SDXL générique + SDXL/LoRA "Fantasy Art XL"** au
  choix ; Flux et LoRA "Medieval Memories" testés mais écartés.
- 2026-08-10 : style "Noir et blanc argentique" calibré. Prompt "black and
  white silver gelatin photograph, vintage film grain, portrait of an old
  fisherman on a pier, dramatic shadows, 1950s photography style" (seed
  42) : Realistic Vision (préréglage initial, ~20s/512px) déjà bon.
  SDXL (~2min/1024px) plus riche/détaillé (scène complète cabane/jetée).
  Deux LoRA SDXL initialement visées ("Noir-Style Photography & Film V2",
  "Touch of Grain") bloquées par Civitai (401, connexion requise) —
  substituées par deux LoRA SD1.5 plus anciennes et ouvertes : "Analog
  Film Photography" (civitai.com/models/14826, strength 0.7 recommandée
  par le créateur) et "Black & White 1920s Style"
  (civitai.com/models/64301). Realistic Vision + LoRA "Analog Film
  Photography" : très bon, grain naturel et net. Realistic Vision + LoRA
  "Black & White 1920s Style" : dégradé, artefacts et taches de couleur
  qui percent — écartée. Décision utilisateur : garder **SDXL générique +
  Realistic Vision/LoRA "Analog Film Photography"** au choix. Ajout du
  champ `lora_strength` au schéma des presets (jusque-là fixé à 1.0 en
  dur dans comfyui_client.py) pour refléter fidèlement le strength 0.7
  testé et validé pour cette LoRA.
- 2026-08-10 : style "Pop art" calibré. Prompt "pop art style, Andy Warhol
  inspired, bold vibrant colors, halftone dot pattern, thick black
  outlines, portrait of a woman wearing sunglasses" (seed 42) : Counterfeit
  (préréglage initial, ~20s/512px) donne des couleurs vives mais penche
  vers l'illustration/anime, peu de trame demi-teinte. SDXL (~2min/1024px)
  produit un vrai style Warhol (trame de points, blocs de couleurs,
  contours nets) — nettement meilleur match. Décision utilisateur :
  garder **SDXL + Counterfeit-V2.5** au choix (checkpoint "fast" du
  preset changé vers sd_xl_base_1.0 en position principale, 1024×1024).
- 2026-08-10 : style "Minimaliste vectoriel" calibré. Prompt "minimalist
  vector illustration, flat design, clean geometric shapes, simple color
  palette, no gradients, a fox sitting in a forest" (seed 42) : SD1.5
  (~20s/512px) donne un vrai style plat/vectoriel simple. SDXL
  (~2min/1024px) plus riche/détaillé, niveau illustration éditoriale,
  reste très propre. Décision utilisateur : garder **SDXL seul**
  (modèle unique, auto-sélection), checkpoint "fast" du preset changé
  vers sd_xl_base_1.0 (1024×1024, au lieu de v1-5-pruned-emaonly 512×512).
- 2026-08-10 : style "Surréaliste" calibré. Prompt "surrealist digital
  painting, dreamlike imagery, melting clock, impossible architecture,
  symbolic elements, Salvador Dali inspired" (seed 42) : SDXL
  (~2min/1024px) excellent, composition narrative forte (ville dans
  l'horloge fondante). SD1.5 (~20s/512px) correct mais plus abstrait/
  confus, composition moins lisible. Décision utilisateur : garder
  **SDXL seul** (modèle unique, auto-sélection).
- 2026-08-10 : style "Steampunk" calibré. Prompt "steampunk style, ornate
  brass and copper machinery, gears and cogs, Victorian era airship,
  intricate mechanical details, sepia tones" (seed 42) : SDXL
  (~2min/1024px) très détaillé, engrenages complexes, teintes sépia.
  SD1.5 (~20s/512px) correct mais rendu plus "objet plat" que scène.
  LoRA "Steampunk [Style] LoRA XL" (civitai.com/models/135168, strength
  0.8 recommandée) : nettement le meilleur — vraie scène narrative
  (dirigeable au premier plan + machinerie en fond), esthétique planche
  technique victorienne. Décision utilisateur : garder **SDXL + LoRA
  "Steampunk Style XL" seul** (modèle unique, auto-sélection).
- 2026-08-10 : style "Gothique" calibré. Prompt "gothic style, dark
  cathedral architecture, ornate stained glass windows, dramatic shadows,
  medieval gothic atmosphere, gargoyles" (seed 42) : SDXL (~2min/1024px)
  quasi photoréaliste, vitraux colorés somptueux. SD1.5 (~20s/512px)
  rendu en noir et blanc, moins riche — écarté. LoRA "Dark Gothic Fantasy"
  (civitai.com/models/293532, strength 1.0) : rendu plus peint/sombre,
  gargouilles suspendues visibles, très "dark fantasy". Décision
  utilisateur : garder **SDXL générique + SDXL/LoRA "Dark Gothic
  Fantasy"** au choix.
- 2026-08-10 : style "Art nouveau" calibré. Prompt "art nouveau style,
  ornate flowing organic lines, floral motifs, Alphonse Mucha inspired,
  decorative border, elegant woman portrait" (seed 42) : SDXL
  (~2min/1024px) très fidèle, cadre décoratif riche, couleurs chaudes.
  SD1.5 (~20s/512px) tout aussi convaincant, palette Mucha authentique.
  LoRA "Inspired by Mucha" (civitai.com/models/142990, strength 1.0) :
  cadre encore plus ornemental/entrelacé, tons dorés monochromes — bon
  mais pas retenue. Décision utilisateur : garder **SDXL générique +
  SD1.5 générique** au choix, LoRA testée mais écartée.
- 2026-08-10 : style "Cartoon" calibré. Prompt "cartoon style
  illustration, bold outlines, bright flat colors, exaggerated features,
  a happy dog character, western animation style" (seed 42) : Counterfeit
  (préréglage initial, ~20s/512px) correct, character design simple.
  SDXL (~2min/1024px) bon, contours épais, expression exagérée. LoRA
  "Animated Concept SDXL" (civitai.com/models/187625, strength 0.75) :
  nettement le meilleur, vrai niveau studio d'animation. Décision
  utilisateur : garder **SDXL + LoRA "Animated Concept" seul** (modèle
  unique, auto-sélection), checkpoint "fast" du preset changé vers
  sd_xl_base_1.0 (1024×1024, au lieu de Counterfeit-V2.5_fp16 512×512).
- 2026-08-10 : style "Isométrique" calibré. Prompt "isometric
  illustration, 3D isometric room diorama, clean geometric perspective,
  miniature cozy bedroom scene, vibrant colors" (seed 42) : SD1.5
  (~20s/512px) bon diorama simple, couleurs vives. SDXL (~2min/1024px)
  nettement plus détaillé/riche, mobilier complet, vraie ambiance cosy.
  Décision utilisateur : garder **SDXL seul** (modèle unique,
  auto-sélection), checkpoint "fast" du preset changé vers
  sd_xl_base_1.0 (1024×1024, au lieu de v1-5-pruned-emaonly 512×512).
- 2026-08-10 : style "Impressionniste" calibré (dernier des 20 styles).
  Prompt "impressionist oil painting, visible brush strokes, soft light,
  Claude Monet inspired, garden landscape with a pond and water lilies"
  (seed 42) : SDXL (~2min/1024px) et SD1.5 (~20s/512px) tous les deux
  excellents et proches en qualité (bassin aux nénuphars riche vs pont
  japonais de Giverny). LoRA "Monet Painting Style"
  (civitai.com/models/460366, strength 0.9) : le plus proche d'un vrai
  Monet, texture et palette quasi identiques aux Nymphéas. Décision
  utilisateur : garder **SDXL + LoRA "Monet Painting Style" seul**
  (modèle unique, auto-sélection).

## Calibration terminée (2026-08-10)

Les 20 styles + le preset "default" sont désormais calibrés. Résumé des
statuts : voir le tableau ci-dessus (tous "validé"). Prochaines pistes
possibles : recalibrer un style si un meilleur modèle/LoRA apparaît,
ou étendre le mécanisme de choix multi-modèles à d'autres cas d'usage.

- 2026-08-10 : deux ajustements post-calibration décidés par l'utilisateur.
  (1) Modèle généraliste fixé à **SDXL** (preset `default` → `sdxl_default`,
  1024×1024), remplace l'ancien repli SD1.5 512×512. (2) Style "Art nouveau"
  simplifié en **modèle unique SDXL** (`sdxl_art_nouveau`), l'option SD1.5
  retirée pour rester cohérent avec le nouveau généraliste. `presets.json`,
  `tests/test_presets.py` et ce document mis à jour ; suite de tests (45)
  et validité JSON revérifiées.
- 2026-08-10 : test Anima sur le style "Cartoon" (même prompt que les
  autres tests du style, seed 42, ~7min/1024px) réalisé à la demande de
  l'utilisateur, en comparaison de SDXL + LoRA "Animated Concept" (modèle
  actuellement retenu). Décision utilisateur : garder **SDXL + LoRA
  "Animated Concept" seul** (modèle unique inchangé, Anima écarté).
- 2026-08-10 : nettoyage disque `ComfyUI/models/` — suppression de 7
  fichiers non référencés par `presets.json`/`config.py` (~5,16 Go
  récupérés) : checkpoint `v1-5-pruned-emaonly.safetensors` (4,27 Go,
  plus utilisé depuis le passage du généraliste et d'"Art nouveau" à
  SDXL) et 6 LoRAs testées puis écartées ou jamais câblées :
  `pixar_style_sdxl` (228,5 Mo), `medieval_memories_sdxl` (228,5 Mo),
  `inspired_by_mucha` (228,5 Mo), `bw_1920s_style` (19,0 Mo),
  `pencil_sketch_style_sd15` (37,9 Mo), `anima-turbo-lora-v0.2`
  (148,9 Mo). Décision utilisateur.
- 2026-08-10 : exploration backend MLX pour Flux, suite à la constatation
  que Flux dev (GGUF+MPS, `flux1-krea-dev-Q5_K_M`) prend ~12min23s/image
  sur ce Mac mini M4 24 Go. Installation du custom node `Mflux-ComfyUI`
  (wrapper du package `mflux`, réimplémentation MLX native de Flux) dans
  `ComfyUI/custom_nodes/`. **Résultat Flux dev via MLX : aucun gain réel**
  (11min32s de génération pure, modèle chargé en mémoire, 20 steps,
  1024×1024 — ~7% plus rapide que GGUF, pas les 50-90s annoncés par les
  benchmarks en ligne). Cause identifiée : `system_profiler` confirme que
  ce Mac mini a le **chip M4 de base (10 cœurs GPU)**, pas un M4 Pro/Max —
  les benchmarks cités sont mesurés sur M4 Pro (16-20 cœurs GPU, ~2x la
  bande passante mémoire). Le goulot d'étranglement est matériel, pas
  logiciel. **Flux schnell (4 steps au lieu de 20) via MLX, en revanche,
  change la donne** : ~2min28s de génération pure (testé sur le prompt
  Photoréaliste, seed 42) et ~2min21s sur le prompt Cyberpunk (seed 42) —
  vitesse comparable à SDXL/Realistic Vision, qualité proche de Flux dev
  sur les deux prompts testés (fidélité de scène conservée, juste une
  interprétation parfois différente — ex. Cyberpunk : rendu cyborg plus
  littéral que SDXL). Décision utilisateur : **ajouter Flux schnell comme
  3ème choix** sur les styles "Photoréaliste" et "Cyberpunk" (sans retirer
  les options existantes) — voir lignes #2 et #9 du tableau. Implémentation
  complète : nouveau moteur `engine_type: "flux_schnell"` (schémas backend
  `schemas.py`, settings `config.py`, workflow ComfyUI dédié
  `app/workflows/flux_schnell_workflow.json` utilisant les nœuds
  `MfluxModelsDownloader` + `QuickMfluxNode`, dispatch dans
  `routers/generate.py`, entrées `flux_schnell_photo`/`flux_schnell_cyberpunk`
  dans `presets.json`), côté frontend (`EngineType` dans `types/index.ts`,
  message de chargement dédié dans `ResultPage.tsx`). Testé de bout en
  bout contre la vraie API ComfyUI (pas seulement les tests unitaires
  mockés) : génération réussie via `/api/generate` avec
  `model_id: "flux_schnell_cyberpunk"`. Suite de tests backend (62, dont 3
  nouveaux pour flux_schnell) et validité JSON revérifiées. Modèle
  `flux.1-schnell-mflux-4bit` (~7 Go, quantisé 4-bit) et
  `flux.1-dev-mflux-4bit` (~9,2 Go, non retenu) téléchargés dans
  `ComfyUI/models/Mflux/`. Effet de bord technique : l'installation de
  `mflux==0.4.1` a rétrogradé `pillow`, `huggingface-hub` et `transformers`
  dans le venv ComfyUI — vérifié sans régression sur le pipeline SDXL
  existant (smoke test). Flux dev reste inchangé (toujours sur GGUF+MPS,
  aucun gain à basculer vers MLX pour ce variant sur ce hardware) ; les 18
  autres styles n'ont pas été retestés avec schnell (à faire au cas par
  cas si besoin).
- 2026-08-10 : protocole d'affichage des modèles défini et appliqué aux 33
  entrées de `presets.json` (voir section "Protocole d'affichage des
  modèles" en haut de ce document) — séparation de l'ancien champ `label`
  (qui mélangeait registre + nom + parfois temps, incohérent d'un style à
  l'autre) en 4 champs structurés : `label` (nom technique seul), `version`,
  `estimated_time` (temps normalisé), `description` (phrase courte, sans
  jargon ni temps). Ajout des champs `version`/`estimated_time` à
  `ModelOption` et `PresetUsed` (`schemas.py`), propagation dans
  `_preset_used` (`generate.py`) et dans l'option Flux auto-injectée
  (`presets.py`). Frontend : `ModelSelector.tsx` affiche
  `{label} · {version} · {estimated_time}` en titre, `ResultPage.tsx` mis à
  jour (titres multi-résultats, mode démo, message de chargement — ce
  dernier simplifié pour lire directement `estimated_time` au lieu d'un
  texte codé en dur par `engine_type`, donc plus de risque de désync futur).
  Vérifié par types TypeScript (`tsc -b`), tests backend (62) et frontend
  (5), et visuellement dans l'app réelle (styles Cyberpunk et Fantasy
  médiéval, ce dernier confirmant le cas de deux options "SDXL" distinguées
  uniquement par leur `version`).
- 2026-08-10 : sélection multiple des modèles (checkboxes, 1 à N choix),
  génération par lot (2 images/modèle sauf Flux dev qui reste à 1), estimation
  du temps total affichée sur le bouton, et affichage progressif des images
  au fur et à mesure (file triée du plus rapide au plus lent) implémentés
  côté frontend (`ModelSelector.tsx`, `ScriptPreviewPage.tsx`,
  `ResultPage.tsx`, `useGenerationFlow.ts`, nouvel utilitaire
  `utils/estimate.ts`). Vérifié avec une vraie génération ComfyUI
  (Realistic Vision ×2, images affichées au fur et à mesure). Case à cocher
  visuelle retirée ensuite sur demande utilisateur — la sélection reste
  indiquée par la bordure accentuée déjà existante sur l'option cochée.
- 2026-08-10 : **Flux schnell rendu disponible sur tous les styles**, pas
  seulement Photoréaliste et Cyberpunk. `presets.py::_ensure_flux_schnell_option`
  ajoute automatiquement l'option (label "Flux", version "schnell", ~2min30,
  description générique "Aussi rapide qu'un modèle standard, avec la
  composition de Flux.") à tout style qui ne l'a pas déjà explicitement
  définie — même mécanisme que `_ensure_flux_option` pour Flux dev.
  Photoréaliste et Cyberpunk gardent leurs descriptions sur-mesure (déjà
  explicites dans `presets.json`, donc non écrasées). `resolve_style_models()`
  applique désormais les deux `_ensure_*` en cascade (flux puis flux
  schnell). Tests mis à jour en conséquence (63) ; vérifié dans l'app réelle
  sur "Croquis crayon" (un style à un seul modèle auparavant) qui propose
  maintenant bien 3 choix.
- 2026-08-10 : scan disque de `ComfyUI/` (51 Go) à la demande de
  l'utilisateur — tous les checkpoints/LoRAs/diffusion models/text
  encoders/VAE en usage sont référencés par `presets.json`/`config.py`,
  sauf `models/Mflux/flux.1-dev-mflux-4bit/` (9,2 Go, le modèle non retenu
  du test MLX ci-dessus). Supprimé sur confirmation utilisateur — 9,2 Go
  récupérés. `flux.1-schnell-mflux-4bit` (9,2 Go, utilisé) conservé.
- 2026-08-11 : **5ᵉ moteur — Flux Kontext dev**, modèle d'édition d'image
  par instruction (contrairement à l'img2img par denoise partiel des 3
  autres moteurs img2img, il conditionne la génération sur le latent de
  l'image via `ReferenceLatent`, à `denoise=1` fixe). Image de référence
  obligatoire — rejet 422 (`reference_image_required_for_model`) si absente,
  symétrique du rejet déjà en place pour Flux schnell + image. Toujours
  proposé par `_ensure_flux_kontext_option` comme flux/flux_schnell, mais
  visible côté frontend uniquement quand une image de référence est
  attachée (`useGenerationFlow.ts::availableModels`, filtre inverse de celui
  de flux_schnell). GGUF `flux1-kontext-dev-Q6_K.gguf` (9,85 Go) téléchargé
  sur confirmation utilisateur ; réutilise les encodeurs texte/VAE déjà en
  place pour Flux dev. `estimated_time` mesuré deux fois en conditions
  réelles à ~26 min (1533s puis 1555s) — **pas seulement au premier
  chargement** : sur cette machine (24 Go RAM unifiée), ComfyUI ne garde
  qu'un seul gros modèle en mémoire, donc le rechargement du GGUF est le cas
  courant dès qu'un autre moteur a tourné entre-temps (`flux_kontext_timeout_seconds`
  remonté de 1200s à 2400s en conséquence). Vérifié par une génération
  réelle bout en bout (prompt "add a swimming pool ... warm sunset" sur une
  image de test synthétique) : résultat cohérent, pool ajoutée et éclairage
  changé comme demandé, composition du jardin d'origine respectée. Tests
  backend (74) et frontend (10) mis à jour en conséquence.
