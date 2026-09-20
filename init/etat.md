# État du projet — Générateur d'images 4W1H

Snapshot au 20/09/2026 (mise à jour : séparation physique du pack Gumroad
+ regroupement des sorties OpenAI). Le `README.md` à la racine ne décrit
que la V1 initiale ; ce fichier documente ce qui a été ajouté depuis, sans
dupliquer le contenu du README (installation, presets, checklist Mac
mini — voir `README.md` pour ça).

**Emplacement du projet (session du 20/09)** : l'app vivait auparavant
dans `Projets Claude code/Image generator /Image-generator/`, mélangée à
la racine avec le pack Gumroad commercial "Méthode 5Q" (PDFs, vidéos,
CSV). Les deux ont été séparés physiquement en deux dossiers frères :
l'app est désormais directement `Projets Claude code/ShowMe-5WH/` (dépôt
git déplacé tel quel, historique intact), le pack a migré vers
`Projets Claude code/Pack Gumroad Methode 5Q/`. Les chemins relatifs
internes au repo (`backend/`, `frontend/`, `ComfyUI/`…) sont inchangés,
seule la racine a bougé.

## Vue d'ensemble

Application locale (React + FastAPI) qui construit un script de génération
d'image en répondant à 5 questions — What / Who / Where / When / How —
puis l'envoie à ComfyUI (Stable Diffusion) exécuté en local. Usage
personnel, mono-utilisateur, pensé pour un **Mac mini M4 de base** (pas
Pro/Max), backend MPS d'Apple, sans GPU CUDA. L'app s'appelle **"ShowMe-5WH"**
(titre d'onglet + `<h1>` de l'accueil — anciennement "LookMe 5WH").

## Ce qui a changé depuis le README

Le README ne documente que le flux V1 (un seul moteur SDXL, presets
statiques). Depuis :

- **Dispatch multi-moteurs** (`backend/app/services/generation_dispatch.py`) :
  la génération supporte désormais 6 moteurs (`engine_type`) — SDXL, Flux
  dev, Anima, Flux schnell (via le node MLX natif `QuickMfluxNode` du
  custom node ComfyUI `Mflux-ComfyUI`), Flux Kontext (img2img avec
  image de référence + force de denoise), et OpenAI GPT Image 2 (cloud,
  voir section dédiée plus bas). La logique de validation/dispatch
  est partagée entre `/api/generate` (`routers/generate.py`) et le runner
  de batch (voir ci-dessous) pour éviter de dupliquer le branchement à
  plusieurs voies.
- **Génération par lots overnight** (`routers/batches.py`,
  `services/batch_runner.py`, `services/batch_store.py`) : on compose une
  liste de jobs personnalisés (chacun avec son propre script/style/
  modèle/image de référence), on lance, ça tourne côté serveur en tâche de
  fond (`asyncio.create_task`, survit à la fermeture de l'onglet). Le
  runner exécute les items **strictement en série** (contrainte ComfyUI :
  un seul job à la fois) et **continue malgré une erreur sur un item**
  (contrairement à l'ancienne boucle frontend `useGenerationFlow.ts` qui
  s'arrêtait à la première erreur). Persistance fichier, pas de base de
  données : un dossier par batch sous `backend/generated_batches/<batch_id>/`
  avec `manifest.json` + un PNG par item, écrit après chaque item (état
  visible en direct, survit à un crash). Un batch tué en cours de route
  (redémarrage backend) est marqué `"interrupted"` au démarrage suivant —
  pas de reprise automatique en V1, volontairement.
- **Assistant intégré au composeur de batch** (`frontend/src/state/
  useQuestionFlow.ts`, extrait de `useGenerationFlow.ts` et réutilisé par
  `useBatchComposer.ts`) : chaque item du batch a maintenant un bouton
  "Texte libre" / "Assistant" — bascule vers le même questionnaire 5
  questions que le flux "Générateur", avec aperçu du prompt qui se
  construit à la volée (`components/PromptPreview.tsx`, partagé avec
  `QuestionPage.tsx`) et, une fois les 5 réponses données, le même tableau
  d'édition par question (`components/AnswerFieldEditor.tsx` — prompt
  libre / liste / aléatoire) que `ScriptPreviewPage.tsx`.
- **Sélection multi-modèles + 2 images par modèle dans le batch** : le
  sélecteur de modèle par item passe en vrai multi-select (`modelIds:
  string[]`, plus un seul `modelId`). Au lancement, chaque item est éclaté
  en `N modèles × imagesPerModel(modèle)` `GenerateRequest` via
  `buildGenerationQueue` (`frontend/src/utils/estimate.ts`, déjà utilisé
  par le flux non-batch) — 2 images par modèle, sauf Flux dev/Kontext (plus
  lents) qui restent à 1. Purement frontend : `/api/batches` acceptait déjà
  une liste plate de requêtes, aucun changement backend nécessaire.
- **Page "Historique"** côté frontend (`pages/HistoryPage.tsx`) : liste
  des batches passés/en cours, miniatures servies en fichiers statiques via
  un nouveau mount `/generated` (`StaticFiles`), poll toutes les ~3s tant
  qu'un batch affiché est `"running"`. La légende tronquée qui s'affichait
  sous chaque vignette a été retirée ; à la place, un bandeau affiche le
  prompt **complet** (non tronqué) de l'item actuellement en cours de
  génération, tant que le batch est réellement `"running"` (un item resté
  `"running"` après un crash/redémarrage ne déclenche pas ce bandeau). Le
  libellé du modèle reste affiché sous chaque vignette.
- **Mode démo retiré** : suppression complète (pas juste masqué) — état
  `mockMode`/`setMockMode`, génération d'images factices dans
  `useGenerationFlow.ts`, rendu "Mode démo : aucune image n'a été générée…"
  dans `ResultPage.tsx`, champ `mocked` du type `GenerateResponse`, et la
  case à cocher sur l'accueil. La génération appelle désormais toujours
  l'API réelle (ComfyUI doit tourner pour générer une image).
- **Nouvelle nav frontend à 3 vues** dans `App.tsx` — `Générateur` /
  `Créer un batch` / `Historique` — sans librairie de routing (juste un
  état `view` orthogonal au `flow.step` existant, qui reste inchangé pour
  la vue "Générateur").
- **Accès LAN au frontend de dev** (`frontend/vite.config.ts` →
  `server.host: true`) pour tester l'app depuis un iPad sur le même Wi-Fi.
  Le proxy Vite (`/api`, `/generated` → `localhost:8000`) évite tout besoin
  de toucher au CORS backend : le navigateur ne parle qu'à l'origine Vite.

## Refonte design de l'interface (en cours)

Le frontend avait un design minimal (une seule feuille CSS de 996 lignes
sans échelle de tokens, rayons incohérents, pas de police custom, aucune
librairie UI). Décision avec l'utilisateur : direction visuelle **créative /
studio photo** (esprit Midjourney/Playground), responsive **mobile-first**
en priorité (usage réel iPad via LAN), et refonte **page par page** — la
page d'accueil donne le ton, le reste suit dans des itérations futures.

- **Étape 1 (faite) : page d'accueil.** Fondations posées dans
  `frontend/src/index.css` (`:root`) : échelle d'espacement `--space-1..8`,
  rayons `--radius-sm/md/lg/pill`, ombres `--shadow-sm/md/lg`, échelle
  typographique `--text-xs..3xl`, police d'affichage `--font-display`
  (Space Grotesk via Google Fonts, chargée dans `frontend/index.html`),
  accent secondaire `--accent2` (corail) en plus du violet existant —
  déclinés en light **et** dark (`prefers-color-scheme`). Primitives
  réutilisables ajoutées : `.btn` (`--primary`/`--secondary`) et `.card`,
  pensées pour être reprises par les prochaines pages sans redesign des
  tokens. `HomePage.tsx` a un hero (titre à accent dégradé, halo radial,
  accroche) et `ModeSelector.tsx` a des tuiles en cartes avec badge
  d'icône, hover lift, et grille **mobile-first** (1 colonne → 2 dès 480px
  → 4 dès 900px, à l'inverse de l'ancienne logique qui partait de 4
  colonnes). Deux icônes ajoutées dans `components/icons.tsx`
  (`SparkleIcon`, `WarningIcon`), même style SVG outline que les
  existantes. Vérifié : lint + 25 tests frontend passants, contrôle visuel
  mobile/tablette/desktop et light/dark via le navigateur intégré.
