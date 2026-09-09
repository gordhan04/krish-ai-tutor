import io
from typing import List


def create_simple_pdf(pages_text: List[List[str]]) -> bytes:
    """
    Constructs a valid, multi-page PDF with genuine text streams in pure Python.
    No external C libraries or heavy dependencies needed.
    pages_text: List of pages, where each page is a list of lines.
    """
    objects = []
    
    # 1 0 obj: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    
    # We will reserve index 2 for Pages object, which needs kid references
    num_pages = len(pages_text)
    page_obj_ids = [3 + i * 2 for i in range(num_pages)]
    font_obj_id = 3 + num_pages * 2
    
    # 2 0 obj: Pages
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    pages_dict = f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode()
    objects.append(pages_dict)
    
    # Generate Page and Content stream objects
    for i, lines in enumerate(pages_text):
        content_obj_id = page_obj_ids[i] + 1
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        ).encode()
        objects.append(page_dict)
        
        # Build text stream
        stream_parts = [b"BT\n/F1 12 Tf\n50 740 Td\n16 TL\n"]
        for line in lines:
            # Escape PDF string literals
            escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_parts.append(f"({escaped_line}) Tj\nT*\n".encode("latin-1", errors="replace"))
        stream_parts.append(b"ET\n")
        
        stream_data = b"".join(stream_parts)
        stream_obj = f"<< /Length {len(stream_data)} >>\nstream\n".encode() + stream_data + b"endstream"
        objects.append(stream_obj)
        
    # Font object
    font_dict = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects.append(font_dict)
    
    # Build cross reference table and write out
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    
    offsets = []
    for i, obj_bytes in enumerate(objects):
        offsets.append(out.tell())
        out.write(f"{i + 1} 0 obj\n".encode())
        out.write(obj_bytes)
        out.write(b"\nendobj\n")
        
    xref_offset = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
        
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    
    return out.getvalue()


