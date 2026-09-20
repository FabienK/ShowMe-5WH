# Frontend — App génération d'images (4W1H)

## En une phrase
Application qui construit un script de génération d'image en répondant à 5 questions (What / Who / Where / When / How), puis l'envoie à ComfyUI (Stable Diffusion) en local.

## Utilisateur
- Usage personnel uniquement, un seul utilisateur
- Niveau technique : dev junior +
- Machine : Mac mini M4, usage desktop
- Fréquence : génération ponctuelle (pas de session longue/continue)

## Plateforme
- V1 : application web locale (React), ouverte dans le navigateur sur la machine
- Pas de version mobile/tablette prévue
- Packaging natif Mac (Tauri) envisageable plus tard, hors scope V1

## Flux principal (V1)

Deux niveaux de choix : un mode **global** qui peut court-circuiter tout le protocole, et pour chaque question un mode **local** si l'utilisateur avance question par question.

### Modes globaux (avant de rentrer dans le détail des 5 questions)
1. **Prompt libre global** — l'utilisateur écrit directement un prompt complet, sans passer par les 5 questions
2. **Tout générer pour moi** — tirage aléatoire d'un nombre par question (5 tirages), chaque nombre correspondant à une entrée dans la liste fixe et numérotée de la question concernée

### Modes par question (si l'utilisateur répond question par question)
Pour chacune des 5 questions **What / Who / Where / When / How** :
1. **Liste de propositions** — liste fixe et numérotée, propre à chaque question
2. **Réponse libre** — champ texte libre
3. **App décide pour cette question** — même mécanique que le mode global "tout aléatoire" : tirage d'un nombre dans la liste numérotée de cette question uniquement

Un seul algorithme de tirage aléatoire dans les listes numérotées, appelé soit sur une question isolée (mode 3 local), soit sur les 5 d'un coup (mode global "tout générer pour moi").

### Particularité de "What"
"What" inclut le **style visuel** (BD, photoréaliste, etc.), présent dans sa liste numérotée. Le choix du style détermine le preset technique utilisé côté génération (voir backend.md) — presets construits manuellement par l'utilisateur après ses propres essais, pas de déduction automatique en V1.

## Listes fixes et numérotées (V1)

Chaque liste contient 20 entrées maximum. Note : "How" mélange deux registres (cadrage et lumière/couleur) — accepté tel quel, pas de séparation en sous-listes.

### What (style visuel)
1. Bande dessinée
2. Photoréaliste
3. Anime
4. Peinture à l'huile
5. Aquarelle
6. Pixel art
7. 3D render
8. Croquis crayon
9. Cyberpunk
10. Fantasy médiéval
11. Noir et blanc argentique
12. Pop art
13. Minimaliste vectoriel
14. Surréaliste
15. Steampunk
16. Gothique
17. Art nouveau
18. Cartoon
19. Isométrique
20. Impressionniste

### Who (sujet principal)
1. Personnage humain seul
2. Duo de personnages
3. Foule
4. Animal
5. Créature fantastique
6. Robot / IA
7. Portrait de visage
8. Silhouette
9. Enfant
10. Vieillard
11. Guerrier
12. Personnage féminin
13. Personnage masculin
14. Personnage non-humain hybride
15. Objet animé (personnifié)
16. Groupe familial
17. Figure historique (générique, non nommée)
18. Personnage mystérieux/encapuchonné
19. Couple
20. Aucun sujet (paysage pur)

### Where (lieu)
1. Forêt
2. Ville futuriste
3. Désert
4. Montagne
5. Océan / sous-marin
6. Espace / autre planète
7. Intérieur domestique
8. Ruines antiques
9. Château
10. Village médiéval
11. Métropole contemporaine
12. Jungle
13. Toundra / paysage enneigé
14. Laboratoire / lieu high-tech
15. Marché / bazar
16. Bibliothèque
17. Champ de bataille
18. Île isolée
19. Souterrain / grotte
20. Lieu abstrait / onirique

### When (moment / époque)
1. Aube
2. Matin
3. Midi
4. Après-midi
5. Crépuscule
6. Nuit
7. Antiquité
8. Moyen Âge
9. Renaissance
10. Époque victorienne
11. Années 1920
12. Années 1980
13. Époque contemporaine
14. Futur proche
15. Futur lointain
16. Post-apocalyptique
17. Préhistoire
18. Saison : hiver
19. Saison : été
20. Temporalité indéterminée / hors du temps

### How (technique / composition)
1. Plan large
2. Gros plan
3. Vue aérienne
4. Contre-plongée
5. Plongée
6. Symétrie parfaite
7. Règle des tiers
8. Contre-jour
9. Lumière dramatique (clair-obscur)
10. Lumière douce diffuse
11. Flou artistique (bokeh)
12. Netteté totale (hyperfocale)
13. Composition centrée
14. Perspective forcée
15. Mouvement suggéré (dynamique)
16. Statique / posé
17. Couleurs saturées
18. Palette monochrome
19. Contraste élevé
20. Ambiance tamisée / basse lumière

### Après les 5 réponses (ou le prompt libre global)
- Le script assemblé est visible avant envoi (pas d'envoi "en aveugle" à ComfyUI)
- Lancement de la génération
- Affichage du résultat, avec la possibilité de relancer

## Direction artistique
- Sobre, minimaliste
- Pas de contrainte de charte imposée par ailleurs — libre à construire

## Accessibilité
- Pas de besoin spécifique identifié pour la V1 (usage personnel)
- Micro / saisie vocale du prompt : **repoussé en V2**

## Hors scope V1 (backlog V2+)
- Upload de fichiers texte/image pour préremplir automatiquement les réponses aux 5W1H
- Saisie vocale (micro) pour les prompts
- Stockage cloud des images générées (accès multi-appareils)
- Auto-sélection intelligente des modules ComfyUI à partir du script (V1 = presets manuels uniquement)
- Génération vidéo (repoussée, pas de version cible fixée)

## Critère de réussite
Les générations obtenues via l'appli doivent plaire à l'utilisateur — pas de métrique quantitative, évaluation qualitative directe sur le rendu.
