"""
Chapter 1 Curriculum Enricher & Question Bank Builder
Grounded strictly in:
Karnataka Class 8 Science Part-I (2025-26), Chapter 1: Crop Production and Management
Printed pages 1-13 (PDF pages 13-25).
"""

import uuid
from typing import List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import Topic, Concept, LearningObjective, Section, Chapter
from app.models.assessment import Question, QuestionOption, QuestionRubric


CHAPTER_1_TITLE = "CROP PRODUCTION AND MANAGEMENT"

CANONICAL_CONCEPTS = [
    {
        "name": "Agricultural Practices & Crop Seasons",
        "summary": "Classification of crops into Kharif (sown in rainy season June-Sept: paddy, maize, cotton) and Rabi (grown in winter season Oct-March: wheat, gram, mustard).",
        "difficulty_tier": 1,
        "section_number": "1.1",
        "objectives": [
            {
                "statement": "Classify common Indian crops into Kharif and Rabi seasons based on their sowing and harvesting periods.",
                "bloom": "Recall",
            },
            {
                "statement": "Explain why paddy cannot be grown in winter season due to high water requirements.",
                "bloom": "Understanding",
            }
        ]
    },
    {
        "name": "Preparation of Soil",
        "summary": "Loosening and turning the soil (tilling/ploughing) to allow roots to penetrate deep and breathe, helping earthworms and soil microbes, followed by leveling.",
        "difficulty_tier": 2,
        "section_number": "1.3",
        "objectives": [
            {
                "statement": "Describe how loosening the soil supports root respiration and encourages friendly microorganisms and earthworms.",
                "bloom": "Understanding",
            },
            {
                "statement": "Identify the tools and process used to break big clumps of soil (crumbs) and level the field.",
                "bloom": "Recall",
            }
        ]
    },
    {
        "name": "Agricultural Implements",
        "summary": "Primary tools for soil preparation: Plough (ploughshare, ploughshaft), Hoe (iron rod, bent plate for pulling weeds/loosening), and Cultivator (tractor-driven, saving time and labor).",
        "difficulty_tier": 2,
        "section_number": "1.3",
        "objectives": [
            {
                "statement": "Identify the structural parts and functions of the plough, hoe, and modern tractor-driven cultivator.",
                "bloom": "Recall",
            }
        ]
    },
    {
        "name": "Sowing & Seed Selection",
        "summary": "Selecting clean, healthy, high-yielding seeds. Activity 1.1 reveals damaged seeds become hollow, lighter, and float. Traditional funnel vs modern Seed Drill for uniform depth and bird protection.",
        "difficulty_tier": 2,
        "section_number": "1.4",
        "objectives": [
            {
                "statement": "Explain why damaged seeds float on water during seed selection in Activity 1.1.",
                "bloom": "Understanding",
            },
            {
                "statement": "Compare the traditional funnel sowing method with the modern seed drill regarding spacing, depth, and seed protection.",
                "bloom": "Application",
            }
        ]
    },
    {
        "name": "Adding Manure and Fertilisers",
        "summary": "Replenishing soil nutrients with organic manure (decomposed plant/animal waste, rich in humus) versus inorganic chemical fertilisers (NPK, urea, superphosphate, potash). Activity 1.2 seedling comparison.",
        "difficulty_tier": 3,
        "section_number": "1.5",
        "objectives": [
            {
                "statement": "Analyze the experimental observations from Activity 1.2 on seedling growth with manure, fertiliser, and no added nutrient.",
                "bloom": "Understanding",
            },
            {
                "statement": "Contrast chemical fertilisers with organic manure regarding soil texture, humus, and long-term soil health.",
                "bloom": "Reasoning",
            }
        ]
    },
    {
        "name": "Crop Rotation & Soil Replenishment",
        "summary": "Restoring soil fertility naturally through crop rotation, specifically planting leguminous crops (pulses, peas) whose root nodules harbor Rhizobium bacteria to fix atmospheric nitrogen.",
        "difficulty_tier": 3,
        "section_number": "1.5",
        "objectives": [
            {
                "statement": "Explain how crop rotation with leguminous plants and Rhizobium bacteria naturally replenishes soil nitrogen.",
                "bloom": "Application",
            }
        ]
    },
    {
        "name": "Irrigation: Traditional vs Modern Systems",
        "summary": "Supplying water to crops at regular intervals. Traditional methods: Moat (pulley), Chain pump, Dhekli, Rahat (water wheel). Modern water-saving methods: Sprinkler system (uneven/sandy land) and Drip system (drop by drop at roots, zero waste).",
        "difficulty_tier": 3,
        "section_number": "1.6",
        "objectives": [
            {
                "statement": "Identify traditional irrigation implements (Moat, Chain pump, Dhekli, Rahat).",
                "bloom": "Recall",
            },
            {
                "statement": "Select and justify the appropriate modern irrigation method (Sprinkler vs Drip) for specific terrains and water availability conditions.",
                "bloom": "Application",
            }
        ]
    },
    {
        "name": "Protection from Weeds",
        "summary": "Undesirable wild plants that compete with crops for water, nutrients, space, and light. Removed manually using Khurpi or by spraying weedicides like 2,4-D (requiring face protection).",
        "difficulty_tier": 2,
        "section_number": "1.7",
        "objectives": [
            {
                "statement": "Explain how weeds reduce crop yield and how physical removal with a khurpi differs from chemical weedicide spraying.",
                "bloom": "Understanding",
            },
            {
                "statement": "Describe essential safety precautions a farmer must adopt while handling and spraying chemical weedicides like 2,4-D.",
                "bloom": "Application",
            }
        ]
    },
    {
        "name": "Harvesting and Threshing",
        "summary": "Cutting of mature crops manually by sickle or machine. Threshing separates grains from chaff. Modern Combine performs both harvesting and threshing. Winnowing separates chaff by wind. Harvest festivals celebrate yield.",
        "difficulty_tier": 2,
        "section_number": "1.8",
        "objectives": [
            {
                "statement": "Describe the operational function of a Combine machine and contrast it with traditional winnowing.",
                "bloom": "Recall",
            }
        ]
    },
    {
        "name": "Storage of Food Grains",
        "summary": "Grains must be sun-dried to reduce moisture before storage to prevent attacks by insects, pests, bacteria, and fungi. Large-scale storage in Silos and Granaries. Dried neem leaves used at home.",
        "difficulty_tier": 3,
        "section_number": "1.9",
        "objectives": [
            {
                "statement": "Analyze why freshly harvested grains must be sun-dried before storage and explain the biological consequences of high moisture.",
                "bloom": "Reasoning",
            },
            {
                "statement": "Identify large-scale grain storage structures (silos, granaries) and household preservation methods like dried neem leaves.",
                "bloom": "Recall",
            }
        ]
    },
    {
        "name": "Food from Animals & Animal Husbandry",
        "summary": "Rearing animals on a large scale for food (milk, eggs, meat) with proper food, shelter, and care (Activity 1.3). Fish as a nutritious source of protein and Vitamin D (cod liver oil).",
        "difficulty_tier": 1,
        "section_number": "1.10",
        "objectives": [
            {
                "statement": "Define animal husbandry and identify the key nutritional benefits of animal foods such as fish and cod liver oil.",
                "bloom": "Recall",
            }
        ]
    }
]