def generate_class_8_combustion_textbook_pdf() -> bytes:
    """
    Generates a realistic NCERT Class 8 Science Chapter 4 (Combustion and Flame) PDF.
    """
    page1 = [
        "Chapter 4: Combustion and Flame",
        "We use different kinds of fuel for various purposes at home, in industry and for running automobiles.",
        "Can you name a few fuels used in our homes? Name a few fuels used in trade and industry.",
        "What fuels are used for running automobiles? Your list will contain cowdung, wood, coal, charcoal, petrol, diesel, CNG.",
        "You are familiar with the burning of a candle. What is the difference between the burning of a candle and the burning of a fuel like coal?",
        "Perhaps you were able to guess right: candle burns with a flame whereas coal does not.",
        "",
        "4.1 WHAT IS COMBUSTION?",
        "Recall the activity of burning of magnesium ribbon performed in Class VII. We learnt that magnesium burns to form magnesium oxide and produces heat and light.",
        "We can perform a similar activity with a piece of charcoal. Hold the piece with a pair of tongs and bring it near the flame of a candle.",
        "What do you observe? We find that charcoal burns in air. We know that coal, too, burns in air producing carbon dioxide, heat and light.",
        "A chemical process in which a substance reacts with oxygen to give off heat is called combustion.",
        "The substance that undergoes combustion is said to be combustible. It is also called a fuel.",
        "The fuel may be solid, liquid or gas. Sometimes, light is also given off during combustion, either as a flame or as a glow.",
        "",
        "Activity 4.1: Combustible and non-combustible substances",
        "Collect some materials like straw, matchsticks, kerosene oil, paper, iron nails, stone pieces, glass.",
        "Under the supervision of your teacher, try to burn each of these materials one by one.",
        "If combustion takes place mark the material combustible, otherwise mark it non-combustible.",
    ]
    
    page2 = [
        "4.2 HOW DO WE CONTROL FIRE?",
        "You must have seen or heard of fire breaking out in homes, shops and factories.",
        "If you have seen such an accident, write a short description in your notebook. Also share the experience with your classmates.",
        "Does your city have a fire brigade station? When a fire brigade arrives, what does it do?",
        "It pours water on the fire. Water cools the combustible material so that its temperature is brought below its ignition temperature.",
        "The lowest temperature at which a substance catches fire is called its ignition temperature.",
        "This prevents the fire from spreading. Water vapours also surround the combustible material, helping in cutting off the supply of air. So, the fire is extinguished.",
        "You have learnt that there are three essential requirements for producing fire. These are: fuel, air (to supply oxygen) and heat (to raise temperature).",
        "The fire can be controlled by removing one or more of these requirements.",
        "The most common fire extinguisher is water. But water works only when things like wood and paper are on fire.",
        "If electrical equipment is on fire, water may conduct electricity and harm those trying to douse the fire.",
        "For fires involving electrical equipment and inflammable materials like petrol, carbon dioxide is the best extinguisher.",
        "CO2, being heavier than oxygen, covers the fire like a blanket. Since the contact between the fuel and oxygen is cut off, the fire is controlled.",
    ]
    
    page3 = [
        "4.3 TYPES OF COMBUSTION",
        "Bring a burning matchstick or a gas lighter near a gas stove in the kitchen. Turn on the knob of the gas stove. What do you observe?",
        "We find that the gas burns rapidly and produces heat and light. Such combustion is known as rapid combustion.",
        "There are substances like phosphorus which burn in air at room temperature.",
        "The type of combustion in which a material suddenly bursts into flames, without the application of any apparent cause, is called spontaneous combustion.",
        "Spontaneous combustion of coal dust has resulted in many disastrous fires in coal mines.",
        "Spontaneous forest fires are sometimes due to the heat of the sun or due to lightning strike.",
        "We generally have fireworks on festival days. When a cracker is ignited, a sudden reaction takes place with the evolution of heat, light and sound.",
        "A large amount of gas formed in the reaction is liberated. Such a reaction is called explosion.",
        "",
        "4.4 FLAME",
        "Observe an LPG flame. Can you tell the colour of the flame? What is the colour of a candle flame?",
        "Recall your experience of burning a magnesium ribbon in Class VII. The substances which vaporise during burning, give flames.",
        "For example, kerosene oil and molten wax rise through the wick and are vaporised during burning and form flames.",
        "Charcoal, on the other hand, does not vaporise and so does not produce a flame.",
        "A flame has three zones: innermost dark zone, middle yellow luminous zone, and outermost non-luminous blue zone (the hottest part).",
    ]
    
    page4 = [
        "4.5 WHAT IS A FUEL AND FUEL EFFICIENCY?",
        "Recall that the sources of heat energy for domestic and industrial purposes are mainly wood, charcoal, petrol, kerosene.",
        "These substances are called fuels. A good fuel is one which is readily available, cheap, burns easily in air at a moderate rate.",
        "It produces a large amount of heat. It does not leave behind any undesirable substances.",
        "There is probably no fuel that could be considered as an ideal fuel. We should look for a fuel which fulfills most requirements.",
        "The amount of heat energy produced on complete combustion of 1 kg of a fuel is called its calorific value.",
        "The calorific value of a fuel is expressed in a unit called kilojoule per kg (kJ/kg).",
        "",
        "Burning of fuels leads to harmful products:",
        "1. Carbon fuels like wood, coal, petroleum release unburnt carbon particles. These fine particles are dangerous pollutants causing respiratory diseases, such as asthma.",
        "2. Incomplete combustion of these fuels gives carbon monoxide gas. It is a very poisonous gas. It is dangerous to burn coal in a closed room.",
        "3. Combustion of most fuels releases carbon dioxide in the environment. Increased concentration of carbon dioxide in the air is believed to cause global warming.",
        "4. Burning of coal and diesel releases sulphur dioxide gas. It is an extremely suffocating and corrosive gas. Oxides of sulphur and nitrogen dissolve in rain water to form acid rain.",
        "",
        "4.6 EXERCISES",
        "1. List conditions under which combustion can take place.",
        "2. Fill in the blanks: (a) A chemical process in which a substance reacts with oxygen to give off heat is called combustion. (b) The lowest temperature at which a substance catches fire is called ignition temperature.",
        "3. Explain how the use of CNG in automobiles has reduced pollution in our cities.",
        "4. Compare LPG and wood as fuels.",
    ]
    
    return create_simple_pdf([page1, page2, page3, page4])
