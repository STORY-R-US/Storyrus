"""Theme-aware art direction for existing image calls; never buys extra images.

Catalog identity controls finish/layout, while the customer's theme controls props.
Saved-stage keys deliberately do not include this direction's revision.
"""

import json
import re
import unicodedata

VERSION = "thematic-scenery-2"

# Examples are conditional material cues, not a compulsory shopping list.
FAMILIES = {
    "aviation": (
        "aviacao aeroclube aviao avioes aviation airplane aeroplane aircraft",
        "coherent aircraft geometry, grounded landing gear, plausible cockpit controls, hangar structure and layered airfield terrain; only when this action actually involves aircraft",
    ),
    "football": (
        "futebol football soccer goleiro goalkeeper",
        "field markings following perspective, grass variation, distant stands and goal-net depth",
    ),
    "ballet": (
        "bale ballet danza danca dance",
        "wood floor grain, a grounded barre and softly lit stage curtains or studio windows",
    ),
    "beach": (
        "praia beach playa litoral",
        "tide marks, scattered small shells on sand, wet-sand reflections and distant coastal layers",
    ),
    "underwater": (
        "underwater oceano ocean submarino marinho",
        "layered coral or sea plants, sandy seabed ripples and soft underwater light falloff",
    ),
    "space": (
        "space espaco espacial astronauta astronaut planetas",
        "distant planetary layers, rock strata or spacecraft material joints appropriate to this scene",
    ),
    "dinosaurs": (
        "dinosaurs dinossauros dinosaurios dinossauro",
        "fern layers, ancient tree bark, mossy rocks and distant prehistoric terrain",
    ),
    "fantasy": (
        "fantasy fantasia princess princesa princesas castelo castle",
        "carved stone, winding paths, layered gardens and restrained magical lighting within the requested world",
    ),
    "superhero": (
        "superhero superheroes heroi heroina superherois",
        "coherent city depth, masonry, windows and street surfaces appropriate to the requested rescue",
    ),
    "sport": (
        "sport sports esporte deportes esportes",
        "equipment belonging to the actual sport, court or track markings, surface texture and distant venue depth",
    ),
    "adventure": (
        "adventure aventura floresta forest trilha",
        "layered foliage, grounded stones, paths and distant landscape contours",
    ),
    "christmas": (
        "christmas natal navidad",
        "warm festive light, fabric textures and a few grounded seasonal ornaments matching the setting",
    ),
    "birthday": (
        "birthday aniversario cumpleanos",
        "layered celebration decorations, fabric and table textures with restrained coordinated colors",
    ),
    "easter": (
        "easter pascoa pascua",
        "woven basket texture, spring foliage and small seasonal details appropriate to the requested action",
    ),
    "new_year": (
        "new_year ano_novo reveillon",
        "subtle festive light reflections and coordinated celebration materials without visual clutter",
    ),
    "wedding": (
        "casamento wedding boda",
        "delicate floral arrangements, natural fabrics and coherent venue architecture",
    ),
    "pets": (
        "pets pet mascota mascotas",
        "a few relevant care objects, textile textures and grounded garden or home details; no additional animals",
    ),
    "newborn": (
        "recem_nascidos newborn bebe baby",
        "soft cotton weave, gentle window light and calm nursery furniture; no loose objects near the baby",
    ),
    "learning": (
        "alfabetizacao_inicial pensamento_matematico cores aprendizagem learning escola school",
        "unlettered learning materials, wood or paper textures and a coherent classroom or home setting",
    ),
    "routine": (
        "higiene_desfralde vestir_autonomia animais_sons transporte_ajudantes literacia_emocional rotina_dormir compartilhar_revezar consciencia_corporal",
        "a few age-appropriate everyday objects directly supporting this action, tactile materials and calm room depth",
    ),
    "biblical": (
        "biblico biblical biblia",
        "period-appropriate stone, woven cloth, pottery and landscape layers without modern objects",
    ),
    "family": (
        "mothers_day fathers_day grandparents_love grandfather_love family_love childrens_day dia_da_mulher dia_da_sogra dia_da_familia dia_do_irmao dia_dos_namorados dia_do_amigo tio_tia dia_dos_filhos independencia dia_do_idoso familia family mae mama mamae pai papai grandma abuelo abuela",
        "warm familiar materials, garden or room depth and a few meaningful objects belonging to this family activity",
    ),
}