- **Halo interactif sur `.card`** (`index.css`, `HomePage.tsx`) : un halo
  radial (`--accent-soft`) suit le curseur derrière le contenu de la carte,
  fondu à l'entrée/sortie du survol. Demande initiale de l'utilisateur :
  reproduire l'effet du composant `spotlight-cards` de la registry shadcn/
  kokonutui (tilt 3D + glow + shimmer via Framer Motion) — non repris tel
  quel puisque le projet n'a ni Tailwind ni Framer Motion ; implémenté à la
  place en CSS pur, sans nouvelle dépendance : `--spot-x`/`--spot-y` mis à
  jour par un handler `onMouseMove` (`trackSpotlight`), halo en `::before`
  avec `z-index: -1` + `isolation: isolate` sur `.card` pour rester sous le
  contenu. Désactivé sur tactile (`@media (hover: hover)`), transition
  coupée sous `prefers-reduced-motion`. Appliqué pour l'instant aux deux
  panneaux `.card` de `HomePage.tsx` (prompt libre, image de référence) ;
  automatique pour toute future carte réutilisant `.card`. Vérifié dans le
  navigateur intégré (le halo suit bien le curseur) + lint/build/25 tests.
- **Nav globale, mode-selector, icônes, couleur, typographie, illustration
  du hero** (session du 19/08, suite de la refonte de l'accueil) — voir
  détail juste en dessous.
- **Étape 2 (faite) : module Assistant** (`QuestionPage.tsx`,
  `ScriptPreviewPage.tsx`, `QuestionCard.tsx`, `OptionList.tsx`,
  `PromptPreview.tsx`, `AnswerFieldEditor.tsx`) — application directe des
  primitives déjà posées à l'accueil (pas de divergence `/prototype`, les
  décisions visuelles étaient déjà prises). `QuestionCard` passe en `.card`
  (halo spotlight au survol, via `trackSpotlight` déjà partagé). Barre de
  progression ajoutée sous "Question X / Y" (dégradé `--accent`→`--accent2`).
  `PromptPreview` : les réponses déjà données deviennent des pastilles
  pleines (`--accent-soft`), celles en attente des pastilles en pointillés
  — remplace l'ancien texte séparé par des virgules. `OptionList` : le
  numéro de chaque option devient un badge circulaire, fond `--accent-soft`
  au survol. Nouveau modificateur `.btn--sm` (petit bouton plein `--accent`)
  appliqué aux boutons "Confirm"/"Update the prompt" de QuestionCard,
  AnswerFieldEditor et ScriptPreviewPage — remplace des boutons non stylés.
  `.script-preview-page__confirm` (génération) unifié sur `.btn.btn--primary`
  au lieu d'une règle dupliquée. Conversion des valeurs rem/px codées en dur
  vers les tokens `--space-*`/`--radius-*`/`--text-*` : **faite** sur
  `QuestionPage`/`QuestionCard`/`OptionList`/`PromptPreview` (déjà bonne dès
  cette étape) et sur `ScriptPreviewPage` (rattrapée en session du 20/08 —
  détail plus bas). Deux valeurs volontairement laissées telles quelles sur
  `.option-list__number` (badge circulaire numéroté) faute de token exact :
  `width/height: 20px` (dimension fixe d'icône/badge, jamais tokenisée nulle
  part dans le fichier) et `font-size: 0.65rem` (le token le plus proche,
  `--text-xs` à 0.75rem, aurait agrandi le badge d'environ 15 %). Vérifié :
  lint + build + 25 tests passants, parcours complet des 5 questions jusqu'à
  la génération testé dans le navigateur intégré (dark/light, desktop/mobile).
- **Pas encore touché** : le layout propre à ResultPage, BatchComposerPage,
  HistoryPage. Ils héritent déjà des nouvelles icônes, de la palette couleur
  et de l'effet spotlight (`ModelSelector`, partagé avec `BatchComposerPage`,
  en a hérité en session du 20/08 — voir plus bas), donc ne détonnent plus
  autant qu'avant avec l'accueil, mais n'ont pas eu de refonte de
  layout/densité propre.

