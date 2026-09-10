"""
Pre-built example prompts library for quick 3D model generation.

Provides common engineering and science topics with suggested prompts.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExamplePrompt:
    """An example prompt for 3D model generation."""
    category: str
    title: str
    prompt: str
    description: str
    difficulty: str  # beginner, intermediate, advanced


class ExamplePromptLibrary:
    """Library of pre-built example prompts."""

    EXAMPLES = [
        # Electrical Engineering
        ExamplePrompt(
            category="Electrical Engineering",
            title="Transformer",
            prompt="Create a detailed electrical transformer showing the primary winding, secondary winding, iron core, and magnetic field flow between coils",
            description="Visualize how transformers transfer electrical energy",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Electrical Engineering",
            title="Electric Motor",
            prompt="Build a 3D electric motor with stator, rotor, coil, magnetic field, and rotor axis. Show how the magnetic field rotates the coil",
            description="See how motors convert electricity to mechanical motion",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Electrical Engineering",
            title="AC Generator",
            prompt="Design an AC generator with rotating coil in magnetic field, showing how rotation produces alternating current",
            description="Visualize AC electricity generation",
            difficulty="intermediate",
        ),
        # Mechanical Engineering
        ExamplePrompt(
            category="Mechanical Engineering",
            title="Hydraulic Brake System",
            prompt="Create a hydraulic braking system showing brake pedal, master cylinder, brake fluid lines, caliper, and brake pads pressing on disc",
            description="Understand how hydraulic brakes work",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Mechanical Engineering",
            title="Four-Stroke Engine",
            prompt="Build a four-stroke internal combustion engine showing cylinder, piston, connecting rod, crankshaft, intake valve, exhaust valve, and spark plug",
            description="Visualize all four strokes: intake, compression, combustion, exhaust",
            difficulty="advanced",
        ),
        ExamplePrompt(
            category="Mechanical Engineering",
            title="Gear System",
            prompt="Design a gear train showing multiple meshing gears with different sizes, demonstrating torque multiplication and speed reduction",
            description="See how gears transfer and modify rotational force",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Mechanical Engineering",
            title="Pulley System",
            prompt="Create a pulley system with multiple pulleys, rope, and load, showing mechanical advantage",
            description="Understand pulley mechanics and force multiplication",
            difficulty="beginner",
        ),
        # Biology
        ExamplePrompt(
            category="Biology",
            title="DNA Double Helix",
            prompt="Build a DNA double helix showing the two strands, base pairs (A-T and G-C), sugar-phosphate backbone, and hydrogen bonds",
            description="Visualize the structure of DNA",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Biology",
            title="Human Heart",
            prompt="Design a detailed human heart showing four chambers (left/right atria and ventricles), valves, major blood vessels (aorta, pulmonary artery, vena cava, pulmonary vein)",
            description="Understand heart anatomy and blood flow",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Biology",
            title="Mitochondria",
            prompt="Create a mitochondrion showing outer membrane, inner membrane, cristae, matrix, and ribosome, depicting the powerhouse of the cell",
            description="Visualize cellular energy production",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Biology",
            title="Photosynthesis Process",
            prompt="Build a 3D diagram of photosynthesis showing sunlight, chlorophyll, water molecules, CO2 molecules, glucose production, and oxygen release",
            description="See how plants convert light to energy",
            difficulty="advanced",
        ),
        # Physics
        ExamplePrompt(
            category="Physics",
            title="Atom Structure",
            prompt="Design an atom showing nucleus with protons and neutrons, electron orbitals, and electron positions",
            description="Visualize atomic structure",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Physics",
            title="Water Cycle",
            prompt="Create a water cycle diagram showing evaporation from water body, condensation in clouds, precipitation, and runoff back to water body",
            description="Understand Earth's water cycle",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Physics",
            title="Light Refraction",
            prompt="Build a light refraction model showing light ray entering water, bending at interface, and angle of incidence vs angle of refraction",
            description="See how light behaves in different mediums",
            difficulty="intermediate",
        ),
        # Civil Engineering
        ExamplePrompt(
            category="Civil Engineering",
            title="Truss Bridge",
            prompt="Design a truss bridge structure showing triangular elements, support beams, compression and tension forces",
            description="Understand structural engineering",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Civil Engineering",
            title="Building Foundation",
            prompt="Create a building foundation system showing footings, concrete base, load distribution, soil layers",
            description="Visualize foundation engineering",
            difficulty="intermediate",
        ),
        # Chemistry
        ExamplePrompt(
            category="Chemistry",
            title="Water Molecule",
            prompt="Build a water molecule (H2O) showing oxygen atom and two hydrogen atoms with covalent bonds and electron sharing",
            description="Understand molecular structure",
            difficulty="beginner",
        ),
        ExamplePrompt(
            category="Chemistry",
            title="Chemical Reaction",
            prompt="Design a chemical reaction model showing reactants, transition state, and products with energy levels",
            description="Visualize how chemical reactions work",
            difficulty="intermediate",
        ),
        # Aerospace & Space
        ExamplePrompt(
            category="Aerospace",
            title="Rocket Engine",
            prompt="Create a liquid propellant rocket engine with turbopumps, injector dome, combustion chamber, throat, and supersonic bell expansion nozzle",
            description="See how rocket engines produce supersonic thrust",
            difficulty="advanced",
        ),
        ExamplePrompt(
            category="Aerospace",
            title="Turbofan Jet Engine",
            prompt="Build a turbofan aircraft jet engine showing titanium fan, low and high pressure compressors, annular combustor, turbines, and exhaust nozzle",
            description="Understand jet propulsion thermodynamics",
            difficulty="advanced",
        ),
        ExamplePrompt(
            category="Aerospace",
            title="Quadcopter Drone",
            prompt="Design a quadcopter drone with carbon fiber frame, flight controller MCU, LiPo battery, 4 brushless motors and CW/CCW propellers",
            description="Learn drone aerodynamics and flight dynamics",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Aerospace",
            title="Communications Satellite",
            prompt="Build a communications satellite with central bus chassis, deployable solar panel wings, parabolic high-gain dish, and ion thruster",
            description="Visualize space communications hardware",
            difficulty="intermediate",
        ),
        ExamplePrompt(
            category="Aerospace",
            title="Solar System",
            prompt="Design the solar system with Sun, Mercury, Venus, Earth, Mars, and Jupiter showing planetary orbits and relative distances",
            description="Explore planetary orbital mechanics",
            difficulty="beginner",
        ),
        # Energy & Power
        ExamplePrompt(
            category="Energy & Power",
            title="Nuclear Reactor (PWR)",
            prompt="Create a pressurized water nuclear reactor with reactor vessel, uranium fuel assembly, control rods, and steam generator heat exchanger",
            description="Understand controlled nuclear fission power",
            difficulty="advanced",
        ),
        ExamplePrompt(
            category="Energy & Power",
            title="Lithium-Ion Battery Cell",
            prompt="Build a lithium-ion battery cell with copper and aluminum current collectors, graphite anode, porous polymer separator, and metal oxide cathode",
            description="Visualize electrochemical energy storage and Li+ ion transport",
            difficulty="intermediate",
        ),
    ]

    @classmethod
    def get_all(cls) -> list[ExamplePrompt]:
        """Get all available examples."""
        return cls.EXAMPLES

    @classmethod
    def get_by_category(cls, category: str) -> list[ExamplePrompt]:
        """Get examples by category."""
        return [e for e in cls.EXAMPLES if e.category.lower() == category.lower()]

    @classmethod
    def get_categories(cls) -> list[str]:
        """Get all unique categories."""
        return sorted(set(e.category for e in cls.EXAMPLES))

    @classmethod
    def get_by_difficulty(cls, difficulty: str) -> list[ExamplePrompt]:
        """Get examples by difficulty level."""
        return [e for e in cls.EXAMPLES if e.difficulty.lower() == difficulty.lower()]

    @classmethod
    def search(cls, keyword: str) -> list[ExamplePrompt]:
        """Search examples by keyword."""
        keyword = keyword.lower()
        return [
            e
            for e in cls.EXAMPLES
            if keyword in e.title.lower()
            or keyword in e.description.lower()
            or keyword in e.prompt.lower()
        ]

    @classmethod
    def get_random(cls, count: int = 1):
        """Get random examples."""
        import random
        if count == 1:
            return random.choice(cls.EXAMPLES) if cls.EXAMPLES else None
        return random.sample(cls.EXAMPLES, min(count, len(cls.EXAMPLES)))

    @classmethod
    def to_dict(cls) -> dict:
        """Export as dictionary for UI rendering."""
        categories = {}
        for example in cls.EXAMPLES:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(
                {
                    "title": example.title,
                    "prompt": example.prompt,
                    "description": example.description,
                    "difficulty": example.difficulty,
                }
            )
        return categories

