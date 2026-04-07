import spacy
from nltk.corpus import wordnet as wn

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Define character-like human nouns
character_words = {
    "man", "woman", "guy", "girl", "boy", "kid", "dude", "mate",
    "child", "person", "gentleman", "lady"
}

# Manual override for known physical objects
manual_thing_words = {
    "money", "camera", "gun", "bomb", "phone", "bag", "glass", "bottle", "lab", "lot"
}

# ✅ Add this missing function
def is_physical_object(word):
    """Use WordNet to determine if a noun is a physical object"""
    synsets = wn.synsets(word, pos=wn.NOUN)
    for syn in synsets:
        if 'artifact' in syn.lexname() or 'object' in syn.lexname() or 'noun.artifact' in syn.lexname():
            return True
    return False

# Main categorization function
def categorize_nouns_single_line(text):
    doc = nlp(text)
    people = set()
    places = set()
    characters = set()
    things = set()
    animals = set()
    others = set()

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            people.add(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            places.add(ent.text)

    for token in doc:
        word = token.text.lower()
        if token.pos_ == "NOUN" and token.text not in people and token.text not in places:
            if word in character_words:
                characters.add(token.text)
            elif wn.synsets(word, pos=wn.NOUN) and any("animal" in syn.lexname() for syn in wn.synsets(word, pos=wn.NOUN)):
                animals.add(token.text)
            elif word in manual_thing_words or is_physical_object(word):
                things.add(token.text)
            else:
                others.add(token.text)



    parts = []
    if people:
        parts.append("People - " + ", ".join(sorted(people)))
    if places:
        parts.append("Places - " + ", ".join(sorted(places)))
    if characters:
        parts.append("Characters - " + ", ".join(sorted(characters)))
    if things:
        parts.append("Things - " + ", ".join(sorted(things)))
    if animals:
        parts.append("Animals - " + ", ".join(sorted(animals)))
    if others:
        parts.append("Others - " + ", ".join(sorted(others)))

    return ", ".join(parts)