### Suite de la refonte (session du 19/08) : nav, mode-selector, icônes, couleur, bandeau

Trois décisions de design ont été prises via le skill `/prototype` (skill de
divergence, `.claude/skills/prototype/`) plutôt qu'en itérant directement sur
le code de prod : 3 variantes réellement différentes construites dans une
surface isolée (nouvelle entrée Vite `frontend/prototype-*.html` +
`frontend/prototype/<nom>/`, jamais importée par le code de prod), comparées
via un picker flottant standardisé, puis la variante choisie (`keep <nom>`)
promue dans le code de prod et la surface de prototype supprimée.

- **Tuiles mode-selector** (`ModeSelector.tsx`) : Quiet / Spotlight /
  Segmented, puis riff autour de Spotlight → Gallery / **Alive** / Collage.
  **Alive** retenu : tuile "Assistant" mise en avant en pleine largeur
  (dégradé `--accent`→`--accent2`), les 3 autres tuiles en grille dessous,
  halo qui suit le curseur (réutilise le pattern `--spot-x`/`--spot-y` de
  `.card`, extrait dans `frontend/src/utils/spotlight.ts` pour être partagé
  entre l'accueil et le mode-selector) et légère rotation de l'icône au
  survol.
- **Système d'icônes** (`components/icons.tsx`) : un premier essai
  (Crisp/Soft/Duotone) ne faisait varier que le *rendu* (épaisseur de trait)
  des mêmes formes — écarté, ce n'était pas la demande de l'utilisateur, qui
  voulait de vraies métaphores différentes. Deuxième essai : Object /
  Symbolic / **Playful**. **Playful** retenu (pinceau, éventail de cartes,
  chapeau de magicien, diaphragme d'appareil photo, pellicule, sablier,
  polaroid) — les formes ont été remplacées dans `icons.tsx` en gardant les
  noms d'export (`SparkleIcon`, `HomeIcon`, `ListIcon`, `ClockIcon`,
  `FreePromptIcon`, `DiceIcon`, `AssistantIcon`, `UploadIcon`), donc propagé
  automatiquement partout où ces icônes sont utilisées (nav, mode-selector,
  QuestionCard, AnswerFieldEditor, BatchComposerPage, ScriptPreviewPage).
- **Thème couleur** (`index.css`, `:root`) : Sunset / Ocean / Pop, chacun ne
  faisant varier que les tokens `--accent`/`--accent2`/`--accent-hover`/
  `--accent-soft`/`--accent-contrast` (light + dark) sur le même markup et
  les mêmes icônes réels. **Sunset** retenu : rose profond `#d94f70` → ambre
  `#ffab4a` (dark : `#f4839c` → `#ffc178`), en remplacement du violet/corail
  d'origine.
- **Nav globale** (`App.tsx`, `.app__nav`) : passée de simples onglets texte
  à un segmented control en pilule avec icônes ; icônes seules (labels
  cachés) sous 480px pour éviter un débordement repéré en testant à 375px.
- **Typographie** : tracking négatif (`-0.02em`) ajouté sur
  `.home-page__title`, seule vraie "large display text" du projet — décidé
  après un audit inspiré du skill `apple-design`, qui a aussi confirmé que
  springs/gestes/`backdrop-filter` ne s'appliquaient pas ici (pas
  d'interaction de type drag sur ces composants, nav non flottante
  au-dessus de contenu qui défile).
- **Bug d'alignement** corrigé sur les tuiles du mode-selector :
  `justify-content: center` faisait atterrir l'icône plus bas sur la tuile
  au texte le plus court (les 3 tuiles ont la même hauteur via le stretch de
  grille, donc un contenu plus court laisse plus de "slack" au centrage) —
  passé en `flex-start`.