def family(theme):
    normalized = (
        unicodedata.normalize("NFKD", str(theme or "")).encode("ascii", "ignore").decode().lower()
    )
    words = set(re.findall(r"[a-z_]+", normalized))
    for name, (keywords, _) in FAMILIES.items():
        if words.intersection(keywords.split()):
            return name
    return "custom"


def direction(*, theme, action, role, design=None, text_region=None):
    """One consistent rule for cover, story pages, quiet pages and expansion.

    Do not infer theme from a catalog title, sample name or reference artwork.
    Unknown/custom themes still receive contextual depth rather than football props.
    """
    selected = family(theme)
    cues = FAMILIES.get(
        selected,
        (
            "",
            "materials, architecture, vegetation and small objects justified by the customer's theme and this specific action",
        ),
    )[1]
    quiet = role == "reading"
    return "\nTHEMATIC SCENERY CONTRACT: " + json.dumps(
        {
            "version": VERSION,
            "family": selected,
            "customer_theme": theme,
            "current_action": action,
            "role": role,
            "catalog_design": (design or {}).get("id", "default"),
            "finish": (design or {}).get("finish", "preserve the selected book finish"),
            "text_region": text_region,
            "composition": (
                "Keep the catalog's reading-page structure and quiet paper. Add only discreet theme-related edge details OUTSIDE the entire reading rectangle; no scene or people behind the passage."
                if quiet
                else "Build a coherent foreground, action plane and distant background within the selected catalog layout. Include a few distinct relevant environmental details, not merely sharpening. Use natural scale, perspective, contact shadows and depth of field; keep the protagonist recognizable and the scene readable, not crowded."
            ),
            "conditional_material_cues": cues,
            "naturalism": {
                "staging": "When characters are present, use spontaneous but readable gestures, natural gaze toward the current activity or companion and subtle expression appropriate to the story. Do not give everyone identical fixed smiles or repeat the same cover pose on every page. Vary camera angle and blocking only when justified by the exact stanza, without altering cast, wardrobe or the requested action.",
                "identity_scope": "Reference photos define likeness, age and each requested person's distinguishing features. Their pose, camera crop, location and furniture are not instructions for the new scene, even if mentioned in an identity description. Preserve distinct faces; never clone one face onto companions.",
                "anatomy": "When people are present, use age-appropriate head-to-body proportions, limb lengths and joint positions. Young children must not acquire adult shoulders or muscular arms. Preserve natural skin texture and expression within the selected photographic or illustrated finish; do not force photorealism onto cartoon models.",
                "physical_support": "Every sitting or standing person needs a plausible supporting surface and visible contact appropriate to the pose. Hands must meet the object they use with a natural grip; feet and clothing must not fuse into objects. Arrange the activity and camera to fit the scene instead of stretching bodies or equipment.",
                "light_and_depth": "Use one coherent lighting direction, consistent contact shadows, horizon and perspective across people and scenery. Separate foreground, action and distant background by natural scale and material detail, not pasted silhouettes, halos, heavy blur or glossy plastic skin.",
                "environment": "Keep a small number of well-formed, theme-relevant objects with believable size and construction. Richness comes from coherent materials and spatial relationships, not extra clutter. Respect the requested action and existing text-safe regions; do not add cast or change the story to satisfy these details.",
            },
            "continuity": "Choose only cues that fit this actual location and action. Keep approved wardrobe, palette, materials and recurring setting consistent across pages. Do not transplant an outdoor scene into an indoor room or repeat the same props on every page. The customer's theme overrides the example book's subject; never import its characters or story objects.",
            "protection": "Keep the entire measured text region and its breathing margin quiet. No detail, face, hair, hat, hands or essential action may intersect lettering. Preserve whole heads including hair and hats, original identity and body proportions. Reframe the whole scene naturally when necessary; never shrink only a face. No stretched, mirrored, tiled or blurred side extensions, seams, banners or pasted portraits.",
            "restraint": "Examples are optional, never mandatory. Omit any detail that conflicts with the action, selected finish, text safety or established continuity. No additional cast, animals, logos or generated lettering. Richness must remain part of the same scene, not sticker decoration.",
        },
        ensure_ascii=False,
    )