CALIBRATED_QUESTIONS = [
    # Concept 1: Agricultural Practices & Crop Seasons
    {
        "concept_name": "Agricultural Practices & Crop Seasons",
        "cognitive_level": 1,
        "prompt": "Which of the following sets contains only Kharif crops that are sown during the rainy season (June to September) in India?",
        "explanation": "According to the textbook (p. 2), Kharif crops are sown in the rainy season (June to September). Examples include paddy, maize, soyabean, groundnut, and cotton. Wheat and mustard are Rabi crops.",
        "source_page": 2,
        "options": [
            {"key": "A", "text": "Paddy, maize, soyabean, and cotton", "is_correct": True, "feedback": "Correct! These are all sown during the monsoon (June to September)."},
            {"key": "B", "text": "Wheat, gram, pea, and mustard", "is_correct": False, "feedback": "Wheat, gram, pea, and mustard are Rabi crops grown in winter (October to March)."},
            {"key": "C", "text": "Paddy, wheat, maize, and mustard", "is_correct": False, "feedback": "Wheat and mustard are Rabi crops, while paddy and maize are Kharif crops."},
            {"key": "D", "text": "Barley, gram, groundnut, and cotton", "is_correct": False, "feedback": "Barley and gram are Rabi crops."}
        ],
        "rubric": {
            "expected_concepts": ["Kharif crops", "Rainy season", "Crop classification"],
            "required_points": ["June to September season", "Examples: paddy, maize, cotton"],
            "misconception_traps": {
                "rabi_confusion": "Confusing winter crops (wheat, mustard) with monsoon crops (paddy, maize)."
            }
        }
    },
    {
        "concept_name": "Agricultural Practices & Crop Seasons",
        "cognitive_level": 2,
        "prompt": "Why can paddy (rice) NOT be successfully cultivated during the winter (Rabi) season in most parts of India?",
        "explanation": "Textbook p. 2 explicitly states: 'Paddy requires a lot of water. Therefore, it is grown only in the rainy season.' Winter conditions lack the continuous high volume of water paddy needs.",
        "source_page": 2,
        "options": [
            {"key": "A", "text": "Paddy requires a continuous large amount of water that is available primarily during the monsoon season", "is_correct": True, "feedback": "Correct! Rice paddies require standing water and immense moisture."},
            {"key": "B", "text": "Paddy seeds cannot germinate when temperatures drop below 35°C", "is_correct": False, "feedback": "Incorrect; temperature is not the main limiting factor described in the textbook."},
            {"key": "C", "text": "Paddy roots absorb too much nitrogen during cold weather", "is_correct": False, "feedback": "Incorrect; this is biologically inaccurate."},
            {"key": "D", "text": "Paddy plants are destroyed by normal winter morning dew", "is_correct": False, "feedback": "Incorrect; water availability is the true textbook reason."}
        ],
        "rubric": {
            "expected_concepts": ["Paddy water requirement", "Kharif conditions", "Rainy season dependence"],
            "required_points": ["Requires huge volume of water", "Monsoon provides necessary water supply"],
            "misconception_traps": {
                "temperature_only": "Assuming crops fail in winter solely due to temperature rather than moisture availability."
            }
        }
    },
    {
        "concept_name": "Agricultural Practices & Crop Seasons",
        "cognitive_level": 4,
        "prompt": "If a farmer in Karnataka decides to sow wheat seeds in the month of July alongside paddy, what is the most scientifically sound outcome?",
        "explanation": "Wheat is a Rabi crop requiring cool weather and moderate moisture (p. 2). Excessive monsoon water in July causes wheat seeds and roots to rot from waterlogging, resulting in poor germination or crop failure.",
        "source_page": 2,
        "options": [
            {"key": "A", "text": "The wheat crop is likely to rot and fail due to excessive monsoon water and lack of cool winter conditions", "is_correct": True, "feedback": "Correct! Wheat cannot tolerate waterlogged soils and requires winter temperatures for healthy grain development."},
            {"key": "B", "text": "The wheat crop will grow twice as fast because of excessive rainwater", "is_correct": False, "feedback": "Incorrect; wheat roots rot in waterlogged monsoon soil."},
            {"key": "C", "text": "The wheat will naturally convert into Kharif crops", "is_correct": False, "feedback": "Incorrect; plant genetics and seasonal adaptation do not change dynamically."},
            {"key": "D", "text": "The wheat plants will produce double the grains with zero fertiliser", "is_correct": False, "feedback": "Incorrect; excessive rain severely damages wheat."}
        ],
        "rubric": {
            "expected_concepts": ["Rabi crop requirements", "Waterlogging vulnerability", "Seasonal adaptation"],
            "required_points": ["Wheat needs cool winter weather", "Heavy monsoon rain causes root rotting and fungal spoilage"],
            "misconception_traps": {
                "more_water_always_better": "Believing that more water always increases growth for all crop varieties."
            }
        }
    },

    # Concept 2: Preparation of Soil
    {
        "concept_name": "Preparation of Soil",
        "cognitive_level": 1,
        "prompt": "What is the process of loosening and turning the soil called?",
        "explanation": "Textbook p. 2 defines: 'The process of loosening and turning of the soil is called tilling or ploughing.'",
        "source_page": 2,
        "options": [
            {"key": "A", "text": "Tilling or ploughing", "is_correct": True, "feedback": "Correct! Tilling/ploughing is done using a plough, hoe, or cultivator."},
            {"key": "B", "text": "Weeding or winnowing", "is_correct": False, "feedback": "Weeding removes weeds; winnowing separates grain from chaff."},
            {"key": "C", "text": "Threshing or harvesting", "is_correct": False, "feedback": "These occur after crop maturation."},
            {"key": "D", "text": "Levelling and sowing", "is_correct": False, "feedback": "Levelling breaks crumbs; sowing places seeds."}
        ],
        "rubric": {
            "expected_concepts": ["Tilling", "Ploughing", "Soil preparation"],
            "required_points": ["Loosening and turning the topsoil"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Preparation of Soil",
        "cognitive_level": 2,
        "prompt": "Why does loosening and turning the soil help plant roots grow healthy?",
        "explanation": "Textbook p. 2 explains: 'The loose soil allows the roots to breathe easily even when they go deep into the soil. The loosened soil also helps in the growth of earthworms and microbes.'",
        "source_page": 2,
        "options": [
            {"key": "A", "text": "It traps air in soil pores so deep roots can breathe and aids the growth of friendly earthworms and microbes", "is_correct": True, "feedback": "Correct! Aeration and porous structure allow gas exchange and microbial humus production."},
            {"key": "B", "text": "It packs the soil completely solid so water cannot evaporate", "is_correct": False, "feedback": "Loosening makes soil porous, not solid."},
            {"key": "C", "text": "It permanently removes all earthworms from the field", "is_correct": False, "feedback": "Earthworms are friends of the farmer and thrive in loosened soil."},
            {"key": "D", "text": "It brings infertile rock minerals to the surface", "is_correct": False, "feedback": "It brings nutrient-rich soil from lower layers to the top."}
        ],
        "rubric": {
            "expected_concepts": ["Soil aeration", "Root respiration", "Earthworm/microbial activity"],
            "required_points": ["Roots breathe easily in loose soil", "Supports earthworms that add humus"],
            "misconception_traps": {
                "compaction_desirable": "Thinking densely packed soil holds roots better than aerated soil."
            }
        }
    },
    {
        "concept_name": "Preparation of Soil",
        "cognitive_level": 3,
        "prompt": "After ploughing a dry field, a farmer observes large hard chunks of soil called 'crumbs'. What is the necessary next step and tool used?",
        "explanation": "Textbook p. 3 states: 'The ploughed field may have big clumps of soil called crumbs. It is necessary to break these crumbs. Levelling the field is beneficial for sowing as well as for irrigation. Levelling of soil is done with the help of a leveller.'",
        "source_page": 3,
        "options": [
            {"key": "A", "text": "Break the crumbs and level the field using a wooden or iron leveller", "is_correct": True, "feedback": "Correct! Levelling breaks crumbs and ensures uniform irrigation and sowing."},
            {"key": "B", "text": "Immediately sow seeds deep inside the large crumbs", "is_correct": False, "feedback": "Seeds cannot germinate evenly inside hard crumbs."},
            {"key": "C", "text": "Flood the field with weedicide to dissolve the crumbs", "is_correct": False, "feedback": "Weedicides destroy weeds, not soil clumps."},
            {"key": "D", "text": "Collect and discard all the crumbs outside the field", "is_correct": False, "feedback": "The crumbs are topsoil and must be broken down, not discarded."}
        ],
        "rubric": {
            "expected_concepts": ["Crumbs", "Levelling", "Leveller tool"],
            "required_points": ["Break clumps for uniform seedbed", "Leveller used for smooth irrigation"],
            "misconception_traps": {
                "discard_crumbs": "Thinking crumbs are useless stones rather than fertile clay/soil clumps."
            }
        }
    },

    # Concept 3: Agricultural Implements
    {
        "concept_name": "Agricultural Implements",
        "cognitive_level": 1,
        "prompt": "Which part of the traditional wooden plough contains the strong triangular iron strip?",
        "explanation": "Textbook p. 3 (Fig. 1.1(a)) states: 'It contains a strong triangular iron strip called ploughshare. The main part of the plough is a long log of wood which is called a ploughshaft.'",
        "source_page": 3,
        "options": [
            {"key": "A", "text": "Ploughshare", "is_correct": True, "feedback": "Correct! The ploughshare is the triangular cutting iron strip."},
            {"key": "B", "text": "Ploughshaft", "is_correct": False, "feedback": "The ploughshaft is the long central log of wood."},
            {"key": "C", "text": "Beam", "is_correct": False, "feedback": "The beam is placed on the bullocks' necks."},
            {"key": "D", "text": "Bent plate", "is_correct": False, "feedback": "The bent iron plate is a component of a hoe."}
        ],
        "rubric": {
            "expected_concepts": ["Plough anatomy", "Ploughshare", "Fig 1.1(a)"],
            "required_points": ["Ploughshare is the triangular iron strip", "Ploughshaft is the wood handle/log"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Agricultural Implements",
        "cognitive_level": 2,
        "prompt": "What major advantage does a tractor-driven cultivator (Fig. 1.1(c)) offer over a traditional pair of bullocks with a plough?",
        "explanation": "Textbook p. 4 explicitly explains: 'Nowadays ploughing is done by tractor-driven cultivator. The use of cultivator saves labour and time.'",
        "source_page": 4,
        "options": [
            {"key": "A", "text": "It saves significant human labour and working time", "is_correct": True, "feedback": "Correct! A cultivator rapidly covers large fields with minimal manual labor."},
            {"key": "B", "text": "It eliminates the need for water during irrigation", "is_correct": False, "feedback": "Cultivation is soil preparation; it does not replace watering."},
            {"key": "C", "text": "It automatically injects chemical fertilisers into seeds", "is_correct": False, "feedback": "Cultivators only till and loosen soil."},
            {"key": "D", "text": "It prevents weeds from ever growing again permanently", "is_correct": False, "feedback": "No implement permanently stops weed germination."}
        ],
        "rubric": {
            "expected_concepts": ["Cultivator", "Tractor implement", "Labor and time saving"],
            "required_points": ["Saves labor", "Saves time compared to bullock ploughing"],
            "misconception_traps": {}
        }
    },

    # Concept 4: Sowing & Seed Selection
    {
        "concept_name": "Sowing & Seed Selection",
        "cognitive_level": 2,
        "prompt": "In Activity 1.1, when wheat seeds are placed into a beaker of water, some seeds sink to the bottom while others float on top. Why do those seeds float?",
        "explanation": "Textbook p. 4 (Activity 1.1) states: 'Damaged seeds become hollow and are thus lighter. Therefore, they float on water. This is a good method for separating good, healthy seeds from the damaged ones.'",
        "source_page": 4,
        "options": [
            {"key": "A", "text": "Damaged seeds have been hollowed out by pests/decay, making them lighter than water", "is_correct": True, "feedback": "Correct! Insect damage or disease leaves seeds hollow and buoyant."},
            {"key": "B", "text": "Floating seeds are the healthiest because they contain extra air pockets for rapid growth", "is_correct": False, "feedback": "Misconception! Floating seeds are damaged and hollow, not healthy."},
            {"key": "C", "text": "Seeds float because healthy seeds naturally have water-repellent wax coatings", "is_correct": False, "feedback": "Healthy sound seeds are dense and sink."},
            {"key": "D", "text": "Only seeds from hybrid plants float, while desi seeds sink", "is_correct": False, "feedback": "Buoyancy here indicates physical emptiness due to pest damage."}
        ],
        "rubric": {
            "expected_concepts": ["Activity 1.1", "Seed buoyancy", "Damaged hollow seeds"],
            "required_points": ["Damaged seeds are hollow and lighter", "Healthy dense seeds sink to bottom"],
            "misconception_traps": {
                "floating_is_healthy": "Believing that buoyant, floating seeds are superior or contain more energy."
            }
        }
    },
    {
        "concept_name": "Sowing & Seed Selection",
        "cognitive_level": 3,
        "prompt": "Why is sowing seeds using a modern seed drill (Fig. 1.2(b)) significantly better than broadcasting seeds by hand scattering?",
        "explanation": "Textbook p. 5 explains: 'This sows the seeds uniformly at equal distance and depth. It ensures that seeds get covered by the soil after sowing. This protects seeds from being eaten by birds. Sowing by using a seed drill saves time and labour. An appropriate distance between the seeds is necessary to avoid overcrowding of plants.'",
        "source_page": 5,
        "options": [
            {"key": "A", "text": "It sows seeds at uniform depth and spacing, covers them with soil to protect from birds, and prevents overcrowding", "is_correct": True, "feedback": "Correct! Uniform depth, spacing, and soil cover maximize germination and prevent bird predation."},
            {"key": "B", "text": "It ensures seeds are deposited strictly on the soil surface exposed to direct sunlight", "is_correct": False, "feedback": "Surface seeds get eaten by birds or dry out."},
            {"key": "C", "text": "It crushes the seed coat so germination happens within 10 minutes", "is_correct": False, "feedback": "Seed drills do not crush seeds; crushing would kill the embryo."},
            {"key": "D", "text": "It drops 20 seeds into a single spot to maximize competition", "is_correct": False, "feedback": "Overcrowding reduces sunlight, water, and nutrient availability."}
        ],
        "rubric": {
            "expected_concepts": ["Seed drill", "Uniform spacing and depth", "Bird protection", "Avoiding overcrowding"],
            "required_points": ["Uniform depth and distance", "Covers with soil against birds", "Prevents competition from overcrowding"],
            "misconception_traps": {
                "broadcasting_equal": "Believing hand scattering gives equal distribution as precision drills."
            }
        }
    },

    # Concept 5: Adding Manure and Fertilisers
    {
        "concept_name": "Adding Manure and Fertilisers",
        "cognitive_level": 2,
        "prompt": "What did the seedling experiment in Activity 1.2 (Fig. 1.3) demonstrate about plant growth in Glass A (fertiliser), Glass B (manure), and Glass C (soil only)?",
        "explanation": "Textbook p. 6 (Activity 1.2) shows seedlings with chemical fertilisers grew fastest initially, manure showed steady healthy growth with enhanced soil texture, while soil with no nutrient addition had poor stunted growth.",
        "source_page": 6,
        "options": [
            {"key": "A", "text": "Plants supplied with manure and fertilisers grew significantly better than plain soil, with fertilisers providing fast nutrient uptake", "is_correct": True, "feedback": "Correct! Continuous crop cultivation exhausts soil nutrients; replenishment via manure or fertiliser is essential for vigorous growth."},
            {"key": "B", "text": "Plants in Glass C without any manure grew the tall and healthiest seedlings", "is_correct": False, "feedback": "Glass C without nutrients had the poorest stunted growth."},
            {"key": "C", "text": "Chemical fertilisers turned the soil into sand within 2 days", "is_correct": False, "feedback": "Activity 1.2 measures seedling growth, not immediate soil erosion."},
            {"key": "D", "text": "Cow dung manure prevented seedlings from absorbing any water", "is_correct": False, "feedback": "Manure actually improves water holding capacity."}
        ],
        "rubric": {
            "expected_concepts": ["Activity 1.2", "Nutrient replenishment", "Seedling growth comparison"],
            "required_points": ["Unsupplemented soil leads to stunted growth", "Nutrient addition is necessary"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Adding Manure and Fertilisers",
        "cognitive_level": 4,
        "prompt": "Based on Table 1.1 in the textbook, what is a fundamental difference between organic manure and chemical fertilisers regarding soil humus and water pollution?",
        "explanation": "Textbook p. 7 (Table 1.1) highlights: 'Fertiliser does not provide any humus to the soil. Manure provides a lot of humus to the soil.' Excessive fertiliser use also leads to water pollution and makes soil alkaline/acidic over time.",
        "source_page": 7,
        "options": [
            {"key": "A", "text": "Manure provides abundant humus and enhances soil texture without polluting water, whereas chemical fertilisers provide no humus and cause water pollution when overused", "is_correct": True, "feedback": "Correct! Manure is organic and creates porous, humus-rich soil, while synthetic fertilisers add mineral salts with zero organic matter."},
            {"key": "B", "text": "Chemical fertilisers provide 100% organic humus, while manure is manufactured in factories from rock salts", "is_correct": False, "feedback": "Misconception! Fertilisers are factory salts with no humus; manure is organic."},
            {"key": "C", "text": "Manure completely depletes soil of all microbes, whereas fertilisers stimulate earthworms", "is_correct": False, "feedback": "Manure feeds friendly microbes and earthworms; excessive fertilisers harm them."},
            {"key": "D", "text": "There is no scientific difference between manure and chemical fertilisers", "is_correct": False, "feedback": "They differ fundamentally in composition, origin, humus contribution, and environmental impact."}
        ],
        "rubric": {
            "expected_concepts": ["Table 1.1 comparison", "Humus content", "Soil texture", "Water pollution risk"],
            "required_points": ["Fertiliser provides zero humus", "Manure provides rich humus", "Fertiliser runoff causes water pollution"],
            "misconception_traps": {
                "fertiliser_is_superior": "Believing chemical fertiliser improves long-term soil structure better than organic manure."
            }
        }
    },

    # Concept 6: Crop Rotation & Soil Replenishment
    {
        "concept_name": "Crop Rotation & Soil Replenishment",
        "cognitive_level": 3,
        "prompt": "How does growing leguminous crops (such as pulses or beans) in rotation with cereal crops (such as wheat) replenish soil fertility without chemical fertilisers?",
        "explanation": "Textbook p. 7-8 explains: 'In the previous classes, you have learned about Rhizobium bacteria. These are present in the nodules of the roots of leguminous plants. They fix atmospheric nitrogen.' This naturally enriches the soil with nitrogen.",
        "source_page": 8,
        "options": [
            {"key": "A", "text": "Rhizobium bacteria in the root nodules of leguminous plants fix atmospheric nitrogen into the soil", "is_correct": True, "feedback": "Correct! Symbiotic Rhizobium converts gaseous nitrogen into plant-absorbable nitrates."},
            {"key": "B", "text": "Leguminous plant roots release synthetic urea directly into groundwater", "is_correct": False, "feedback": "Urea is a manufactured chemical fertiliser, not a biological secretion."},
            {"key": "C", "text": "Pulses absorb heavy metals and convert them into phosphorus", "is_correct": False, "feedback": "Elements cannot be transmuted biologically."},
            {"key": "D", "text": "Crop rotation causes earthworms to produce potassium crystals", "is_correct": False, "feedback": "The primary mechanism is Rhizobium nitrogen fixation."}
        ],
        "rubric": {
            "expected_concepts": ["Crop rotation", "Leguminous plants", "Rhizobium bacteria", "Nitrogen fixation"],
            "required_points": ["Rhizobium in root nodules", "Fixes atmospheric nitrogen into soil nutrients"],
            "misconception_traps": {
                "soil_never_depletes": "Believing soil nutrients replenish on their own without rotation or organic matter."
            }
        }
    },

    # Concept 7: Irrigation: Traditional vs Modern Systems
    {
        "concept_name": "Irrigation: Traditional vs Modern Systems",
        "cognitive_level": 1,
        "prompt": "Which of the following groups consists ENTIRELY of traditional methods of lifting water for irrigation as illustrated in Fig. 1.4?",
        "explanation": "Textbook p. 8 (Fig. 1.4) lists traditional methods: Moat (pulley system), Chain pump, Dhekli, and Rahat (lever system). Sprinkler and drip systems are modern methods.",
        "source_page": 8,
        "options": [
            {"key": "A", "text": "Moat, Chain pump, Dhekli, and Rahat", "is_correct": True, "feedback": "Correct! These are the four traditional human/animal powered systems shown in Fig. 1.4."},
            {"key": "B", "text": "Drip system, Sprinkler system, Moat, and Rahat", "is_correct": False, "feedback": "Drip and sprinkler are modern systems."},
            {"key": "C", "text": "Chain pump, Dhekli, Submersible pump, and Tractor", "is_correct": False, "feedback": "Submersible pumps and tractors are modern mechanical equipment."},
            {"key": "D", "text": "Canal gates, Drip emitters, Combine, and Rahat", "is_correct": False, "feedback": "Combine is a harvesting tool, drip is modern irrigation."}
        ],
        "rubric": {
            "expected_concepts": ["Traditional irrigation", "Fig 1.4", "Moat, Chain pump, Dhekli, Rahat"],
            "required_points": ["Identify traditional cattle/human powered systems"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Irrigation: Traditional vs Modern Systems",
        "cognitive_level": 3,
        "prompt": "A farmer has farmland on uneven, sloping terrain with sandy soil where water supply is scarce. Which modern irrigation method is most suitable, and why?",
        "explanation": "Textbook p. 9 explains: 'Sprinkler System is more useful on uneven land where sufficient water is not available. It gets sprinkled on the crop as if it is raining. Sprinkler is very useful for sandy soil.'",
        "source_page": 9,
        "options": [
            {"key": "A", "text": "Sprinkler system, because rotating nozzles distribute water uniformly over uneven terrain like rain and suit sandy soil", "is_correct": True, "feedback": "Correct! Sprinklers work on perpendicular pipes with rotating nozzles, ideal for uneven sandy soils."},
            {"key": "B", "text": "Traditional moat system, because cattle can walk up steep sandy slopes effortlessly", "is_correct": False, "feedback": "Moat causes severe surface runoff and water wastage on uneven slopes."},
            {"key": "C", "text": "Flooding the entire field continuously from a wide canal", "is_correct": False, "feedback": "Flooding leads to massive water wastage, soil erosion, and uneven pooling on slopes."},
            {"key": "D", "text": "Rain dance ritual without any physical pipes", "is_correct": False, "feedback": "Non-scientific method."}
        ],
        "rubric": {
            "expected_concepts": ["Sprinkler system", "Uneven land", "Sandy soil", "Rotating nozzles"],
            "required_points": ["Sprinkler resembles artificial rain", "Effective for uneven ground where water cannot pool"],
            "misconception_traps": {
                "flooding_is_universal": "Assuming surface flooding is suitable for all types of soil and terrain."
            }
        }
    },
    {
        "concept_name": "Irrigation: Traditional vs Modern Systems",
        "cognitive_level": 4,
        "prompt": "Why is the Drip Irrigation System (Fig. 1.5(b)) considered the ultimate water-conserving boon in drought-prone regions for fruit orchards and gardens?",
        "explanation": "Textbook p. 9 states: 'In drip system, water falls drop by drop directly near the roots. So it is called drip system. It is the best technique for watering fruit plants, gardens and trees. Water is not wasted at all. It is a boon in regions where availability of water is poor.'",
        "source_page": 9,
        "options": [
            {"key": "A", "text": "Water falls drop by drop directly at the plant root zone, eliminating evaporation and surface runoff with virtually zero water waste", "is_correct": True, "feedback": "Correct! Targeted root delivery achieves near 100% water efficiency."},
            {"key": "B", "text": "It floods the entire field surface so weeds get suffocated under water", "is_correct": False, "feedback": "Drip irrigation targets only the crop roots and actually prevents weed growth by keeping between-row soil dry."},
            {"key": "C", "text": "It dissolves rainwater into pure chemical fertilizer inside the pipe", "is_correct": False, "feedback": "Drip systems deliver water; fertigation is an optional addition, not inherent magic."},
            {"key": "D", "text": "It cools the ambient air temperature across 5 kilometers of surrounding villages", "is_correct": False, "feedback": "Drip irrigation does not alter regional weather."}
        ],
        "rubric": {
            "expected_concepts": ["Drip system", "Drop by drop delivery", "Root zone efficiency", "Zero water wastage"],
            "required_points": ["Delivers directly to root zone", "Prevents evaporation and runoff", "Boon in water-poor regions"],
            "misconception_traps": {
                "sprinkler_saves_more": "Believing overhead sprayers save more water than direct sub-surface or root drip lines."
            }
        }
    },

    # Concept 8: Protection from Weeds
    {
        "concept_name": "Protection from Weeds",
        "cognitive_level": 1,
        "prompt": "What are weeds, and why must they be removed from agricultural fields?",
        "explanation": "Textbook p. 10 defines: 'In a field many other undesirable plants may grow naturally along with the crop. These undesirable plants are called weeds. Weeding is necessary since weeds compete with the crop plants for water, nutrients, space and light.'",
        "source_page": 10,
        "options": [
            {"key": "A", "text": "Undesirable wild plants that compete with crop plants for water, nutrients, space, and sunlight", "is_correct": True, "feedback": "Correct! Competition from weeds severely reduces crop yield."},
            {"key": "B", "text": "Beneficial companion plants that protect crops from direct sunlight", "is_correct": False, "feedback": "Weeds steal vital light and resources."},
            {"key": "C", "text": "Microscopic bacteria living on leaf surfaces", "is_correct": False, "feedback": "Weeds are unwanted macroscopic plants, not bacteria."},
            {"key": "D", "text": "Insects that feed on crop roots during the night", "is_correct": False, "feedback": "Those are pests; weeds are plants."}
        ],
        "rubric": {
            "expected_concepts": ["Definition of weeds", "Competition factors", "Nutrient/water theft"],
            "required_points": ["Undesirable plants", "Compete for water, nutrients, space, and light"],
            "misconception_traps": {
                "weeds_are_harmless": "Believing extra greenery in a field has no negative impact on crop nutrition."
            }
        }
    },
    {
        "concept_name": "Protection from Weeds",
        "cognitive_level": 3,
        "prompt": "When a farmer sprays chemical weedicides such as 2,4-D in the field (Fig. 1.6), what vital personal health precaution must be taken?",
        "explanation": "Textbook p. 10 cautions: 'Spraying of weedicides may affect the health of farmers. So they should use these chemicals very carefully. They should cover their nose and mouth with a piece of cloth during spraying of these chemicals.'",
        "source_page": 10,
        "options": [
            {"key": "A", "text": "Cover the nose and mouth securely with a clean cloth or mask to avoid inhaling toxic chemical vapours", "is_correct": True, "feedback": "Correct! 2,4-D and other weedicides are toxic and must not be inhaled."},
            {"key": "B", "text": "Spray against the wind direction while keeping the mouth open", "is_correct": False, "feedback": "Dangerous! Spraying into the wind blows toxic spray directly onto the farmer."},
            {"key": "C", "text": "Drink half a glass of weedicide solution before spraying to build immunity", "is_correct": False, "feedback": "Extremely dangerous! Weedicides are poisonous."},
            {"key": "D", "text": "Spray barefoot during heavy rainstorms without any equipment", "is_correct": False, "feedback": "Rain washes away weedicides and increases chemical skin contact."}
        ],
        "rubric": {
            "expected_concepts": ["Weedicide safety", "2,4-D chemical", "Face and respiratory protection"],
            "required_points": ["Cover mouth and nose", "Prevent toxic inhalation and skin contact"],
            "misconception_traps": {}
        }
    },

    # Concept 9: Harvesting and Threshing
    {
        "concept_name": "Harvesting and Threshing",
        "cognitive_level": 1,
        "prompt": "What is the modern farm machine called that combines the operations of both harvesting and threshing simultaneously (Fig. 1.8)?",
        "explanation": "Textbook p. 11 (Fig. 1.8) states: 'In the harvested crop, the grain seeds need to be separated from the chaff. This process is called threshing. This is carried out with the help of a machine called Combine which is in fact a combined harvester and thresher.'",
        "source_page": 11,
        "options": [
            {"key": "A", "text": "Combine", "is_correct": True, "feedback": "Correct! A combine reaps, threshes, and winnows grains in a single run."},
            {"key": "B", "text": "Cultivator", "is_correct": False, "feedback": "Cultivators till and loosen the soil before sowing."},
            {"key": "C", "text": "Seed Drill", "is_correct": False, "feedback": "Seed drills are used for sowing seeds at uniform depth."},
            {"key": "D", "text": "Khurpi", "is_correct": False, "feedback": "A khurpi is a small hand tool used for manual weeding."}
        ],
        "rubric": {
            "expected_concepts": ["Combine machine", "Harvesting", "Threshing"],
            "required_points": ["Dual function: harvester and thresher combined"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Harvesting and Threshing",
        "cognitive_level": 2,
        "prompt": "Farmers with small holdings of land do the separation of grain and chaff by which traditional method (Fig. 1.9)?",
        "explanation": "Textbook p. 11 (Fig. 1.9) specifies: 'Farmers with small holdings of land do the separation of grain and chaff by winnowing.' Wind blows the lighter chaff away while denser grains fall straight down.",
        "source_page": 11,
        "options": [
            {"key": "A", "text": "Winnowing, using wind currents to separate lighter chaff from heavier grain seeds", "is_correct": True, "feedback": "Correct! Winnowing takes advantage of the weight difference in the breeze."},
            {"key": "B", "text": "Drip irrigation in reverse", "is_correct": False, "feedback": "Irrigation supplies water, it does not separate grain from chaff."},
            {"key": "C", "text": "Spraying 2,4-D weedicide on harvested piles", "is_correct": False, "feedback": "Spraying weedicide on harvested grain would poison food supplies."},
            {"key": "D", "text": "Burying grain pods under deep soil crumbs", "is_correct": False, "feedback": "Burying would rot or germinate the grain."}
        ],
        "rubric": {
            "expected_concepts": ["Winnowing", "Grain and chaff separation", "Small-scale farming"],
            "required_points": ["Wind separates light chaff from heavy grain"],
            "misconception_traps": {}
        }
    },

    # Concept 10: Storage of Food Grains
    {
        "concept_name": "Storage of Food Grains",
        "cognitive_level": 2,
        "prompt": "Why is it absolutely vital to sun-dry freshly harvested grains before packing and storing them in bags or containers?",
        "explanation": "Textbook p. 11-12 stresses: 'If freshly harvested grains are stored without drying, they may get spoilt or attacked by organisms, losing their germination capacity. Hence, before storing them, the grains are properly dried in the sun to reduce the moisture in them. This prevents the attack by insect pests, bacteria and fungi.'",
        "source_page": 11,
        "options": [
            {"key": "A", "text": "Moisture attracts insect pests, bacteria, and fungi which spoil the grains and destroy their germination capacity", "is_correct": True, "feedback": "Correct! Moisture creates an ideal breeding environment for mould and pests."},
            {"key": "B", "text": "Sunlight bleaches the grains to give them an artificial white color", "is_correct": False, "feedback": "Drying removes moisture, not for cosmetic coloring."},
            {"key": "C", "text": "Drying turns grain carbohydrates directly into pure protein", "is_correct": False, "feedback": "Nutrient composition does not transmute during sun drying."},
            {"key": "D", "text": "Fresh grains explode if kept at room temperature without direct sun radiation", "is_correct": False, "feedback": "Grains do not explode; they rot due to fungal and microbial growth."}
        ],
        "rubric": {
            "expected_concepts": ["Grain drying", "Moisture reduction", "Fungal and pest prevention"],
            "required_points": ["Moisture causes spoilage and insect/fungal attack", "Drying preserves germination and food quality"],
            "misconception_traps": {
                "moisture_preserves": "Thinking moist grains stay fresh and germinate faster in storage."
            }
        }
    },
    {
        "concept_name": "Storage of Food Grains",
        "cognitive_level": 3,
        "prompt": "A household stores 50 kg of wheat at home in iron bins. What traditional, safe, and chemical-free material described in the textbook is used to protect stored grains from insects?",
        "explanation": "Textbook p. 12 mentions: 'Dried neem leaves are used for storing food grains at home. For storing large quantities of grains in big godowns, specific chemical treatments are required to protect them from pests and microorganisms.'",
        "source_page": 12,
        "options": [
            {"key": "A", "text": "Dried neem leaves", "is_correct": True, "feedback": "Correct! Dried neem leaves act as a safe natural insect repellent in home storage."},
            {"key": "B", "text": "Raw cow dung slurry", "is_correct": False, "feedback": "Slurry would contaminate the grains with moisture and bacteria."},
            {"key": "C", "text": "Unrefined crude oil", "is_correct": False, "feedback": "Oil would render grains toxic and inedible."},
            {"key": "D", "text": "Powdered sugar crystals", "is_correct": False, "feedback": "Sugar would attract ants and pests immediately."}
        ],
        "rubric": {
            "expected_concepts": ["Neem leaves", "Natural preservation", "Household storage"],
            "required_points": ["Dried neem leaves repel insects naturally"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Storage of Food Grains",
        "cognitive_level": 4,
        "prompt": "What large-scale commercial storage facilities are depicted in Fig. 1.10(a) and (b) to protect millions of tonnes of national grain stocks from rats and insects?",
        "explanation": "Textbook p. 12 (Fig. 1.10) details: 'Large scale storage of grains is done in silos and granaries to protect them from pests like rats and insects (Fig. 1.10 (a), (b)).'",
        "source_page": 12,
        "options": [
            {"key": "A", "text": "Silos and Granaries with controlled temperature and pest management", "is_correct": True, "feedback": "Correct! Tall cylindrical metal/concrete silos and large granaries protect buffer grain stocks."},
            {"key": "B", "text": "Open roadside dirt pits covered with loose straw", "is_correct": False, "feedback": "Open pits lead to massive spoilage from rain and rodent invasion."},
            {"key": "C", "text": "Submerged river cages", "is_correct": False, "feedback": "Water immersion destroys grains completely."},
            {"key": "D", "text": "Tractor trailers parked continuously in village courtyards", "is_correct": False, "feedback": "Trailers are transport vehicles, not secure long-term storage facilities."}
        ],
        "rubric": {
            "expected_concepts": ["Silos", "Granaries", "Fig 1.10", "Pest protection"],
            "required_points": ["Silos and granaries store massive quantities", "Defend against rodents and insect pests"],
            "misconception_traps": {}
        }
    },

    # Concept 11: Food from Animals & Animal Husbandry
    {
        "concept_name": "Food from Animals & Animal Husbandry",
        "cognitive_level": 1,
        "prompt": "What is the practice of rearing animals for food, milk, or labour on a large scale with proper food, shelter, and care called?",
        "explanation": "Textbook p. 13 defines: 'When this is done on a large scale, it is called animal husbandry.'",
        "source_page": 13,
        "options": [
            {"key": "A", "text": "Animal husbandry", "is_correct": True, "feedback": "Correct! Animal husbandry involves systematic breeding, feeding, and healthcare of livestock."},
            {"key": "B", "text": "Crop rotation", "is_correct": False, "feedback": "Crop rotation involves alternating plant varieties in farm soil."},
            {"key": "C", "text": "Pesticide management", "is_correct": False, "feedback": "Pesticide management controls insect crop pests."},
            {"key": "D", "text": "Winnowing", "is_correct": False, "feedback": "Winnowing is separating grain from chaff."}
        ],
        "rubric": {
            "expected_concepts": ["Animal husbandry", "Livestock management"],
            "required_points": ["Large-scale rearing with proper food, shelter, and healthcare"],
            "misconception_traps": {}
        }
    },
    {
        "concept_name": "Food from Animals & Animal Husbandry",
        "cognitive_level": 2,
        "prompt": "Why is fish widely consumed as a major dietary component in coastal areas, and which vital vitamin is cod liver oil especially rich in?",
        "explanation": "Textbook p. 13 concludes: 'Fish is good for health. We get cod liver oil from fish which is rich in vitamin D.'",
        "source_page": 13,
        "options": [
            {"key": "A", "text": "Fish provides high quality protein and cod liver oil is very rich in Vitamin D", "is_correct": True, "feedback": "Correct! The textbook specifically notes cod liver oil is rich in Vitamin D."},
            {"key": "B", "text": "Cod liver oil is purely water and sodium chloride", "is_correct": False, "feedback": "Cod liver oil is an organic fish oil rich in fat-soluble vitamins."},
            {"key": "C", "text": "Fish contains no nutritional value and is eaten solely for water hydration", "is_correct": False, "feedback": "Fish is a vital source of protein and healthy lipids."},
            {"key": "D", "text": "Cod liver oil is used solely as fuel for tractors", "is_correct": False, "feedback": "It is a dietary supplement for human nutrition."}
        ],
        "rubric": {
            "expected_concepts": ["Fish nutrition", "Cod liver oil", "Vitamin D"],
            "required_points": ["Cod liver oil is rich in Vitamin D", "Major health and protein source"],
            "misconception_traps": {}
        }
    },

    # Challenge & Synthesizing Questions (Cognitive Level 5)
    {
        "concept_name": "Agricultural Practices & Crop Seasons",
        "cognitive_level": 5,
        "prompt": "Challenge Problem: An organic farmer in Bagalkot, Karnataka owns 5 acres of uneven land with sandy loam soil and scarce groundwater. Formulate the best integrated management plan for the upcoming Kharif season.",
        "explanation": "A comprehensive plan incorporates: (1) Sowing drought-tolerant Kharif crops (e.g., groundnut, maize, or cotton) using a precision seed drill; (2) Applying organic manure and vermicompost rather than heavy chemical fertilisers to improve water retention and soil humus; (3) Installing a sprinkler or drip irrigation system to minimize water loss on uneven sandy soil; (4) Manual weeding with khurpi or organic mulching rather than toxic 2,4-D.",
        "source_page": 9,
        "options": [
            {"key": "A", "text": "Sow Kharif crops with a seed drill, apply organic manure to boost soil water retention, install drip/sprinkler irrigation, and practice mechanical weeding with a khurpi", "is_correct": True, "feedback": "Correct! This integrates all textbook principles for sustainable, water-conserving agriculture on uneven terrain."},
            {"key": "B", "text": "Sow wheat in July, flood the field continuously from a canal, and apply excessive urea fertilisers", "is_correct": False, "feedback": "Wheat is a winter crop, continuous flooding exhausts scarce water, and excess urea damages soil texture."},
            {"key": "C", "text": "Broadcast uninspected floating seeds by hand and never dry harvested crops before storing in humid rooms", "is_correct": False, "feedback": "Floating seeds are hollow/damaged, hand scattering is inefficient, and undried storage causes fungal rot."},
            {"key": "D", "text": "Avoid ploughing completely and leave weeds to shade the soil surface", "is_correct": False, "feedback": "Unloosened soil suffocates roots and unmanaged weeds rob crops of nutrients and moisture."}
        ],
        "rubric": {
            "expected_concepts": ["Integrated agricultural plan", "Water conservation", "Organic manure", "Precision sowing"],
            "required_points": [
                "Select appropriate Kharif crop",
                "Employ modern water-saving irrigation (drip/sprinkler)",
                "Organic soil conditioning with manure",
                "Safe pest/weed control"
            ],
            "misconception_traps": {
                "high_chemical_is_modern": "Equating modern agriculture purely with indiscriminate chemical spraying and excessive irrigation."
            }
        }
    }
]


async def enrich_chapter_1(db: AsyncSession) -> Dict[str, Any]:
    """
    Enriches Chapter 1 in the database:
    - Finds or verifies Chapter 1 and its sections
    - Refines canonical concepts with clean names and rich summaries
    - Creates Bloom-aligned learning objectives
    - Inserts calibrated question bank covering levels 1-5 with options and misconception rubrics
    """
    # 1. Locate Chapter 1
    ch_stmt = select(Chapter).where(Chapter.title.ilike(f"%{CHAPTER_1_TITLE}%"))
    ch_res = await db.execute(ch_stmt)
    chapter = ch_res.scalars().first()
    if not chapter:
        ch_stmt2 = select(Chapter).where(Chapter.chapter_number == 1)
        chapter = (await db.execute(ch_stmt2)).scalars().first()

    if not chapter:
        raise ValueError("Chapter 1 not found in database.")

    # 2. Get sections for Chapter 1
    sec_stmt = select(Section).where(Section.chapter_id == chapter.id).order_by(Section.section_number)
    sec_res = await db.execute(sec_stmt)
    sections = list(sec_res.scalars().all())
    sec_by_num = {s.section_number.strip(): s for s in sections}

    # 3. Create or Update Topics and Concepts
    concept_map = {}
    topic_map = {}

    for c_info in CANONICAL_CONCEPTS:
        sec_num = c_info["section_number"]
        section = sec_by_num.get(sec_num)
        if not section and sections:
            section = sections[0]

        # Find or create Topic
        t_stmt = select(Topic).where(Topic.section_id == section.id, Topic.title == c_info["name"])
        t_res = await db.execute(t_stmt)
        topic = t_res.scalars().first()
        if not topic:
            topic = Topic(
                section_id=section.id,
                title=c_info["name"],
                status="PUBLISHED"
            )
            db.add(topic)
            await db.flush()

        topic_map[c_info["name"]] = topic

        # Find or create Concept
        c_stmt = select(Concept).where(Concept.topic_id == topic.id, Concept.name == c_info["name"])
        c_res = await db.execute(c_stmt)
        concept = c_res.scalars().first()
        if not concept:
            concept = Concept(
                topic_id=topic.id,
                name=c_info["name"],
                summary=c_info["summary"],
                difficulty_tier=c_info["difficulty_tier"],
                status="PUBLISHED"
            )
            db.add(concept)
            await db.flush()
        else:
            concept.summary = c_info["summary"]
            concept.difficulty_tier = c_info["difficulty_tier"]
            concept.status = "PUBLISHED"

        concept_map[c_info["name"]] = concept

        # Objectives
        for obj_info in c_info.get("objectives", []):
            o_stmt = select(LearningObjective).where(
                LearningObjective.concept_id == concept.id,
                LearningObjective.statement == obj_info["statement"]
            )
            existing_obj = (await db.execute(o_stmt)).scalars().first()
            if not existing_obj:
                new_obj = LearningObjective(
                    topic_id=topic.id,
                    concept_id=concept.id,
                    statement=obj_info["statement"],
                    bloom_taxonomy_level=obj_info["bloom"]
                )
                db.add(new_obj)

    await db.flush()

    # 4. Insert Calibrated Questions
    questions_added = 0
    for q_data in CALIBRATED_QUESTIONS:
        concept = concept_map.get(q_data["concept_name"])
        if not concept:
            continue
        topic = topic_map.get(q_data["concept_name"])

        # Check if question already exists with same prompt
        q_stmt = select(Question).where(
            Question.concept_id == concept.id,
            Question.prompt == q_data["prompt"]
        )
        existing_q = (await db.execute(q_stmt)).scalars().first()
        if existing_q:
            continue

        new_q = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="mcq",
            cognitive_level=q_data["cognitive_level"],
            prompt=q_data["prompt"],
            explanation=q_data["explanation"],
            source_page=q_data.get("source_page"),
            source_type="textbook_exercise",
            is_published=True
        )
        db.add(new_q)
        await db.flush()

        # Options
        for opt in q_data["options"]:
            q_opt = QuestionOption(
                question_id=new_q.id,
                option_key=opt["key"],
                option_text=opt["text"],
                is_correct=opt["is_correct"],
                feedback=opt.get("feedback")
            )
            db.add(q_opt)

        # Rubric
        rub = q_data["rubric"]
        q_rub = QuestionRubric(
            question_id=new_q.id,
            expected_concepts=rub.get("expected_concepts", []),
            required_points=rub.get("required_points", []),
            misconception_traps=rub.get("misconception_traps", {}),
            max_score=1.0
        )
        db.add(q_rub)
        questions_added += 1

    await db.commit()
    return {
        "status": "SUCCESS",
        "chapter_id": chapter.id,
        "concepts_count": len(concept_map),
        "questions_added": questions_added
    }