- **Illustration du bandeau d'accueil** (zone claire à droite du hero,
  `home-page__hero-bird` dans `HomePage.tsx`) : premier essai avec 3 cartes
  en dégradé façon pile de photos (abandonné), puis un oiseau sur une branche
  en SVG dessiné à la main (abandonné aussi). **Fixé** : remplacé par une
  vraie photo générée par l'utilisateur via l'app
  (`ComfyUI/output/oiseau.png`), détourée sur fond blanc (script Python
  ponctuel, seuil de distance colorimétrique au blanc + feathering des bords,
  pas de dépendance ajoutée au projet), recadrée, mise en miroir pour que la
  branche entre par la droite comme demandé, puis exportée en WebP
  (`frontend/src/assets/hero-bird.webp`, ~89 Ko) et affichée via une balise
  `<img>` (`filter: drop-shadow(...)` pour la profondeur), toujours masquée
  sous 640px. `home-page__tagline` réduit à `max-width: 30ch` au-delà de
  640px pour que le texte ne passe plus sous l'oiseau. Repositionnée ensuite
  en ancrage bas (`bottom: 4%` au lieu d'un centrage vertical avec
  `translateY`, largeur 195px) car la tête (crête, œil, bec) était rognée par
  le `overflow: hidden` du hero — la photo tient maintenant en entier dans le
  bandeau, vérifié en dark et light.
