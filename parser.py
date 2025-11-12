import re
import difflib

# Lista dos exercícios conhecidos
EXERCISES = [
    "supino",
    "remada baixa fechada",
    "remada baixa aberta",
    "serrote",
    "triceps corda",
    "triceps barra",
    "ombro anterior",
    "ombro lateral",
    "ombro posterior",
]

def fuzzy_match_exercise(text):
    """Tenta identificar o nome do exercício com base em similaridade."""
    text = re.sub(r"[^\w\s]", "", text.lower()).strip()  # remove pontuação
    match = difflib.get_close_matches(text, EXERCISES, n=1, cutoff=0.75)
    if match:
        return match[0]
    return None

# Dicionário de números por extenso (mesmo de antes)
NUM_WORDS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100
}

def word_to_number(word):
    word = word.lower()
    if word in NUM_WORDS:
        return NUM_WORDS[word]
    parts = word.split(" e ")
    total = 0
    for p in parts:
        if p in NUM_WORDS:
            total += NUM_WORDS[p]
        else:
            return None
    return total if total > 0 else None

def normalize_numbers(text):
    tokens = text.lower().split()
    normalized = []
    skip_next = False
    for i, t in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if t in NUM_WORDS:
            if i + 2 < len(tokens) and tokens[i + 1] == "e" and tokens[i + 2] in NUM_WORDS:
                composed = f"{t} e {tokens[i + 2]}"
                num = word_to_number(composed)
                if num:
                    normalized.append(str(num))
                    skip_next = True
                    continue
            normalized.append(str(NUM_WORDS[t]))
        else:
            normalized.append(t)
    return " ".join(normalized)

def parse_command(text: str):
    text = text.lower().strip()
    text = normalize_numbers(text)

    # início/final de exercício
    if text.startswith("início"):
        name = text.replace("início", "").strip()
        exercise = fuzzy_match_exercise(name)
        return {"action": "start", "exercise": exercise or name}

    if text.startswith("final"):
        name = text.replace("final", "").strip()
        exercise = fuzzy_match_exercise(name)
        return {"action": "end", "exercise": exercise or name}

    # padrão de carga e repetições
    match_weight = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:kilo|quilo|kg|quilos|kilos)", text)
    match_reps = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:rep(?:etições|s)?|repeticao|repeticoes)", text)

    weight = float(match_weight.group(1).replace(",", ".")) if match_weight else None
    reps = int(float(match_reps.group(1).replace(",", "."))) if match_reps else None

    if weight is not None and reps is not None:
        return {"action": "set", "weight": weight, "reps": reps}

    return {"action": "unknown", "raw": text}
