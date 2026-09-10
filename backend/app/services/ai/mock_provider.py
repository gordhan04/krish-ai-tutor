import re
from typing import Dict, Any, List, Optional
from app.services.ai.base import AIProvider, TutorResponse, EvaluationResult


class MockAIProvider(AIProvider):
    """
    High-fidelity deterministic Mock AI Provider for testing and offline development.
    Emulates grounded responses, rubric evaluations, misconception detection, and hint ladder.
    """

    async def generate_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        c_lower = concept_name.lower()
        if "seed" in c_lower or "sow" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Farmers must select clean, healthy seeds of good quality. "
                f"Textbook Activity 1.1 reveals that damaged seeds are hollow and light, so they float in water, while healthy seeds sink to the bottom.\n\n"
                f"💡 **Check question:** If you place wheat seeds into water, what tells you which seeds are healthy?"
            )
            replies = ["Healthy seeds sink to the bottom.", "Healthy seeds float on water.", "Both float equally."]
        elif "soil" in c_lower or "plough" in c_lower or "till" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Soil preparation is the first agricultural step. "
                f"Tilling and loosening allows crop roots to breathe easily and penetrate deep, while helping friendly earthworms add rich humus.\n\n"
                f"💡 **Check question:** Why is loosening soil so beneficial for young crop roots?"
            )
            replies = ["It allows roots to breathe and grow deep.", "It packs the soil tightly.", "It stops roots from growing."]
        elif "manure" in c_lower or "fertilis" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Continuous cropping depletes nutrients. "
                f"Organic manure adds natural humus and improves soil texture, while chemical fertilisers supply targeted minerals like nitrogen and potassium.\n\n"
                f"💡 **Check question:** What major advantage does organic manure have over synthetic fertilisers?"
            )
            replies = ["Organic manure adds humus and improves soil texture.", "Chemical fertilisers add more humus.", "Neither adds nutrients."]
        elif "irrigation" in c_lower or "water" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Crops require timely water supply. "
                f"Modern methods like Sprinkler systems suit uneven sandy soils, whereas Drip systems deliver water drop-by-drop directly to the roots without wastage.\n\n"
                f"💡 **Check question:** Why is drip irrigation preferred in regions where water is scarce?"
            )
            replies = ["Drip drops water right at roots with zero waste.", "Sprinklers save more water.", "Traditional moat is better."]
        elif "weed" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Weeds are unwanted wild plants that compete with crops for sunlight, water, and nutrients. "
                f"Farmers remove them manually with a khurpi or spray weedicides like 2,4-D while covering their mouth and nose.\n\n"
                f"💡 **Check question:** Why must farmers remove weeds from their fields?"
            )
            replies = ["Weeds compete for nutrients, water, and light.", "Weeds help crops grow taller.", "Weeds attract rain."]
        elif "storage" in c_lower or "grain" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Freshly harvested grains carry moisture. "
                f"They must be thoroughly dried in the sun before storage to prevent fungi, bacteria, and insect pests from spoiling them in silos or granaries.\n\n"
                f"💡 **Check question:** What happens if grains are stored without proper sun-drying?"
            )
            replies = ["Moisture allows fungi and pests to spoil them.", "Grains become heavier and stronger.", "Nothing happens."]
        elif "crop" in c_lower:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** Crops in India are categorized by season: Kharif crops (like paddy and maize) are sown in the rainy season, while Rabi crops (like wheat and gram) are grown in winter.\n\n"
                f"💡 **Check question:** Why is paddy sown during the monsoon instead of winter?"
            )
            replies = ["Paddy requires large amounts of monsoon water.", "Paddy prefers cold winter air.", "Paddy grows only in frost."]
        else:
            message = (
                f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
                f"**Key Idea:** According to your textbook, pure distilled water does not conduct electricity. "
                f"However, when mineral salts, acids, or bases are dissolved in water, they produce free ions. "
                f"These moving ions carry electric current through the liquid!\n\n"
                f"💡 **Check question:** What do you think happens if we test tap water versus pure distilled water in a tester circuit?"
            )
            replies = [
                "Tap water conducts electricity, distilled water does not.",
                "Both conduct electricity equally.",
                "Neither conducts electricity."
            ]

        return TutorResponse(
            message=message,
            pedagogical_intent="explain",
            strategy="DIRECT_EXPLANATION",
            hint_level=0,
            suggested_quick_replies=replies
        )

    async def generate_strategy_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        strategy: str,
        student_name: str = "Krish",
        prior_misconception: str = None,
    ) -> TutorResponse:
        strategy_upper = strategy.upper()
        c_lower = (concept_name + " " + (curriculum_context[:200] if curriculum_context else "")).lower()

        # Concept Domain 1: Crop Seasons & Agricultural Practices
        if any(kw in c_lower for kw in ["crop", "season", "kharif", "rabi", "agricultural"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Think about how your wardrobe changes throughout the year. You wear light cotton clothes and carry an umbrella in the pouring monsoon, "
                    f"but you pull out thick sweaters in the cold winter. You wouldn't wear a heavy woolen coat in July! "
                    f"In the exact same way, crops have seasonal preferences: **Kharif crops** thrive in monsoon warmth and rain, "
                    f"whereas **Rabi crops** need cooler temperatures and dry sunshine to mature."
                )
                replies = ["Crops have seasonal needs like clothes.", "What happens if we sow wheat in monsoon?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"In India, farmers eagerly await the arrival of the southwest monsoon in June to sow paddy (rice), "
                    f"while they wait until October or November to plant wheat. Why? "
                    f"Paddy seedlings require abundant standing water and warm humidity, which dry winter cannot provide. "
                    f"That is why crops are classified into **Kharif crops** (rainy season) and **Rabi crops** (winter season)!"
                )
                replies = ["Paddy needs monsoon water; wheat needs winter.", "Why do crops have different seasons?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down the **7 Agricultural Practices** step by step, {student_name}:\n\n"
                    f"1. **Preparation of Soil**: Loosening and tilling soil using a plough.\n"
                    f"2. **Sowing**: Selecting clean, viable seeds and sowing with a seed drill.\n"
                    f"3. **Adding Manure and Fertilisers**: Enriching the soil with organic matter and nutrients.\n"
                    f"4. **Irrigation**: Supplying water at regular intervals.\n"
                    f"5. **Protecting from Weeds**: Removing wild competing plants with a khurpi or weedicides.\n"
                    f"6. **Harvesting**: Cutting and threshing the mature crop.\n"
                    f"7. **Storage**: Sun-drying grains and protecting them in silos and granaries."
                )
                replies = ["Step 1 is soil, then sowing and manure.", "Why is storage the final critical step?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "any crop can be grown in any season if watered"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. It is natural to assume that seeds can grow whenever planted if watered. "
                    f"But crops strictly require specific temperatures, rainfall, and daylight cycles. "
                    f"For instance, paddy requires huge volumes of water; sowing it in winter would stunt its growth, "
                    f"while sowing wheat in heavy monsoon would cause its roots to rot."
                )
                replies = ["Got it: crops depend on rainfall and temperature.", "Can we practice identifying crop types?"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Why do you think farmers across India sow paddy, maize, and cotton between June and September, "
                    f"but wait until October to sow wheat and mustard? What conditions does the monsoon provide that winter cannot?"
                )
                replies = ["Monsoon provides the heavy water paddy needs.", "I'd like a hint to think about this."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Kharif Crops**: Sown during rainy season (June–Sept) — e.g., Paddy, Maize, Soyabean, Groundnut, Cotton.\n"
                    f"• **Rabi Crops**: Grown in winter season (Oct–March) — e.g., Wheat, Gram, Pea, Mustard, Linseed.\n"
                    f"• **Agricultural Practices**: The 7 systematic steps from soil preparation to storage."
                )
                replies = ["I understand the recap.", "Let's practice!"]
            else:
                message = (
                    f"Let's examine **{concept_name}**, {student_name}:\n\n"
                    f"When plants of the same kind are cultivated at one place on a large scale, it is called a **crop**. "
                    f"In India, crops are categorized by seasons: **Kharif** crops (sown in June–Sept during monsoon) and "
                    f"**Rabi** crops (sown in Oct–March during winter)."
                )
                replies = ["Kharif is monsoon, Rabi is winter.", "Let's practice!"]

        # Concept Domain 2: Preparation of Soil
        elif any(kw in c_lower for kw in ["soil", "till", "plough", "crumb", "levell"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Imagine trying to sleep under a heavy concrete slab versus a fluffy, breathable cotton blanket. "
                    f"Young plant roots need room to 'inhale' oxygen! Hard, compacted soil suffocates roots, "
                    f"but tilling acts like fluffing up a blanket, creating airy pockets for roots to breathe and grow freely."
                )
                replies = ["Tilling creates airy pockets for roots.", "Why do we need a leveller next?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"Have you ever tried pushing a wooden pencil into hard, sun-baked clay versus into loose garden soil? "
                    f"In loose soil, it glides right in! When farmers plough their fields, they loosen packed earth so "
                    f"young seedling roots can easily penetrate deep and breathe trapped air, while earthworms enrich the topsoil."
                )
                replies = ["Loose soil lets roots breathe and grow deep.", "What are the big crumbs called?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Soil Preparation** step by step, {student_name}:\n\n"
                    f"1. **Ploughing/Tilling**: Loosening and turning topsoil to bring nutrient-rich soil to the top.\n"
                    f"2. **Breaking Crumbs**: Crushing large hard chunks of soil called 'crumbs' using a plank.\n"
                    f"3. **Levelling**: Smoothing and flattening the loosened field with a leveller for uniform sowing.\n"
                    f"4. **Manuring**: Adding natural manure before final tilling so it mixes evenly into the soil."
                )
                replies = ["Tilling, breaking crumbs, then levelling.", "Why do earthworms thrive in loose soil?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "hard packed soil holds plant roots better"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. People often think compact, hard soil holds plants more securely. "
                    f"In reality, hard soil prevents root penetration, traps zero air for root respiration, and causes water to pool. "
                    f"Loosening soil is essential for healthy root respiration and friendly microbes!"
                )
                replies = ["Roots actually need air pockets to breathe.", "Let's test this concept."]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Only a few centimeters of the top layer of soil support plant growth. "
                    f"Why does turning and loosening this soil make such a huge difference to growing roots and soil microbes?"
                )
                replies = ["It brings nutrient-rich soil up and adds oxygen.", "I'd like a hint to think about this."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Tilling/Ploughing**: Loosens soil, allows roots to penetrate and breathe.\n"
                    f"• **Earthworms & Microbes**: Thrive in loose soil, adding rich humus.\n"
                    f"• **Crumbs & Levelling**: Hard lumps are crushed and levelled for even watering."
                )
                replies = ["I understand the soil preparation steps.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Preparation of soil is the first agricultural step. "
                    f"Tilling and loosening allows crop roots to breathe easily and penetrate deep, while helping earthworms add rich humus."
                )
                replies = ["Loosening allows roots to breathe.", "Let's practice!"]

        # Concept Domain 3: Sowing & Seed Selection
        elif any(kw in c_lower for kw in ["seed", "sow", "drill", "transplant"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Imagine a crowded classroom where students are placed randomly on top of each other versus having their own spaced desks. "
                    f"If seeds are scattered haphazardly by hand (broadcasting), seedlings choke each other for light and water. "
                    f"A modern **seed drill** gives every seed its own spaced spot at the proper depth and distance!"
                )
                replies = ["Seed drill prevents overcrowding.", "Why cover seeds with soil?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"In textbook Activity 1.1, a farmer puts wheat seeds into a bucket of water. Within seconds, some seeds float while others sink! "
                    f"Why? Pest-eaten seeds have hollow, damaged insides, making them light enough to float. "
                    f"Healthy, nutrient-packed seeds are dense and sink—allowing the farmer to select only the best seeds for sowing."
                )
                replies = ["Healthy seeds sink, damaged ones float.", "How does a seed drill help?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Sowing & Seed Selection** step by step, {student_name}:\n\n"
                    f"1. **Seed Selection**: Conducting the water-flotation test (Activity 1.1) to filter out hollow, damaged seeds.\n2. **Tool Selection**: Using a tractor-driven seed drill rather than uneven manual broadcasting.\n3. **Uniform Spacing**: Sowing seeds at precise distances to avoid overcrowding.\n4. **Proper Depth & Soil Cover**: Ensuring seeds are covered by soil to protect them from birds."
                )
                replies = ["Water test, seed drill, correct depth and spacing.", "What is transplantation?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "broadcasting seeds by hand is just as effective as using a seed drill"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. Broadcasting seeds by hand may seem fast, but seeds fall in clusters, "
                    f"causing severe overcrowding, while many remain exposed on the surface and are eaten by birds. "
                    f"A seed drill ensures uniform depth, exact spacing, and protective soil cover."
                )
                replies = ["Seed drills protect seeds from birds and crowding.", "Let's retest this."]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"When a seed drill sows seeds at uniform distances, why does this spacing directly increase the harvest yield?"
                )
                replies = ["Plants don't compete for sunlight, water, and nutrients.", "I'd like a hint to think about this."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Selection (Activity 1.1)**: Healthy seeds sink; hollow damaged seeds float.\n"
                    f"• **Seed Drill**: Sows seeds uniformly at proper depth and covers them with soil.\n"
                    f"• **Overcrowding**: Prevented by maintaining sufficient distance between seeds."
                )
                replies = ["I understand seed selection and sowing.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Sowing is a critical part of crop production. "
                    f"Good quality, clean and healthy seeds of a good variety are selected. Activity 1.1 shows damaged seeds float while healthy seeds sink."
                )
                replies = ["Healthy seeds sink in water.", "Let's practice!"]

        # Concept Domain 4: Manure & Fertilisers
        elif any(kw in c_lower for kw in ["manure", "fertilis", "humus", "rhizobium", "rotation"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Imagine a bank account. Every harvest withdraws minerals like nitrogen from the soil. "
                    f"If you only deposit synthetic chemicals, the soil texture goes bankrupt. "
                    f"Adding manure and planting leguminous crops with **Rhizobium** bacteria in their root nodules is like making a natural deposit that keeps the soil's biological bank healthy!"
                )
                replies = ["Rhizobium bacteria fix nitrogen in root nodules.", "Why do fertilisers cause pollution?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"Think about drinking a sugary energy drink versus having a balanced home-cooked meal. "
                    f"Chemical fertilisers are like the energy drink—they give an instant burst of nitrogen, phosphorus, and potassium (NPK), but leave zero humus. "
                    f"Organic manure is like the balanced meal—it slowly feeds the soil, enriches it with natural humus, and improves water retention for years!"
                )
                replies = ["Manure adds organic humus and texture.", "What is crop rotation?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Manure and Fertilisers** step by step, {student_name}:\n\n"
                    f"1. **Nutrient Depletion**: Continuous cultivation strips soil of essential minerals.\n2. **Organic Manure**: Decomposing plant and animal waste provides natural humus and improves soil porosity.\n3. **Chemical Fertilisers**: Factory-made mineral salts (Urea, NPK) supply concentrated nutrients for rapid initial growth.\n4. **Balancing & Crop Rotation**: Rotating cereal crops with leguminous plants replenishes nitrogen naturally via Rhizobium."
                )
                replies = ["Manure adds humus; fertilisers give quick NPK.", "Why is crop rotation important?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "chemical fertilisers can permanently replace organic manure"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. While chemical fertilisers dramatically boost short-term yield, "
                    f"excessive use makes soil alkaline or acidic and destroys friendly soil organisms. "
                    f"Manure enriches soil texture, promotes beneficial microbes, and enhances water-holding capacity without chemical harm."
                )
                replies = ["Excess fertiliser damages soil and causes water pollution.", "Let's practice!"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Why do farmers rotate wheat with leguminous crops like peas or beans? What happens inside the root nodules of those legumes?"
                )
                replies = ["Rhizobium bacteria fix atmospheric nitrogen into the soil.", "I'd like a hint."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Manure**: Natural organic substance, adds abundant humus, improves soil texture.\n"
                    f"• **Fertilisers**: Inorganic chemical salts (Urea, NPK), high in nutrients but zero humus.\n"
                    f"• **Rhizobium**: Nitrogen-fixing bacteria living in root nodules of leguminous plants."
                )
                replies = ["I understand manure vs fertilisers.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Continuous cropping depletes nutrients. "
                    f"Organic manure adds natural humus and improves soil texture, while chemical fertilisers supply targeted minerals like nitrogen and potassium."
                )
                replies = ["Manure adds humus and improves texture.", "Let's practice!"]

        # Concept Domain 5: Irrigation & Water Management
        elif any(kw in c_lower for kw in ["irrigation", "drip", "sprinkler", "moat", "rahat"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"A **sprinkler system** is like gentle artificial rain from rotating nozzles. It is perfect for uneven, sandy land where water cannot pool evenly. "
                    f"Meanwhile, a **drip system** is like a targeted IV drip in a hospital—delivering essential fluid drop-by-drop right where it is absorbed with zero waste!"
                )
                replies = ["Sprinklers are like rain; drip is targeted delivery.", "What are traditional irrigation methods?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"Imagine watering a houseplant using a giant bucket where water splashes everywhere and runs off, versus using an eyedropper directly at the base of the stem. "
                    f"In dry, water-scarce regions like parts of Rajasthan or Karnataka, **drip irrigation** delivers water drop by drop directly to the plant roots. Zero water is lost to evaporation!"
                )
                replies = ["Drip delivers water drop by drop at roots.", "Where are sprinklers best used?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Irrigation Methods** step by step, {student_name}:\n\n"
                    f"1. **Traditional Methods**: Moat (pulley), Chain pump, Dhekli, and Rahat—cheaper but labor-intensive and inefficient.\n2. **Modern Sprinkler System**: Perpendicular pipes with rotating nozzles spray water like artificial rain over uneven sandy soil.\n3. **Modern Drip System**: Narrow tubing releases water drop-by-drop directly at the root zone.\n4. **Conservation Benefit**: Drip systems prevent waterlogging and evaporation, making them ideal for arid regions."
                )
                replies = ["Drip for water scarcity; sprinkler for uneven land.", "How often should crops be irrigated?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "flooding crops with more water is always better"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. Giving crops excessive water isn't helpful—in fact, waterlogging blocks air from reaching the roots and damages crops! "
                    f"That is why modern drip and sprinkler systems supply measured water at precise intervals rather than flooding fields."
                )
                replies = ["Waterlogging damages roots by suffocating them.", "Let's retest this."]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"In regions with acute water shortages and sandy soil, why is drip irrigation vastly superior to traditional canal flooding?"
                )
                replies = ["Drip prevents evaporation and deep percolation loss.", "I'd like a hint."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Irrigation**: Supplying water to crops at regular intervals.\n"
                    f"• **Sprinkler System**: Rotating nozzles spray water like rain; best for uneven or sandy soils.\n"
                    f"• **Drip System**: Delivers water drop by drop directly at roots; zero waste in arid regions."
                )
                replies = ["I understand modern irrigation methods.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Crops require timely water supply. "
                    f"Modern methods like Sprinkler systems suit uneven sandy soils, whereas Drip systems deliver water drop-by-drop directly to the roots without wastage."
                )
                replies = ["Drip drops water right at roots with zero waste.", "Let's practice!"]

        # Concept Domain 6: Protection from Weeds
        elif any(kw in c_lower for kw in ["weed", "khurpi", "weedicide", "2,4-d"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Imagine sharing a single plate of lunch with three uninvited party crashers who eat all your food! "
                    f"Weeds are uninvited botanical crashers in the field. They starve the crop plants of water, sunlight, and soil nutrients unless the farmer weeds them out early."
                )
                replies = ["Weeds are uninvited resource thieves.", "What is weeding called?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"If you plant a tomato seedling in a pot, but crabgrass and wild dandelions spring up around it, the tomato stays small and yellow. "
                    f"Why? The wild weeds greedily consume the water, fertiliser nutrients, and sunlight intended for your tomato! "
                    f"Farmers must remove weeds using a khurpi or spray weedicides like 2,4-D."
                )
                replies = ["Weeds steal light, water, and nutrients.", "How do farmers protect themselves from sprays?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Weed Control** step by step, {student_name}:\n\n"
                    f"1. **Identification**: Spotting unwanted wild plants (like wild oat or amaranthus) growing alongside crops.\n2. **Tilling Before Sowing**: Uproots and kills young weeds so they dry up and decompose into humus.\n3. **Manual Weeding**: Physically cutting or uprooting weeds close to the ground using a **khurpi**.\n4. **Chemical Weedicides**: Spraying chemicals like **2,4-D** during vegetative growth before they flower, while wearing protective face masks."
                )
                replies = ["Tilling, manual khurpi, and weedicides like 2,4-D.", "Why spray before flowering?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "weeds are harmless wild plants that don't affect crops"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. Weeds might look harmless, but they are aggressive competitors. "
                    f"If left alone, they slash crop yield drastically, and some weeds are even poisonous to livestock and humans!"
                )
                replies = ["Weeds can be toxic and drastically reduce yield.", "Let's practice!"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Why is it best to remove weeds before they produce flowers and seeds, rather than after?"
                )
                replies = ["To prevent them from dispersing thousands of new seeds.", "I'd like a hint."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Weeds**: Unwanted plants competing for sunlight, space, water, and nutrients.\n"
                    f"• **Removal**: Manual uprooting with a khurpi or tilling before sowing.\n"
                    f"• **Weedicides**: Diluted chemicals like 2,4-D sprayed with face protection."
                )
                replies = ["I understand weed management.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Weeds are unwanted wild plants that compete with crops for sunlight, water, and nutrients. "
                    f"Farmers remove them manually with a khurpi or spray weedicides like 2,4-D while covering their mouth and nose."
                )
                replies = ["Weeds compete for nutrients, water, and light.", "Let's practice!"]

        # Concept Domain 7: Harvesting & Threshing
        elif any(kw in c_lower for kw in ["harvest", "thresh", "combine", "winnow"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Think about peeling the shell off a boiled peanut. The golden wheat stalk and outer husk are just the packaging; the grain inside is what we eat. "
                    f"Threshing cracks open the packaging, and winnowing uses the wind to blow away the light husk while heavy grains fall straight down!"
                )
                replies = ["Threshing separates grain from chaff.", "Why are harvest festivals celebrated?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"When golden wheat stalks ripen in April, you will see huge machines called **Combines** rolling through farm fields. "
                    f"A combine is an ingenious 2-in-1 machine: it simultaneously cuts the mature crop (harvester) and separates the edible grain seeds from the outer chaff (thresher) in a single pass!"
                )
                replies = ["A combine harvests and threshes at once.", "What is winnowing?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Harvesting & Threshing** step by step, {student_name}:\n\n"
                    f"1. **Harvesting**: Cutting the mature crop manually with a sickle or with a harvester.\n2. **Threshing**: Beating or mechanically separating the grain seeds from the chaff.\n3. **Winnowing**: Smallholders use wind currents to blow away light chaff from heavy grains.\n4. **Combine Harvester**: A modern agricultural machine combining harvesting and threshing."
                )
                replies = ["Cutting, threshing, and winnowing.", "What harvest festivals are celebrated?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "harvesting is only about cutting the plant"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. Cutting the plant is only the first half of the harvest! "
                    f"Unless threshing and winnowing cleanly separate the grain from the chaff, the produce cannot be processed or stored safely."
                )
                replies = ["Threshing and winnowing are essential parts of harvest.", "Let's practice!"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Small farmers with small landholdings use winnowing rather than giant combine machines. "
                    f"How does natural wind help separate the grain from the chaff?"
                )
                replies = ["Wind blows lighter chaff away while dense grain falls down.", "I'd like a hint."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Harvesting**: Cutting mature crop with sickle or harvester.\n"
                    f"• **Threshing**: Separating grains from the chaff.\n"
                    f"• **Combine**: Machine that acts as both a harvester and a thresher.\n"
                    f"• **Winnowing**: Wind-based separation of light chaff from grain."
                )
                replies = ["I understand harvesting and threshing.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Harvesting is the cutting of the mature crop. "
                    f"In the harvested crop, the grain seeds need to be separated from the chaff; this process is called threshing, often done using a combine machine."
                )
                replies = ["Harvesting cuts crops; threshing separates grain.", "Let's practice!"]

        # Concept Domain 8: Storage of Food Grains
        elif any(kw in c_lower for kw in ["storage", "grain", "silo", "granar", "moisture"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Think of grain storage like a bank vault for food security. "
                    f"Giant metal **silos** and government **granaries** are fortresses with temperature control and fumigation treatments "
                    f"that keep millions of tons of food grains safe from moisture, rats, and insects until they reach our dinner tables."
                )
                replies = ["Silos protect grains on a large scale.", "Why do people use dried neem leaves at home?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"If you put a warm, slightly wet slice of bread inside a plastic bag and leave it in a dark cupboard, green mold appears in two days. "
                    f"Freshly harvested grains are packed with moisture! If stored damp, fungi, bacteria, and insect pests will attack and ruin them. "
                    f"That is why farmers thoroughly sun-dry grains before packing them into gunny bags or giant metal silos."
                )
                replies = ["Sun-drying prevents mold and insect rot.", "What are silos and granaries?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **Storage of Grains** step by step, {student_name}:\n\n"
                    f"1. **Sun-Drying**: Reducing moisture content in harvested grains to prevent microbial germination.\n2. **Small-Scale Storage**: Farmers pack dried grains in jute gunny bags or metallic bins, often adding dried neem leaves.\n3. **Large-Scale Storage**: Storing grains in tall metal silos or warehouse granaries.\n4. **Chemical Protection**: Periodic fumigation and pest control to guard against insects and rodents."
                )
                replies = ["Sun-dry first, then bags or silos with neem/fumigation.", "Why does moisture cause spoilage?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "grains can be stored immediately in airtight bags"
                message = (
                    f"Let's clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. People often think storing grains immediately in airtight containers preserves them. "
                    f"But if grains are stored without thorough sun-drying, the trapped moisture causes fungal rot and destroys the grains' ability to germinate!"
                )
                replies = ["Trapped moisture is the biggest danger to stored grain.", "Let's practice!"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"Why do families traditionally place dried neem leaves in iron bins when storing wheat or rice at home?"
                )
                replies = ["Neem leaves act as a natural organic insect repellent.", "I'd like a hint."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• **Sun-Drying**: Crucial first step to eliminate moisture before storage.\n"
                    f"• **Storage Facilities**: Gunny bags, metallic bins, tall silos, and granaries.\n"
                    f"• **Protection**: Dried neem leaves at home and chemical fumigation in granaries."
                )
                replies = ["I understand grain storage principles.", "Let's practice!"]
            else:
                message = (
                    f"Hello {student_name}! 👋 Freshly harvested grains carry moisture. "
                    f"They must be thoroughly dried in the sun before storage to prevent fungi, bacteria, and insect pests from spoiling them in silos or granaries."
                )
                replies = ["Drying prevents fungal and insect rot.", "Let's practice!"]

        # Default Domain: Electricity & Chemical Effects (Chapter 11 and test suite baseline)
        elif any(kw in c_lower for kw in ["conduct", "liquid", "ion", "electrolyte", "electric", "circuit", "water"]):
            if strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Imagine a busy highway. In solid metal wires, electrons are like fast sports cars zooming in their lanes. "
                    f"In liquids, however, there are no loose sports cars! Instead, dissolved mineral salts split into charged 'ferry boats' called **ions**. "
                    f"These ferry boats carry the electric charge across the liquid pool.\n\n"
                    f"No ferry boats (distilled water)? No traffic flows!"
                )
                replies = ["The ions act like boats carrying charge.", "So pure water has no boats?"]
            elif strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"If you ever touch electrical switches with wet hands, it is dangerous. Why? "
                    f"Pure water doesn't conduct, but our tap water and the moisture on our skin has dissolved mineral salts. "
                    f"Those tiny dissolved salts turn regular water into a conductor!"
                )
                replies = ["Dissolved salts make tap water conductive.", "That's why distilled water is safe?"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **{concept_name}** step by step:\n\n"
                    f"1. **Dissolution**: Solid salts (like sodium chloride) enter the liquid.\n"
                    f"2. **Ionization**: The molecules break apart into positively and negatively charged ions.\n"
                    f"3. **Conduction**: When a battery voltage is applied, positive ions move toward the negative terminal and negative ions toward the positive terminal.\n"
                    f"4. **Current Flow**: This movement of ions constitutes the electric current in liquids!"
                )
                replies = ["Step 1: Dissolve, Step 2: Ions, Step 3: Flow.", "What if the salt doesn't dissolve?"]
            elif strategy_upper == "CORRECT_MISCONCEPTION":
                misc = prior_misconception or "electrons flow through pure water"
                message = (
                    f"Let's pause and clear up a common trap, {student_name}!\n\n"
                    f"You might have thought: *'{misc}'*. It is very natural to think that! "
                    f"In metal wires, electrons do all the moving. But in liquids, individual electrons cannot survive freely. "
                    f"Textbook Activity 11.2 proves that electric current only flows when dissolved salts produce **ions**.\n\n"
                    f"Let's remember: **Metals = Free electrons; Liquids = Dissolved ions**."
                )
                replies = ["Got it: Liquids use ions, not electrons.", "Can we retest this?"]
            elif strategy_upper == "SOCRATIC":
                message = (
                    f"{student_name}, let's think about **{concept_name}** together.\n\n"
                    f"When you dissolve table salt into water, what happens at the microscopic level? "
                    f"How might that allow electrical charge to move between submerged electrodes?"
                )
                replies = ["Salt splits into charged particles.", "I'd like a hint to think about this."]
            elif strategy_upper == "RECAP":
                message = (
                    f"**Quick Recap on {concept_name}**:\n"
                    f"• Pure distilled water is an insulator (poor conductor).\n"
                    f"• Adding salt, acid, or base produces charged ions.\n"
                    f"• These ions carry electric current through liquids."
                )
                replies = ["I understand the recap.", "Let's practice!"]
            else:
                resp = await self.generate_explanation(
                    concept_name=concept_name,
                    learning_objective=learning_objective,
                    curriculum_context=curriculum_context,
                    student_name=student_name,
                )
                resp.strategy = strategy_upper
                return resp
        else:
            # General fallback for any other curriculum concepts
            if strategy_upper == "REAL_WORLD_EXAMPLE":
                message = (
                    f"Let's look at an everyday example, {student_name}:\n\n"
                    f"When exploring **{concept_name}**, we observe this in our daily surroundings according to your textbook: "
                    f"'{learning_objective}'. Understanding these principles helps us see how science governs the world around us!"
                )
                replies = ["I see how it applies to everyday life.", "Let's practice!"]
            elif strategy_upper == "ANALOGY":
                message = (
                    f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                    f"Think of **{concept_name}** like a well-organized system where each part has a specific role: '{learning_objective}'."
                )
                replies = ["The analogy makes sense.", "Let's test this!"]
            elif strategy_upper == "STEP_BY_STEP":
                message = (
                    f"Let's break down **{concept_name}** step by step, {student_name}:\n\n"
                    f"1. **Core Principle**: {learning_objective}.\n"
                    f"2. **Textbook Evidence**: Observations and activities illustrate how this works.\n"
                    f"3. **Practical Application**: Farmers and scientists apply these rules for optimal results."
                )
                replies = ["Step by step is clear.", "Let's practice!"]
            else:
                resp = await self.generate_explanation(
                    concept_name=concept_name,
                    learning_objective=learning_objective,
                    curriculum_context=curriculum_context,
                    student_name=student_name,
                )
                resp.strategy = strategy_upper
                return resp

        return TutorResponse(
            message=message,
            pedagogical_intent="explain",
            strategy=strategy_upper,
            hint_level=0,
            suggested_quick_replies=replies,
        )

    async def evaluate_socratic_response(
        self,
        concept_name: str,
        socratic_question: str,
        student_response: str,
        curriculum_context: str,
    ) -> Dict[str, Any]:
        normalized = student_response.lower().strip()

        # Handle student emotional evasion, confusion, or boredom constructively
        evasion_phrases = ["don't know", "dont know", "bored", "tired", "too hard", "joke", "give up", "confused", "no idea", "boring"]
        if any(ep in normalized for ep in evasion_phrases):
            return {
                "understanding_confirmed": False,
                "feedback": "That's totally fine, Krish! Science can be challenging at first. Let's take a simpler angle with a friendly clue.",
                "suggested_replies": ["Give me a hint", "Show a quick example", "Take a short break"],
            }

        # Look for conceptual words
        keywords = [
            "ion", "salt", "conduct", "acid", "glow", "flow", "yes", "current", "dissolve", "heat", "oxygen", "fire",
            "seed", "float", "soil", "breathe", "root", "manure", "fertiliser", "fertilizer", "crop", "water",
            "plough", "loosening", "weeds", "dry", "tilling", "crumbs", "hollow", "drill", "drip", "sprinkler",
            "sink", "humus", "nutrients", "rhizobium", "silos", "paddy", "rabi", "kharif"
        ]
        matches = [kw for kw in keywords if kw in normalized]

        if len(matches) >= 2 or ("yes" in normalized and ("ion" in normalized or "acid" in normalized or "seed" in normalized or "soil" in normalized or "sink" in normalized)):
            return {
                "understanding_confirmed": True,
                "feedback": f"Excellent reasoning! You correctly recognized how the underlying mechanism functions. Ready to test this in practice?",
                "suggested_replies": ["Ready for practice question!", "Explain one more detail"],
            }
        elif len(matches) == 1:
            return {
                "understanding_confirmed": True,
                "feedback": f"Good intuition! You noticed {matches[0]}. Now let's see how it applies to a standard question.",
                "suggested_replies": ["Start practice question", "Show a hint"],
            }
        else:
            if any(w in (concept_name + " " + socratic_question).lower() for w in ["seed", "soil", "crop", "manure", "irrigation", "weed", "storage", "fertiliser"]):
                fallback = f"Good attempt, Krish! Let's think about the key observation in your textbook regarding {concept_name}. Let's examine a quick hint to guide you."
            else:
                fallback = "You're exploring interesting ideas, but remember: in liquids it's the dissolved ions that carry the current. Let's look at an example before practicing."
            return {
                "understanding_confirmed": False,
                "feedback": fallback,
                "suggested_replies": ["Show me a worked example", "Explain again"],
            }

    async def generate_misconception_remediation(
        self,
        concept_name: str,
        misconception_text: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        misc_lower = misconception_text.lower()
        if "seed" in misc_lower or "float" in misc_lower:
            message = (
                f"Let's clear this up together, {student_name}!\n\n"
                f"You noticed: *'{misconception_text}'*.\n\n"
                f"Here is what textbook Activity 1.1 reveals: When seeds are damaged by pests, they become hollow inside. "
                f"Being hollow, they become much lighter and float to the surface! Healthy seeds are dense and sink to the bottom.\n\n"
                f"Does that make sense why floating seeds are actually the damaged ones?"
            )
            replies = ["Yes, damaged seeds are hollow and float.", "Can we retest this now?"]
        elif "fertiliser" in misc_lower or "fertilizer" in misc_lower or "manure" in misc_lower:
            message = (
                f"Let's compare these two, {student_name}!\n\n"
                f"You noticed: *'{misconception_text}'*.\n\n"
                f"Chemical fertilisers provide quick mineral nutrients, but they add zero humus to the soil. "
                f"Over time, relying solely on synthetic fertilisers harms soil texture. In contrast, organic manure enriches the soil with humus and boosts water retention.\n\n"
                f"Does the difference between mineral nutrients and organic humus make sense now?"
            )
            replies = ["Yes, manure provides organic humus.", "Can we retest this now?"]
        elif "irrigation" in misc_lower or "sprinkler" in misc_lower or "drip" in misc_lower:
            message = (
                f"Let's look closely at modern irrigation, {student_name}!\n\n"
                f"You noticed: *'{misconception_text}'*.\n\n"
                f"Sprinklers are fantastic on uneven rolling land, but in water-scarce regions, drip irrigation is the ultimate conservation technique because water trickles drop-by-drop right at the roots with zero evaporation waste.\n\n"
                f"Does the drop-by-drop root delivery make sense now?"
            )
            replies = ["Yes, drip delivers water right to roots.", "Can we retest this now?"]
        elif "moisture" in misc_lower or "dry" in misc_lower or "storage" in misc_lower:
            message = (
                f"Let's check grain storage safety, {student_name}!\n\n"
                f"You noticed: *'{misconception_text}'*.\n\n"
                f"Freshly harvested grains contain significant moisture. Storing them wet encourages fungi and insect pests to attack, destroying their ability to germinate. Thorough sun-drying removes this moisture so grains stay safe for months.\n\n"
                f"Does the need for thorough sun-drying make sense now?"
            )
            replies = ["Yes, drying prevents fungal and pest rot.", "Can we retest this now?"]
        else:
            message = (
                f"Let's untangle this concept together, {student_name}!\n\n"
                f"You noticed: *'{misconception_text}'*.\n\n"
                f"Here is what the textbook experiment shows: when we place a tester in distilled water, the bulb does not glow. "
                f"The moment we add a pinch of common salt, the bulb glows brightly! "
                f"This proves that it is the **dissolved mineral ions**, not pure water itself, that allows electricity to flow.\n\n"
                f"Does the contrast between pure water and salt solution make sense now?"
            )
            replies = [
                "Yes, salt ions carry the current.",
                "Can we retest this now?",
            ]

        return TutorResponse(
            message=message,
            pedagogical_intent="remediation",
            strategy="CORRECT_MISCONCEPTION",
            hint_level=0,
            suggested_quick_replies=replies,
        )

    async def evaluate_explain_it_back(
        self,
        concept_name: str,
        student_explanation: str,
        key_points: Optional[List[str]] = None,
        curriculum_context: str = "",
        concept_explanation: str = "",
    ) -> Dict[str, Any]:
        if not key_points:
            c_lower = concept_name.lower()
            if "seed" in c_lower or "sow" in c_lower:
                key_points = [
                    "Healthy good seeds are dense and sink in water",
                    "Damaged seeds are hollowed out by insects and float on top",
                    "Activity 1.1 separates damaged seeds from healthy seeds"
                ]
            elif "manure" in c_lower or "fertilis" in c_lower:
                key_points = [
                    "Manure provides organic humus and improves soil texture",
                    "Chemical fertilisers add specific mineral nutrients without humus",
                    "Crop rotation replenishes nitrogen through Rhizobium bacteria"
                ]
            elif "soil" in c_lower or "plough" in c_lower or "till" in c_lower:
                key_points = [
                    "Tilling loosens soil so roots breathe easily",
                    "Loosened soil helps earthworms and friendly microbes grow",
                    "Levelling breaks big crumbs for uniform irrigation and sowing"
                ]
            elif "irrigation" in c_lower or "water" in c_lower:
                key_points = [
                    "Modern sprinkler system works on uneven sandy land",
                    "Drip system delivers water drop by drop directly to roots",
                    "Traditional methods like moat and rahat use human and animal power"
                ]
            elif "weed" in c_lower:
                key_points = [
                    "Weeds compete with crops for nutrients water and space",
                    "Removed with khurpi or sprayed with weedicide 2,4-D",
                    "Farmers must cover nose and mouth while spraying chemicals"
                ]
            elif "storage" in c_lower or "grain" in c_lower:
                key_points = [
                    "Fresh grains must be sun dried to reduce moisture",
                    "Moisture causes fungi bacteria and insect pests to attack",
                    "Silos and granaries provide large scale storage protection"
                ]
            elif any(w in c_lower for w in ["crop", "season", "kharif", "rabi", "agricultural"]):
                key_points = [
                    "Kharif crops like paddy and maize grow in the rainy monsoon season",
                    "Rabi crops like wheat and mustard are grown during winter",
                    "Agricultural practices follow a systematic 7-step sequence"
                ]
            else:
                key_points = [
                    "Pure distilled water lacks free ions and is a poor conductor",
                    "Dissolved mineral salts dissociate into positive and negative ions",
                    "These mobile ions carry electric current through the liquid",
                ]
        normalized = student_explanation.lower().strip()

        # Check for explicit ignorance or evasion phrases
        IGNORANCE_PATTERNS = [
            r"\b(don't|dont|do not)\s+know\b",
            r"\bno\s+idea\b",
            r"\bnot\s+sure\b",
            r"\bno\s+clue\b",
            r"\b(don't|dont|do not)\s+understand\b",
            r"\bhaven'?t\s+a\s+clue\b",
            r"\bcan'?t\s+explain\b",
            r"\bi\s+forget\b",
            r"\bforgot\b",
            r"\bblah\b",
        ]
        is_ignorant = any(re.search(pat, normalized) for pat in IGNORANCE_PATTERNS)
        word_count = len([w for w in re.split(r'\W+', normalized) if w])

        matched = []
        missing = []

        if is_ignorant or word_count < 4:
            matched = []
            missing = list(key_points)
            score = 0.0
            is_correct = False
            depth = "SURFACE"
            feedback = (
                "It seems you might be feeling unsure about this concept. "
                f"Take a moment to review the core idea: {missing[0]}. Would you like to review the step-by-step explanation together?"
            )
        else:
            stopwords = {"that", "this", "these", "those", "with", "from", "into", "have", "been", "poor", "good"}
            for kp in key_points:
                words = [w for w in re.split(r'\W+', kp.lower()) if len(w) > 3 and w not in stopwords]
                matched_words = [w for w in words if re.search(rf"\b{re.escape(w)}\b", normalized)]
                # Require at least 2 substantive keyword matches per key point (or 1 if kp only has 1)
                req_count = min(2, len(words))
                if len(matched_words) >= req_count:
                    matched.append(kp)
                else:
                    missing.append(kp)

            score = round(len(matched) / max(len(key_points), 1), 2)
            is_correct = score >= 0.60
            if is_correct:
                feedback = (
                    f"Fantastic synthesis in your own words, Krish! You explained {len(matched)} key points accurately. "
                    + (f"For perfection on exams, don't forget: {missing[0]}." if missing else "Your explanation shows solid conceptual mastery!")
                )
                depth = "DEEP" if score >= 0.80 else "SOLID"
            else:
                feedback = (
                    f"Good effort trying to explain it back! You're on the right track, but some detail is missing: "
                    f"remember to explain {', '.join(missing[:2])}."
                )
                depth = "SURFACE"

        return {
            "score": score,
            "accurate": is_correct,
            "depth": depth,
            "feedback": feedback,
            "criteria_scores": {
                "accuracy": score,
                "completeness": round(score * 0.9, 2),
                "clarity": 1.0 if is_correct else 0.5,
            },
            "suggested_replies": [
                "Review my learning gain",
                "Try another challenge",
                "Finish lesson",
            ],
        }

    async def generate_socratic_check(
        self,
        concept_name: str,
        curriculum_context: str,
        prior_explanation: str,
    ) -> TutorResponse:
        c_lower = (concept_name + " " + (curriculum_context[:200] if curriculum_context else "")).lower()
        if any(kw in c_lower for kw in ["crop", "season", "kharif", "rabi", "agricultural"]):
            message = (
                f"Before we jump into practice, think about this: If a farmer accidentally sowed paddy seeds in November "
                f"during the cold, dry winter season, what do you think would happen to the crop? Why?"
            )
            replies = [
                "Paddy wouldn't grow well because it needs heavy monsoon water.",
                "Paddy would grow fine anywhere.",
            ]
        elif any(kw in c_lower for kw in ["seed", "sow", "drill", "transplant"]):
            message = (
                f"Before we jump into practice, imagine putting a handful of wheat seeds into a bowl of water. "
                f"Why do you think damaged seeds float to the surface while healthy ones sink?"
            )
            replies = [
                "Pests make damaged seeds hollow and lighter, so they float.",
                "Healthy seeds are lighter and float.",
            ]
        elif any(kw in c_lower for kw in ["soil", "till", "plough", "crumb", "levell"]):
            message = (
                f"Before we jump into practice, why do you think a farmer ploughs the field to turn and loosen the soil "
                f"before sowing, instead of just dropping seeds on hard ground?"
            )
            replies = [
                "Loosening allows roots to breathe and penetrate deep.",
                "Hard ground is better for seeds.",
            ]
        elif any(kw in c_lower for kw in ["manure", "fertilis", "humus", "rhizobium"]):
            message = (
                f"Before we jump into practice, why do farmers prefer organic manure or crop rotation "
                f"over continuous, excessive use of chemical fertilisers?"
            )
            replies = [
                "Manure enriches humus and soil texture without chemical degradation.",
                "Chemical fertilisers add more humus than manure.",
            ]
        elif any(kw in c_lower for kw in ["irrigation", "water", "drip", "sprinkler"]):
            message = (
                f"Before we jump into practice, why is drip irrigation considered a boon in regions where water is scarce, "
                f"compared to sprinkler or surface canal irrigation?"
            )
            replies = [
                "Drip delivers water drop by drop right at the roots with zero waste.",
                "Sprinklers save more water than drip.",
            ]
        elif any(kw in c_lower for kw in ["weed", "khurpi", "weedicide", "2,4-d"]):
            message = (
                f"Before we jump into practice, why do farmers spend so much effort removing wild weeds from their fields?"
            )
            replies = [
                "Weeds compete with crops for nutrients, space, and sunlight.",
                "Weeds help crops grow faster.",
            ]
        elif any(kw in c_lower for kw in ["harvest", "thresh", "combine", "winnow"]):
            message = (
                f"Before we jump into practice, why do small farmers use winnowing with natural wind after harvesting their crop?"
            )
            replies = [
                "Wind blows lighter chaff away while dense grain falls down.",
                "Wind dries the harvested wheat.",
            ]
        elif any(kw in c_lower for kw in ["storage", "grain", "silo", "granar", "moisture"]):
            message = (
                f"Before we jump into practice, why must freshly harvested grains be dried in the sun before being packed into gunny bags or silos?"
            )
            replies = [
                "Moisture causes fungi, bacteria, and pests to spoil the grains.",
                "Drying makes grains heavier.",
            ]
        else:
            message = (
                f"Before we jump into practice, imagine you connect a battery, a small LED, and two metal pins dipped into lemon juice. "
                f"Do you think the LED will glow? Why or why not?"
            )
            replies = [
                "Yes, because lemon juice contains acid with free ions.",
                "No, lemon juice is an insulator."
            ]
        return TutorResponse(
            message=message,
            pedagogical_intent="socratic_check",
            hint_level=0,
            suggested_quick_replies=replies,
        )

    async def evaluate_student_answer(
        self,
        question_prompt: str,
        student_answer: str,
        expected_concepts: List[str],
        required_points: List[str],
        misconception_traps: Dict[str, str],
        curriculum_context: str,
    ) -> EvaluationResult:
        normalized_answer = student_answer.lower()

        # Check for known misconception traps with negation awareness
        detected_misconception = None
        for trap_keyword, misconception_desc in misconception_traps.items():
            kw = trap_keyword.lower()
            if kw in normalized_answer:
                # Check if keyword is explicitly negated by prefix or postfix negation
                prefix_neg = rf"\b(not|no|never|without|neither|nor|false|incorrect|don't|dont|doesn't|rather\s+than|instead\s+of)\s+(?:[\w\s]{{0,25}})?\b{re.escape(kw)}\b"
                postfix_neg = rf"\b{re.escape(kw)}\b\s+(?:[\w\s]{{0,15}})?(do\s+not|cannot|can't|don't|dont|does\s+not|doesn't|never|not\s+present)"
                if re.search(prefix_neg, normalized_answer) or re.search(postfix_neg, normalized_answer):
                    # Student explicitly refuted or excluded the misconception!
                    continue
                detected_misconception = misconception_desc
                break

        # Check missing concepts
        missing = []
        found_count = 0
        for concept in expected_concepts:
            # Check if keywords from expected concept appear in answer
            words = [w for w in re.split(r'\W+', concept.lower()) if len(w) > 3]
            matched = any(w in normalized_answer for w in words) if words else False
            if matched:
                found_count += 1
            else:
                missing.append(concept)

        total_expected = max(len(expected_concepts), 1)
        base_score = found_count / total_expected

        is_electricity = any(w in (question_prompt + " " + curriculum_context).lower() for w in ["ion", "conduct", "current", "electric", "circuit", "liquid"])

        if detected_misconception:
            score = max(0.2, base_score * 0.5)
            is_correct = False
            if is_electricity:
                extra = "In liquids, it is dissolved ions (charged particles), not free electrons or pure water molecules, that carry the current!"
            else:
                extra = f"Remember the core textbook principle: {detected_misconception}."
            feedback = (
                f"You're thinking along interesting lines, but notice a common misconception: {detected_misconception}. {extra}"
            )
            action = "retry_with_hint"
        elif base_score >= 0.7:
            score = min(1.0, round(base_score, 2))
            is_correct = True
            feedback = (
                f"Spot on! You clearly grasped the core mechanism. "
                + (f"To make your school exam answer 100% complete, also mention: {', '.join(missing)}." if missing else "Your explanation is complete and grounded in your textbook!")
            )
            action = "advance"
        else:
            score = max(0.3, round(base_score, 2))
            is_correct = False
            clue = "Recall what happens to salt crystals when they dissolve in water." if is_electricity else "Review the key observations and activities in your textbook."
            feedback = (
                f"Good start! You mentioned some relevant ideas, but your answer is missing key concepts: {', '.join(missing) if missing else 'the primary mechanism'}. {clue}"
            )
            action = "retry_with_hint"

        return EvaluationResult(
            score=score,
            is_correct=is_correct,
            missing_concepts=missing,
            misconception_detected=detected_misconception,
            detailed_feedback=feedback,
            recommended_action=action,
        )

    async def generate_hint(
        self,
        question_prompt: str,
        student_previous_attempts: List[str],
        hint_level: int,
        curriculum_context: str,
    ) -> TutorResponse:
        q_ctx = (question_prompt + " " + (curriculum_context[:300] if curriculum_context else "")).lower()

        if any(kw in q_ctx for kw in ["crop", "kharif", "rabi", "season", "agricultural"]):
            hints = {
                1: "Hint 1 (Clue): Think about the seasons: Kharif crops are sown during the monsoon rains (June to September).",
                2: "Hint 2 (Concept): Notice water and temperature requirements. Crops like paddy and maize require abundant water, while crops like wheat thrive in cool winters.",
                3: "Hint 3 (First Step): Separate monsoon crops (paddy, maize, soyabean, groundnut, cotton) from winter crops (wheat, gram, pea, mustard).",
                4: "Hint 4 (Guided Walkthrough): Check each option carefully to ensure every single crop listed was planted during the monsoon rainy season, not winter.",
                5: "Hint 5 (Full Solution): The Kharif crops are paddy, maize, soyabean, groundnut, and cotton. Wheat, gram, pea, and mustard are Rabi crops grown in winter.",
            }
        elif any(kw in q_ctx for kw in ["seed", "sow", "float", "drill"]):
            hints = {
                1: "Hint 1 (Clue): Remember Activity 1.1 with a bucket of water and wheat seeds.",
                2: "Hint 2 (Concept): What happens when insects or pests eat the inside of a seed?",
                3: "Hint 3 (First Step): Damaged seeds become hollow and lighter, while healthy seeds remain dense and solid.",
                4: "Hint 4 (Guided Walkthrough): Light hollow objects float on water, whereas heavy dense objects sink.",
                5: "Hint 5 (Full Solution): Damaged seeds are hollow and float on the surface, while healthy seeds sink to the bottom.",
            }
        elif any(kw in q_ctx for kw in ["soil", "till", "plough", "crumb", "levell"]):
            hints = {
                1: "Hint 1 (Clue): Consider why soil needs to be turned and loosened before seeds are planted.",
                2: "Hint 2 (Concept): Roots need air trapped in soil spaces to carry out cellular respiration.",
                3: "Hint 3 (First Step): Tilling breaks compact earth and brings nutrient-rich soil to the upper layer.",
                4: "Hint 4 (Guided Walkthrough): Loosened soil also helps earthworms and friendly microbes thrive, which add humus.",
                5: "Hint 5 (Full Solution): Tilling loosens the soil so roots can penetrate deep and breathe easily, while aiding earthworms.",
            }
        elif any(kw in q_ctx for kw in ["manure", "fertilis", "humus", "rhizobium"]):
            hints = {
                1: "Hint 1 (Clue): Compare natural decomposing organic matter with factory-synthesized chemical salts.",
                2: "Hint 2 (Concept): While chemical fertilisers provide specific NPK minerals, they add zero organic humus.",
                3: "Hint 3 (First Step): Manure improves soil physical texture and water-holding capacity.",
                4: "Hint 4 (Guided Walkthrough): Leguminous plants also fix nitrogen naturally using Rhizobium bacteria in their root nodules.",
                5: "Hint 5 (Full Solution): Organic manure adds natural humus, enhances soil texture, and prevents chemical soil degradation.",
            }
        elif any(kw in q_ctx for kw in ["irrigation", "drip", "sprinkler"]):
            hints = {
                1: "Hint 1 (Clue): Think about how water is applied—as artificial rain or directly drop-by-drop at the roots.",
                2: "Hint 2 (Concept): Sprinkler systems are ideal for uneven sandy soils where water cannot stand.",
                3: "Hint 3 (First Step): Drip irrigation provides water drop-by-drop right at the root zone with zero evaporation.",
                4: "Hint 4 (Guided Walkthrough): In regions with acute water shortages, drip irrigation eliminates all water waste.",
                5: "Hint 5 (Full Solution): Sprinklers suit uneven terrain; drip irrigation delivers water drop-by-drop at the roots without waste.",
            }
        elif any(kw in q_ctx for kw in ["weed", "khurpi", "weedicide", "2,4-d"]):
            hints = {
                1: "Hint 1 (Clue): Consider why unwanted wild plants harm crop plants.",
                2: "Hint 2 (Concept): Weeds compete for essential resources like sunlight, space, water, and soil nutrients.",
                3: "Hint 3 (First Step): Weeds are removed manually using a khurpi or sprayed with weedicides like 2,4-D.",
                4: "Hint 4 (Guided Walkthrough): Spraying weedicides must be done during vegetative growth before flowering, wearing protective masks.",
                5: "Hint 5 (Full Solution): Weeds compete for nutrients, water, and sunlight; they are cleared with a khurpi or 2,4-D weedicide.",
            }
        elif any(kw in q_ctx for kw in ["storage", "grain", "silo", "granar", "moisture"]):
            hints = {
                1: "Hint 1 (Clue): What is present in freshly harvested grains that encourages decay?",
                2: "Hint 2 (Concept): High moisture content promotes the growth of fungi, bacteria, and insect pests.",
                3: "Hint 3 (First Step): Grains must be thoroughly sun-dried to reduce moisture before storage.",
                4: "Hint 4 (Guided Walkthrough): Large-scale storage uses tall metal silos and granaries with chemical protection.",
                5: "Hint 5 (Full Solution): Fresh grains are sun-dried to eliminate moisture, preventing fungal rot and insect attacks.",
            }
        else:
            hints = {
                1: "Hint 1 (Clue): Consider whether pure water has any dissolved substances in it.",
                2: "Hint 2 (Concept): Current needs mobile electric charges to flow. In solids it's electrons, but what forms when acids or salts dissolve in water?",
                3: "Hint 3 (First Step): Start by classifying tap water versus distilled water: which one has dissolved minerals?",
                4: "Hint 4 (Guided Walkthrough): When salt ($NaCl$) dissolves in water, it splits into positive sodium ions ($Na^+$) and negative chloride ions ($Cl^-$). Now, what do these ions do when connected to a battery?",
                5: "Hint 5 (Full Solution): Distilled water has no dissolved salts and cannot conduct electricity. Tap water contains small amounts of dissolved mineral salts, providing free ions that conduct electric current. Thus, the circuit is completed and the bulb glows.",
            }

        clamped_level = min(max(hint_level, 1), 5)
        return TutorResponse(
            message=hints.get(clamped_level, hints[1]),
            pedagogical_intent="hint",
            hint_level=clamped_level,
            suggested_quick_replies=["I get it now! Let me answer.", "Could you give another clue?"]
        )

    async def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        import hashlib
        import math

        embeddings = []
        dim = 768
        for text in texts:
            # Deterministic pseudo-embedding based on text tokens and hashing
            vec = [0.0] * dim
            words = re.findall(r'\w+', text.lower())
            for i, word in enumerate(words):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                idx = h % dim
                vec[idx] += 1.0 / (1.0 + (i * 0.05))

            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [round(x / norm, 5) for x in vec]
            else:
                vec = [1.0 / math.sqrt(dim)] * dim
            embeddings.append(vec)
        return embeddings

    async def extract_concepts_and_objectives(
        self,
        topic_title: str,
        topic_text: str,
    ) -> Dict[str, Any]:
        # Deterministic extraction of key concepts from text
        sentences = [s.strip() for s in re.split(r'[.!?]+', topic_text) if len(s.strip()) > 20]
        concept_name = topic_title
        summary = sentences[0] if sentences else f"Core principles of {topic_title}."
        if len(sentences) > 1:
            summary += " " + sentences[1]

        return {
            "concepts": [
                {
                    "name": concept_name,
                    "summary": summary[:400],
                    "difficulty_tier": 2,
                }
            ],
            "learning_objectives": [
                {
                    "statement": f"Understand and explain the principles of {topic_title} as described in the textbook.",
                    "bloom_taxonomy_level": "Understanding",
                }
            ],
        }

    async def generate_candidate_questions(
        self,
        concept_name: str,
        concept_summary: str,
        source_text: str,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "question_type": "mcq",
                "cognitive_level": 2,
                "prompt": f"Based on the concept of '{concept_name}', what is the primary takeaway?",
                "explanation": f"According to the curriculum: {concept_summary[:200]}",
                "source_type": "generated_practice",
                "options": [
                    {"option_key": "A", "option_text": f"{concept_name} plays a key functional role in the process.", "is_correct": True, "feedback": "Correct! Directly grounded in the lesson."},
                    {"option_key": "B", "option_text": f"{concept_name} has no effect on the reaction.", "is_correct": False, "feedback": "Incorrect. The textbook demonstrates the opposite."},
                    {"option_key": "C", "option_text": "The process occurs only in absolute zero conditions.", "is_correct": False, "feedback": "Incorrect."},
                    {"option_key": "D", "option_text": "None of the above.", "is_correct": False, "feedback": "Incorrect."}
                ]
            },
            {
                "question_type": "rubric_explanation",
                "cognitive_level": 3,
                "prompt": f"In your own words, explain how '{concept_name}' operates, citing an example from your textbook.",
                "explanation": f"Students should state: {concept_summary[:200]}",
                "source_type": "generated_practice",
                "rubric": {
                    "expected_concepts": [concept_name, "scientific mechanism", "textbook observation"],
                    "required_points": [
                        f"Defines {concept_name} correctly.",
                        "Explains how conditions affect the phenomenon.",
                    ],
                    "misconception_traps": {
                        "spontaneous": f"Believing {concept_name} occurs without any energy transfer or interaction.",
                        "solids": f"Confusing the state of matter involved in {concept_name}."
                    },
                    "max_score": 1.0
                }
            }
        ]