- **Traduction complète de l'UI en anglais** (décision explicite de
  l'utilisateur, portée "toute l'app" confirmée après clarification) : les
  ~140 chaînes de texte visibles (labels, placeholders, aria-labels,
  messages d'erreur) sur 14 fichiers + 2 fichiers de tests adaptés en
  lockstep. `index.html` en `lang="en"`, format de date de `HistoryPage`
  passé en locale `en-GB` (garde l'ordre jour/mois). **Les commentaires de
  code restent en français** (hors périmètre demandé). Bug repéré et
  corrigé pendant la traduction : une regex (`slugify` dans
  `ResultPage.tsx`) s'est retrouvée écrite avec de vrais caractères Unicode
  combinants littéraux au lieu de l'échappement `\u0300-\u036f` —
  fonctionnellement identique mais dangereux à maintenir, corrigé par script
  Python direct (vérifié en bytes bruts).

Vérifié à chaque étape : lint + build + 25 tests frontend passants, contrôle
visuel mobile/tablette/desktop et light/dark via le navigateur intégré.

### Anneaux d'activité façon Apple Watch (session du 19/08)

Demande utilisateur : `npx shadcn add @kokonutui/apple-activity-card`. Comme
pour `spotlight-cards` précédemment, **pas installé tel quel** — le projet
n'a ni Tailwind ni shadcn (`components.json` inexistant) ; installer aurait
déclenché une init interactive et ajouté Tailwind + `framer-motion`.
Reproduit en React + CSS pur à la place, sans nouvelle dépendance :

- [ActivityRing.tsx](../frontend/src/components/ActivityRing.tsx) : un seul
  anneau SVG réutilisable (`stroke-dashoffset` animé au montage via
  `requestAnimationFrame` + transition CSS, `useId()` pour l'unicité des
  gradients). Respecte `prefers-reduced-motion`.
- [AppleActivityCard.tsx](../frontend/src/components/AppleActivityCard.tsx) :
  empile plusieurs `ActivityRing` en cascade (délai `index * 150ms`) +
  panneau de stats à droite — reproduction du composant kokonutui d'origine,
  données par défaut factices (Move/Exercise/Stand) conservées comme demo.
- **Intégré à deux endroits** :
  - `QuestionPage.tsx` : remplace l'ancienne barre de progression linéaire
    (`question-page__progress-track/fill`, supprimée) par un `ActivityRing`
    compact (40px) coloré `--accent`→`--accent2`, à côté du texte
    "Question X / Y".
  - `HistoryPage.tsx` (`BatchDetailView`) : `AppleActivityCard` avec 2
    anneaux calculés depuis `BatchDetail.items` — "Done" (`completed_items`/
    `total`, dégradé accent) et "Errors" (`error_items`/`total`, `--error-text`,
    dégradé plat) — au-dessus de la grille de vignettes existante, se
    met à jour en direct au poll 3s (l'anneau transitionne en douceur vers
    la nouvelle valeur, l'animation d'entrée ne rejoue pas puisque le
    composant reste monté).
- Vérifié dans le navigateur intégré sur données réelles (dark/light,
  desktop) : progression de l'assistant anneau par anneau sur les 5
  questions, et détail d'un vrai batch avec 1 erreur (2/3 done, 1/3 error).
  Contrôle mobile non re-fait sur cette étape (navigateur intégré
  instable sur le viewport mobile pendant cette session — timeouts sur les
  clics malgré des captures d'écran cohérentes) ; la règle CSS `max-width:
  480px` qui empile la carte verticalement était déjà en place et vérifiée
  à l'installation initiale du composant.

### Retour utilisateur sur QuestionPage (session du 20/08) : 4 correctifs + refonte du bandeau

Après un premier passage sur QuestionPage (session ci-dessus), retour
utilisateur en 5 points :

1. **Anneau faux sur la question 1** — il affichait ~1/4 rempli alors
   qu'aucune réponse n'était encore donnée. Corrigé : la valeur reflète les
   réponses déjà données (`currentQuestionIndex / questions.length`), pas
   la question affichée — 0 % sur la question 1, 80 % en arrivant sur la 5ᵉ.
2. **Label "What"** : `"What — sujet et style visuel"` → **`"What — style
   visuel"`** ([questions.py](../backend/app/data/questions.py)) — "sujet"
   fait doublon avec "Who — sujet principal", et c'est ce que dit déjà
   `frontend.md` (source de vérité du texte, jamais mise à jour côté
   backend).
3. **Trop de rouge** : l'icône du prompt libre (`.question-card__free-text-icon`)
   passe d'accent plein à neutre (`--text-h`, opacity 0.6, aligné sur
   l'icône dé juste à côté qui n'est accent qu'au survol) ; les 3 boutons
   "Confirm"/"Update the prompt" (QuestionCard, AnswerFieldEditor,
   ScriptPreviewPage) passent de `.btn--primary` (plein accent) à
   `.btn--secondary` (contour neutre).
4. **Bouton Accueil isolé** en haut à droite de QuestionPage, plus
   "exclu de la scène" que jamais malgré 3 tentatives de le regrouper avec
   la progression (bandeau fusionné / posé sur la carte / barre de nav
   unifiée — surface de prototype `frontend/prototype-question-layout.html`
   + `src/prototype/question-layout/`, comparées via un picker flottant).
   **Les 3 rejetées d'un bloc** ("mauvaise direction globale") : le
   problème n'était pas où placer le bouton, mais qu'il ne devait plus
   exister du tout à cet endroit.
5. Décision finale, après clarification : **le bouton Accueil est retiré de
   QuestionPage** ; cliquer sur l'onglet "Generator" de la nav globale
   pendant le flux (déjà actif) fait maintenant office de retour à l'accueil
   (`App.tsx` : `onClick` de l'onglet appelle `flow.restart()` si
   `view === "generator" && flow.step !== "home"`, `aria-label` dynamique
   "Back to home" dans ce cas). `cancelQuestionFlow` (devenu mort) supprimé
   de `useGenerationFlow.ts`. Corollaire sur l'anneau : plus de texte
   "Question X / Y" à côté — un seul anneau, plus grand (56px), centré,
   avec un **décompte au centre** (5 → 1, `questions.length -
   currentQuestionIndex`) porté par un nouveau prop optionnel
   `centerLabel` sur [ActivityRing.tsx](../frontend/src/components/ActivityRing.tsx)
   (texte SVG centré, `aria-label` adapté — "Questions left: N remaining").
   Surface de prototype supprimée après la décision (convention habituelle).

**Repasse immédiate** : "neutre" pour l'icône prompt/les boutons Confirm
était trop timide — l'utilisateur voulait de la couleur, juste pas la
teinte rose/rouge (`--accent`). Nouveau token `--accent2-contrast`
(`#2a1608`, fixe — `--accent2` reste clair en light **et** dark, un texte
sombre marche dans les deux cas) + `--accent2-hover` (light/dark) et
nouveau modificateur **`.btn--accent2`** (fond `--accent2`, plein, hover
`translateY` + shadow comme `.btn--primary`) appliqué aux 3 boutons
Confirm ; `.question-card__free-text-icon` recoloré en `--accent2` (au
lieu du gris neutre de la session précédente). Anneau + `PromptPreview`
regroupés sur une seule ligne (`.question-page__header`, flex row ; le
`margin` par défaut de `.prompt-preview` est neutralisé uniquement dans ce
contexte via `.question-page__header .prompt-preview`, sans toucher son
usage dans `BatchComposerPage`). Le label "What" était déjà corrigé en
base (`questions.py`) depuis la session précédente — le retour de
l'utilisateur venait du backend partagé (autre session sur le port 8000)
pas encore redémarré, donc encore l'ancien texte en mémoire ; pas
retouché, pas de re-fix nécessaire côté code.

Vérifié dans le navigateur intégré (dark/light) : anneau vide sur la
question 1, décompte 5→4 en avançant, clic sur "Generator" en plein milieu
du flux ramène bien à l'accueil. Lint + build + 25 tests frontend + 81
tests backend passants après chaque étape.

**Micro-ajustement** : l'écart anneau ↔ `PromptPreview` sur la même ligne
(`.question-page__header`) était trop serré — `gap` passé de
`var(--space-4)` (16px) à `var(--space-7)` (48px). Vérifié dans le
navigateur, build + 25 tests toujours passants.

### Refonte ScriptPreviewPage (session du 20/08)

Suite directe de l'étape 2 (module Assistant) : rattrapage de la conversion
des tokens sur `ScriptPreviewPage.tsx`, puis retour utilisateur en plusieurs
passes sur cette même page.

- **Bouton Accueil retiré** de la toolbar de `ScriptPreviewPage`, même
  pattern que celui déjà validé sur `QuestionPage` (session précédente) :
  l'onglet "Generator" de la nav globale fait déjà office de retour à
  l'accueil pendant tout le flux (`App.tsx`), le bouton dédié était
  redondant. La toolbar ne contient plus que le dé (reroll), et ne
  s'affiche même plus du tout quand `onReroll` n'est pas fourni.
- **Titre "Your prompt" retiré.**
- **Couleur ajoutée sur le sélecteur de modèle** (`ModelSelector.tsx`) :
  nom du modèle (`SDXL`, `Flux`…) en `--accent2` (orange, toujours visible,
  pas seulement à la sélection) ; carte sélectionnée avec fond
  `--accent-soft` en plus de la bordure `--accent` déjà existante. Le
  bouton "Generate" est d'abord passé en `--accent2` (pour trancher avec le
  rose déjà très présent ailleurs), puis **repassé en `--primary`** (rouge)
  sur retour explicite de l'utilisateur.
- **3 réorganisations comparées visuellement** avant de choisir la mise en
  page : le skill `/prototype` utilisé le 19/08 n'existe plus dans le repo
  (`.claude/skills` vide au moment de cette session) — comparaison faite à
  la place via un mockup HTML (outil `visualize`, publié en Artifact),
  recréé avec les vraies couleurs/tokens/police du projet plutôt qu'un style
  générique, pour que la comparaison soit fidèle au rendu réel.
  - **A — Compact** : ordre actuel resserré, script mis en avant (fond
    teinté) pour compenser le titre retiré, CTA seule collée en bas d'écran.
  - **B — Decide first** : script → modèle → CTA remontent en haut ; les 5
    réponses éditables passent dans un volet repliable en dessous.
  - **C — Two cards** : deux blocs séparés "Prompt" (script + réponses) et
    "Generate" (modèles + CTA), la carte Generate collée en bas d'écran.
  - **C retenue en premier** (avec la carte Generate sticky), implémentée :
    deux `<div>` `.script-preview-page__prompt-card`/`__generate-card`,
    labels "Prompt"/"Generate" colorés (`--accent`/`--accent2`),
    `position: sticky` sur la carte Generate entière (`bottom: var(--space-4)`,
    ombre `--shadow-md`). Marges par défaut neutralisées là où le nouveau
    `gap` flex faisait doublon (image de référence, script, liste de
    réponses, `.model-selector`), sans toucher aux règles partagées avec
    `ResultPage`.
  - **Revenue ensuite sur A** (compact) après un tour d'essai : les deux
    cartes et leurs labels supprimés, retour à un flux unique. Le script
    garde son fond teinté (`--accent-soft`, bordure transparente) via un
    nouveau modificateur `.script-preview-page__script--hero`. Petit label
    neutre "Model" (`.script-preview-page__section-label`, masqué si un
    seul modèle comme `ModelSelector` lui-même) au-dessus du sélecteur.
    Seule la barre d'action (`.script-preview-page__actions`, ciblée via
    `.script-preview-page > .script-preview-page__actions` pour ne pas
    affecter `.result-page__actions` qui partage la règle de base) reste
    `position: sticky` en bas d'écran, dans un petit bandeau flottant
    (fond, bordure, radius, ombre) — le reste défile normalement derrière.
- **Bug découvert et corrigé pendant l'itération sur C** : "la génération
  aléatoire fait trembler la page". Cause réelle — le flag `loading` de
  `useGenerationFlow.ts` est partagé entre `chooseGlobalRandom` (reroll),
  `updateAnswerField` (édition d'une réponse) et `generateForModels` (la
  vraie génération). Pour ce dernier cas le `step` bascule sur "result"
  *avant* que `loading` passe à `true`, donc `ScriptPreviewPage` n'est déjà
  plus montée — mais pour le reroll et l'édition de réponse, la page reste
  affichée pendant tout l'appel réseau. Or `ScriptPreviewPage` remplaçait
  `ModelSelector` + bouton par un petit `<Loader>` tant que `loading` était
  vrai : la zone s'effondrait puis se redéployait à la réponse de l'API, un
  saut de hauteur très visible une fois la carte/barre passée en sticky.
  Corrigé en gardant `ModelSelector` et le bouton **toujours affichés**,
  simplement désactivés (`disabled={loading}`) pendant le chargement — plus
  aucun changement de hauteur, donc plus de tremblement (vérifié en
  observant la hauteur via `ResizeObserver` pendant un reroll : aucun
  redimensionnement pendant tout le cycle réseau).
- **Effet spotlight étendu** : ajouté sur le bloc script mis en avant
  (`.script-preview-page__script--hero`, halo 280px) et sur chaque carte du
  sélecteur de modèle (`.model-selector__option`, halo 200px) — même
  mécanisme `--spot-x`/`--spot-y` que `.card`/`.mode-selector__tile`
  (`trackSpotlight`, `frontend/src/utils/spotlight.ts`). `ModelSelector`
  étant partagé avec `BatchComposerPage`, l'effet s'y propage aussi.
- **Instabilité du navigateur intégré** rencontrée sur une bonne partie de
  cette session (captures d'écran figées sur une image obsolète ou réduites
  à quelques pixels, sur plusieurs onglets/serveurs différents — pas un cas
  isolé comme lors de la session précédente). Vérifications faites via le
  DOM à la place : `getComputedStyle` pour les couleurs/position/valeurs
  calculées, dispatch manuel d'événements `mousemove` pour confirmer le
  halo, `ResizeObserver` pour confirmer l'absence de saut de hauteur. Lint +
  build + 25 tests passants après chaque étape.

## Micro-animations

Passage des skills `find-animation-opportunities` puis `improve-animations`
sur le frontend : rapport de 6 opportunités, **les 6 implémentées** via des
plans autonomes dans `plans/` (`plans/001` à `plans/006`, tous **DONE** —
détail dans `plans/README.md`). Aucun changement de dépendance, tout en CSS
pur (`@starting-style`, transitions) sauf les plans 002 et 005 qui ajoutent
un peu d'état React pour gérer l'animation de sortie d'un rendu
conditionnel/d'une liste.

- **001 — retour au clic** (`frontend/src/index.css`, règle `button` de
  base) : `:active { transform: scale(0.97) }` + transition 120ms,
  `prefers-reduced-motion` géré. Touche tous les boutons bruts de l'app
  (options de questionnaire, icon-buttons, lignes d'historique, sélecteur
  de modèle, toggle de mode batch) — hors `.btn` (accueil) et
  `.mode-selector__tile`, qui ont leur propre hover `translateY` et
  restent volontairement hors périmètre (conflit de spécificité à traiter
  à part si besoin).
- **002 — lightbox** (`ResultPage.tsx` + `index.css`) : ouverture/fermeture
  symétriques (fondu + scale 0.96→1). Nécessite un état `lightboxVisible` +
  un timeout JS (250ms) pour laisser l'animation de sortie jouer avant le
  démontage React — un simple `@starting-style` ne gère que le montage, pas
  le démontage d'un rendu conditionnel.
- **003 — révélation des résultats** (`index.css` seul, `@starting-style`) :
  chaque image générée apparaît (fondu + léger scale) à son arrivée réelle.
  Pas de stagger artificiel : les résultats arrivent déjà un par un
  (génération strictement séquentielle, `useGenerationFlow.ts`).
- **004 — vignettes Historique** (`index.css` seul) : fondu à l'opacité
  quand une vignette passe de "en attente"/"en cours" à "réussie"/"erreur"
  au poll de 3s. **Piège CSS rencontré et documenté dans le fichier** :
  une seule règle `@starting-style` générique ne suffit pas pour la
  variante `--pending` (qui a son propre `opacity: 0.7` au repos) — à
  spécificité égale, une règle normale gagne le calcul de l'état de départ
  si elle vient après dans le fichier ; il faut une seconde règle
  `@starting-style` dédiée à `--pending`, placée après sa règle normale.
- **005 — ajout/suppression d'item batch** (`useBatchComposer.ts` +
  `BatchComposerPage.tsx` + `index.css`) : entrée via `@starting-style`
  (chaque item a un `id` stable, donc un vrai montage) ; sortie via un
  `Set<string> removingIds` + timeout (220ms), même principe que le plan
  002 généralisé à une liste — l'item est marqué "leaving" (fondu +
  `pointer-events: none`) puis réellement filtré de `items` une fois la
  transition terminée. A cassé un test unitaire qui figeait l'ancien
  retrait synchrone (`useBatchComposer.test.ts`) — mis à jour avec
  `waitFor`, pas contourné.
