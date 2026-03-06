from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def run_seed(db: AsyncSession) -> None:
    seed_data = [
        ("Variable Initialization", "Variable used before being assigned a value", "State awareness"),
        ("Data Type Compatibility", "Operation attempted between incompatible types", "Type reasoning"),
        ("List Management", "Index access outside list bounds", "Boundary reasoning"),
        ("Dictionary Usage", "Key accessed that does not exist in dictionary", "Mapping reasoning"),
    ]
    
    for name, description, cognitive_skill in seed_data:
        stmt = text("""
            INSERT INTO concept_categories (name, description, cognitive_skill)
            VALUES (:name, :description, :cognitive_skill)
            ON CONFLICT (name) DO NOTHING
        """)
        await db.execute(stmt, {"name": name, "description": description, "cognitive_skill": cognitive_skill})
    
    await db.commit()


async def run_hint_seed(db: AsyncSession) -> None:
    hint_data = [
        ("Variable Initialization", 1, "Concept", "Check where variables are defined before use."),
        ("Variable Initialization", 2, "Directional", "Initialize the variable before the line that uses it."),
        ("Variable Initialization", 3, "Near-Solution", "You need to assign a value to the variable on a line before you reference it."),
        ("Data Type Compatibility", 1, "Concept", "Check the types of the values you are combining."),
        ("Data Type Compatibility", 2, "Directional", "Python cannot add a string and an integer directly — convert one first."),
        ("Data Type Compatibility", 3, "Near-Solution", "Use `str()` or `int()` to convert one value to match the other's type."),
        ("List Management", 1, "Concept", "Check the valid index range for your list before accessing it."),
        ("List Management", 2, "Directional", "List indices start at 0 — the last valid index is `len(list) - 1`."),
        ("List Management", 3, "Near-Solution", "Your list has fewer items than the index you are using. Check the list length first."),
        ("Dictionary Usage", 1, "Concept", "Check which keys actually exist in your dictionary before accessing them."),
        ("Dictionary Usage", 2, "Directional", "Use `in` to check if a key exists before accessing it, or use `.get()` with a default."),
        ("Dictionary Usage", 3, "Near-Solution", "The key you are accessing was never added to the dictionary. Print the dictionary to see its actual contents."),
    ]
    
    for concept_category, tier, tier_name, hint_text in hint_data:
        stmt = text("""
            INSERT INTO hint_sequences (concept_category, tier, tier_name, hint_text)
            VALUES (:concept_category, :tier, :tier_name, :hint_text)
            ON CONFLICT (concept_category, tier) DO NOTHING
        """)
        await db.execute(stmt, {
            "concept_category": concept_category,
            "tier": tier,
            "tier_name": tier_name,
            "hint_text": hint_text
        })
    
    await db.commit()