- **006 — bandeau d'erreur** (`index.css` seul, `@starting-style`) :
  fondu + `translateY(-4px)` (direction négative, contrairement aux plans
  003/005 — une bannière d'alerte "tombe" depuis le haut, un item de liste
  "monte" à sa place). Pas de sortie animée : `setError(null)` est toujours
  déclenché silencieusement en début de l'action suivante, jamais via un
  bouton "fermer" regardé par l'utilisateur.

Vérification de chaque plan : `npm run lint && npm run build && npm run test`,
plus un feel-check visuel — surtout via un harnais HTML jetable servi en
local (`python3 -m http.server`), en supposant ComfyUI non lancé. **Ce
n'était plus vrai à partir du plan 006** : en essayant de provoquer une
vraie erreur API pour tester le bandeau, une vraie génération SDXL a été
déclenchée par erreur (backend + ComfyUI tournaient bel et bien sur la
machine à ce moment) — laissée filer sans l'interrompre plutôt que de
gâcher le rendu en cours. À garder en tête pour de prochaines sessions de
test UI : vérifier l'état de ComfyUI avant d'exercer les vrais flux de
génération, pas seulement supposer qu'il est éteint.

## Moteur OpenAI GPT Image 2 (session du 30/08)

Ajout d'un 6ᵉ moteur de génération, **GPT Image 2 (API OpenAI)**, à parité
avec les 5 moteurs ComfyUI existants — pas un fallback, une option choisie
par l'utilisateur au même niveau que les autres. Demande initiale :
disposer d'une option cloud occasionnelle à côté du pipeline local Mac
mini, avec un solde de crédit suivi localement (il n'existe pas d'API de
facturation OpenAI fiable), décrémenté uniquement après un succès confirmé.

- **Coût réel, pas un tarif forfaitaire** : le premier jet de la spec
  (`openai-fallback-implementation.md`, tarif plat par résolution) s'est
  révélé obsolète/faux à l'implémentation — GPT Image 2 facture par
  tokens (texte/image en entrée, image en cache, sortie), pas à l'image.
  Le coût réel est calculé après chaque appel depuis `ImagesResponse.usage`
  (`backend/app/services/openai_generator.py::cost_from_usage`), avec des
  tarifs $/token vérifiés dans `config.py`. Un `estimated_cost_per_generation_usd`
  séparé (estimation qualité moyenne/1024×1024) ne sert qu'à l'affichage
  avant génération — jamais à la vraie décrémentation.
- **Intégration** : `engine_type="openai"` ajouté au `Literal` de
  `ModelOption` (`schemas.py`), branché dans `generation_dispatch.py`
  (même pattern qu'un moteur ComfyUI de plus) et dans
  `presets.py::_ensure_openai_option` (calqué sur `_ensure_flux_option`,
  toujours proposé quel que soit le style). Nouveau
  `openai_state_store.py` : persiste juste `balance_usd` en JSON, même
  pattern fichier temporaire + `os.replace` atomique que `batch_store.py`.
  Clé lue via `OPENAI_API_KEY` (pydantic-settings comme le reste de la
  config) ; clé manquante lève `OpenAIMissingApiKeyError` avant tout appel
  SDK. Nouveau routeur `backend/app/routers/openai_settings.py`
  (`GET/PUT /api/openai/balance`).
- **Piège technique à retenir** : le SDK Python `openai` (3.6.0) embarque
  son propre fork `httpx2`/`httpcore2`, pas le `httpx` habituel du projet.
  Pour mocker les appels OpenAI dans les tests, il faut injecter un
  `httpx2.MockTransport` via `openai_generator._client()` (même principe
  de point d'injection unique que `comfyui_client._build_client`), pas du
  `httpx` classique.
- **Deux décisions prises avec l'utilisateur** :
  1. OpenAI est **exclu du composeur de batch overnight**
     (`useBatchComposer.ts::excludeOpenAI` le filtre de tout
     `item.models` côté frontend) — dépenser de l'argent réel par item,
     sans confirmation, dans un batch séquentiel non surveillé, jugé trop
     risqué pour une V1. `batch_runner.py` (backend) n'a pas été touché
     (pas de classification d'erreur OpenAI) puisqu'aucune requête OpenAI
     ne doit l'atteindre via l'UI normale.
  2. Nouvel **onglet de nav "Settings"** (`SettingsPage.tsx`, 4ᵉ `View`
     dans `App.tsx`) porte le champ de solde éditable manuellement + un
     tableau de tarifs en lecture seule — préféré à une modale contextuelle
     sur la tuile du modèle pour garder `ModelSelector` présentationnel/
     sans état (il reçoit un `modelExtras` optionnel calculé par la page
     appelante plutôt que de connaître OpenAI lui-même).

Vérifié : 93 tests backend (10 nouveaux, HTTP mocké réel — succès/échec/
clé manquante + aller-retour du store de solde), 33 tests frontend (8
nouveaux), lint + build propres, et un passage manuel complet dans le
navigateur contre le vrai backend — erreur de clé manquante propre,
tuile désactivée visuellement si solde insuffisant (`disabled: true`
confirmé dans le DOM), édition du solde dans Settings répercutée en
direct sur la tuile Générateur, composeur de batch confirmé sans jamais
proposer GPT Image 2.

**Correction (session du 20/09)** : les images GPT Image 2 générées hors
batch atterrissaient dans un dossier séparé, `backend/generated_openai/`.
Sur demande de l'utilisateur ("tout regrouper dans le même dossier"),
`generated_openai_dir` (`config.py`) pointe maintenant vers `ComfyUI/output/`
— même dossier que les 5 moteurs ComfyUI, un seul endroit à parcourir pour
retrouver une image quel que soit le moteur utilisé. L'image déjà générée
a été migrée manuellement, l'ancien dossier supprimé. Les tests (isolés
via `monkeypatch` sur `settings.generated_openai_dir` dans `conftest.py`)
n'ont pas eu besoin d'être modifiés — ils lisent le chemin dynamiquement.

## Architecture / carte des fichiers clés

```
backend/app/routers/       questions.py, script.py, generate.py, batches.py,
                            openai_settings.py
backend/app/services/      generation_dispatch.py, comfyui_client.py,
                            batch_store.py, batch_runner.py, presets.py,
                            openai_generator.py, openai_state_store.py
backend/app/models/        schemas.py (GenerateRequest, Batch*, PresetUsed…)
backend/app/workflows/     *.json — un graphe ComfyUI par moteur
                            (base_workflow, flux_workflow, flux_schnell_workflow,
                            flux_kontext_workflow, anima_workflow)
                            — OpenAI GPT Image 2 n'a pas de workflow ComfyUI,
                            appel direct à l'API via openai_generator.py
backend/generated_batches/ sorties des batches (gitignored)

frontend/src/pages/        HomePage, QuestionPage, ScriptPreviewPage,
                            ResultPage, BatchComposerPage, HistoryPage,
                            SettingsPage (solde OpenAI + tarifs)
frontend/src/state/        useGenerationFlow.ts, useQuestionFlow.ts
                            (questionnaire 5 questions, partagé),
                            useBatchComposer.ts
frontend/src/components/   QuestionCard, AnswerFieldEditor, PromptPreview
                            (partagés Générateur/batch), ModelSelector…
frontend/src/utils/        estimate.ts (imagesPerModel/buildGenerationQueue),
                            answers.ts (toAnswerInput), spotlight.ts
                            (trackSpotlight, halo curseur .card/mode-selector)
frontend/src/api/client.ts wrapper HTTP (postGenerate, postScript,
                            postBatch, getBatches, getBatch)

plans/                      plans d'animation (improve-animations), un par
                             opportunité — voir plans/README.md
```

## Contraintes matérielles connues

Mac mini M4 **base** (pas Pro/Max), 24 Go RAM unifiée. ComfyUI ne traite
qu'un seul job à la fois et recharge un gros modèle à chaque changement de
moteur — toute future fonctionnalité doit rester séquentielle, jamais
paralléliser les appels ComfyUI. Temps mesurés en conditions réelles :
~4 min 15 s par image SDXL, jusqu'à 40 min pour Flux Kontext.

## État du contrôle de version

Un seul commit existe dans l'historique git (« Implémenter la V1 de l'app
4W1H »). **Tout le travail depuis — img2img/Flux Kontext, dispatch
multi-moteurs, génération par lots, assistant/multi-modèles dans le batch,
page Historique, accès LAN, retrait du mode démo, renommage, refonte design
de l'accueil (dont l'effet spotlight sur `.card`), micro-animations
(plans 001-006), la suite de la refonte du 19/08 (nav, mode-selector,
icônes, couleur, typographie, bandeau, traduction UI en anglais), la
refonte de `ScriptPreviewPage` du 20/08 (réorganisation, couleur, spotlight
étendu au sélecteur de modèle), et le moteur OpenAI GPT Image 2 du 30/08
(6ᵉ moteur, solde de crédit, onglet Settings) —
n'est pas committé** (plus de 70 fichiers modifiés, non stagés à ce jour).
Décision explicite de l'utilisateur : pas de commit, l'app reste locale et
n'est pas destinée à être déployée.

## Tests

- Backend : 93 tests passants (`cd backend && source .venv/bin/activate && pytest`).
- Frontend : 33 tests passants, build et lint propres
  (`cd frontend && npm run test && npm run build && npm run lint`).

## Pistes traitées / notes

- Le dossier `Mflux` créé en parallèle par le node `QuickMfluxNode` du
  custom node ComfyUI (image + JSON de métadonnées, redondant avec le
  `SaveImage` déjà consommé par l'app pour Flux schnell) : **résolu** —
  `metadata` est passé à `false` dans `flux_schnell_workflow.json`, ce
  dossier ne se remplit plus.
- Le `README.md` n'a pas été mis à jour avec les fonctionnalités listées
  ci-dessus.
